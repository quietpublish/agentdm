# Acceptance trial record — 2026-09-13 (working session)

Second record under the [acceptance trial protocol](ACCEPTANCE_TRIAL.md), after
the [first](ACCEPTANCE_TRIAL_2026_09_12.md). Evidence as found, local time
(CDT). `<checkout>` is the agentdm source checkout, `<state>` the state root.
Unlike the first day, the operator chose ordinary work rather than scripted
tasks; the recorder wrote no prompts.

## Preconditions as found (23:50)

| Precondition | State | Evidence |
| --- | --- | --- |
| 1. Unattended runs protected | As before: deny list on both darker surfaces; hook inertness has local receipts; the real-launcher hook receipt is still open | darker `d3d94417`; AR-01 |
| 2a/2b. Claude Code hooks | Session and prompt hooks at user scope (unchanged); **the experimental PostToolUse count hook added at project scope** in darker's local settings, claims wording, five-second timeout | `.claude/settings.local.json` in darker (gitignored) |
| 2c. Codex hooks | **Installed and trusted** this evening: `.codex/hooks.json` in darker with SessionStart (matcher `startup|resume|clear|compact`), SessionEnd, UserPromptSubmit; trusted through `/hooks` four times as the definition was diagnosed | trust entries in the Codex config; the three findings recorded in [HOOKS.md](HOOKS.md) |
| 3. Private backup remote | Unconfirmed, as before | |

Both hosts launch `<checkout>/bin/agentdm-server` at `4641477` (public main),
which carries everything built since the first record: outcome receipts,
pager with cap and ids, awareness envelope, diagnosing wait, contested claims,
`log`, `glance`. Both new servers were spawned at 23:48:55–56, so they run
that code.

### Roster snapshot, darker store (23:50)

```text
claude-code-a64f54bd   online          host 2298, startup binding 23:48:54
codex-2954             online          host 2321, startup binding 23:49:42 (first prompt)
claude-code-499d8039   transport-only  this morning's session, resumed in-process (P-1 pattern)
codex-43702            transport-only  this morning's Codex session, pre-hooks
human                  n/a
```

**First time both hosts read `online` at once.** The Codex row bound at its
first prompt, 48 seconds after its server started, consistent with the
first-turn finding. Two older servers from this morning are still alive in
the checkout and correctly read `transport-only`.

Claims: one stale claim from last night's Codex session (`68ee0f1cd0ae`, six
paths, holder gone). Not released; the human reconcile is available if it
gets in the way. Unread mail sits in four retired or offline mailboxes from
earlier days (`glance`: `codex-b:1 codex-darker:4 darker-22:1 darker-be:3`);
truthful, and litter for the operator to `gc` or leave.

Checkout: darker main at `357bf36f`, clean apart from the untracked
`.codex/` pilot directory.

## Observations (append as found)

| Time | Kind | Observation |
| --- | --- | --- |
| 23:50 | presence | Both new rows `online` from their first turn. No wrong presence. |
| 10:12 (09-14) | presence | The operator started fresh sessions the next morning: `claude-code-e844d57a` (bound at startup 10:12:52) and `codex-86736` (bound at its first prompt, 10:23:20). Both `online`. Last night's pair had ended. |
| 10:23 | round 1 | Task A (toolchain table in `docs/COMPATIBILITY.md`, now thirteen rows with required/optional) and Task B (`bin/darker-doctor` added to `docs/INSTALL.md`, pointer left in the compatibility doc) are both done in the working tree, uncommitted. Both files carry the same mtime, 10:23:56, thirty-six seconds after Codex's first prompt: consistent with Claude finishing the table earlier and Codex writing INSTALL plus the pointer in one turn. |
| 10:27 | claims / messages | **No claim and no message was created in any store in the last twelve hours.** Neither agent used agentdm during the round. The natural overlap happened (both edited `docs/COMPATIBILITY.md`) with no claim to find and nothing to negotiate; no overwrite is visible, because the edits landed in different paragraphs and sequentially. Whether the operator's prompts asked for claims is pending the operator's report; if they did, this is the day's central finding, and if they did not, it is the baseline the protocol expects from uninstructed agents. |
| 10:27 | nudges / pager | Nothing to nudge and nothing to push: no request existed. The PostToolUse pilot on Claude and the prompt hook on Codex had zero unread to report and stayed silent, which is correct. |
| 10:35 | round 1 (operator report) | Neither prompt asked for claims; both were the task descriptions verbatim. Round 1 is therefore the **uninstructed baseline**: agents with agentdm available, nudges live and a real overlap did not coordinate at all. The Codex prompt even ended with the recorder's aside "that last step is where it meets Claude's claim"; Codex edited the file without calling `claims`. A passing mention is not an instruction. Round 2 repeats the shape with the one-line coordination convention from the protocol added to both prompts, for a direct comparison. |
| 10:35–10:37 | round 2 | Same sessions, same shape, the convention paragraph added to both prompts. Store timeline, no human in it: 10:35:08 Claude claims `docs/OPERATOR_GUIDE.md`; 10:35:50 Codex claims `README.md`; 10:35:53 Codex sends Claude a `claim`-kind request **with `about_claim`** naming Claude's claim; 10:36:01 Codex finishes README, releases it at 10:36:04; 10:36 the PostToolUse pilot on Claude emits a count (state file created, later reset when the mailbox drained); Claude fetches, `accept`s (outcome recorded), releases at 10:36:15 and replies at 10:36:20 with a duplication warning about its own edit; 10:36:34 Codex claims the guide, edits it at 10:36:46 "preserving your edits", releases at 10:36:48, and sends a done note at 10:36:50. **Request to release: 22 seconds. Whole conflict: 62 seconds.** |
| 10:39 | checkout | The shared file holds both edits: Claude's nine-row wrapper table (it found and documented `darker-doctor` itself) followed by Codex's preflight line pointing at INSTALL. No clobber, no duplicate. README carries the same line. All four files from both rounds are modified and uncommitted, as instructed. |
| 10:39 | nudges | Claude: the PostToolUse pilot fired once, mid-task, and the holder fetched and answered. The first live use of the mid-turn count, and it did what the experiment predicted under the claims wording. Codex: no request ever reached it; its prompt-hook count had nothing to say. |
| 10:39 | pager | Two pushes admitted by the cap window: the request at 10:35:53 and the accept at 10:36:20, each with ids. Operator to confirm receipt. |
| 10:39 | contested | Claude's claim read `contested` for the 22 seconds between request and outcome, with `codex-86736`'s request listed under it; it now reads released with the request `acknowledged`, outcome `accepted`. First live use of `about_claim`, chosen by the requester unprompted. |
| 10:39 | relays / authority | None. No operator prompt between the two task prompts. No message started work: Codex's request asked; Claude's accept was its own decision within its task. |
| 10:41 | pager (operator report) | Phone shows both pushes: 10:35 "codex-86736 -> claude-code-e844d57a: claim [msg 94f134de] [claims cede3f79df6a]" and 10:36 "claude-code-e844d57a accepted claim from codex-86736 [msg 94f134de]". Ids present, no path, no subject. |
| 10:41 | authority (store) | Verified from the store rather than by report: all three round-2 claims were released by their holders, zero messages from `human` since 10:30, zero outcomes decided by `human`. No intervention of any kind. |
| 10:41 | organic use | The same phone screen shows pushes from 2026-09-12 that no trial produced: `darker-be -> codex-61473: question` and `codex-61473 accepted question from darker-be`, twice. The store confirms two outcome receipts recorded by `codex-61473` on 09-13 02:27Z and 03:05Z. Two sessions doing ordinary darker work adopted request kinds and outcome receipts on their own, the day after they shipped. |

## Summary

Round 1 and round 2 used the same two sessions, the same store, the same kind
of overlap and the same recorder, and differed by one paragraph in the
prompts. Round 1: zero claims, zero messages, the overlap resolved by luck.
Round 2: three claims, one contested claim, one request naming the claim it
concerned, one accept receipt, two pushes, a duplication warning, a done note,
and a shared file holding both edits, in 62 seconds with no human action, the
mid-turn count on Claude firing once and doing its job. In the protocol's
categories: no wrong presence (both hosts `online`, the first time), one nudge
that was needed and one that correctly stayed silent, no relays, one claim
disagreement resolved by message, no unauthorized work.

What is still not the protocol's full day: the tasks were chosen by the
recorder and lasted minutes; the request always concerned a file the holder
was actively editing; the operator was watching. The preconditions are now
met except the private backup remote (unconfirmed) and the real-launcher hook
receipt (still open). The pager earned its place on this evidence: both pushes
were correct, carried what the human would need, and the human needed neither.

The lever, confirmed for the third time in three days: the tool works when an
agent is told the convention exists. Nothing in agentdm makes an uninstructed
agent coordinate, and nothing should.
