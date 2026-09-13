# Design note — the idle holder (2026-09-13)

Maintainer design note, not a decision record. Written the day after the
[acceptance trial record](ACCEPTANCE_TRIAL_2026_09_12.md), which produced the
evidence. Nothing here is built; the feature freeze from the
[acceptance protocol](ACCEPTANCE_TRIAL.md) still holds until the maintainer
chooses. Prepared from four parallel research angles; two were completed by
agents, two by the recording session directly after those agents stalled, with
host facts verified against the current hook references cited below.

## The problem, as observed

Agents learn they have mail in exactly two ways: a human starts a turn and the
optional prompt hook adds an unread count, or the agent itself calls `inbox` or
`wait`. On 2026-09-12 a Codex session claimed a file, ended its turn, and a
`claim`-kind request sat `queued` for 9 min 24 s until the human typed "check
your inbox". Codex had no hooks installed. The requester waited three 55-second
rounds and learned only `timeout`. The human's phone had the push within
seconds and was, in effect, the only party who knew.

## The boundary that holds

No mechanism inside the
[design constraints](agent-dm-design-constraints.md) can inform an **idle**
agent. A hook needs a turn to attach to; a message that starts a turn is a
wake, which spends money and authority without a human. That boundary is not
revisited here. Everything below does one of three things instead:

1. gets the count to a **busy** agent sooner;
2. makes idleness **visible** to everyone and **cheap to reconcile**;
3. makes the human's dispatch take seconds rather than a walk.

The four pieces compose. None pushes message content, starts a turn, adds a
daemon, or leaves the standard library.

## Piece 1 — every response is a receipt (no hooks, every host)

The server appends an awareness envelope to **every** tool result:

```json
"awareness": {"unread": 1, "pending_requests": 1, "contested_claims": ["1810b8098b24"]}
```

Counts and ids only, never a subject or body. A mailbox read failure renders
`"awareness": "unavailable"`, never zero (DM-09). `pending_requests` counts
request-kind messages addressed to me with no outcome yet. Any agent that
touches agentdm at all learns mid-turn, on any host, with no hook installed.

- Owners: server dispatch attaches; the awareness owner counts.
- Wire: one additive key on every `tools/call` result.
- Cost: two directory listings per call. Acked mail is never purged today, so
  this grows with mailbox size; acceptable locally, worth a later purge.
- What it would have changed: Codex called `claims` and `claim` before its
  14:33 commit; either response would have carried `unread: 1`.
- What it does not solve: an agent that makes no agentdm call in a turn, or no
  turn at all.

Alongside it, `wait` with `from_alias` returns a diagnosis on timeout rather
than a bare status: the peer's presence and availability, the time of its
last store write, and, when `message_id` is given, the request's receipt and
outcome. No new state; three existing facts reported side by side, each under
its own label. The rendered text must say that `transport-only` plus `queued`
means "no inbox call has happened", not "gone".

## Piece 2 — a mid-turn count hook, verified feasible on both hosts

Verified 2026-09-13 against the host references
([Claude Code hooks](https://code.claude.com/docs/en/hooks),
[Codex hooks](https://learn.chatgpt.com/docs/hooks)):

| Host | Event | Fires | Reaches the model via | Can block |
| --- | --- | --- | --- | --- |
| Claude Code 2.1.269 | `PostToolUse` | during the agentic loop | JSON `hookSpecificOutput.additionalContext` only; plain stdout goes to the debug log | no |
| Claude Code | `UserPromptSubmit` | turn start | plain stdout or `additionalContext` | yes |
| Claude Code | `Stop` | turn end | only by blocking the stop, which continues the turn | yes |
| Codex 0.154.0 | `PostToolUse` | after each tool | `hookSpecificOutput.additionalContext`; plain stdout ignored | yes (not used) |
| Codex | `UserPromptSubmit` | turn start | plain stdout or `additionalContext` | yes |
| Codex | `Stop` | turn end | JSON only; "can auto-generate continuation" | yes |

So one script can serve both hosts on `PostToolUse`, emitting JSON
`additionalContext` with a count only when the count has **changed** since the
hook last spoke, keyed by session in a small state file, so a long tool loop
produces one nudge rather than one per call. `Stop` is excluded on both hosts:
a Stop hook reaches the model only by keeping the turn alive, which is a wake
by another name. Codex project hooks require the exact definition to be
trusted through `/hooks`; that trust step stays with the human.

Prerequisite: Codex never had the session or prompt hooks installed, so its
rows read `transport-only` and it received no count at all. Installing the
existing two hooks there is the protocol's precondition 2 for that host and
comes before any new hook. Whether Codex's `SessionStart` payload carries a
session id and a host pid the existing session hook can use is UNVERIFIED.

Failure modes: hook timeout under load (missing evidence, not zero), ambiguous
binding (emit the fixed unavailable line), unattended markers (silent, as now),
and the duplicate-nudge case the protocol tracks, which the change-detection
state is the whole defence against.

## Piece 3 — leases and lock queues

Borrowed from database lock managers, where a lock wait is visible to everyone
with the blocker named and a wait timeout returns an error that says who held
what, and from Chubby-style leases, where a holder keeps its lease by activity
and loses it by silence.

- **Activity-renewed short leases.** A claim's TTL defaults to minutes, not
  twenty, and any agentdm tool call by the holder's incarnation renews it
  server-side. A holder that ends its turn stops renewing, so its claim reads
  `stale` within minutes. Stale is still never auto-released; it is the state
  in which the human's release is the sanctioned reconcile (M2b). Renewal is
  the holder's own act through its own server, not a hook's.
- **Contested claims.** `send` gains an optional `about_claim` id, stored as a
  header. `claims` derives, per held claim, the request ids and their receipts,
  and `contested: true` when any lacks an outcome. Derived at read time from
  mail and outcomes; the claim file is not written, `held` and release
  authority are untouched. The human CLI shows it too.
- **Warn, never refuse.** A `claim` by an agent with unanswered requests
  records the claim and warns through the envelope. Refusing would let an
  untrusted message gate a tool, which is a message granting authority in
  reverse, and a trivial denial of service.

Rejected: a declared deadline on requests. A lapsed deadline is exactly the
shape that invites "silence means proceed", and the holder never sees it
before fetching. Timeouts stay on the requester's side, as diagnoses.

What it would have changed: with a five-minute lease, the holder's claim would
have read `stale` at about 15:24, and `agentdm claims` would have shown it
contested by a named request since 15:22. The requester's third timeout would
have said so.

## Piece 4 — dispatch, not intervention

The human is the only party allowed to start a turn, so the design makes that
step cheap rather than pretending it away. On-call works the same way: the
pager wakes a person, the person opens the console, the page never runs the
runbook.

- **Dead ends, stated.** One-tap push actions need a listener on the machine
  (ntfy `http` actions) or a bot that polls (Telegram callbacks); neither is
  allowed. The human must not `accept` or `decline` on a holder's behalf: the
  outcome receipt means "the recipient explicitly answered", and the store
  already refuses it. Keep the refusal.
- **`agentdm glance`.** A read-only subcommand printing per-alias unread
  counts for the current project, creating nothing and offering nothing.
  tmux runs it from its status line on its existing interval; Starship as a
  custom module at prompt render. No process of ours stays resident.
- **Ids in pushes.** The pager for a request-kind message carries the short
  message id and the recipient's held claim ids, not paths, so the human's
  next command needs no lookup.
- **Escalation from the requester's own server.** When a requester's final
  `wait` on a named peer expires with the request still unoffered, its server
  sends one more push: "still waiting on codex-b, request unoffered, claim
  1810…". Event-driven, no daemon, one push, never repeated.
- **Two sanctioned moves, documented.** Dispatch: type one word, `agentdm`,
  into the holder's session; the prompt hook does the rest on Claude, and a
  project instruction file defines the word for Codex. Reconcile: `agentdm
  release <claim>` followed by a `note` to the requester, because `wait`
  watches mail, not claims; the request stays queued for the holder to
  decline as moot. Reconcile is for a holder that has ended its turn; dispatch
  is the default.

What it would have changed: 9 min 24 s becomes under two minutes, with every
receipt still produced by the party it names.

## Also from the trial

- The reply to an accepted or declined request is framed as kind `ack`; a
  capable model inferred from that kind that no outcome had been recorded,
  without calling `status`. Mark the reply frame: "outcome accepted recorded on
  <message-id>". Small, and it removes a real misreading.
- `register` and `whoami` return the reclaim token; a "report every tool
  result" instruction put it into both hosts' transcripts. Consider returning
  it once and redacting on `whoami`.

## Suggested order and validation

1. Piece 1 with the wait diagnosis (1–2 days). Scenario: given H holds C and
   R sends a request about C, when H calls any tool, then the result carries
   `unread: 1`, `pending_requests: 1`, `contested_claims: [C]` and no body;
   when R's wait times out, then the result names H's presence, availability
   and the request's receipt.
2. Piece 3 (about a day). Scenario: given a five-minute lease and a holder
   that makes no call, when five minutes pass, then the claim reads `stale`
   and `contested`, and only the holder or the human can release it.
3. Piece 2 as a two-host pilot (a day plus the pilot). Scenario: given a busy
   agent with a queued request, when its next tool call completes, then one
   count line reaches the model, and the next ten tool calls add none.
4. Piece 4 (half a day). Scenario: rerun trial step 3 with the glance
   segment on; record wall time from request to release, that `offers/` gained
   nothing from glancing, and that the outcome was decided by the holder.

Each scenario is written and run red before its code, per
[Contributing](../CONTRIBUTING.md).
