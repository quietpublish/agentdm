"""Optional human notifications. IDs map to docs/TEST_CONTRACT.md (NT-*).

Off by default, enabled only by the human CLI, metadata only, never blocking or failing a send.
"""
import json
import time
from acceptance_support import AcceptanceCase, StdioPeer, LocalEndpoint


class NotifyAcceptance(AcceptanceCase):
    def test_nt01_nothing_leaves_the_machine_unless_the_human_opted_in(self):
        """Given no notify setting; when a request is sent; then no HTTP request occurs."""
        endpoint = LocalEndpoint(self)
        self.assertEqual(self.cli("notify").stdout.strip(), "off")
        peer = self.peer()
        peer.call(2, "send", to="human", subject="synthetic", body="synthetic", kind="handoff")
        StdioPeer.payload(peer.response(2))
        self.assertEqual(endpoint.wait_for(1, timeout=0.5), [])
        self.assertFalse(list(self.state.glob("agentdm/notify.json")))

    def test_nt02_ntfy_push_carries_metadata_only_and_never_delays_the_send(self):
        """Given ntfy enabled; when a request is sent; then one titled POST names sender, recipient
        and kind without subject or body, and the send receipt is queued at once."""
        endpoint = LocalEndpoint(self)
        enabled = self.cli("notify", "ntfy", endpoint.url + "/synthetic-topic", "synthetic-token")
        self.assertEqual(enabled.returncode, 0, enabled.stderr)
        sender = self.peer("sender", "sender-session")
        receiver = self.peer("receiver", "receiver-session")
        t0 = time.monotonic()
        sender.call(2, "send", to="receiver", subject="PRIVATE_SUBJECT", body="PRIVATE_BODY", kind="handoff")
        self.assertEqual(StdioPeer.payload(sender.response(2))["state"], "queued")
        self.assertLess(time.monotonic() - t0, 1.0)
        hits = endpoint.wait_for(1)
        self.assertEqual(len(hits), 1)
        hit = hits[0]
        self.assertEqual(hit["path"], "/synthetic-topic")
        self.assertEqual(hit["headers"]["Authorization"], "Bearer synthetic-token")
        self.assertEqual(hit["headers"]["Title"], "agentdm project")
        for needle in ("sender", "receiver", "handoff"):
            self.assertIn(needle, hit["body"])
        self.assertNotIn("PRIVATE_", hit["body"] + json.dumps(hit["headers"]))
        # A note between agents is not the human's business; a note to the human is.
        sender.call(3, "send", to="receiver", subject="PRIVATE_SUBJECT", body="PRIVATE_BODY", kind="note")
        sender.response(3)
        sender.call(4, "send", to="human", subject="PRIVATE_SUBJECT", body="PRIVATE_BODY", kind="note")
        sender.response(4)
        hits = endpoint.wait_for(2)
        self.assertEqual([h["body"].split(":")[0] for h in hits], ["sender -> receiver", "sender -> human"])
        # Subject travels only after the human turns it on explicitly.
        self.cli("notify", "subject", "on")
        sender.call(5, "send", to="human", subject="SHARED_SUBJECT", body="PRIVATE_BODY", kind="question")
        sender.response(5)
        hit = endpoint.wait_for(3)[2]
        self.assertIn("SHARED_SUBJECT", hit["body"])
        self.assertNotIn("PRIVATE_BODY", hit["body"])
        # A decision notifies without its reason.
        receiver.call(2, "inbox")
        receiver.response(2)
        receiver.call(3, "decline", message_id=json.loads(sender.response(2)["result"]["content"][0]["text"])["message_id"],
                      reason="PRIVATE_REASON")
        StdioPeer.payload(receiver.response(3))
        hit = endpoint.wait_for(4)[3]
        self.assertIn("receiver declined handoff from sender", hit["body"])
        self.assertNotIn("PRIVATE_", hit["body"])

    def test_nt03_telegram_push_uses_the_bot_api_shape(self):
        """Given telegram enabled against a loopback API; when the human declines; then one JSON
        POST reaches sendMessage with the chat id and metadata only."""
        endpoint = LocalEndpoint(self)
        self.cli("notify", "telegram", "synthetic-bot-token", "12345")
        config = json.loads(self.cli("store").stdout and (self.state / "agentdm" / "notify.json").read_text())
        config["telegram"]["api"] = endpoint.url
        (self.state / "agentdm" / "notify.json").write_text(json.dumps(config))
        agent = self.peer("agent", "agent-session")
        agent.call(2, "send", to="human", subject="PRIVATE_SUBJECT", body="PRIVATE_BODY", kind="question")
        mid = StdioPeer.payload(agent.response(2))["message_id"]
        endpoint.wait_for(1)
        self.cli("inbox")
        declined = self.cli("decline", mid, "PRIVATE_REASON")
        self.assertEqual(declined.returncode, 0, declined.stderr)
        hits = endpoint.wait_for(2)
        self.assertEqual(len(hits), 2)
        self.assertEqual(hits[1]["path"], "/botsynthetic-bot-token/sendMessage")
        payload = json.loads(hits[1]["body"])
        self.assertEqual(payload["chat_id"], "12345")
        self.assertIn("human declined question from agent", payload["text"])
        self.assertNotIn("PRIVATE_", hits[0]["body"] + hits[1]["body"])

    def test_nt04_unreachable_or_stalled_endpoint_cannot_fail_or_stall_the_send(self):
        """Given ntfy pointing at an endpoint that stalls, then at a closed port; when a request is
        sent; then each receipt is queued, each response is prompt, and the transport survives."""
        stalled = LocalEndpoint(self, stall_s=8.0)
        closed = LocalEndpoint(self)
        closed_url = closed.url
        closed.close()
        for rid, url in ((2, stalled.url + "/slow"), (3, closed_url + "/gone")):
            with self.subTest(url=url):
                self.cli("notify", "ntfy", url)
                peer = self.peer("peer-%d" % rid, "session-%d" % rid)
                t0 = time.monotonic()
                peer.call(rid, "send", to="human", subject="synthetic", body="synthetic", kind="handoff")
                sent = StdioPeer.payload(peer.response(rid))
                self.assertEqual(sent["state"], "queued")
                self.assertLess(time.monotonic() - t0, 1.0)
                peer.send({"jsonrpc": "2.0", "id": rid + 10, "method": "ping"})
                self.assertEqual(peer.response(rid + 10)["result"], {})
                self.assertEqual(json.loads(self.cli("status", sent["message_id"]).stdout)["state"], "queued")

    def test_nt05_human_cli_owns_the_setting(self):
        """Given the CLI; when the human configures, tests and turns off; then each step is honest."""
        endpoint = LocalEndpoint(self, status=200)
        self.assertEqual(self.cli("notify", "test").returncode, 1, "test with nothing configured must fail")
        self.assertEqual(self.cli("notify", "ntfy").returncode, 2)
        self.assertEqual(self.cli("notify", "telegram", "only-token").returncode, 2)
        self.assertEqual(self.cli("notify", "subject", "maybe").returncode, 2)
        self.cli("notify", "ntfy", endpoint.url + "/t")
        shown = json.loads(self.cli("notify").stdout)
        self.assertEqual(shown["ntfy"]["url"], endpoint.url + "/t")
        tested = self.cli("notify", "test")
        self.assertEqual(tested.returncode, 0, tested.stderr)
        self.assertIn("200", tested.stdout)
        self.assertEqual(len(endpoint.wait_for(1)), 1)
        self.assertNotIn("PRIVATE", endpoint.hits[0]["body"])
        self.assertEqual(self.cli("notify", "off").stdout.strip(), "off")
        self.assertEqual(self.cli("notify").stdout.strip(), "off")
        self.assertFalse((self.state / "agentdm" / "notify.json").exists())


class NotifyCapAcceptance(AcceptanceCase):
    def test_nt06_pushes_are_capped_per_sender_per_hour(self):
        """Given ntfy enabled with a cap of 3 per sender per hour; when one sender queues five request
        kinds; then exactly three pushes leave, a second sender still gets its push, every send is
        still queued, and the setting shows the cap."""
        endpoint = LocalEndpoint(self)
        self.cli("notify", "ntfy", endpoint.url + "/t")
        capped = self.cli("notify", "cap", "3")
        self.assertEqual(capped.returncode, 0, capped.stderr)
        self.assertEqual(json.loads(self.cli("notify").stdout)["cap_per_hour"], 3)
        sender = self.peer("sender", "sender-session")
        other = self.peer("other", "other-session")
        for rid in range(2, 7):
            sender.call(rid, "send", to="human", subject="synthetic", body="synthetic", kind="question")
            self.assertEqual(StdioPeer.payload(sender.response(rid))["state"], "queued")
        other.call(2, "send", to="human", subject="synthetic", body="synthetic", kind="question")
        self.assertEqual(StdioPeer.payload(other.response(2))["state"], "queued")
        hits = endpoint.wait_for(4)
        time.sleep(0.5)
        self.assertEqual(len(endpoint.hits), 4, [h["body"] for h in endpoint.hits])
        self.assertEqual(sum(1 for h in hits if h["body"].startswith("sender ->")), 3)
        self.assertEqual(sum(1 for h in hits if h["body"].startswith("other ->")), 1)
        self.assertEqual(self.cli("notify", "cap", "zero").returncode, 2)
