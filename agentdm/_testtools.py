"""Helper processes for the failure tests. Not part of the tool."""
import json, os, sys, time
from .store import resolve_store
from .presence import PresenceHold


def main(argv):
    cmd = argv[0]
    if cmd == "hold":
        project, alias = argv[1], argv[2]
        session = argv[argv.index("--session") + 1] if "--session" in argv else None
        store = resolve_store(project)
        reg = store.register(alias, family="test", pid=os.getpid(), ppid=os.getppid(),
                             session_id=session, session_source="test", provisional="--provisional" in argv)
        hold = PresenceHold(store._presence_path(reg["incarnation_id"]), reg,
                            guard_fork="--no-guard" not in argv)
        if "--fork" in argv:
            pid = os.fork()
            if pid == 0:
                time.sleep(60)                                  # child lingers with the inherited fd
                os._exit(0)
            reg["fork_child_pid"] = pid
            print(json.dumps(reg), flush=True)
            os._exit(0)                                          # parent leaves immediately
        print(json.dumps(reg), flush=True)
        sys.stdin.read()                                         # idle until the test closes stdin or kills us
        hold.close()
        return 0
    if cmd == "fetch":
        project, alias, inc = argv[1], argv[2], argv[3]
        store = resolve_store(project)
        print(json.dumps(store.inbox(alias, inc)))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
