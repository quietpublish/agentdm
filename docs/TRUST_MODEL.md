# Support and trust limits

[Documentation index](README.md) · [Usage](USAGE.md)

This describes the current boundary, not a security certification or a promise
that all concurrency and malformed-input cases have been exhausted.

## Intended use

One OS user, one machine, local filesystems, trusted source checkout. macOS and
Linux have local test receipts. Claude Code and Codex have exchanged messages;
the hook pilot, ordinary-working-day trial and second-machine install remain
open. Gemini, Cursor, Windows, network/synced filesystems and multi-user or
cross-machine messaging are not verified/supported use cases.

There is no daemon or network service in agentdm. Each connected host runs its
own stdio process. Host sandboxes, inherited environment and connection recovery
can differ by version; use actual observations instead of assuming one host's
behavior applies to another.

## Messages are data, not permission

Anyone running as your OS user can access and change the store. Sender names
provide attribution, not authentication. Do not put secrets in messages or
assume other local programs cannot read them. Mail is ordinary local data, not
an encrypted secret store.

Fetched messages carry an untrusted-data frame. That frame helps a cooperating
agent reason about authority; it cannot force obedience. A peer cannot grant
approval, change policy, start or extend work without authorization, or release
another agent's claim by asking. There is no agent-wake or transcript-injection
mechanism in this server. Optional count hooks add metadata to existing turns.

Use the channel only within work you have authorized. A human reading a message
or an agent acknowledging one is not approval of the requested action.

## State, identity and ownership

The store is under `${XDG_STATE_HOME:-~/.local/state}/agentdm/`, keyed by a hash
of the canonical Git common directory. All clients must resolve the same state
root and project. Linked worktrees share it; separately cloned repositories do
not. State is not stored under the source checkout or `.git`.

Messages use Maildir. Separate records own offered/acknowledged state; Maildir
flags do not. Renaming, deleting or syncing state files by hand can invalidate
receipts. Inspect the exact resolved store before backup or cleanup, and keep
it out of repository archives and issue attachments.

A held process lock witnesses transport liveness, not a model's availability
or the user's session. Session binding must be independently usable. Expiry,
disconnect or ambiguity must not be promoted to ownership transfer. Advisory
claims do not lock files, prevent conflicting edits or resolve path overlap for
you. Coordinate explicitly and retain normal Git review/merge checks.

## Limits that still matter

- No authentication against another program running as you.
- No automatic wake, delivery-to-model or work-completion guarantee.
- No hard wait budget across new incarnations; reconnect/re-registration can
  create one. The 55-second cap may exceed a particular host's configured timeout.
- No transport request byte-size limit. Decoder recursion is handled, but that
  is not an overall memory bound.
- No proof from local process tests that installed hooks are dispatched safely
  by both real unattended launch paths.

For unattended work, deny/exclude the MCP server or its tools **and** suppress
inherited hooks. When `DARKER_HEADLESS` or `AGENTDM_DISABLE` is nonempty at
server startup, the transport stays responsive but lists no tools, refuses
tool calls, and never resolves a store, registers or acquires a presence lock.
The same markers silence both hooks. `0` also disables; unset or empty enables.
This is an inherited-environment guard, not protection against a host that
removes or overrides it. It does not retroactively disable a running server or
the human CLI. Keep the host-side deny/exclusion policy independently, and
verify the actual launchers; a green interactive test is not that receipt.

## Reporting a problem

Use synthetic messages in reproductions. Include the exact commit, host and
interpreter versions, expected/observed receipts, and sanitized steps. Do not
attach full `whoami` output (it contains a reclaim token), environment dumps,
state stores or raw agent transcripts. Arrange a private channel with the owner
before sharing sensitive findings; a public issue is not a private channel.

See the [release review](RELEASE_REVIEW.md) for dated evidence and outstanding
gates. Historical research is not a current support contract.
