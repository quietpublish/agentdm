# Roadmap

Maintainer reference, updated 2026-09-10. This records intent and acceptance
gates, not delivery dates or a support promise. See the [user guides](README.md)
for current behavior and the [release review](RELEASE_REVIEW.md) for receipts.

## Current: an experimental local tool

Cross-family send/fetch/ack coordination has been demonstrated with Claude Code
and Codex. Local macOS and Linux tests cover process, store, protocol and hook
boundaries. MIT has been selected and the reader-facing documentation is being
prepared. None of that substitutes for a live acceptance day or publication.

Standing constraints: local, same-user, pull-only; one canonical project store;
separate presence, availability and claims; Python standard library; no daemon.

Added 2026-09-10, ahead of the acceptance day so it can observe them: message
kinds as declared intent, an `accepted`/`declined` outcome receipt separate from
`ack`, and an opt-in, metadata-only human pager over ntfy or Telegram. The pager
is the one outbound network path and is off unless the human enables it.

## Next: earn the release evidence

- Complete the two-step hook pilot after the real unattended launch-path checks.
- Observe one ordinary working day with truthful roster state, chosen names,
  no operator relaying messages, and one deliberately negotiated claim conflict.
  Two working sessions are recorded (2026-09-12, 2026-09-13/14); the second
  produced a negotiated conflict with both hosts online and no operator action.
  A full day of unscripted work remains to be observed.
- Run the declared hosted platform/interpreter matrix on the release candidate.
- Settle the public-history/privacy decision and review the final source archive.
- Have someone on a second machine follow the README and exchange a message
  without relying on the original developer's paths or knowledge.

The [acceptance protocol](ACCEPTANCE_TRIAL.md) owns what to record. Preserve failed
observations; do not clean them up to make a milestone look complete.

## Later: only after acceptance

- Verify Gemini and Cursor independently before claiming support.
- Exercise addressed handoffs during ordinary cross-family work, with claims
  consulted and explicitly released by interactive contributors.
- Consider a pinned-interpreter installer or packaging only after the
  second-machine setup establishes what is actually needed.
- The human pager earned its place on the 2026-09-14 evidence: pushes correct,
  carrying ids, and the human needed neither. Keep it; revisit if a full day
  shows it becoming a nudge to an agent by another route.

Feeding peer messages to unattended campaign children is not a planned shortcut.
Any future design for admitting that assistance needs separate authorization,
attribution and review; the mailbox itself grants none.

## Out of scope

Agent wake or transcript injection, a resident daemon, cross-machine transport,
cross-user authentication, a TUI, memory storage and task queues. Proposals that
need these should revisit the product boundary explicitly rather than quietly
expanding the existing tool.
