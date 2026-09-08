# Acceptance trial protocol

Adopted from the Codex session's rollout recommendation (2026-09-08). The trial answers whether the
roster is truthful and whether claims mediate a shared checkout during ordinary work. It is
observation, not a demonstration: evidence is preserved as found, never cleaned to look green.

Maintainer protocol. For current reader-facing setup and rollback, use
[Optional hooks](HOOKS.md). Do not treat the prerequisites below as completed
because the scripts or their unit tests exist.

## Preconditions (each a separate operator authorization)

1. **Unattended runs protected first.** darker's unattended surfaces deny `mcp__agentdm__*` beside
   `SendMessage`/`ListAgents`, AND both agentdm hooks are inert under `DARKER_HEADLESS=1` (built and
   tested here: no output, no breadcrumb, no store). A tool deny alone does not close the hook path.
2. **Hooks activated in two steps**, scoped to the darker checkout. First the session hook; verify
   startup, end and reconnect read truthfully (`online`, `transport-only`, `offline`, `ambiguous`
   explicit). Then the prompt hook. In Codex, review the definitions through `/hooks`; never bypass
   hook trust. Record the agentdm revision and the interpreter path each host resolves for `python3`.
   Rollback: `claude mcp remove -s user agentdm`, `codex mcp remove agentdm`, delete the two hook
   entries; the store under `~/.local/state/agentdm/` can be left or removed by hand.
3. **A private backup remote** holding source, tests and docs; never the store.

Success is truthful presence, not every row reading `online`.

### Real unattended-launch receipt

Given a reviewed candidate and installed hook definitions in an isolated,
operator-approved pilot, when **each real unattended launch path** starts with
its disable marker, then the hooks emit no context and create/change no
breadcrumb or mailbox state. Confirm independently that the MCP server/tools
are excluded and that any spawned agentdm server stays inert: no registration,
session binding or presence lock, and no store changes. The server now honors
the markers at startup; record the actual loaded revision, not just checkout
HEAD. [AR-01](UNATTENDED_STARTUP_REVIEW.md) records why tool denial alone was
insufficient and the bounded launch controls for the repair.

Run an enabled interactive positive control first to prove the installed hooks
actually dispatch. Record the host/interpreter/candidate revisions, launcher,
marker, observed outputs and state changes for both controls. A missing hook,
mock CLI, source-text assertion or direct script invocation is not this receipt.
Obtain any needed host-trust and model-spend authorization separately.

## The working day

One small real task in darker with clear ownership, both agents live. Each agent:

- checks `git status`, `who` and `claims` before editing;
- claims the paths it will touch, checkpoint-commits, and releases claims explicitly;
- sends handoffs through agentdm, not through the operator.

Include **one deliberate claim conflict**: the second agent must stop and negotiate by message. It must
not overwrite, and it must not treat a stale claim as ownership.

## What to record (as found)

- wrong presence: any row whose state did not match the session's real state, with timestamp;
- missing or duplicate nudges;
- every manual relay the operator had to perform;
- claim disagreements and how they were resolved;
- messages that started or extended work without authorization (there must be none).

Then feature expansion stays frozen until this is complete. Gemini, Cursor, notifications and
packaging wait.
