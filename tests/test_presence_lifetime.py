"""Given/When/Then for descriptor ownership, isolated from the test runner's FDs."""
import subprocess
import sys

from acceptance_support import AcceptanceCase


SETUP = '''
import os
from agentdm.presence import PresenceHold
hold = PresenceHold("presence", {"synthetic": True})
old_fd = hold.fd
hold.close()
# Reuse exactly the old descriptor for an unrelated owned file.
other_fd = os.open("unrelated", os.O_CREAT | os.O_RDWR, 0o600)
if other_fd != old_fd:
    os.dup2(other_fd, old_fd)
    os.close(other_fd)
'''


class PresenceLifetimeAcceptance(AcceptanceCase):
    def run_child(self, code):
        result = subprocess.run([sys.executable, "-c", SETUP + code],
                                cwd=self.project, env=self.env, capture_output=True,
                                timeout=3)
        self.assertEqual(result.returncode, 0, "closed presence hold must not close a reused descriptor")

    def test_pl01_double_close_leaves_reused_descriptor_open(self):
        """Given a closed hold; when its fd is reused and close repeats; then new owner survives."""
        self.run_child('''
hold.close()
os.fstat(old_fd)
os.close(old_fd)
''')

    def test_pl02_fork_callback_leaves_reused_descriptor_open(self):
        """Given a closed hold; when its old fd is reused and fork occurs; then child retains it."""
        self.run_child('''
pid = os.fork()
if pid == 0:
    try:
        os.fstat(old_fd)
    except OSError:
        os._exit(1)
    os._exit(0)
_, status = os.waitpid(pid, 0)
os.close(old_fd)
raise SystemExit(os.waitstatus_to_exitcode(status))
''')
