# Public-readiness receipt — 2026-09-07 CDT

Later work and current release gates: [second release review](RELEASE_REVIEW.md).
The first-slice receipts below are preserved as historical evidence.

This is the first executable hardening slice, not approval to publish or activate
hooks. The release target was assumed to be agentdm, including darker's integration;
the installed checkout and running server were left unchanged.

## What was actually tested

Base: `025863e`. Red test commit: `6ffa40e`. Implementation: `f9835d1`.
Final executable candidate: `b9b26ee97f20307d4c4fdd3e452cb8acd12a0473`.
This receipt is a subsequent documentation-only addition.

[The Given/When/Then contract](TEST_CONTRACT.md) maps eleven new scenarios to
tests and retains the older lifecycle contracts. These use actual stdio child
processes, hooks and disposable Git/state stores, not mocked responses or models.

The first corrected red run on the unchanged implementation ran ten scenarios:
14 failing subcases across AC-01–AC-06, with AC-07–AC-10 passing. It found:

- non-object JSON and malformed envelope shapes could terminate dispatch;
- an empty line was mistaken for EOF;
- a notification-shaped tool call could mutate identity and produce a response;
- unknown cancellation could suppress a later request, and malformed cancellation
  could terminate dispatch;
- explicit zero wait selected the default duration.

Repairs keep wire validation in `agentdm/protocol.py`, before store dispatch;
framing distinguishes EOF from an empty line; cancellation names only an active
wait; zero stays zero. Later AC-02 assertions additionally require the refusal
code and unchanged identity, not survival alone.

Full-suite execution also found an existing fixture that replaced its fake host
with the hook using `exec`. It could pass accidentally beneath a real agent host.
The corrected fixture keeps that process alive and checks its exact PID. AC-11
was separately observed red for inherited Git selection, then passed after
allowlisting fixture environments and disabling inherited Git configuration.
Children are cleaned up before their temporary stores; an unclosed read was fixed.

## Final local receipts

Command on the frozen candidate:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test*.py'
```

| Platform | Python | Tests | Exit | Elapsed |
| --- | --- | --- | --- | --- |
| Local macOS | 3.9.6 | 50 | 0 | 49.804s |
| Local macOS | 3.11.15 | 50 | 0 | 46.215s |
| Local macOS | 3.14.6 | 50 | 0 | 35.894s |

Sequential runs, no model calls. Timings are receipts, not performance baselines.
Earlier intermediate green runs are not substituted for these final runs.

`python3 tests/run_mutation_checks.py` on Python 3.11.15 rejected all eight
deliberate regressions by assertion: scalar JSON, notification authority, blank
line/EOF confusion, zero/default confusion, renewed deadline, ignored cancellation,
session-hook disable removal and prompt-hook disable removal. No surviving or
invalid mutation; this is a selected boundary check, not an overall mutation score.

## Release gates still open

| Gate | State |
| --- | --- |
| Local executable contracts and selected mutation checks | Passed at the candidate above |
| Linux/macOS hosted matrix, Python 3.9/3.11/3.14 | Workflow configured; not run |
| Both real darker launch paths dispatch installed hooks inertly, with positive controls | Pending; direct hook tests and marker pins are not this proof |
| One ordinary working day of truthful roster state and claims-mediated coordination | Pending |
| Tracked content and complete Git history reviewed for public disclosure | Pending |
| License selected by the owner and published support scope settled | Pending |
| Second-machine install and exchange | Pending; no portability claim from one Mac |

Keep the same-user/local-machine trust limitation visible. Do not turn configured
CI, direct-hook tests or a queued message into a stronger receipt than it is.
No push, remote creation, installation, live hook trust or paid work was performed.

Diagnostic hygiene: during test construction, a failing assertion printed inherited
environment values into session tool output. The assertion now reports names only,
and fixtures inherit an allowlist rather than credentials. The operator was notified;
raw development logs must not be published, and affected credentials should be
rotated. No credential values were copied into repository files by this work.
