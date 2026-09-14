"""Given/When/Then scenarios. IDs map to docs/TEST_CONTRACT.md.

These run real stdio servers, hooks and stores, never a model or installed host.
"""
import time
import os
import unittest
from unittest.mock import patch

from acceptance_support import AcceptanceCase, StdioPeer, decoder_nesting_depth, isolated_environment


class ProtocolAcceptance(AcceptanceCase):
    def test_ac01_non_object_json_cannot_end_the_server(self):
        """Given a live transport; when non-object JSON arrives; then ping still works."""
        for invalid in (None, [], 7, "text", False):
            with self.subTest(invalid=invalid), self.peer() as peer:
                peer.send(invalid)
                peer.send({"jsonrpc": "2.0", "id": 2, "method": "ping"})
                self.assertEqual(peer.response(2)["result"], {})
                self.assertIsNone(peer.process.poll())

    def test_ac02_malformed_envelopes_are_refused_without_losing_transport(self):
        """Given a server; when a malformed request arrives; then it cannot kill dispatch."""
        for invalid in (
            {"jsonrpc": "2.0", "id": 2, "method": "initialize", "params": [1]},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": [1]},
            {"jsonrpc": "2.0", "id": [], "method": "tools/call", "params": {
                "name": "register", "arguments": {"alias": "invalid-change"}}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
                "name": "register", "arguments": [1]}},
        ):
            with self.subTest(invalid=invalid), self.peer() as peer:
                peer.send(invalid)
                peer.send({"jsonrpc": "2.0", "id": 3, "method": "ping"})
                self.assertEqual(peer.response(3)["result"], {})
                if invalid["id"] == 2:
                    self.assertEqual(peer.response(2)["error"]["code"], -32602)
                peer.call(4, "whoami")
                self.assertEqual(StdioPeer.payload(peer.response(4))["alias"], "acceptance")

    def test_ac03_empty_lines_are_not_transport_eof(self):
        """Given open stdin; when an empty line arrives; then later requests survive."""
        peer = self.peer()
        peer.raw(b"\n")
        peer.send({"jsonrpc": "2.0", "id": 2, "method": "ping"})
        self.assertEqual(peer.response(2)["result"], {})

    def test_ac04_notification_shaped_tool_call_never_mutates(self):
        """Given a registered identity; when a tool call has no ID; then no mutation/reply."""
        peer = self.peer()
        peer.send({"jsonrpc": "2.0", "method": "tools/call", "params": {
            "name": "register", "arguments": {"alias": "unrequested-change"}}})
        peer.call(2, "whoami")
        self.assertEqual(StdioPeer.payload(peer.response(2))["alias"], "acceptance")
        self.assertEqual([m["id"] for m in peer.messages], [1, 2])

    def test_ac05_unknown_or_malformed_cancellation_cannot_poison_requests(self):
        """Given no wait; when cancellation is unknown/malformed; then future calls work."""
        for params in ({"requestId": 2}, {"requestId": []}, [1], {}):
            with self.subTest(params=params), self.peer() as peer:
                peer.send({"jsonrpc": "2.0", "method": "notifications/cancelled", "params": params})
                peer.call(2, "whoami")
                self.assertEqual(StdioPeer.payload(peer.response(2))["alias"], "acceptance")

    def test_ac06_explicit_zero_wait_is_a_nonblocking_check(self):
        """Given an empty inbox; when timeout is zero; then no default-length wait occurs."""
        peer = self.peer()
        peer.call(2, "wait", timeout_s=0)
        result = StdioPeer.payload(peer.response(2, timeout=0.8))
        self.assertEqual(result["status"], "timeout")
        self.assertLess(result["waited_s"], 0.1)

    def test_ac07_deadline_preserves_fragmented_request(self):
        """Given a wait; when a ping arrives in fragments; then deadline and bytes survive."""
        peer = self.peer()
        peer.call(2, "wait", timeout_s=0.2)
        peer.send({"jsonrpc": "2.0", "id": 3, "method": "ping"})
        peer.response(3)
        peer.raw(b'{"jsonrpc":"2.0","id":4,"method":"ping"')
        for _ in range(8):
            time.sleep(0.05)
            peer.raw(b" ")
        result = StdioPeer.payload(peer.response(2))
        self.assertEqual(result["status"], "timeout")
        self.assertLess(result["waited_s"], 0.4)
        peer.raw(b"}\n")
        self.assertEqual(peer.response(4)["result"], {})

    def test_ac08_cancel_has_no_late_reply_and_does_not_kill_server(self):
        """Given a wait; when cancelled; then ping survives and cancelled reply stays absent."""
        peer = self.peer()
        peer.call(2, "wait", timeout_s=0.2)
        peer.send({"jsonrpc": "2.0", "id": 3, "method": "ping"})
        peer.response(3)
        peer.send({"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 2}})
        peer.send({"jsonrpc": "2.0", "id": 4, "method": "ping"})
        peer.response(4, timeout=0.5)
        time.sleep(0.3)
        peer.send({"jsonrpc": "2.0", "id": 5, "method": "ping"})
        peer.response(5)
        self.assertEqual([m["id"] for m in peer.messages], [1, 3, 4, 5])
        self.assertIsNone(peer.process.poll())

    def test_ac12_sender_filter_matches_alias_not_substring_or_family(self):
        """Given queued mail; when filtering sender; then only its exact alias matches."""
        peer = self.peer()
        peer.call(2, "send", to="acceptance", subject="synthetic", body="synthetic")
        sent = StdioPeer.payload(peer.response(2))
        peer.call(3, "whoami")
        family = StdioPeer.payload(peer.response(3))["family"]
        for rid, sender in enumerate(("accept", family, "acceptance"), 4):
            peer.call(rid, "wait", timeout_s=0, from_alias=sender)
            result = StdioPeer.payload(peer.response(rid))
            self.assertEqual(result["status"], "ready" if sender == "acceptance" else "timeout")
        peer.call(7, "status", message_id=sent["message_id"])
        self.assertEqual(StdioPeer.payload(peer.response(7))["state"], "queued")

    def test_ac13_register_cannot_replace_identity_during_wait(self):
        """Given an active wait; when re-registering; then refuse without replacing its owner."""
        peer = self.peer()
        peer.call(2, "whoami")
        original = StdioPeer.payload(peer.response(2))["incarnation_id"]
        peer.call(3, "wait", timeout_s=0.4)
        peer.send({"jsonrpc": "2.0", "id": 4, "method": "ping"})
        peer.response(4)
        peer.call(5, "register", alias="replacement")
        refused = peer.response(5)
        self.assertTrue(refused["result"].get("isError"), "register must be refused during wait")
        peer.call(6, "whoami")
        self.assertEqual(StdioPeer.payload(peer.response(6))["incarnation_id"], original)
        self.assertEqual(StdioPeer.payload(peer.response(3))["status"], "timeout")
        # The original owner is still charged, and register works after the wait.
        peer.call(7, "wait", timeout_s=2)
        self.assertLess(StdioPeer.payload(peer.response(7, timeout=2.5))["waited_s"], 1.85)
        peer.call(8, "register", alias="replacement")
        self.assertEqual(StdioPeer.payload(peer.response(8))["alias"], "replacement")

    def test_ac14_invalid_wait_arguments_are_refused_without_waiting(self):
        """Given a live server; when wait bounds/filter are invalid; then refuse and keep ping alive."""
        for arguments in ({"timeout_s": True}, {"timeout_s": -1}, {"timeout_s": "0"},
                          {"timeout_s": float("nan")}, {"timeout_s": float("inf")},
                          {"timeout_s": 0, "from_alias": []}, {"timeout_s": 0, "from_alias": ""}):
            with self.subTest(argument_names=tuple(arguments)), self.peer() as peer:
                peer.call(2, "wait", **arguments)
                self.assertTrue(peer.response(2, timeout=0.5)["result"].get("isError"),
                                "invalid wait arguments must be refused")
                peer.send({"jsonrpc": "2.0", "id": 3, "method": "ping"})
                self.assertEqual(peer.response(3)["result"], {})

    def test_ac15_deeply_nested_json_cannot_end_the_server(self):
        """Given a live server; when JSON exceeds decoder nesting; then later ping survives."""
        depth = decoder_nesting_depth()
        peer = self.peer()
        peer.raw(b"[" * depth + b"0" + b"]" * depth + b"\n")
        peer.send({"jsonrpc": "2.0", "id": 2, "method": "ping"})
        self.assertEqual(peer.response(2)["result"], {})


class HookAcceptance(AcceptanceCase):
    def test_ac09_headless_hooks_leave_no_output_or_new_store(self):
        """Given no store; when either disable marker is set; then both hooks are inert."""
        payload = {"session_id": "synthetic", "cwd": str(self.project), "hook_event_name": "SessionStart"}
        self.assertFalse(self.state.exists())
        for marker in ("DARKER_HEADLESS", "AGENTDM_DISABLE"):
            for hook in ("agentdm-session-hook.py", "agentdm-prompt-hook.py"):
                with self.subTest(marker=marker, hook=hook):
                    result = self.hook(hook, payload, {marker: "1"})
                    self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))
                    self.assertFalse(self.state.exists())
        # Positive control: the same real session hook is present and can write.
        result = self.hook("agentdm-session-hook.py", payload)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(list(self.state.glob("agentdm/*/bindings/host/*.json"))), 1)

    def test_ac10_nudge_counts_without_offering_and_disables_on_existing_store(self):
        """Given pending mail; when nudged or disabled; then receipt stays queued and body absent."""
        peer = self.peer()
        peer.call(2, "send", to="acceptance", subject="PRIVATE_SUBJECT", body="PRIVATE_BODY")
        sent = StdioPeer.payload(peer.response(2))
        payload = {"session_id": "acceptance-session", "cwd": str(self.project)}
        result = self.hook("agentdm-prompt-hook.py", payload)
        self.assertIn("1 unread", result.stdout)
        self.assertNotIn("PRIVATE_", result.stdout)
        for marker in ("DARKER_HEADLESS", "AGENTDM_DISABLE"):
            result = self.hook("agentdm-prompt-hook.py", payload, {marker: "1"})
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))
        peer.call(3, "status", message_id=sent["message_id"])
        self.assertEqual(StdioPeer.payload(peer.response(3))["state"], "queued")


class HookWordingAcceptance(AcceptanceCase):
    def test_ac16_prompt_hook_adds_the_claims_sentence_only_for_a_holder_with_a_pending_request(self):
        """Given pending mail; when the prompt hook runs for a session without and then with a held
        claim and a pending request; then the count line appears once, the claims sentence only in
        the second case, and never a subject or body."""
        peer = self.peer()
        peer.call(2, "send", to="acceptance", subject="PRIVATE_SUBJECT", body="PRIVATE_BODY", kind="note")
        peer.response(2)
        payload = {"session_id": "acceptance-session", "cwd": str(self.project)}
        out = self.hook("agentdm-prompt-hook.py", payload).stdout
        self.assertEqual(out.count("agentdm:"), 1)
        self.assertIn("1 unread", out)
        self.assertNotIn("coordinating those claims", out)
        peer.call(3, "send", to="acceptance", subject="PRIVATE_SUBJECT", body="PRIVATE_BODY", kind="claim")
        peer.response(3)
        out = self.hook("agentdm-prompt-hook.py", payload).stdout
        self.assertIn("1 pending request", out)
        self.assertNotIn("coordinating those claims", out, "no claim held: the sentence is not earned")
        peer.call(4, "claim", paths=["a.py"], ttl_s=600); peer.response(4)
        out = self.hook("agentdm-prompt-hook.py", payload).stdout
        self.assertEqual(out.count("agentdm:"), 1)
        self.assertIn("2 unread", out)
        self.assertIn("1 pending request", out)
        self.assertIn("part of coordinating those claims", out)
        self.assertIn("untrusted", out)
        self.assertNotIn("PRIVATE_", out)


class FixtureAcceptance(AcceptanceCase):
    def test_ac11_ambient_git_selection_cannot_redirect_fixture_work(self):
        """Given foreign Git selection; when a fixture starts; then it owns its repo/config."""
        with patch.dict(os.environ, {"GIT_DIR": "/unused-foreign-repo", "GIT_WORK_TREE": "/unused-foreign-tree",
                                     "GIT_CONFIG_GLOBAL": "/unused-user-config", "EXAMPLE_API_TOKEN": "synthetic-only"}):
            env = isolated_environment(self.state)
        self.assertNotIn("GIT_DIR", tuple(env))
        self.assertNotIn("GIT_WORK_TREE", tuple(env))
        self.assertNotIn("EXAMPLE_API_TOKEN", tuple(env))
        self.assertEqual(env["GIT_CONFIG_GLOBAL"], os.devnull)
        self.assertEqual(env["GIT_CONFIG_SYSTEM"], os.devnull)


if __name__ == "__main__":
    unittest.main(verbosity=2)
