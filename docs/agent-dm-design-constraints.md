# Local cross-family agent messaging — design constraints gathered before the prior-art synthesis

Collected 2026-09-07 from Matt's brief, darker's own record, and the Codex session's replies.
This is the constraint list the synthesis must score candidates against.

## From Matt (the brief)
- Local. Any project. A developer-environment tool, not a darker feature.
- Each agent session has an identity and is registered online/offline per project.
- Agents from different families (Claude Code, Codex, others) can address each other.

## From darker's record
- Pull, never push. JOURNAL +286: an inbound peer message auto-delivered into a running
  session's transcript is an unlogged, unvetted turn. Content enters an agent only via an
  explicit tool call, framed as untrusted data with origin attached.
- Dead instrument reads as clean. Presence must fail closed: unknown liveness = offline.
- A send receipt is not a delivery receipt (JOURNAL +286, 2.1.238 re-probe).
- Claims: M2b work-claim gate — a crashed holder's lease lapses to STALE for human
  reconcile, never an auto-steal.
- Unattended surfaces must be able to deny the inbox tool wholesale (same denylist that
  refuses SendMessage/ListAgents today).

## From the Codex session (2026-09-07, two replies)
Never:
1. Turn peer messages into permissions or hidden instructions.
2. Launch paid turns automatically.
3. Interpret silence as permission to take over work.
4. Collect transcripts or credentials by default.
5. Confuse queued, delivered, and acknowledged messages.

Presence facts:
- Explicit session registration plus expiring heartbeats; MCP carries messages, not identity.
  (Codex-side facts offered: MCP readiness can lag session startup; end hooks cannot call
  MCP tools; Codex is said to have SessionStart/SessionEnd command hooks — UNVERIFIED,
  the native-capabilities agent is checking.)
- Presence, availability, and ownership are three separate facts. A heartbeat proves recent
  contact, not willingness to accept work. An expired heartbeat must never release a file
  claim automatically — a claim lapses to stale for a human, which is darker's M2b rule.

## Derived: the state model the tool must expose
- presence:     online | stale | offline        (liveness; fail-closed)
- availability: accepting | busy | unattended   (declared by the agent; never inferred)
- ownership:    claim{paths, branch, holder, since} → held | stale | released
                (stale only by expiry; released only by holder or human)
- message:      queued → delivered (fetched by an explicit tool call) → acknowledged
                (three distinct receipts; none implied by another)
