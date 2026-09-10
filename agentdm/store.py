"""The on-disk store. One canonical store per project, keyed on the git common dir.

State authority lives in agentdm's own records (incarnations/, aliases/, bindings/, offers/, acks/,
claims/). Maildir is storage only: its folders and flags carry no application state.
"""
import email, email.policy, email.utils, hashlib, hmac, json, mailbox, os, re, secrets, subprocess, time, uuid
from email.message import EmailMessage

UNFOLDED = email.policy.default.clone(max_line_length=None)
ALIAS_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
HUMAN = "human"
# Declared intent of a message. Request kinds expect an explicit outcome (accepted|declined) from the
# recipient; acknowledging one is not accepting it, and accepting is not proof the work was done.
KINDS = ("note", "question", "handoff", "review-request", "claim", "ack")
REQUEST_KINDS = ("question", "handoff", "review-request", "claim")
OUTCOMES = ("accepted", "declined")


class AgentdmError(Exception): ...
class Superseded(AgentdmError): ...
class NotRegistered(AgentdmError): ...
class AliasHeld(AgentdmError): ...
class BadToken(AgentdmError): ...
class NotHolder(AgentdmError): ...


def _git(project_dir, *args):
    r = subprocess.run(["git", "-C", project_dir, *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise AgentdmError(f"git {' '.join(args)} failed in {project_dir}: {r.stderr.strip()}")
    return r.stdout.strip()


def git_common_dir(project_dir):
    p = _git(project_dir, "rev-parse", "--git-common-dir")
    if not os.path.isabs(p):
        p = os.path.join(project_dir, p)
    return os.path.realpath(p)


def git_root(project_dir):
    return os.path.realpath(_git(project_dir, "rev-parse", "--show-toplevel"))


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _write_json(path, obj):
    tmp = f"{path}.tmp.{os.getpid()}.{uuid.uuid4().hex[:6]}"
    with open(tmp, "w") as f:
        json.dump(obj, f, sort_keys=True, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _read_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def _mid_key(message_id):
    return re.sub(r"[^A-Za-z0-9._-]", "_", message_id.strip("<>"))


def find_store(project_dir, state_home=None):
    """The store for this project if it already exists; None otherwise. Creates nothing."""
    try:
        common = git_common_dir(project_dir)
    except AgentdmError:
        return None
    key = hashlib.sha256(common.encode()).hexdigest()[:16]
    home = state_home or os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    path = os.path.join(home, "agentdm", key)
    if not os.path.isdir(path):
        return None
    return Store(path, key, common, git_root(project_dir))


def resolve_store(project_dir, state_home=None):
    common = git_common_dir(project_dir)
    key = hashlib.sha256(common.encode()).hexdigest()[:16]
    home = state_home or os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    path = os.path.join(home, "agentdm", key)
    return Store(path, key, common, git_root(project_dir))


class Store:
    DIRS = ("presence", "incarnations", "aliases", "bindings", "bindings/host", "mail", "offers", "acks",
            "outcomes", "claims")

    def __init__(self, path, project_key, common_dir, root):
        self.path, self.project_key, self.common_dir, self.root = path, project_key, common_dir, root
        for d in self.DIRS:
            os.makedirs(os.path.join(path, d), mode=0o700, exist_ok=True)
        pj = os.path.join(path, "project.json")
        if not os.path.exists(pj):
            _write_json(pj, {"git_common_dir": common_dir, "git_root": root, "created_at": _now()})

    # ---------------------------------------------------------------- paths
    def _p(self, *parts):
        return os.path.join(self.path, *parts)

    def _presence_path(self, inc):
        return self._p("presence", inc)

    # ---------------------------------------------------------------- identity
    def _alias_current(self, alias):
        rec = _read_json(self._p("aliases", f"{alias}.json"))
        return rec["incarnation_id"] if rec else None

    def incarnation(self, inc):
        rec = _read_json(self._p("incarnations", f"{inc}.json"))
        if rec is None:
            raise NotRegistered(inc)
        return rec

    def presence_alive(self, inc):
        from .presence import is_held
        return is_held(self._presence_path(inc))

    def register(self, alias, *, family, pid, ppid, ppid_start=None, session_id=None,
                 session_source=None, availability="accepting", reclaim_token=None,
                 worktree=None, model=None, provisional=False):
        if alias == HUMAN or not ALIAS_RE.match(alias):
            raise AgentdmError(f"bad alias: {alias!r}")
        current = self._alias_current(alias)
        reclaimed_from = None
        if current:
            cur = self.incarnation(current)
            if self.presence_alive(current):
                if reclaim_token is None:
                    raise AliasHeld(f"alias {alias!r} is held by a live incarnation {current}")
                if not hmac.compare_digest(_sha(reclaim_token), cur["token_hash"]):
                    raise BadToken("reclaim token does not match")
            reclaimed_from = current
        inc = uuid.uuid4().hex
        token = secrets.token_urlsafe(24)
        rec = {"incarnation_id": inc, "alias": alias, "family": family, "pid": pid, "ppid": ppid,
               "ppid_start": ppid_start, "worktree": worktree, "model": model,
               "availability": availability, "registered_at": _now(), "token_hash": _sha(token),
               "superseded_by": None, "reclaimed_from": reclaimed_from, "provisional": bool(provisional)}
        _write_json(self._p("incarnations", f"{inc}.json"), rec)
        if reclaimed_from:
            old = self.incarnation(reclaimed_from)
            old["superseded_by"], old["superseded_at"] = inc, _now()
            _write_json(self._p("incarnations", f"{reclaimed_from}.json"), old)
        _write_json(self._p("aliases", f"{alias}.json"), {"incarnation_id": inc, "since": _now()})
        if session_id:
            self.bind_session(inc, session_id, session_source or "declared")
        return {"incarnation_id": inc, "alias": alias, "reclaim_token": token,
                "project_key": self.project_key, "store": self.path, "git_root": self.root,
                "reclaimed_from": reclaimed_from}

    def confirm(self, inc):
        """An explicit registration or a human naming turns a spawn-time provisional row into a real one."""
        rec = self.incarnation(inc)
        rec["provisional"] = False
        _write_json(self._p("incarnations", f"{inc}.json"), rec)

    def rename_alias(self, old_alias, new_alias, by=HUMAN):
        """Human authority over naming. Moves the mailbox; the server re-reads its alias on every call."""
        if new_alias == HUMAN or not ALIAS_RE.match(new_alias):
            raise AgentdmError(f"bad alias: {new_alias!r}")
        inc = self._alias_current(old_alias)
        if inc is None or (_read_json(self._p("aliases", f"{old_alias}.json")) or {}).get("retired"):
            raise AgentdmError(f"no live alias {old_alias!r}")
        if os.path.exists(self._p("aliases", f"{new_alias}.json")):
            raise AgentdmError(f"alias {new_alias!r} already exists")
        rec = self.incarnation(inc)
        rec["alias"], rec["provisional"], rec["renamed_by"], rec["renamed_at"] = new_alias, False, by, _now()
        _write_json(self._p("incarnations", f"{inc}.json"), rec)
        _write_json(self._p("aliases", f"{new_alias}.json"), {"incarnation_id": inc, "since": _now(), "renamed_from": old_alias})
        old_mail, new_mail = self._p("mail", old_alias), self._p("mail", new_alias)
        if os.path.isdir(old_mail) and not os.path.exists(new_mail):
            os.rename(old_mail, new_mail)
        a = _read_json(self._p("aliases", f"{old_alias}.json")) or {}
        a["retired"], a["renamed_to"] = True, new_alias
        _write_json(self._p("aliases", f"{old_alias}.json"), a)
        return inc

    def forget(self, alias):
        """Human authority: drop an OFFLINE alias from the roster. Refuses while its incarnation is alive."""
        inc = self._alias_current(alias)
        if inc is None:
            raise AgentdmError(f"no such alias {alias!r}")
        if self.presence_alive(inc):
            raise AgentdmError(f"{alias!r} is alive; it cannot be forgotten")
        for path in (self._p("aliases", f"{alias}.json"), self._p("presence", inc), self._p("bindings", f"{inc}.json")):
            try:
                os.remove(path)
            except FileNotFoundError:
                pass
        return inc

    def gc(self):
        """Remove roster litter: retired aliases and offline provisional rows. Incarnation history and claims stay."""
        removed = []
        for fn in sorted(os.listdir(self._p("aliases"))):
            alias, a = fn[:-5], _read_json(self._p("aliases", fn)) or {}
            inc = a.get("incarnation_id")
            rec = _read_json(self._p("incarnations", f"{inc}.json")) if inc else None
            litter = a.get("retired") or (rec and rec.get("provisional") and not self.presence_alive(inc))
            if not litter:
                continue
            for path in (self._p("aliases", fn), self._p("presence", inc or ""), self._p("bindings", f"{inc}.json")):
                try:
                    os.remove(path)
                except (FileNotFoundError, IsADirectoryError):
                    pass
            removed.append(alias)
        return {"aliases": removed}

    def retire(self, old_inc, new_inc):
        """The same server re-registered under a new alias: the old incarnation is superseded, its alias retired."""
        old = self.incarnation(old_inc)
        old["superseded_by"], old["superseded_at"] = new_inc, _now()
        _write_json(self._p("incarnations", f"{old_inc}.json"), old)
        a = _read_json(self._p("aliases", f"{old['alias']}.json")) or {}
        a["retired"] = True
        _write_json(self._p("aliases", f"{old['alias']}.json"), a)

    def check_incarnation(self, inc):
        rec = self.incarnation(inc)
        if rec.get("superseded_by") or self._alias_current(rec["alias"]) != inc:
            raise Superseded(f"{inc} was superseded by {rec.get('superseded_by')}")
        return rec

    def wait_budget(self, inc, spend_s=None, total_s=600.0):
        """Cumulative waiting budget per incarnation, so repeated waits cannot become an endless loop."""
        rec = self.check_incarnation(inc)
        used = float(rec.get("wait_used_s") or 0.0)
        if spend_s:
            used += float(spend_s)
            rec["wait_used_s"] = used
            _write_json(self._p("incarnations", f"{inc}.json"), rec)
        return {"used_s": used, "remaining_s": max(0.0, total_s - used), "total_s": total_s}

    def set_availability(self, inc, state):
        if state not in ("accepting", "busy", "unattended"):
            raise AgentdmError("availability must be accepting|busy|unattended")
        rec = self.check_incarnation(inc)
        rec["availability"] = state
        _write_json(self._p("incarnations", f"{inc}.json"), rec)

    # ---------------------------------------------------------------- session binding
    def bind_session(self, inc, session_id, source):
        _write_json(self._p("bindings", f"{inc}.json"),
                    {"session_id": session_id, "source": source, "bound_at": _now(), "ended_at": None})

    def end_session(self, inc):
        b = _read_json(self._p("bindings", f"{inc}.json")) or {"session_id": None, "source": None}
        b["ended_at"] = _now()
        _write_json(self._p("bindings", f"{inc}.json"), b)

    def host_bind(self, host_pid, session_id, source, ended=False, clears_others=False):
        """Per-session records under one host pid. An end only ends ITS OWN session id (DM-04): two
        sessions can share a host process (Codex app-server threads), and a SessionStart with source
        `clear` replaces the previous session in the same process."""
        path = self._p("bindings", "host", f"{int(host_pid)}.json")
        b = _read_json(path) or {"sessions": {}}
        sessions = b.setdefault("sessions", {})
        if ended:
            rec = sessions.setdefault(session_id, {"source": source, "bound_at": None, "ended_at": None})
            rec["ended_at"], rec["ended_source"] = _now(), source
        else:
            if clears_others:
                for sid, rec in sessions.items():
                    if sid != session_id and rec.get("ended_at") is None:
                        rec["ended_at"], rec["ended_source"] = _now(), f"cleared-by:{session_id}"
            sessions[session_id] = {"source": source, "bound_at": _now(), "ended_at": None}
        _write_json(path, b)

    def host_binding(self, host_pid):
        return _read_json(self._p("bindings", "host", f"{int(host_pid)}.json"))

    def binding(self, inc):
        """Resolve the incarnation's session binding.

        A transport that carries its OWN identity (env binding S) is only ever confirmed, ended, or
        moved along an explicit `clear` succession by the host breadcrumb; it never adopts whichever
        session happens to be live (DM-05). A transport with no identity of its own adopts the host's
        session only when that pid's history is one linear line: a single session, or clears chaining to
        a single live one. Any other shape (two threads, one ended by SessionEnd) is ambiguous and fails
        closed to transport-only."""
        env = _read_json(self._p("bindings", f"{inc}.json"))
        rec = _read_json(self._p("incarnations", f"{inc}.json")) or {}
        host = self.host_binding(rec["ppid"]) if rec.get("ppid") else None
        if not host:
            return env
        sessions = host.get("sessions", {})

        def follow(sid):                              # walk explicit clear-successions to the live head
            seen = set()
            while sid in sessions and sid not in seen:
                seen.add(sid)
                r = sessions[sid]
                if r.get("ended_at") is None:
                    return sid, r
                src = r.get("ended_source") or ""
                if not src.startswith("cleared-by:"):
                    return sid, r                     # ended for real
                sid = src.split(":", 1)[1]
            return None, None

        def bound(sid, r):
            return {"session_id": sid, "source": r.get("source"), "bound_at": r.get("bound_at"),
                    "ended_at": None, "env_binding": env}

        own = (env or {}).get("session_id")
        if own:
            if own not in sessions:
                return env                            # the hook never saw this session: keep what the host told us
            sid, r = follow(own)
            if r and r.get("ended_at") is None:
                return bound(sid, r)
            return {"session_id": None, "ended": [own], "env_binding": env}
        live = [sid for sid, r in sessions.items() if r.get("ended_at") is None]
        linear = all((r.get("ended_at") is None) or (r.get("ended_source") or "").startswith("cleared-by:")
                     for r in sessions.values())
        if len(live) == 1 and linear:
            return bound(live[0], sessions[live[0]])
        if not sessions or (not live and linear):
            return {"session_id": None, "ended": sorted(sessions), "env_binding": env}
        return {"session_id": None, "ambiguous": sorted(sessions), "env_binding": env}

    def presence_state(self, inc):
        if not self.presence_alive(inc):
            return "offline"
        b = self.binding(inc)
        if b and b.get("session_id") and not b.get("ended_at"):
            return "online"
        return "transport-only"

    def roster(self, include_all=False):
        rows = [{"alias": HUMAN, "incarnation_id": None, "presence": "n/a", "availability": "n/a",
                 "family": "human"}]
        for fn in sorted(os.listdir(self._p("aliases"))):
            alias = fn[:-5]
            if (_read_json(self._p("aliases", fn)) or {}).get("retired"):
                continue
            inc = self._alias_current(alias)
            rec = self.incarnation(inc)
            presence = self.presence_state(inc)
            if rec.get("provisional") and presence == "offline" and not include_all:
                continue                                       # spawn-time litter: hidden, gc removes it
            rows.append({"alias": alias, "incarnation_id": inc, "family": rec["family"],
                         "presence": presence, "availability": rec["availability"],
                         "provisional": bool(rec.get("provisional")),
                         "session": (self.binding(inc) or {}).get("session_id"),
                         "worktree": rec.get("worktree"), "pid": rec["pid"],
                         "claims": [c["id"] for c in self.claims() if c["holder"] == inc and c["state"] == "held"]})
        return rows

    # ---------------------------------------------------------------- mail
    def _maildir(self, alias):
        return mailbox.Maildir(self._p("mail", alias), factory=None, create=True)

    def _actor(self, alias, inc):
        if alias == HUMAN:
            return {"alias": HUMAN, "family": "human"}
        rec = self.check_incarnation(inc)
        if rec["alias"] != alias:
            raise AgentdmError("incarnation does not own that alias")
        return rec

    def send(self, from_alias, from_inc, to_alias, subject, body, kind="note", in_reply_to=None):
        actor = self._actor(from_alias, from_inc)
        if to_alias != HUMAN and self._alias_current(to_alias) is None:
            raise AgentdmError(f"unknown recipient alias {to_alias!r}")
        if kind not in KINDS:
            raise AgentdmError("kind must be " + "|".join(KINDS))
        mid = f"<{uuid.uuid4().hex}@agentdm>"
        msg = EmailMessage(policy=UNFOLDED)
        msg["Message-ID"] = mid
        msg["Date"] = email.utils.formatdate(localtime=True)
        msg["From"] = f"{actor['family']}/{from_alias}@agentdm"
        msg["To"] = f"{to_alias}@agentdm"
        msg["Subject"] = subject
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
        msg["X-Agentdm-Kind"] = kind
        msg["X-Agentdm-From-Incarnation"] = from_inc or HUMAN
        msg["X-Agentdm-Project"] = self.project_key
        # cte is explicit: with max_line_length=None the auto-encoder compares int <= None on 3.9-3.11.
        msg.set_content(body, cte="8bit")
        self._maildir(to_alias).add(msg)
        return mid

    def _parse(self, path):
        with open(path, "rb") as f:
            m = email.message_from_binary_file(f, policy=email.policy.default)
        body = m.get_body(preferencelist=("plain",))
        kind = m["X-Agentdm-Kind"]
        return {"message_id": m["Message-ID"], "from": m["From"], "to": m["To"],
                "subject": m["Subject"], "date": m["Date"], "kind": kind,
                "expects_outcome": kind in REQUEST_KINDS,
                "in_reply_to": m["In-Reply-To"], "body": body.get_content() if body else ""}

    def _find(self, alias, message_id):
        """The stored message with this Message-ID in one alias's mailbox, or None."""
        base = self._p("mail", alias)
        for sub in ("new", "cur"):
            folder = os.path.join(base, sub)
            if not os.path.isdir(folder):
                continue
            for fn in sorted(os.listdir(folder)):
                m = self._parse(os.path.join(folder, fn))
                if m["message_id"] == message_id:
                    return m
        return None

    def inbox(self, alias, inc):
        """Return queued + offered-but-unacknowledged messages. Idempotent and replayable."""
        self._actor(alias, inc)
        md = self._maildir(alias)
        new, cur = os.path.join(md._path, "new"), os.path.join(md._path, "cur")
        for fn in sorted(os.listdir(new)):
            os.rename(os.path.join(new, fn), os.path.join(cur, fn + ":2,S"))
            if os.environ.get("AGENTDM_TEST_CRASH_AFTER_RENAME"):
                os._exit(3)                                  # the crash window under test
        out = []
        for fn in sorted(os.listdir(cur)):
            m = self._parse(os.path.join(cur, fn))
            key = _mid_key(m["message_id"])
            if os.path.exists(self._p("acks", f"{key}.json")):
                continue
            prior = _read_json(self._p("offers", f"{key}.json"))
            _write_json(self._p("offers", f"{key}.json"),
                        {"offered_to": inc or HUMAN, "alias": alias, "offered_at": _now(),
                         "first_offered_at": (prior or {}).get("first_offered_at") or _now()})
            m["state"] = "offered"
            m["previously_offered"] = prior is not None
            outcome = _read_json(self._p("outcomes", f"{key}.json"))
            if outcome:
                m["outcome"] = outcome["outcome"]
            out.append(m)
        return out

    def ack(self, alias, inc, message_id):
        self._actor(alias, inc)
        key = _mid_key(message_id)
        offer = _read_json(self._p("offers", f"{key}.json"))
        if not offer or offer["alias"] != alias:
            raise AgentdmError("message was never offered to that alias")
        if offer["offered_to"] != (inc or HUMAN):
            raise AgentdmError("message was offered to a different incarnation; fetch it first")
        _write_json(self._p("acks", f"{key}.json"), {"acked_by": inc or HUMAN, "alias": alias, "acked_at": _now()})

    def decide(self, alias, inc, message_id, outcome, note=""):
        """Record the recipient's explicit outcome for a request-kind message and queue a reply to
        its sender. A fourth receipt, separate from ack: acknowledging is not accepting, and
        accepting is not completion. One outcome per message; the first decision stands."""
        self._actor(alias, inc)
        if outcome not in OUTCOMES:
            raise AgentdmError("outcome must be " + "|".join(OUTCOMES))
        key = _mid_key(message_id)
        offer = _read_json(self._p("offers", f"{key}.json"))
        if not offer or offer["alias"] != alias:
            raise AgentdmError("message was never offered to that alias")
        if offer["offered_to"] != (inc or HUMAN):
            raise AgentdmError("message was offered to a different incarnation; fetch it first")
        if os.path.exists(self._p("outcomes", f"{key}.json")):
            raise AgentdmError("message already has an outcome; the first decision stands")
        m = self._find(alias, message_id)
        if m is None:
            raise AgentdmError("message is no longer in that mailbox")
        if m["kind"] not in REQUEST_KINDS:
            raise AgentdmError(f"kind {m['kind']!r} does not take an outcome; only " + "|".join(REQUEST_KINDS))
        sender = str(m["from"] or "").partition("/")[2].rpartition("@")[0]
        reply = self.send(alias, inc, sender, f"{outcome}: {m['subject']}", note or "", "ack", message_id)
        _write_json(self._p("outcomes", f"{key}.json"),
                    {"outcome": outcome, "decided_by": inc or HUMAN, "alias": alias, "decided_at": _now(),
                     "kind": m["kind"], "reply_message_id": reply, "note": note or ""})
        return {"message_id": message_id, "outcome": outcome, "reply_message_id": reply,
                "reply_to": sender, "kind": m["kind"]}

    def status(self, message_id):
        key = _mid_key(message_id)
        outcome = _read_json(self._p("outcomes", f"{key}.json"))
        extra = {"outcome": outcome} if outcome else {}
        if os.path.exists(self._p("acks", f"{key}.json")):
            return {"state": "acknowledged", **_read_json(self._p("acks", f"{key}.json")), **extra}
        offer = _read_json(self._p("offers", f"{key}.json"))
        if offer:
            return {"state": "offered", **offer, **extra}
        return {"state": "queued"}

    # ---------------------------------------------------------------- claims
    def claim(self, inc, paths, branch=None, ttl_s=3600):
        rec = self.check_incarnation(inc)
        cid = uuid.uuid4().hex[:12]
        _write_json(self._p("claims", f"{cid}.json"),
                    {"id": cid, "holder": inc, "alias": rec["alias"], "paths": list(paths), "branch": branch,
                     "since": _now(), "expires_at": time.time() + ttl_s, "released": None})
        return cid

    def release(self, claim_id, *, by_incarnation=None, by_human=False):
        c = _read_json(self._p("claims", f"{claim_id}.json"))
        if not c:
            raise AgentdmError("no such claim")
        if by_human:
            who = HUMAN
        else:
            self.check_incarnation(by_incarnation)
            if c["holder"] != by_incarnation:
                raise NotHolder("only the holder incarnation or a human may release a claim")
            who = by_incarnation
        c["released"] = {"by": who, "at": _now()}
        _write_json(self._p("claims", f"{claim_id}.json"), c)

    def claims(self):
        out = []
        for fn in sorted(os.listdir(self._p("claims"))):
            c = _read_json(self._p("claims", fn))
            if c["released"]:
                c["state"] = "released"
            elif not self.presence_alive(c["holder"]) or time.time() > c["expires_at"]:
                c["state"] = "stale"                          # never auto-released
            else:
                c["state"] = "held"
            out.append(c)
        return out


def _sha(s):
    return hashlib.sha256(s.encode()).hexdigest()
