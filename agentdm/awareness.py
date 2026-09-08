"""Mailbox awareness, kept apart from session binding (DM-06).

Counting is read-only: it never offers a message. A lookup that cannot name exactly one live transport
for the session is `unavailable`, never zero, because a dead instrument must not read as clean.
"""
import os
from .store import _read_json, _mid_key, HUMAN, AgentdmError


def unread_count(store, alias, from_alias=None):
    """Messages `inbox` would return for `alias` right now, without offering them.
    Any failure to read the mailbox raises: a count that cannot be taken is not zero (DM-09)."""
    try:
        base = store._p("mail", alias)
        if not os.path.isdir(base):
            return 0
        n = 0
        for sub in ("new", "cur"):
            for fn in os.listdir(os.path.join(base, sub)):
                m = store._parse(os.path.join(base, sub, fn))
                # Stored From is family/alias@agentdm. The family and partial aliases
                # do not identify the requested sender; this is attribution, not auth.
                sender = str(m["from"] or "").partition("/")[2]
                if from_alias is not None and sender != from_alias + "@agentdm":
                    continue
                if not os.path.exists(store._p("acks", f"{_mid_key(m['message_id'])}.json")):
                    n += 1
        return n
    except AgentdmError:
        raise
    except Exception as exc:
        raise AgentdmError(f"mailbox read failure for {alias}: {type(exc).__name__}") from exc


def unread_for_session(store, session_id):
    matches, ended = [], 0
    for fn in sorted(os.listdir(store._p("aliases"))):
        a = _read_json(store._p("aliases", fn)) or {}
        if a.get("retired"):
            continue
        inc = a.get("incarnation_id")
        if not inc or not store.presence_alive(inc):
            continue
        b = store.binding(inc)
        if b and b.get("session_id") == session_id:
            if b.get("ended_at"):                                  # DM-08: an ended binding is not a binding
                ended += 1
                continue
            matches.append((fn[:-5], inc))
    if not matches:
        reason = "session ended for its transport" if ended else "no live transport is bound to this session"
        return {"status": "unavailable", "reason": reason}
    if len(matches) > 1:
        return {"status": "unavailable", "reason": "ambiguous: %d transports bound to this session" % len(matches)}
    alias, inc = matches[0]
    try:
        return {"status": "ok", "alias": alias, "incarnation_id": inc, "unread": unread_count(store, alias)}
    except AgentdmError as exc:
        return {"status": "unavailable", "reason": str(exc)}
