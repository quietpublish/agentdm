#!/usr/bin/env python3
"""Host session hook for agentdm. Reads the host's JSON on stdin, writes ONE breadcrumb, prints NOTHING.

Register it for SessionStart and SessionEnd. Hook stdout is model context on Claude Code, Codex and
Gemini, so this script never writes to stdout, and it exits 0 on every path so it can never block a
host. The breadcrumb is keyed by the pid of the nearest host-like ancestor (claude, codex, gemini,
cursor-agent), falling back to the immediate parent, so the MCP server, whose parent is the host
process, can match it. Ends carry the ending session's id and end nothing else (DM-04).
"""
import json, os, subprocess, sys

HOSTS = ("claude", "codex", "gemini", "cursor-agent")


def _ps(pid, col):
    try:
        return subprocess.run(["ps", "-o", f"{col}=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
    except Exception:
        return ""


def host_like(pid):
    """Match on argv[0] only (plus node-hosted CLIs by script path), never on a substring of the whole
    command line: a shell whose argv contains the word "gemini" is not a host."""
    cmd = _ps(pid, "command")
    if not cmd:
        return False
    toks = cmd.split()
    argv0 = os.path.basename(toks[0])
    if argv0 in HOSTS:
        return True
    return argv0 in ("node", "bun") and any(t.endswith(("gemini.js", "/gemini", "cursor-agent")) for t in toks[1:3])


def host_pid(limit=4):
    pid, first = os.getppid(), os.getppid()
    for _ in range(limit):
        if pid <= 1:
            break
        if host_like(pid):
            return pid
        try:
            pid = int(_ps(pid, "ppid") or 0)
        except ValueError:
            break
    return first                                   # unknown ancestry: the immediate parent only, never four


UNATTENDED_MARKERS = ("DARKER_HEADLESS", "AGENTDM_DISABLE")


def main():
    if any(os.environ.get(k) for k in UNATTENDED_MARKERS):
        return 0                                   # a lights-out run gets no mailbox context and leaves no trace
    try:
        data = json.loads(sys.stdin.read() or "{}")
        session = data.get("session_id") or data.get("conversation_id")
        event = data.get("hook_event_name") or data.get("event") or ""
        source = data.get("source") or ""
        cwd = data.get("cwd") or os.getcwd()
        if not session:
            return 0
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
        from agentdm.store import resolve_store
        store = resolve_store(cwd)
        store.host_bind(host_pid(), session, source=f"hook:{event}:{source}".rstrip(":"),
                        ended=event.lower().endswith("end"), clears_others=(source == "clear"))
    except Exception as exc:
        sys.stderr.write(f"agentdm-session-hook: {exc}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
