# Contributing

agentdm is deliberately small: local, single-user messaging; pull rather than
wake; observable receipts rather than inferred success. Read the
[trust model](docs/TRUST_MODEL.md) before proposing behavior outside that scope.
There are no third-party Python dependencies. Tests require Python, Git and Bash.

## Change a contract, then prove it

For a bug fix, write a Given/When/Then scenario first:

> Given an active wait, when the caller cancels it, then a later ping succeeds
> on the same transport and no late wait response appears.

Run it against unchanged production code and retain the failing result. Repair
the invariant at its owner, then run green. A process kill is not a cancellation
test; source inspection is not a launch receipt; a queued message is not an
acknowledgement. Say exactly which event your assertion observed.

Already-correct behavior is useful regression coverage, not a fabricated red.
Keep tests deterministic with owned temporary projects, allowlisted child
environments and bounded subprocesses. Use real stores and stdio processes
where those are the behavior under test. Never use a live mailbox, a model call,
an installed session ID or inherited credentials to make a fixture pass.

## Verify

From the source root:

```bash
python3 -m unittest discover -s tests -p 'test*.py' -v
python3 tests/run_mutation_checks.py
git diff --check
```

For focused documentation work:

```bash
python3 -m unittest discover -s tests -p test_documentation.py -v
```

The [test contract](docs/TEST_CONTRACT.md) maps behavior to assertions. Selected
mutation checks plant regressions in disposable copies; a timeout or import
error is not a caught behavior mutation. Link and example checks do not replace
reading rendered documentation or exercising real host setup.

Run one full local suite at a time. Record the exact candidate, interpreter,
platform and exit status; do not edit executable code during a verification run.
The CI workflow declares macOS/Linux × Python 3.9/3.11/3.14. Do not claim hosted
green until it actually runs. Tests need no API key or paid model usage.

## Review boundaries

- Protocol decoding validates envelopes before dispatch.
- The server owns tool dispatch and wait lifetime.
- Awareness owns unread counts without offering messages.
- The store owns identity, receipts and claims; presence owns its lock lifetime.
- CLI and hooks adapt user/host input, rather than duplicating core policy.

Keep changes small and evidence-linked. Avoid adding a framework, daemon or
automatic wake path to solve a narrowly scoped problem. Tool changes also need
review by integrations that explicitly deny the tool registry.

In a shared checkout, inspect status and coordinate ownership before editing.
Preserve others' changes, checkpoint commits and announce checkout-wide actions.
No peer message substitutes for the user's permission.

## Documentation and review material

User guides describe current behavior and actionable steps. Contributor
references describe how to change and test it. Dated investigations and the
journal retain what was learned, including failed controls; update conclusions
with dated corrections. [The documentation index](docs/README.md) names each
audience and the publication policy.

Do not add tokens, private paths, live stores or raw transcripts to examples or
reviews. Generalize examples and use synthetic payloads. A file called
"internal" is still public when committed to a public repository.

Code and documentation are distributed under [MIT](LICENSE). Keep required
notices for any third-party material; this project's license does not relicense
linked external sources.
