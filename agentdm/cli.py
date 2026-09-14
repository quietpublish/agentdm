"""Human CLI. The human is a participant with fixed alias `human`."""
import json, os, sys, time
from .store import resolve_store, HUMAN, AgentdmError, KINDS
from . import notify

USAGE = """agentdm - local DMs between agent sessions in this project

  agentdm who [--all]                  roster with presence / availability / claims (--all shows offline provisional rows)
  agentdm name <alias> <new-alias>     name a session (human authority; moves its mailbox)
  agentdm gc                           remove roster litter: retired aliases, offline provisional rows
  agentdm forget <alias>               drop one offline alias from the roster (refused while alive)
  agentdm send <to> <subject> [body]   body from argv or stdin; --kind note|question|handoff|review-request|claim|ack
  agentdm inbox                        fetch messages addressed to `human` (marks them offered)
  agentdm ack <message-id>             acknowledge reading; for a request this is not acceptance
  agentdm accept <message-id> [note]   answer a request kind: records the outcome, replies to the sender
  agentdm decline <message-id> [reason]
  agentdm status <message-id>          queued | offered | acknowledged, plus outcome once decided
  agentdm claims                       all claims with state held | stale | released
  agentdm release <claim-id>           human release (the only path besides the holder)
  agentdm tail                         poll human's inbox every second
  agentdm log                          one timeline of every message (receipt, outcome) and claim; reads only
  agentdm store                        resolved store path for this project
  agentdm notify                       show the human notification setting (off by default)
  agentdm notify ntfy <topic-url> [token]        push metadata to an ntfy topic
  agentdm notify telegram <bot-token> <chat-id>  push metadata to a Telegram chat
  agentdm notify subject on|off        include the message subject (default off; never the body)
  agentdm notify cap <n>               at most n pushes per sender per hour (default 20)
  agentdm notify test                  send one synthetic push now and print the result
  agentdm notify off                   remove the setting
Project is $AGENTDM_PROJECT_DIR or the current directory (any subdir or worktree of the repo).
"""


def _notify_form_ok(args):
    head, rest = tuple(args[:1]), args[1:]
    if not args or args in (["off"], ["test"], ["subject", "on"], ["subject", "off"]):
        return True
    if head == ("ntfy",):
        return len(rest) in (1, 2)
    if head == ("cap",):
        return len(rest) == 1 and rest[0].isdigit() and int(rest[0]) > 0
    return head == ("telegram",) and len(rest) == 2


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(USAGE); return 0
    cmd, args = argv[0], argv[1:]
    # Validate usage before resolving a project or creating any local state.
    kind = "note"
    if cmd == "send" and "--kind" in args:
        at = args.index("--kind")
        kind = args[at + 1] if at + 1 < len(args) else ""
        args = args[:at] + args[at + 2:]
    arity = {"who": (0, 1), "send": (2, None), "inbox": (0, 0), "ack": (1, 1),
             "accept": (1, None), "decline": (1, None),
             "status": (1, 1), "claims": (0, 0), "release": (1, 1), "tail": (0, 0),
             "name": (2, 2), "forget": (1, 1), "gc": (0, 0), "store": (0, 0), "notify": (0, 3), "log": (0, 0)}
    minimum, maximum = arity.get(cmd, (0, 0))
    invalid = (cmd not in arity or len(args) < minimum
               or (maximum is not None and len(args) > maximum)
               or (cmd == "who" and args not in ([], ["--all"]))
               or (cmd == "send" and kind not in KINDS)
               or (cmd == "notify" and not _notify_form_ok(args)))
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
            print(store.send(HUMAN, None, to, subject, body, kind))
        elif cmd == "inbox":
            for m in store.inbox(HUMAN, None):
                asks = "  (request: accept or decline)" if m["expects_outcome"] and not m.get("outcome") else ""
                print(f"--- {m['message_id']}  from {m['from']}  [{m['kind']}]{asks} {m['subject']}\n{m['body']}")
        elif cmd == "ack":
            store.ack(HUMAN, None, args[0]); print("acknowledged")
        elif cmd in ("accept", "decline"):
            outcome = "accepted" if cmd == "accept" else "declined"
            result = store.decide(HUMAN, None, args[0], outcome, " ".join(args[1:]))
            notify.notify(store, {"event": "outcome", "by": HUMAN, "to": result["reply_to"],
                                  "kind": result["kind"], "outcome": outcome}, sync=True)
            print(f"{outcome}; reply {result['reply_message_id']} queued for {result['reply_to']}")
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
        elif cmd == "log":
            for r in store.timeline():
                at = r["at"].astimezone().strftime("%Y-%m-%d %H:%M:%S")
                if r["type"] == "message":
                    sender = r["from"].partition("/")[2].rpartition("@")[0] or r["from"]
                    outcome = f" outcome={r['outcome']}" if r["outcome"] else ""
                    reply = " (reply)" if r["in_reply_to"] else ""
                    print(f"{at}  msg   {r['id']}  {sender} -> {r['to']}  [{r['kind']}] {r['state']}{outcome}{reply}  {r['subject']}")
                else:
                    rel = f" released {r['released_at'][11:19]}Z by {'human' if r['released_by'] == HUMAN else r['alias']}" if r["released_at"] else ""
                    print(f"{at}  claim {r['id']}  {r['alias']}  {r['state']}{rel}  {' '.join(r['paths'])}")
        elif cmd == "name":
            print(store.rename_alias(args[0], args[1]))
        elif cmd == "forget":
            print(store.forget(args[0]))
        elif cmd == "gc":
            print(json.dumps(store.gc()))
        elif cmd == "store":
            print(store.path)
        elif cmd == "notify":
            config = notify.load(store) or {}
            if not args:
                print(json.dumps({k: v for k, v in config.items()}, indent=1) if config else "off")
            elif args[0] == "off":
                notify.save(store, None); print("off")
            elif args[0] == "ntfy":
                config["ntfy"] = {"url": args[1], "token": args[2] if len(args) > 2 else None}
                notify.save(store, config); print("ntfy: " + args[1])
            elif args[0] == "telegram":
                config["telegram"] = {"bot_token": args[1], "chat_id": args[2]}
                notify.save(store, config); print("telegram: chat " + args[2])
            elif args[0] == "subject":
                config["subject"] = args[1] == "on"
                notify.save(store, config); print("subject: " + args[1])
            elif args[0] == "cap":
                config["cap_per_hour"] = int(args[1])
                notify.save(store, config); print("cap: %s per sender per hour" % args[1])
            elif args[0] == "test":
                if not config:
                    raise AgentdmError("notifications are off; configure ntfy or telegram first")
                title, text = notify.render(store, config, {"event": "send", "from": HUMAN, "to": HUMAN,
                                                           "kind": "note", "subject": "synthetic test"})
                results = notify.deliver(notify.requests_for(config, title, text))
                for url, result in results:
                    print(f"{url}: {result}")
                if not results or any(not isinstance(r, int) or r >= 400 for _, r in results):
                    return 1
        else:
            print(USAGE); return 2
    except AgentdmError as exc:
        print(f"agentdm: {exc}", file=sys.stderr); return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
