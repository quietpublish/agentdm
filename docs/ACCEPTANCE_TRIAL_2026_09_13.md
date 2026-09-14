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
