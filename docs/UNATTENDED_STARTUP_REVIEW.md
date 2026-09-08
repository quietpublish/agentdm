# Unattended startup review — 2026-09-08

## AR-01: denying tools did not prevent registration

The published base `504cb9d` still registered an MCP incarnation, acquired a
presence lock and wrote an environment session binding when a host spawned it
with `DARKER_HEADLESS=1`. Both hooks were silent and the host withheld every
agentdm tool. The missing invariant was at startup, before any tool call.

Test-only commit `5fe4e19` added four Given/When/Then scenarios (UA-01–04).
Against unchanged production code they produced nine failing subcases; the
enabled control passed. Fix `7006db5` checks either nonempty disable marker
before project/store resolution or identity work, advertises an empty registry,
and refuses even cached direct tool calls. Initialization, ping and EOF remain
usable. Startup is silent. No message, binding, lock or registration is created.

The server constructor owns this boundary; the existing tool-call refusal owns
the error response. No mailbox policy, tool registry, hook behavior, human CLI
or host configuration changed. The markers are inherited configuration, not
an authorization mechanism against a host that clears them. Existing processes
must restart to pick up the implementation and environment.

## Actual launcher controls

The replay used darker denial branch `cab1d9ca`, real Claude Code 2.1.263 for
the shell lane and the SDK-bundled 2.1.259 for the SDK lane. Separate enabled
controls used each exact CLI binary. Agentdm, projects, messages and host config
were isolated; a macOS sandbox denied network and restricted writes to the
pilot. An independent socket control received EPERM before launch. Prompts were
synthetic and a separate host hook blocked processing; every actual host result
reported zero turns and zero cost.

| Case | Published base | Fix `7006db5` |
| --- | --- | --- |
| Enabled CLI controls | 11 tools, dispatched hooks, one unread count, state written | Same enabled behavior |
| Real shell launcher | No tools/context, but registration/binding/presence written | No tools/context; complete agentdm state unchanged |
| Shell `/darker` prelaunch | Not replayed on base in this slice | Same isolation; prelaunch path exercised |
| Real SDK launcher | No tools/context, but registration/binding/presence written | No tools/context; complete agentdm state unchanged |

The fixed unattended cases witnessed both hooks executing with the marker and
zero stdout/stderr. State comparison included presence files and directory
inventory, not just mailbox receipts. Synthetic mail stayed queued everywhere.
Twenty recorded pilot PIDs/process groups were absent after completion.

Two replay corrections are retained as failures, not erased: the SDK ledger
is in the sprint directory, not the run directory; and a deliberately blocked
SDK task exits 1 with `evaluator_escalated`. Its zero-turn host result proves the
observation boundary, not a successful darker sprint. The first replay rejected
that exit rather than accepting missing evidence.

## Limits

The 68-test suite passed on local Python 3.9.6, 3.11.15, 3.14.6 and 3.13.7. The first
Apple Python 3.9 run hit the existing two-second session-hook launch timeout;
a full serial rerun with no live host pilots passed unchanged. The timeout's
cause is not established. All 18 selected mutations were rejected by assertions
on 3.11.15, with no invalid/surviving cases. On 3.13.7 and 3.14.6, the existing recursion
mutation survived: that interpreter accepts the 2,000 nested arrays used by
the fixture, whereas 3.11 raises `RecursionError`. That mutation run is not
green; both new startup mutations were caught on both interpreters. Python 3.13
is outside the declared CI matrix, but 3.14 is supported, so portable mutation
coverage remains an explicit test-hardening follow-up. Increasing array depth
alone is not a demonstrated portable fix: 3.14 also accepts 20,000 nested arrays
in a direct stdlib control. No unrelated parser change or weakened acceptance
assertion is included in the startup repair.

These are isolated macOS launch receipts, not shared hook activation, ordinary
model-context delivery, a working-day trial or a production-release guarantee.
The shell uses a recording CLI shim; the SDK uses its actual launch artifact
and host messages. Enabled controls prove both binary versions dispatch the
hooks, but do not constitute an enabled darker SDK task (that lane is purposely
unattended). No installed checkout or shared configuration changed.

The hook observer adds a parent process; its startup breadcrumb is dispatch
evidence here, not a fresh proof of exact host-PID binding. The prompt control
works through the server's synthetic environment binding. Earlier direct-hook
lifecycle controls remain a separate receipt.

Run the portable scenarios with:

```bash
python3 -m unittest discover -s tests -p test_unattended.py -v
python3 -m unittest discover -s tests -p 'test*.py' -v
python3 tests/run_mutation_checks.py
```

The local replay archive is private synthetic evidence, not shipped runtime
data. Publishing this fix still needs CI on its own candidate; baseline CI does
not verify a later commit. Host denial and shared activation remain separate
integration/operator decisions.
