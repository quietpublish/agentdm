"""AR-01: startup isolation, observed through real stdio and owned state."""
import hashlib
import unittest

from acceptance_support import AcceptanceCase, StdioPeer


class UnattendedAcceptance(AcceptanceCase):
    def snapshot(self):
        if not self.state.exists():
            return None
        return {str(p.relative_to(self.state)):
                (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns) if p.is_file() else None
                for p in self.state.rglob("*")}

    def assert_inert(self, peer):
        peer.send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        self.assertEqual(peer.response(2)["result"]["tools"], [])
        # Even a caller retaining an old registry must not reach store operations.
        names = ("whoami", "who", "register", "send", "inbox", "ack", "claim",
                 "release", "claims", "wait", "status", "unknown-tool")
        for rid, name in enumerate(names, 3):
            peer.call(rid, name)
            result = peer.response(rid)["result"]
            self.assertTrue(result.get("isError"), name)
            self.assertEqual(result["content"], [{"type": "text", "text":
                             "AgentdmError: agentdm is inactive: unattended"}])
        peer.send({"jsonrpc": "2.0", "id": 20, "method": "ping"})
        self.assertEqual(peer.response(20)["result"], {})
        peer.process.stdin.close()
        self.assertEqual(peer.process.wait(timeout=2), 0)
        peer.stderr.seek(0)
        self.assertEqual(peer.stderr.read(), b"")

    def test_ua01_disabled_startup_creates_no_state(self):
        """Given no store; when either marker is nonempty; then startup and calls are inert."""
        for marker in ("DARKER_HEADLESS", "AGENTDM_DISABLE"):
            for value in ("1", "0", "false"):
                with self.subTest(marker=marker, value=value):
                    self.env.update(DARKER_HEADLESS="", AGENTDM_DISABLE="")
                    self.env[marker] = value
                    with self.peer() as peer:
                        self.assertIsNone(self.snapshot(), "startup created state before any tool call")
                        self.assert_inert(peer)
                    self.assertIsNone(self.snapshot())

    def test_ua02_disabled_startup_preserves_existing_mail_and_binding(self):
        """Given a live bound peer and queued mail; when disabled peers start; then all state stays identical."""
        with self.peer() as enabled:
            enabled.call(2, "send", to="acceptance", subject="synthetic", body="synthetic")
            mid = StdioPeer.payload(enabled.response(2))["message_id"]
            before = self.snapshot()
            self.assertTrue(before)
            for marker in ("DARKER_HEADLESS", "AGENTDM_DISABLE"):
                with self.subTest(marker=marker):
                    self.env.update(DARKER_HEADLESS="", AGENTDM_DISABLE="")
                    self.env[marker] = "1"
                    with self.peer() as disabled:
                        self.assertEqual(self.snapshot(), before, "startup changed existing state")
                        self.assert_inert(disabled)
                    self.assertEqual(self.snapshot(), before)
            enabled.call(3, "status", message_id=mid)
            self.assertEqual(StdioPeer.payload(enabled.response(3))["state"], "queued")

    def test_ua03_unset_or_empty_markers_keep_enabled_startup(self):
        """Given unset or empty markers; when a server starts; then it registers and exposes its tools."""
        for value in (None, ""):
            with self.subTest(value=value):
                for marker in ("DARKER_HEADLESS", "AGENTDM_DISABLE"):
                    if value is None:
                        self.env.pop(marker, None)
                    else:
                        self.env[marker] = value
                with self.peer() as peer:
                    peer.send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
                    self.assertIn("inbox", [t["name"] for t in peer.response(2)["result"]["tools"]])
                    peer.call(3, "whoami")
                    identity = StdioPeer.payload(peer.response(3))
                    self.assertEqual(identity["alias"], "acceptance")
                    self.assertEqual(identity["presence"], "online")
                    self.assertTrue(self.snapshot())

    def test_ua04_disabled_startup_does_not_require_a_git_project(self):
        """Given no Git project; when disabled startup runs; then it reports the marker, not resolution errors."""
        self.project = self.scratch
        self.env["AGENTDM_DISABLE"] = "1"
        with self.peer() as peer:
            self.assert_inert(peer)
        self.assertIsNone(self.snapshot())


if __name__ == "__main__":
    unittest.main()
