"""The seven failure tests. Each names the observable event that earns or denies a claim.

Written before the mailbox interface. They drive the real store, the real presence lock and the
real MCP server over stdio; nothing here starts a model session or spends money.
"""
import json, os, select, signal, subprocess, sys, tempfile, threading, time, unittest
from pathlib import Path
from acceptance_support import isolated_environment

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
PY = sys.executable


def _alive(pid):
    try:
        os.kill(pid, 0); return True
    except OSError:
        return False


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, env=isolated_environment(None, ROOT),
                          check=True, capture_output=True, text=True).stdout.strip()


def make_repo(tmp, name="repo"):
    d = os.path.join(tmp, name)
    os.makedirs(d)
    git("init", "-q", cwd=d)
    git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "init", cwd=d)
    return d


class Base(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="agentdm-test-")
        self.addCleanup(self.temporary.cleanup)
        self.tmp = self.temporary.name
        self.state = os.path.join(self.tmp, "state")
        self.repo = make_repo(self.tmp)
        self.env = isolated_environment(self.state, ROOT)
        self.procs = []
        from agentdm.store import resolve_store
        self.store = resolve_store(self.repo, state_home=self.state)

    def tearDown(self):
        for p in self.procs:
            if p.poll() is None:
                p.kill()
                p.wait()
            for f in (p.stdin, p.stdout, p.stderr):
                if f:
                    f.close()

    def holder(self, alias, session=None, extra=()):
        """Start a process that registers `alias`, holds its presence lock, and idles."""
        cmd = [PY, "-X", "faulthandler", "-m", "agentdm._testtools", "hold", self.repo, alias, *extra]
        if session:
            cmd += ["--session", session]
        p = subprocess.Popen(cmd, env=self.env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True)
        self.procs.append(p)
        ready, _, _ = select.select([p.stdout], [], [], 10)
        if not ready:                                   # a hung helper fails loudly with its own stack
            os.kill(p.pid, signal.SIGABRT); time.sleep(0.5); p.kill(); p.wait()
            self.fail("holder produced no line in 10s; child stack:\n" + p.stderr.read())
        line = p.stdout.readline()
        if not line:                                    # read stderr ONLY after the child is gone: read() blocks until EOF
            p.kill(); p.wait()
            self.fail("holder printed nothing: " + p.stderr.read())
        reg = json.loads(line)
        if reg.get("fork_child_pid"):
            self.addCleanup(lambda pid=reg["fork_child_pid"]: (os.kill(pid, signal.SIGKILL) if _alive(pid) else None))
        return p, reg

    def presence_of(self, alias):
        for row in self.store.roster():
            if row["alias"] == alias:
                return row
        return None


class T1SessionEndsWhileHostSurvives(Base):
    def test_binding_withdrawn_reads_transport_only_not_online(self):
        p, reg = self.holder("worker", session="sess-1")
        self.assertEqual(self.presence_of("worker")["presence"], "online")
        # The host process lives on, but the conversation ended (what a SessionEnd hook reports).
        self.store.end_session(reg["incarnation_id"])
        self.assertEqual(self.presence_of("worker")["presence"], "transport-only")
        p.kill(); p.wait()
        self.assertEqual(self.presence_of("worker")["presence"], "offline")

    def test_liveness_without_any_binding_is_transport_only(self):
        p, reg = self.holder("nobind")
        self.assertEqual(self.presence_of("nobind")["presence"], "transport-only")


class T2ServerDiesAfterFetchBeforeResponse(Base):
    def test_message_is_offered_again_not_lost_and_not_acknowledged(self):
        reg = self.store.register("reader", family="test", pid=os.getpid(), ppid=os.getppid())
        inc = reg["incarnation_id"]
        mid = self.store.send("human", None, "reader", "hello", "body text")
        self.assertEqual(self.store.status(mid)["state"], "queued")
        # A fetch that crashes after the Maildir rename and before the response could reach a model.
        r = subprocess.run([PY, "-m", "agentdm._testtools", "fetch", self.repo, "reader", inc],
                           env=dict(self.env, AGENTDM_TEST_CRASH_AFTER_RENAME="1"),
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 3, r.stderr)
        # The folder moved but no offer record was written: state comes from records, not folders,
        # so the sender still sees `queued`. Never claim `offered` without the record.
        self.assertEqual(self.store.status(mid)["state"], "queued")
        again = self.store.inbox("reader", inc)
        self.assertEqual([m["message_id"] for m in again], [mid])
        self.assertEqual(again[0]["state"], "offered")
        self.store.ack("reader", inc, mid)
        self.assertEqual(self.store.status(mid)["state"], "acknowledged")
        self.assertEqual(self.store.inbox("reader", inc), [])


class T3ReclaimWhileOldIncarnationAlive(Base):
    def test_superseded_incarnation_is_rejected_and_its_claims_untouched(self):
        from agentdm.store import Superseded, AliasHeld
        p1, reg1 = self.holder("worker", session="s1")
        inc1, tok1 = reg1["incarnation_id"], reg1["reclaim_token"]
        claim = self.store.claim(inc1, ["scripts/x.sh"], branch="main", ttl_s=3600)
        with self.assertRaises(AliasHeld):
            self.store.register("worker", family="test", pid=1, ppid=1)          # no token
        reg2 = self.store.register("worker", family="test", pid=1, ppid=1, reclaim_token=tok1)
        inc2 = reg2["incarnation_id"]
        self.assertNotEqual(inc1, inc2)
        mid = self.store.send("human", None, "worker", "s", "b")
        for op in (lambda: self.store.send("worker", inc1, "human", "s", "b"),
                   lambda: self.store.ack("worker", inc1, mid),
                   lambda: self.store.claim(inc1, ["y"]),
                   lambda: self.store.release(claim, by_incarnation=inc1)):
            with self.assertRaises(Superseded):
                op()
        c = self.store.claims()[0]
        self.assertEqual(c["holder"], inc1)          # not transferred to inc2
        self.assertEqual(c["state"], "held")         # inc1's lock is still alive
        with self.assertRaises(Exception):
            self.store.release(claim, by_incarnation=inc2)   # successor cannot release predecessor's work


class T3bReregisterRetiresAutoAlias(Base):
    def test_renaming_retires_the_spawn_alias_and_hides_it_from_the_roster(self):
        reg = self.store.register("codex-12006", family="codex", pid=12006, ppid=1)
        new = self.store.register("codex-darker", family="codex", pid=12006, ppid=1)
        self.store.retire(reg["incarnation_id"], new["incarnation_id"])
        aliases = [r["alias"] for r in self.store.roster()]
        self.assertIn("codex-darker", aliases)
        self.assertNotIn("codex-12006", aliases)
        from agentdm.store import Superseded
        with self.assertRaises(Superseded):
            self.store.send("codex-12006", reg["incarnation_id"], "human", "s", "b")


class T4TwoWorktreesSameStore(Base):
    def test_worktrees_resolve_identical_store(self):
        from agentdm.store import resolve_store
        wt = os.path.join(self.tmp, "wt")
        git("worktree", "add", "-q", wt, "-b", "side", cwd=self.repo)
        a = resolve_store(self.repo, state_home=self.state)
        b = resolve_store(wt, state_home=self.state)
        self.assertEqual(a.path, b.path)
        self.assertEqual(a.project_key, b.project_key)


class T5ExpiredPresenceLeavesClaimStale(Base):
    def test_dead_holder_claim_is_stale_never_released(self):
        p, reg = self.holder("worker", session="s1")
        inc = reg["incarnation_id"]
        cid = self.store.claim(inc, ["a", "b"], ttl_s=3600)
        self.assertEqual(self.store.claims()[0]["state"], "held")
        p.kill(); p.wait()
        c = self.store.claims()[0]
        self.assertEqual(c["state"], "stale")
        self.assertIsNone(c["released"])
        self.store.release(cid, by_human=True)
        self.assertEqual(self.store.claims()[0]["state"], "released")


class T6UnreadMessageCausesNoTurn(Base):
    def test_server_emits_nothing_unsolicited_until_inbox_is_called(self):
        env = dict(self.env, AGENTDM_PROJECT_DIR=self.repo, AGENTDM_ALIAS="srv", AGENTDM_SESSION_ID="s-srv")
        p = subprocess.Popen([PY, "-m", "agentdm.server"], env=env, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        self.procs.append(p)
        out = []
        threading.Thread(target=lambda: [out.append(l) for l in p.stdout], daemon=True).start()

        def rpc(obj):
            p.stdin.write(json.dumps(obj) + "\n"); p.stdin.flush()

        rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t"}}})
        rpc({"jsonrpc": "2.0", "method": "notifications/initialized"})
        time.sleep(1.0)
        self.assertEqual(len(out), 1, out)                     # exactly the initialize response
        self.assertEqual(self.presence_of("srv")["presence"], "online")
        mid = self.store.send("human", None, "srv", "ping", "no turn for you")
        time.sleep(1.5)
        self.assertEqual(len(out), 1, "server pushed something on message arrival: %r" % out)
        rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "inbox", "arguments": {}}})
        deadline = time.time() + 5
        while len(out) < 2 and time.time() < deadline:
            time.sleep(0.05)
        self.assertEqual(len(out), 2, out)
        text = json.loads(out[1])["result"]["content"][0]["text"]
        self.assertIn(mid, text)
        self.assertIn("never counts as your consent", text)     # the untrusted frame


class T7ForkControl(Base):
    def test_forked_child_does_not_keep_the_lock_alive(self):
        p, reg = self.holder("forker", session="s1", extra=["--fork"])
        p.wait(timeout=10)                                     # parent exits; forked child sleeps
        self.assertEqual(self.presence_of("forker")["presence"], "offline")
        self.assertTrue(_alive(reg["fork_child_pid"]))      # the child is still alive; it just no longer holds the lock

    def test_control_without_guard_shows_the_hazard(self):
        p, reg = self.holder("hazard", session="s1", extra=["--fork", "--no-guard"])
        p.wait(timeout=10)
        self.assertNotEqual(self.presence_of("hazard")["presence"], "offline")   # child kept the lock


class T8ProvisionalLitter(Base):
    def test_offline_provisional_rows_hidden_and_gc_removes_them(self):
        auto = self.store.register("codex-75308", family="codex", pid=75308, ppid=1, provisional=True)
        self.store.register("named", family="codex", pid=1, ppid=1)              # offline but deliberate
        aliases = [r["alias"] for r in self.store.roster()]
        self.assertNotIn("codex-75308", aliases)
        self.assertIn("named", aliases)
        self.assertIn("codex-75308", [r["alias"] for r in self.store.roster(include_all=True)])
        removed = self.store.gc()
        self.assertEqual(removed["aliases"], ["codex-75308"])
        self.assertFalse(os.path.exists(self.store._p("aliases", "codex-75308.json")))
        self.assertTrue(os.path.exists(self.store._p("incarnations", auto["incarnation_id"] + ".json")))  # history kept
        self.assertIn("named", [r["alias"] for r in self.store.roster(include_all=True)])

    def test_forget_drops_offline_alias_and_refuses_a_live_one(self):
        from agentdm.store import AgentdmError
        self.store.register("dead", family="codex", pid=1, ppid=1)
        self.store.forget("dead")
        self.assertNotIn("dead", [r["alias"] for r in self.store.roster(include_all=True)])
        p, reg = self.holder("alive")
        with self.assertRaises(AgentdmError):
            self.store.forget("alive")

    def test_live_provisional_row_is_shown(self):
        p, reg = self.holder("codex-1", extra=["--provisional"])
        self.assertIn("codex-1", [r["alias"] for r in self.store.roster()])


class T9HumanNaming(Base):
    def test_rename_moves_mail_retires_old_alias_and_clears_provisional(self):
        from agentdm.store import AgentdmError
        reg = self.store.register("claude-code-5010", family="claude-code", pid=1, ppid=1, provisional=True)
        mid = self.store.send("human", None, "claude-code-5010", "hi", "before rename")
        inc = self.store.rename_alias("claude-code-5010", "darker-22")
        self.assertEqual(inc, reg["incarnation_id"])
        rec = self.store.incarnation(inc)
        self.assertEqual(rec["alias"], "darker-22")
        self.assertFalse(rec["provisional"])
        self.assertEqual([m["message_id"] for m in self.store.inbox("darker-22", inc)], [mid])
        aliases = [r["alias"] for r in self.store.roster(include_all=True)]
        self.assertIn("darker-22", aliases)
        self.assertNotIn("claude-code-5010", aliases)
        with self.assertRaises(AgentdmError):
            self.store.rename_alias("darker-22", "human")
        with self.assertRaises(AgentdmError):
            self.store.rename_alias("nope", "x")


class T10HostBinding(Base):
    def test_hook_breadcrumb_binds_and_unbinds_by_host_pid(self):
        p, reg = self.holder("codex-x")                       # no env session: transport-only; its ppid is this process
        self.assertEqual(self.presence_of("codex-x")["presence"], "transport-only")
        self.store.host_bind(os.getpid(), "thread-abc", source="hook:codex:SessionStart")
        self.assertEqual(self.presence_of("codex-x")["presence"], "online")
        self.assertEqual(self.store.binding(reg["incarnation_id"])["session_id"], "thread-abc")
        self.store.host_bind(os.getpid(), "thread-abc", source="hook:codex:SessionEnd", ended=True)
        self.assertEqual(self.presence_of("codex-x")["presence"], "transport-only")

    def test_ending_one_session_never_ends_a_sibling_under_the_same_host_pid(self):   # DM-04
        p, reg = self.holder("codex-y")
        self.store.host_bind(os.getpid(), "A", source="hook:SessionStart")
        self.store.host_bind(os.getpid(), "B", source="hook:SessionStart")
        self.store.host_bind(os.getpid(), "A", source="hook:SessionEnd", ended=True)
        b = self.store.binding(reg["incarnation_id"])
        self.assertIsNone(b["session_id"])                    # DM-05: a transport with no identity of its own
        self.assertEqual(sorted(b["ambiguous"]), ["A", "B"])  # must not adopt the survivor
        self.assertEqual(self.presence_of("codex-y")["presence"], "transport-only")

    def test_dm05_ending_a_never_makes_a_transport_bound_to_a_adopt_b(self):
        pa, ra = self.holder("t-a", session="A")             # two transports under one host pid, each with
        pb, rb = self.holder("t-b", session="B")             # its own env identity (Claude's shape)
        self.store.host_bind(os.getpid(), "A", source="hook:SessionStart")
        self.store.host_bind(os.getpid(), "B", source="hook:SessionStart")
        self.assertEqual(self.presence_of("t-a")["presence"], "online")
        self.assertEqual(self.presence_of("t-b")["presence"], "online")
        self.store.host_bind(os.getpid(), "A", source="hook:SessionEnd", ended=True)
        self.assertEqual(self.presence_of("t-a")["presence"], "transport-only")   # A's transport ended, not re-homed
        self.assertEqual(self.store.binding(ra["incarnation_id"])["session_id"], None)
        self.assertEqual(self.store.binding(rb["incarnation_id"])["session_id"], "B")
        self.assertEqual(self.presence_of("t-b")["presence"], "online")

    def test_env_bound_transport_follows_an_explicit_clear_succession_only(self):
        p, reg = self.holder("cl", session="S")
        self.store.host_bind(os.getpid(), "S", source="hook:SessionStart:startup")
        self.store.host_bind(os.getpid(), "Y", source="hook:SessionStart:clear", clears_others=True)
        b = self.store.binding(reg["incarnation_id"])
        self.assertEqual(b["session_id"], "Y")                # S was explicitly replaced by Y in this process
        self.assertEqual(self.presence_of("cl")["presence"], "online")
        self.store.host_bind(os.getpid(), "Y", source="hook:SessionEnd", ended=True)
        self.assertEqual(self.presence_of("cl")["presence"], "transport-only")

    def test_env_bound_transport_the_hook_never_saw_keeps_its_env_binding(self):
        p, reg = self.holder("late", session="S")
        self.store.host_bind(os.getpid(), "OTHER", source="hook:SessionStart")   # hook installed mid-life; S unseen
        self.assertEqual(self.store.binding(reg["incarnation_id"])["session_id"], "S")
        self.assertEqual(self.presence_of("late")["presence"], "online")

    def test_two_live_sessions_under_one_host_pid_is_ambiguous_and_fails_closed(self):
        p, reg = self.holder("codex-z")
        self.store.host_bind(os.getpid(), "A", source="hook:SessionStart")
        self.store.host_bind(os.getpid(), "B", source="hook:SessionStart")
        b = self.store.binding(reg["incarnation_id"])
        self.assertIsNone(b["session_id"])
        self.assertEqual(sorted(b["ambiguous"]), ["A", "B"])
        self.assertEqual(self.presence_of("codex-z")["presence"], "transport-only")

    def test_clear_ends_the_previous_session_in_the_same_process(self):
        p, reg = self.holder("claude-c")
        self.store.host_bind(os.getpid(), "X", source="hook:SessionStart:startup")
        self.store.host_bind(os.getpid(), "Y", source="hook:SessionStart:clear", clears_others=True)
        self.assertEqual(self.store.binding(reg["incarnation_id"])["session_id"], "Y")
        self.assertEqual(self.presence_of("claude-c")["presence"], "online")

    def test_hook_writes_exactly_one_breadcrumb_for_the_nearest_host_like_ancestor(self):
        hook = os.path.join(ROOT, "hooks", "agentdm-session-hook.py")
        payload = json.dumps({"session_id": "s-host", "cwd": self.repo, "hook_event_name": "SessionStart"})
        # Given a live synthetic host; when its child runs the hook; then the
        # one breadcrumb belongs to that exact host, not a real ancestor agent.
        # Do not exec the hook: that replaces the supposed host with its child.
        script = ('exec -a claude bash -c '\
                  '\'printf "%s\\n" "$$" >&2; "$1" "$2"; rc=$?; exit "$rc"\' fixture "$1" "$2"')
        r = subprocess.run(["bash", "-c", script, "fixture", PY, hook],
                           input=payload, env=self.env, capture_output=True, text=True,
                           cwd=self.repo, timeout=5)
        self.assertEqual((r.returncode, r.stdout), (0, ""), r.stderr)
        files = os.listdir(self.store._p("bindings", "host"))
        host = int(r.stderr.strip())
        self.assertEqual(files, [f"{host}.json"])
        pid = int(files[0][:-5])
        self.assertEqual(self.store.host_binding(pid)["sessions"]["s-host"]["ended_at"], None)

    def test_hook_script_writes_breadcrumb_for_its_ancestor_and_prints_nothing(self):
        hook = os.path.join(ROOT, "hooks", "agentdm-session-hook.py")
        payload = {"session_id": "s-hook", "cwd": self.repo, "hook_event_name": "SessionStart"}
        r = subprocess.run([PY, hook], input=json.dumps(payload), env=self.env, capture_output=True, text=True, cwd=self.repo)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "")                        # hook stdout is model context on every host: never write it
        # Keyed by the nearest host-like ancestor of the hook (under a real Claude session that is the
        # session's own pid; under a bare shell it is this test process): exactly one breadcrumb either way.
        files = os.listdir(self.store._p("bindings", "host"))
        self.assertEqual(len(files), 1, files)
        self.assertIsNone(self.store.host_binding(int(files[0][:-5]))["sessions"]["s-hook"]["ended_at"])
        r = subprocess.run([PY, hook], input="not json", env=self.env, capture_output=True, text=True, cwd=self.repo)
        self.assertEqual((r.returncode, r.stdout), (0, ""))


class T11ServerRobustness(Base):
    def test_garbage_unknown_and_failing_calls_never_end_the_server_and_alias_is_reread(self):
        env = dict(self.env, AGENTDM_PROJECT_DIR=self.repo, AGENTDM_ALIAS="srv2", AGENTDM_SESSION_ID="s")
        p = subprocess.Popen([PY, "-m", "agentdm.server"], env=env, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        self.procs.append(p)
        out = []
        threading.Thread(target=lambda: [out.append(json.loads(l)) for l in p.stdout], daemon=True).start()

        def rpc(obj):
            p.stdin.write(json.dumps(obj) + "\n"); p.stdin.flush()

        def wait(n):
            deadline = time.time() + 5
            while len(out) < n and time.time() < deadline:
                time.sleep(0.05)
            self.assertEqual(len(out), n, out)

        rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
        p.stdin.write("this is not json\n"); p.stdin.flush()
        rpc({"jsonrpc": "2.0", "id": 2, "method": "no/such/method"})
        rpc({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "bogus", "arguments": {}}})
        rpc({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "send", "arguments": {"to": "nobody", "subject": "s", "body": "b"}}})
        wait(4)
        self.assertEqual(out[1]["error"]["code"], -32601)
        self.assertTrue(out[2]["result"]["isError"])
        self.assertTrue(out[3]["result"]["isError"])
        self.store.rename_alias("srv2", "renamed")           # the human names the session from outside
        rpc({"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "whoami", "arguments": {}}})
        wait(5)
        self.assertIn('"alias": "renamed"', out[4]["result"]["content"][0]["text"])
        self.assertIsNone(p.poll())


class T12CountNudge(Base):
    """DM-06: awareness targets the session explicitly; a failed lookup is unavailable, never zero;
    counting never offers a message."""

    def test_count_targets_the_bound_session_and_never_mutates(self):
        from agentdm.awareness import unread_for_session
        p, reg = self.holder("w1", session="sess-w1")
        mid = self.store.send("human", None, "w1", "s", "b")
        r = unread_for_session(self.store, "sess-w1")
        self.assertEqual((r["status"], r["alias"], r["unread"]), ("ok", "w1", 1))
        self.assertEqual(self.store.status(mid)["state"], "queued")          # counting is not offering
        self.assertEqual(unread_for_session(self.store, "sess-w1"), r)         # idempotent

    def test_unknown_or_ambiguous_session_is_unavailable_not_zero(self):
        from agentdm.awareness import unread_for_session
        self.assertEqual(unread_for_session(self.store, "nobody")["status"], "unavailable")
        pa, ra = self.holder("dup-a", session="same")
        pb, rb = self.holder("dup-b", session="same")
        r = unread_for_session(self.store, "same")
        self.assertEqual(r["status"], "unavailable")
        self.assertIn("ambiguous", r["reason"])

    def test_ended_binding_is_unavailable_for_the_nudge(self):                       # DM-08
        from agentdm.awareness import unread_for_session
        p, reg = self.holder("ended", session="sess-e")
        self.store.send("human", None, "ended", "s", "b")
        self.assertEqual(unread_for_session(self.store, "sess-e")["status"], "ok")
        self.store.end_session(reg["incarnation_id"])                              # roster: transport-only
        r = unread_for_session(self.store, "sess-e")
        self.assertEqual(r["status"], "unavailable", r)
        self.assertIn("ended", r["reason"])

    def test_mailbox_read_failure_is_unavailable_not_silence(self):                   # DM-09
        from agentdm.awareness import unread_for_session
        hook = os.path.join(ROOT, "hooks", "agentdm-prompt-hook.py")
        p, reg = self.holder("broken", session="sess-br")
        self.store.send("human", None, "broken", "s", "b")
        self.store.inbox("broken", reg["incarnation_id"])                          # message now in cur/
        cur = self.store._p("mail", "broken", "cur")
        victim = os.path.join(cur, os.listdir(cur)[0])
        os.chmod(victim, 0)
        try:
            r = unread_for_session(self.store, "sess-br")
            self.assertEqual(r["status"], "unavailable", r)
            self.assertIn("read", r["reason"])
            out = subprocess.run([PY, hook], input=json.dumps({"session_id": "sess-br", "cwd": self.repo}),
                                 env=self.env, capture_output=True, text=True, cwd=self.repo).stdout
            self.assertIn("unavailable", out)                                      # never the silence that means zero
        finally:
            os.chmod(victim, 0o600)

    def test_prompt_hook_prints_one_metadata_line_or_nothing(self):
        hook = os.path.join(ROOT, "hooks", "agentdm-prompt-hook.py")
        p, reg = self.holder("w2", session="sess-w2")
        run = lambda sid, cwd=self.repo: subprocess.run([PY, hook], input=json.dumps({"session_id": sid, "cwd": cwd}),
                                                        env=self.env, capture_output=True, text=True, cwd=cwd)
        self.assertEqual(run("sess-w2").stdout, "")                            # zero unread: silence
        self.store.send("human", None, "w2", "the subject must not leak", "nor the body")
        out = run("sess-w2").stdout
        self.assertIn("1 unread", out)
        self.assertIn("w2", out)
        self.assertNotIn("subject must not leak", out)
        self.assertNotIn("nor the body", out)
        out = run("unbound-session").stdout
        self.assertIn("unavailable", out)                                      # not "0"
        self.assertNotIn(" 0 ", out)
        other = os.path.join(self.tmp, "no-store"); os.makedirs(other)
        subprocess.run(["git", "init", "-q"], cwd=other, check=True)
        self.assertEqual(run("sess-w2", cwd=other).stdout, "")                 # no store here: print nothing, create nothing
        self.assertFalse(os.path.isdir(os.path.join(self.state, "agentdm")) and
                         any("no-store" in Path(self.state, "agentdm", d, "project.json").read_text()
                             for d in os.listdir(os.path.join(self.state, "agentdm"))))


class T13BoundedWait(Base):
    def _server(self, alias):
        env = dict(self.env, AGENTDM_PROJECT_DIR=self.repo, AGENTDM_ALIAS=alias, AGENTDM_SESSION_ID="s-" + alias,
                   AGENTDM_WAIT_BUDGET_S="3")
        p = subprocess.Popen([PY, "-m", "agentdm.server"], env=env, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        self.procs.append(p)
        out = []
        threading.Thread(target=lambda: [out.append(json.loads(l)) for l in p.stdout], daemon=True).start()
        def rpc(obj):
            p.stdin.write(json.dumps(obj) + "\n"); p.stdin.flush()
        def wait_for(n, t=10):
            deadline = time.time() + t
            while len(out) < n and time.time() < deadline:
                time.sleep(0.05)
            return out
        rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
        wait_for(1)
        return p, rpc, out, wait_for

    def test_wait_returns_early_on_arrival_without_offering(self):
        p, rpc, out, wait_for = self._server("waiter")
        rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "wait", "arguments": {"timeout_s": 8}}})
        time.sleep(1.0)
        self.assertEqual(len(out), 1)                                          # still waiting
        mid = self.store.send("human", None, "waiter", "s", "b")
        wait_for(2, 8)
        res = json.loads(out[1]["result"]["content"][0]["text"])
        self.assertEqual((res["status"], res["unread"]), ("ready", 1))
        self.assertLess(res["waited_s"], 5)
        self.assertEqual(self.store.status(mid)["state"], "queued")           # wait reports, inbox offers

    def test_wait_budget_is_cumulative_and_then_refuses(self):
        p, rpc, out, wait_for = self._server("budget")
        rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "wait", "arguments": {"timeout_s": 2}}})
        wait_for(2, 8)
        r1 = json.loads(out[1]["result"]["content"][0]["text"])
        self.assertEqual(r1["status"], "timeout")
        rpc({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "wait", "arguments": {"timeout_s": 2}}})
        wait_for(3, 8)
        r2 = json.loads(out[2]["result"]["content"][0]["text"])
        self.assertIn(r2["status"], ("timeout", "budget_exhausted"))
        rpc({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "wait", "arguments": {"timeout_s": 2}}})
        wait_for(4, 8)
        r3 = json.loads(out[3]["result"]["content"][0]["text"])
        self.assertEqual(r3["status"], "budget_exhausted")                     # 3 s budget: refused immediately
        self.assertLess(r3["waited_s"], 0.5)

    def test_cancelling_a_wait_frees_the_server_at_once_and_charges_only_elapsed_time(self):   # DM-07
        p, rpc, out, wait_for = self._server("cancel")
        rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "wait", "arguments": {"timeout_s": 30}}})
        time.sleep(1.0)
        rpc({"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 2, "reason": "user"}})
        t0 = time.time()
        rpc({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "whoami", "arguments": {}}})
        wait_for(2, 5)
        self.assertLess(time.time() - t0, 3.0)                                     # not blocked until the 30 s timeout
        self.assertEqual([o["id"] for o in out], [1, 3])                            # no response for the cancelled request
        # the budget was charged for the second actually waited, not the 30 requested (budget is 3 s here)
        rpc({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "wait", "arguments": {"timeout_s": 1}}})
        wait_for(3, 5)
        self.assertEqual(json.loads(out[2]["result"]["content"][0]["text"])["status"], "timeout")

    def test_a_request_arriving_during_a_wait_is_answered_while_the_wait_continues(self):
        p, rpc, out, wait_for = self._server("inline")
        rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "wait", "arguments": {"timeout_s": 6}}})
        time.sleep(0.8)
        rpc({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "who", "arguments": {}}})
        wait_for(2, 3)
        self.assertEqual(out[1]["id"], 3)                                           # answered inline
        rpc({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "wait", "arguments": {"timeout_s": 5}}})
        wait_for(3, 3)
        self.assertEqual(out[2]["id"], 4)
        self.assertIn("refused", json.loads(out[2]["result"]["content"][0]["text"])["status"])   # one wait at a time
        self.store.send("human", None, "inline", "s", "b")
        wait_for(4, 8)
        self.assertEqual(out[3]["id"], 2)
        self.assertEqual(json.loads(out[3]["result"]["content"][0]["text"])["status"], "ready")

    def test_host_exit_during_a_wait_ends_the_server_promptly(self):
        p, rpc, out, wait_for = self._server("orphan")
        rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "wait", "arguments": {"timeout_s": 30}}})
        time.sleep(0.8)
        p.stdin.close()                                                             # the host went away
        p.wait(timeout=5)
        self.assertEqual(self.presence_of("orphan")["presence"], "offline")

    def test_fragmented_input_does_not_renew_the_wait_and_partial_input_survives(self):   # DM-10
        p, rpc, out, wait_for = self._server("frag")
        rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "wait", "arguments": {"timeout_s": 0.6}}})
        t0 = time.time()
        frags = ['{"jsonrpc": "2.0", ', '"id": 3, ', '"method": "ping"']    # a request arriving one fragment at a time
        for f in frags:
            time.sleep(0.25)
            p.stdin.write(f); p.stdin.flush()
        wait_for(2, 5)                                                       # the wait's own response
        elapsed = time.time() - t0
        self.assertEqual(out[1]["id"], 2)
        self.assertEqual(json.loads(out[1]["result"]["content"][0]["text"])["status"], "timeout")
        self.assertLess(elapsed, 1.2, "fragments renewed the timeout")       # 0.6 s requested, fragments every 0.25 s
        p.stdin.write("}\n"); p.stdin.flush()                                # complete the fragmented request
        wait_for(3, 3)
        self.assertEqual(out[2]["id"], 3)                                     # partial input was preserved, not dropped

    def test_killing_the_server_mid_wait_leaves_no_state_and_reads_offline(self):
        p, rpc, out, wait_for = self._server("victim")
        rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "wait", "arguments": {"timeout_s": 30}}})
        time.sleep(0.8)
        before = sorted(os.listdir(self.store._p("offers")))
        p.terminate(); p.wait(timeout=5)
        self.assertEqual(self.presence_of("victim")["presence"], "offline")
        self.assertEqual(sorted(os.listdir(self.store._p("offers"))), before)
        self.assertEqual(len(out), 1)                                          # no response was fabricated


class T14UnattendedKillSwitch(Base):
    """Codex's rollout point: a tool deny alone does not stop mailbox context reaching an unattended run
    through inherited hooks. Under darker's unattended marker, or an explicit disable, both hooks do
    nothing: no output, no breadcrumb, no store."""

    def _run(self, hook, payload, extra_env):
        return subprocess.run([PY, os.path.join(ROOT, "hooks", hook)], input=json.dumps(payload),
                              env=dict(self.env, **extra_env), capture_output=True, text=True, cwd=self.repo)

    def test_prompt_hook_is_silent_and_inert_under_unattended_markers(self):
        p, reg = self.holder("att", session="sess-att")
        self.store.send("human", None, "att", "s", "b")
        payload = {"session_id": "sess-att", "cwd": self.repo}
        self.assertIn("1 unread", self._run("agentdm-prompt-hook.py", payload, {}).stdout)      # control
        for marker in ({"DARKER_HEADLESS": "1"}, {"AGENTDM_DISABLE": "1"}):
            r = self._run("agentdm-prompt-hook.py", payload, marker)
            self.assertEqual((r.returncode, r.stdout), (0, ""), marker)

    def test_session_hook_writes_nothing_under_unattended_markers(self):
        payload = {"session_id": "s-x", "cwd": self.repo, "hook_event_name": "SessionStart"}
        for marker in ({"DARKER_HEADLESS": "1"}, {"AGENTDM_DISABLE": "1"}):
            r = self._run("agentdm-session-hook.py", payload, marker)
            self.assertEqual((r.returncode, r.stdout), (0, ""), marker)
            self.assertEqual(os.listdir(self.store._p("bindings", "host")), [], marker)


class T15ToolRegistryPin(Base):
    """darker denies this family on its unattended surfaces by an EXPLICIT list of names
    (scripts/darker_sdk.py _PEER_MESSAGING_MCP_TOOLS, wo-ad11). A new tool here that is not added there
    would be reachable by a lights-out drive with no test failing on either side. This pin makes the
    registry change loud: update KNOWN_TOOLS and darker's list together."""
    KNOWN_TOOLS = ["ack", "claim", "claims", "inbox", "register", "release", "send", "status", "wait", "who", "whoami"]

    def test_tool_registry_matches_the_list_darker_denies(self):
        from agentdm.server import TOOLS
        self.assertEqual(sorted(t["name"] for t in TOOLS), self.KNOWN_TOOLS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
