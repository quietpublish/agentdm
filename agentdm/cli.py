"""Human CLI. The human is a participant with fixed alias `human`."""
import json, os, sys, time
from .store import resolve_store, HUMAN, AgentdmError

USAGE = """agentdm - local DMs between agent sessions in this project

  agentdm who [--all]                  roster with presence / availability / claims (--all shows offline provisional rows)
  agentdm name <alias> <new-alias>     name a session (human authority; moves its mailbox)
  agentdm gc                           remove roster litter: retired aliases, offline provisional rows
  agentdm forget <alias>               drop one offline alias from the roster (refused while alive)
  agentdm send <to> <subject> [body]   body from argv or stdin
  agentdm inbox                        fetch messages addressed to `human` (marks them offered)
  agentdm ack <message-id>
  agentdm status <message-id>          queued | offered | acknowledged
  agentdm claims                       all claims with state held | stale | released
  agentdm release <claim-id>           human release (the only path besides the holder)
  agentdm tail                         poll human's inbox every second
  agentdm store                        resolved store path for this project
Project is $AGENTDM_PROJECT_DIR or the current directory (any subdir or worktree of the repo).
"""


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(USAGE); return 0
    cmd, args = argv[0], argv[1:]
    # Validate usage before resolving a project or creating any local state.
    arity = {"who": (0, 1), "send": (2, None), "inbox": (0, 0), "ack": (1, 1),
             "status": (1, 1), "claims": (0, 0), "release": (1, 1), "tail": (0, 0),
             "name": (2, 2), "forget": (1, 1), "gc": (0, 0), "store": (0, 0)}
    minimum, maximum = arity.get(cmd, (0, 0))
    invalid = (cmd not in arity or len(args) < minimum
               or (maximum is not None and len(args) > maximum)
               or (cmd == "who" and args not in ([], ["--all"])))
    if invalid:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        store = resolve_store(os.environ.get("AGENTDM_PROJECT_DIR") or os.getcwd())
        if cmd == "who":
            for r in store.roster(include_all="--all" in args):
                claims = ",".join(r.get("claims") or []) or "-"
                print(f"{r['alias']:<24} {r['family']:<12} {r['presence']:<15} {r['availability']:<10} claims={claims}")
        elif cmd == "send":
            to, subject = args[0], args[1]
            body = " ".join(args[2:]) if len(args) > 2 else sys.stdin.read()
            print(store.send(HUMAN, None, to, subject, body))
        elif cmd == "inbox":
            for m in store.inbox(HUMAN, None):
                print(f"--- {m['message_id']}  from {m['from']}  [{m['kind']}] {m['subject']}\n{m['body']}")
        elif cmd == "ack":
            store.ack(HUMAN, None, args[0]); print("acknowledged")
        elif cmd == "status":
            print(json.dumps(store.status(args[0]), indent=1))
        elif cmd == "claims":
            for c in store.claims():
                print(f"{c['id']}  {c['state']:<9} {c['alias']:<20} {c['branch'] or '-':<12} {' '.join(c['paths'])}")
        elif cmd == "release":
            store.release(args[0], by_human=True); print("released")
        elif cmd == "tail":
            seen = set()
            while True:
                for m in store.inbox(HUMAN, None):
                    if m["message_id"] not in seen:
                        seen.add(m["message_id"])
                        print(f"{time.strftime('%H:%M:%S')}  {m['from']}  [{m['kind']}] {m['subject']}: {m['body'].strip()}", flush=True)
                time.sleep(1)
        elif cmd == "name":
            print(store.rename_alias(args[0], args[1]))
        elif cmd == "forget":
            print(store.forget(args[0]))
        elif cmd == "gc":
            print(json.dumps(store.gc()))
        elif cmd == "store":
            print(store.path)
        else:
            print(USAGE); return 2
    except AgentdmError as exc:
        print(f"agentdm: {exc}", file=sys.stderr); return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
