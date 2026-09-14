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


class LogAcceptance(AcceptanceCase):
    def test_cl04_log_is_one_timeline_and_offers_nothing(self):
        """Given a handoff (offered, accepted), its reply (queued), a held claim and a queued request
        about it; when the human runs `log`; then one dated timeline shows each message once with its
        receipt state and outcome and each claim with its state, and offers/acks are unchanged."""
        from acceptance_support import StdioPeer
        a = self.peer("alpha", "alpha-session")
        b = self.peer("beta", "beta-session")
        a.call(2, "send", to="beta", subject="synthetic handoff", body="PRIVATE_BODY", kind="handoff")
        handoff = StdioPeer.payload(a.response(2))["message_id"]
        b.call(2, "inbox"); b.response(2)
        b.call(3, "accept", message_id=handoff, note="ok"); b.response(3)
        b.call(4, "claim", paths=["docs/x.md"], ttl_s=600)
        claim = StdioPeer.payload(b.response(4))["claim_id"]
        a.call(3, "send", to="beta", subject="request: docs/x.md", body="PRIVATE_BODY", kind="claim")
        request = StdioPeer.payload(a.response(3))["message_id"]
        state = self.state / "agentdm"
        before = sorted(str(p.relative_to(state)) for p in state.rglob("*") if p.parent.name in ("offers", "acks", "outcomes"))
        result = self.cli("log")
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout
        self.assertNotIn("PRIVATE_BODY", out)
        self.assertEqual(out.count(handoff), 1)
        self.assertEqual(out.count(request), 1)
        self.assertIn("offered", out.split(handoff, 1)[1].splitlines()[0])
        self.assertIn("accepted", out.split(handoff, 1)[1].splitlines()[0])
        self.assertIn("queued", out.split(request, 1)[1].splitlines()[0])
        self.assertIn(claim, out)
        self.assertIn("held", out.split(claim, 1)[1].splitlines()[0])
        lines = [l for l in out.splitlines() if l.strip()]
        stamps = [l[:19] for l in lines if l[:4].isdigit()]
        self.assertEqual(stamps, sorted(stamps), "timeline must be in date order")
        after = sorted(str(p.relative_to(state)) for p in state.rglob("*") if p.parent.name in ("offers", "acks", "outcomes"))
        self.assertEqual(before, after, "reading the log must not offer, ack or decide anything")
        self.assertEqual(self.cli("log", "extra").returncode, 2)
