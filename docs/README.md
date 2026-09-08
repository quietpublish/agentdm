# Documentation

Start with the [project overview](../README.md). Current guides take precedence
over dated development records when you are deciding how to use agentdm.

This tree is a [clean-history release snapshot](EXPORT_NOTE.md). Development
revision references below belong to the retained local history, not this new
repository's ancestry.

## User-facing guides

| Read this | When you need |
| --- | --- |
| [Getting started](GETTING_STARTED.md) | Source setup, host connection, first exchange and removal |
| [Usage](USAGE.md) | Agent tools, human CLI, receipts and advisory coordination |
| [Optional hooks](HOOKS.md) | A staged, explicitly trusted awareness pilot and rollback |
| [Support and trust limits](TRUST_MODEL.md) | Supported scope, authority boundaries and reporting hygiene |

These pages should be usable without knowing darker, a work-order number, a
developer's local paths or the history of the prototype. Examples use synthetic
names and path placeholders. Known limitations belong here, not only in a journal.

## Contributor and maintainer references

- [Contributing](../CONTRIBUTING.md): TDD workflow and verification commands.
- [Executable test contract](TEST_CONTRACT.md): Given/When/Then scenarios.
- [Acceptance trial](ACCEPTANCE_TRIAL.md): operator-owned live evidence protocol.
- [Roadmap](ROADMAP.md): intent and acceptance gates, not a support promise.
- [Release review](RELEASE_REVIEW.md): exact candidate receipts and open gates.
- [Unattended startup review](UNATTENDED_STARTUP_REVIEW.md): AR-01 red/green and bounded real-launcher receipts.

## Development archive—not onboarding material

These files remain at their existing paths so evidence links do not break.
They are retained for design provenance, not as current install instructions:

- [Journal](JOURNAL.md): lessons and dated decisions.
- [First public-readiness receipt](PUBLIC_READINESS.md): superseded test snapshot.
- [Design constraints](agent-dm-design-constraints.md): the original brief.
- [Prior-art synthesis, revision 2](PRIOR_ART_SYNTHESIS_2026_09_07.md): reviewed research.
- [Prior-art synthesis, revision 1](PRIOR_ART_SYNTHESIS_2026_09_07.v1.md): superseded claims retained as history.
- Lane reports: [protocols](lane-1-protocols.md), [shipped tools](lane-2-shipped-tools.md),
  [native CLIs](lane-3-native-cli.md), [substrates](lane-4-substrates.md).

Research dates matter. A lane report may propose a design the implementation
later rejected. It must not be used to infer host compatibility, storage layout
or a release guarantee today.

## What belongs in the public repository

Source, tests, license, user guides and reviewed contributor references belong
in the public source tree. Sanitized development lessons can be useful too, but
they are optional reading, not prerequisites to use the tool.

**Every tracked file and reachable commit will be public if that history is
published.** Calling a file an archive or internal does not restrict access.
Personal-path examples are generalized in the current tree; the existing Git
history still needs its separate disclosure decision and final review.

Never include runtime mailboxes, credentials, reclaim tokens, private host
configuration, raw transcripts or scratch dumps. Do not hide those behind a
directory name or rely on `.gitignore` to remove already committed content.
No history rewrite, removal of development evidence, or public push follows
from reorganizing this documentation.
