"""Real human-entrypoint Given/When/Then contracts; no installed configuration."""
import subprocess
import sys

from acceptance_support import AcceptanceCase, ROOT


class CliAcceptance(AcceptanceCase):
    def cli(self, *arguments, outside=False, state=None):
        return subprocess.run([sys.executable, str(ROOT / "bin" / "agentdm"), *arguments],
                              cwd=self.scratch if outside else self.project,
                              env=dict(self.env, XDG_STATE_HOME=str(state or self.state)),
                              capture_output=True, text=True, input="", timeout=3)

    def test_cl01_invalid_arguments_refuse_before_creating_store(self):
        """Given no store; when required args/options are invalid; then usage, exit 2, no store."""
        for i, arguments in enumerate((("send",), ("send", "human"), ("ack",), ("name", "old"),
                          ("release",), ("forget",), ("status",), ("who", "--typo"),
                          ("claims", "extra"), ("unknown",))):
            with self.subTest(arguments=arguments):
                state = self.scratch / ("state-%d" % i)
                result = self.cli(*arguments, state=state)
                self.assertEqual(result.returncode, 2)
                self.assertIn("agentdm", result.stdout + result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse(state.exists())

    def test_cl02_outside_git_reports_error_without_traceback(self):
        """Given a non-Git directory; when requesting roster; then a concise failure, no traceback."""
        result = self.cli("who", outside=True)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(result.stderr.startswith("agentdm:"))
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse(self.state.exists())

    def test_cl03_help_and_real_send_remain_usable(self):
        """Given a fresh project; when help then valid send run; then help is inert and mail persists."""
        help_result = self.cli("--help", outside=True)
        self.assertEqual(help_result.returncode, 0)
        self.assertFalse(self.state.exists())
        sent = self.cli("send", "human", "synthetic subject", "synthetic body")
        self.assertEqual(sent.returncode, 0)
        self.assertIn("@agentdm>", sent.stdout)
        fetched = self.cli("inbox")
        self.assertEqual(fetched.returncode, 0)
        self.assertIn("synthetic body", fetched.stdout)
