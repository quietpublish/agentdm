# agentdm journal

Newest first. Written at the moment of realization, not reconstructed. Append-only.

## 2026-09-08 — A denied tool can still have a live process behind it

The host withheld every agentdm tool and both hooks stayed silent, yet startup
still registered a session. Testing only what the agent could call missed what
the server had already done. The repair belongs before store resolution, not in
another tool deny entry. A disabled transport now stays responsive without
owning an identity or touching a mailbox.

The real-launcher replay also rejected our first receipt: a deliberately blocked
SDK task is escalated, not successfully completed. Zero turns is useful evidence
for this experiment precisely because it is not a successful sprint.
[AR-01](UNATTENDED_STARTUP_REVIEW.md) retains the red tests, fixture corrections,
enabled controls and unchanged-state observations.

## 2026-09-08 — The README is a user interface, not the development transcript

The old front page asked a stranger to understand our host investigations,
work-order IDs and personal filesystem before sending a first message. Those
records are useful, but they answer a different question from "how do I use it?"
The new front door is short; setup, usage, hooks and trust have their own guides,
with contributor and development records routed through a documentation index.
Existing evidence paths stay stable. Calling them an archive does not make them
private, and generalizing today's path examples does not erase Git history.

Checking the prose against the implementation and host references caught claims
we should not carry forward: one machine's environment is not every host's
contract, 55 seconds is not below every configured timeout, and offered is not
proof a host received the response. Documentation tests now make reader routes,
hook wiring, MIT notices and portable examples executable promises. Matt chose
MIT; [the release record](RELEASE_REVIEW.md) keeps that choice separate from
history disclosure and live acceptance.

## 2026-09-07 CDT — Cleanup must stop owning a descriptor after it closes

A presence handle remembered its fd number after closing it. The kernel reused
that number for another file, and a later fork callback closed the replacement.
The old cleanup test asked whether the presence lock disappeared. The missing
question was whether an unrelated new owner survived. Real repeat-close and
fork controls fail before the fix and pass after the handle retires its number.

The same ownership question exposed a wait whose identity could change while
it was running. Registration now waits for cancellation or completion; counting
uses the exact sender alias, and invalid bounds fail before consuming a wait.
The human CLI now rejects bad usage before creating state. These are fixes to
existing promises, not additions to the messaging surface.

[The second release review](RELEASE_REVIEW.md) records each red commit and the
final 59-test candidate across three local interpreters and offline Linux, plus
fourteen deliberately broken implementations caught by assertions. A Linux
receipt did not require a push. Publication still needs something tests cannot
choose: a license, the owner's public-history decision, and live acceptance.

## 2026-09-07 CDT — Given, when, then made the missing boundaries executable

Matt asked for stronger tests before a public release. Eleven named scenarios
now distinguish an empty line from EOF, a notification from a request, unknown
cancellation from authority over future work, and a zero wait from its default.
The first red run exposed fourteen failing subcases across six scenarios; the
repairs live behind a small incoming-protocol boundary rather than expanding
mailbox policy. Fifty tests pass on three local interpreters, and eight planted
regressions are rejected by assertions.

The tests needed scrutiny too. A fake host used `exec` to replace itself with
the hook, so a real ancestor agent could accidentally supply the missing host.
Keeping the fake alive and checking its exact PID made the fixture tell the
truth. A diagnostic assertion also exposed inherited environment values; names-
only failures and allowlisted fixture environments now keep diagnostics bounded.

[The receipt](PUBLIC_READINESS.md) and [GWT contract](TEST_CONTRACT.md) name the
evidence and the remaining live, platform and publication gates. A public-ready
label is not earned by a larger test count. The installed server remains on its
original checkout; these changes are a local review candidate.

## 2026-09-08 — The channel reviewed itself, and every finding was a claim I had not earned

Seven findings from the Codex session in one evening, DM-04 through DM-10, every one of them a
place where the code claimed more than the observable event supported. An end event without an
identity ended sibling sessions. A surviving host session was handed to a transport that had been
bound to a different one. A killed server proved cleanup on death and I called it cancellation,
when the wait was blocking the only thread and could not even read the cancel. A count that failed
printed the same silence as a verified zero. A fragment without a newline renewed a timeout I had
noticed and dismissed as rare, and Codex measured a 0.3-second wait lasting 1.08. Each fix was a
test written from Codex's reproduction, then the smallest change that made it pass, on three
interpreters, and each closure was verified by Codex at the exact commit.

From DM-05 onward the whole loop ran over agentdm itself. Finding, reproduction, fix note, revision
hash, verification receipt: pull-only, three receipts each, no relay. The channel's first real job was
reviewing the channel. Two rules to keep from it. Measure rather than dismiss: the thing I waved off
is the thing the other agent will time. And name what a test proves: a kill test proves cleanup, a
cancel test proves cancellation, and the README should say which is which.

Codex's closing recommendation is the right next step and it is not more code: live acceptance, a
working day of roster accuracy and claims-mediated collaboration, rather than further inferred
maturity.

## 2026-09-08 — The first exchange crossed, and every fact worth keeping came from a failure

The claim of the experiment held: a Claude Code session and a Codex session exchanged messages in
both directions with nothing pushed and three distinct receipts. But the day's durable facts were all
found by things going wrong. Codex's first `send` crashed because `python3` on this machine resolves
to pyenv 3.11 under both hosts, not the 3.14 the tests first ran on, and 3.11's content encoder cannot
compare a line length to a `max_line_length` of None. Codex's roster showed two rows for one process
because spawn-time registration and explicit registration each mint an incarnation. Killing my own
server to test respawn proved Claude Code does not respawn a stdio MCP server, which makes "the
server must never die on a per-call error" a hard rule rather than a preference. And a health check
run from the wrong directory made me report an alias in the wrong project's store, because the CLI
reads whatever repository you are standing in.

The lesson is the one darker keeps relearning: an instrument that says `transport-only` when it can
see a process but not a conversation is worth more than one that says `online` because a handshake
succeeded. Codex read its own row as `transport-only` with a null binding and reported exactly that,
without upgrading it. That is the behaviour to protect as this grows.

## 2026-09-07 — Build it, because everything that exists wakes the agent

Four read-only research lanes over about 36 tools, 6 protocols, 4 installed CLIs and 9 substrates
found no candidate that fit. The reason was consistent: every existing tool spends its effort on
waking the receiving agent, and every one that added a wake path grew a lock, repair and loop-guard
subsystem larger than its mailbox. Pull-only was a de-configured corner everywhere. Fail-closed
presence existed nowhere. The one project with the right identity vocabulary was a daemon with a
license rider. Maildir and a held `flock` fell out of the substrate lane; the Codex session's review
then corrected the synthesis in five places, the two that mattered most being that a lock witnesses a
process and not a session, and that moving a file proves a fetch and not a delivery. Seven failure
tests were written before any interface. Two of the first three hours were lost to my own test
harness: an eager `stderr.read()` that blocked until pipe EOF, and a `pkill -f` whose pattern matched
the shell running my tests.
