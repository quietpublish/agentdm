"""Typed intents and the outcome receipt. IDs map to docs/TEST_CONTRACT.md (IN-*).

Acknowledging a request is not accepting it; accepting is not completion; one outcome per message.
"""
import json
from acceptance_support import AcceptanceCase, StdioPeer


class IntentAcceptance(AcceptanceCase):
    def exchange(self, kind, subject="synthetic", body="synthetic body"):
        """One sender, one receiver, one message of `kind`, fetched once. Aliases are pinned, so
        each test may open this pair only once; later messages reuse the returned peers."""
        sender = self.peer("sender", "sender-session")
        receiver = self.peer("receiver", "receiver-session")
        sender.call(2, "send", to="receiver", subject=subject, body=body, kind=kind)
        sent = StdioPeer.payload(sender.response(2))
        receiver.call(2, "inbox")
        return sender, receiver, sent["message_id"], receiver.response(2)["result"]["content"][0]["text"]

    def test_in01_decline_is_a_receipt_separate_from_ack_and_replies_to_the_sender(self):
        """Given an offered handoff; when the recipient declines; then status shows the outcome, the
        sender's inbox holds the reply, ack stays separate, and a second decision is refused."""
        sender, receiver, mid, _ = self.exchange("handoff")
        receiver.call(3, "decline", message_id=mid, reason="already mid-refactor here")
        decided = StdioPeer.payload(receiver.response(3))
        self.assertEqual(decided["outcome"], "declined")
        sender.call(3, "status", message_id=mid)
        status = StdioPeer.payload(sender.response(3))
        self.assertEqual(status["state"], "offered", "declining must not invent an acknowledgement")
        self.assertEqual(status["outcome"]["outcome"], "declined")
        self.assertEqual(status["outcome"]["reply_message_id"], decided["reply_message_id"])
        sender.call(4, "wait", timeout_s=0, from_alias="receiver")
        self.assertEqual(StdioPeer.payload(sender.response(4))["status"], "ready")
        sender.call(5, "inbox")
        text = sender.response(5)["result"]["content"][0]["text"]
        self.assertIn("already mid-refactor here", text)
        self.assertIn('"in_reply_to": "%s"' % mid, text)
        self.assertIn('"kind": "ack"', text)
        for rid, tool in ((6, "accept"), (7, "decline")):
            receiver.call(rid, tool, message_id=mid)
            self.assertTrue(receiver.response(rid)["result"].get("isError"), "the first decision stands")
        receiver.call(8, "ack", message_id=mid)
        receiver.response(8)
        sender.call(9, "status", message_id=mid)
        status = StdioPeer.payload(sender.response(9))
        self.assertEqual((status["state"], status["outcome"]["outcome"]), ("acknowledged", "declined"))

    def test_in02_outcomes_need_an_offered_request_kind(self):
        """Given a note and an unfetched handoff; when accept/decline is attempted; then both are
        refused, no outcome exists, and no reply is queued."""
        sender, receiver, note_mid, _ = self.exchange("note")
        sender.call(3, "send", to="receiver", subject="synthetic", body="synthetic", kind="handoff")
        unfetched = StdioPeer.payload(sender.response(3))["message_id"]
        for rid, (tool, mid) in enumerate((("accept", note_mid), ("decline", note_mid),
                                           ("accept", unfetched), ("decline", unfetched)), 4):
            receiver.call(rid, tool, message_id=mid, reason="x", note="x")
            self.assertTrue(receiver.response(rid)["result"].get("isError"), (tool, mid))
        for rid, mid in ((8, note_mid), (9, unfetched)):
            sender.call(rid, "status", message_id=mid)
            self.assertNotIn("outcome", StdioPeer.payload(sender.response(rid)))
        sender.call(10, "wait", timeout_s=0)
        self.assertEqual(StdioPeer.payload(sender.response(10))["status"], "timeout")

    def test_in03_inbox_marks_requests_and_explains_that_ack_is_not_acceptance(self):
        """Given a review-request and a note; when fetched; then only the request expects an
        outcome and the frame says how to answer it."""
        sender, receiver, _, text = self.exchange("review-request")
        self.assertIn('"expects_outcome": true', text)
        self.assertIn("accept or decline", text)
        self.assertIn("not proof of completion", text)
        sender.call(3, "send", to="receiver", subject="synthetic", body="synthetic", kind="note")
        self.assertFalse(StdioPeer.payload(sender.response(3))["expects_outcome"])
        receiver.call(3, "inbox")
        text = receiver.response(3)["result"]["content"][0]["text"]
        self.assertIn('"expects_outcome": false', text)
        self.assertEqual(text.count('"expects_outcome": true'), 1)

    def test_in04_unknown_kind_is_refused_before_anything_is_stored(self):
        """Given a live sender; when kind is outside the vocabulary; then refused and nothing queued."""
        sender = self.peer("sender", "sender-session")
        receiver = self.peer("receiver", "receiver-session")
        sender.call(2, "send", to="receiver", subject="synthetic", body="synthetic", kind="order")
        self.assertTrue(sender.response(2)["result"].get("isError"))
        receiver.call(2, "wait", timeout_s=0)
        self.assertEqual(StdioPeer.payload(receiver.response(2))["status"], "timeout")

    def test_in05_human_answers_a_request_from_the_cli(self):
        """Given an agent's question to the human; when the human accepts from the CLI; then the
        agent's inbox carries the reply and status shows accepted; a note cannot be answered."""
        agent = self.peer("agent", "agent-session")
        agent.call(2, "send", to="human", subject="synthetic question", body="synthetic", kind="question")
        mid = StdioPeer.payload(agent.response(2))["message_id"]
        agent.call(3, "send", to="human", subject="synthetic note", body="synthetic", kind="note")
        note_mid = StdioPeer.payload(agent.response(3))["message_id"]
        fetched = self.cli("inbox")
        self.assertIn("(request: accept or decline)", fetched.stdout)
        self.assertEqual(fetched.stdout.count("(request"), 1)
        refused = self.cli("decline", note_mid, "not a request")
        self.assertEqual(refused.returncode, 1)
        accepted = self.cli("accept", mid, "yes, go ahead")
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertIn("accepted", accepted.stdout)
        status = json.loads(self.cli("status", mid).stdout)
        self.assertEqual(status["outcome"]["outcome"], "accepted")
        agent.call(4, "inbox")
        text = agent.response(4)["result"]["content"][0]["text"]
        self.assertIn("yes, go ahead", text)
        self.assertIn('"in_reply_to": "%s"' % mid, text)
        sent = self.cli("send", "agent", "synthetic", "synthetic", "--kind", "handoff")
        self.assertEqual(sent.returncode, 0, sent.stderr)
        agent.call(5, "inbox")
        self.assertIn('"kind": "handoff"', agent.response(5)["result"]["content"][0]["text"])
        self.assertEqual(self.cli("send", "agent", "s", "b", "--kind", "order").returncode, 2)
