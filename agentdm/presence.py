"""Presence: a held flock witnesses the TRANSPORT PROCESS, nothing more.

The kernel releases the lock when the last open file description closes, so a dead server reads as
offline with no sweeper. A forked child inherits the open file description and would keep the lock
alive after the parent dies (close-on-exec is not close-on-fork); the at-fork guard closes the
descriptor in every child so that cannot happen.
"""
import errno, fcntl, json, os


class PresenceHold:
    def __init__(self, path: str, record: dict, guard_fork: bool = True):
        self.path = path
        self.fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
        os.set_inheritable(self.fd, False)          # close-on-exec (NOT close-on-fork)
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            os.close(self.fd)
            if exc.errno in (errno.EWOULDBLOCK, errno.EAGAIN):
                raise RuntimeError("presence already held: " + path) from None
            raise
        os.ftruncate(self.fd, 0)
        os.write(self.fd, json.dumps(record, sort_keys=True).encode())
        os.fsync(self.fd)
        if guard_fork:
            os.register_at_fork(after_in_child=self._close_in_child)

    def _close_in_child(self):
        self.close()

    def close(self):
        fd, self.fd = self.fd, None
        if fd is None:
            return
        try:
            os.close(fd)
        except OSError:
            pass


def is_held(path: str) -> bool:
    """True iff some live process holds the lock. Fails closed: no file, or lock free, means offline."""
    try:
        fd = os.open(path, os.O_RDONLY)
    except FileNotFoundError:
        return False
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in (errno.EWOULDBLOCK, errno.EAGAIN):
                return True
            raise
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    finally:
        os.close(fd)
