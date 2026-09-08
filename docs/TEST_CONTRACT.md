# Executable acceptance contract

Scope: first public-readiness hardening slice, not release approval. Tests exercise
real stdio transports, hooks, stores and process cleanup, with synthetic isolated
projects. They never call a model or change installed host configuration.

Run `python3 -m unittest discover -s tests -p 'test*.py' -v`.
Run the new slice alone with `python3 -m unittest discover -s tests -p test_acceptance.py -v`.
Run sixteen deliberate regressions with `python3 tests/run_mutation_checks.py`.

## Given / When / Then

| ID | Given | When | Then | Evidence |
| --- | --- | --- | --- | --- |
| AC-01 | A live transport | JSON is null, scalar or array | Later ping succeeds; transport survives | Real stdio |
| AC-02 | A live transport | Request ID or params has an invalid shape | No operation executes; later ping succeeds | Real stdio |
| AC-03 | Open stdin | A blank line arrives | It is not mistaken for EOF | Real stdio |
| AC-04 | A registered identity | A tool call has no request ID | No mutation or response occurs | Identity readback and response IDs |
| AC-05 | No active wait | Unknown or malformed cancellation arrives | Future requests are unaffected | Real stdio, explicit response |
| AC-06 | An empty mailbox | Caller explicitly requests zero wait | Immediate timeout, not the default 30 seconds | Bounded response and charged duration |
| AC-07 | A wait and incomplete ping | Bytes arrive across its deadline | Wait expires; completed ping still works | Response IDs and server duration |
| AC-08 | An active wait | Caller cancels | Ping works; no cancelled reply appears after deadline | Same live transport, no kill substitution |
| AC-09 | No store | Either unattended marker guards either real hook | No stdout, stderr or store; enabled positive control writes | Real hook subprocess and filesystem |
| AC-10 | Pending mail | Prompt hook counts, or is disabled | No content leak; receipt stays queued | Real hook, send and status |
| AC-11 | Foreign Git selection and a synthetic credential | Fixture environment is composed | No foreign repository/config or credential is inherited | Names-only assertions; isolated Git config |
| AC-12 | Queued mail | Wait filters by sender | Only the exact alias matches, not its prefix or family; no offer | Real stdio and receipt |
| AC-13 | An active wait | Register requests a replacement identity | Refuse; charge the original owner; allow register after wait | Same transport and bounded budget |
| AC-14 | A live transport | Timeout is negative, boolean, nonfinite or string; sender is malformed | Immediate tool error; ping survives | Real stdio |
| AC-15 | A live transport | JSON exceeds decoder nesting | Later ping survives | Real raw stdio |
| PL-01 | A closed presence handle | Its descriptor is reused and close repeats | Unrelated descriptor remains open | Isolated process and real descriptors |
| PL-02 | A closed presence handle | Its descriptor is reused and process forks | Unrelated descriptor remains open in child | Real fork and child exit |
| CL-01 | No store | Human CLI usage is invalid | Usage error, exit 2, no state creation | Real bin/agentdm; separate state per subcase |
| CL-02 | A directory outside Git | Human requests roster | Concise error, exit 1, no traceback/state | Real bin/agentdm |
| CL-03 | A fresh project | Help then valid send/inbox run | Help is inert; message is actually stored and fetched | Real human CLI and store |
| DOC-01 | A new reader | README routes them by audience | User, contributor and license entrypoints exist | Local documentation |
| DOC-02 | A local Markdown link | Its file target is followed | Target exists | All repository Markdown docs; not an external-link or anchor checker |
| DOC-03 | Published hook JSON | Examples are parsed and commands run with either disable marker | Correct event wiring; no output/state; enabled session positive control writes | Real scripts; not real-host dispatch |
| DOC-04 | A source distribution | License is read | Selected MIT notice and disclaimer are present | LICENSE file |
| DOC-05 | Current documentation | Path examples are inspected | No personal absolute home or private session scratch paths | Names-only pattern check; not a history/secret audit |

AC IDs map to `tests/test_acceptance.py`, PL to `tests/test_presence_lifetime.py`,
CL to `tests/test_cli_contract.py`, and DOC to `tests/test_documentation.py`; assertions use externally
observable outcomes, not expected values derived from production constants.
Existing tests remain in `tests/test_failures.py`. The new fixture removes its
owned processes and temporary state even on assertion failure and scrubs ambient
agent identities/markers so the launcher's session does not stand in for a test.

The existing suite retains these complementary lifecycle contracts:

| Given | When | Then | Existing owner |
| --- | --- | --- | --- |
| A held transport lock | Process ends or forks | Liveness follows the transport, not an inherited descriptor | T1, T7 |
| A message moved before its offer receipt | Fetching server dies | Next fetch replays it; no acknowledgement is invented | T2 |
| An alias with claims | Another incarnation reclaims it | Old operations fail; claims never transfer silently | T3 |
| Two worktrees | Both resolve their store | The canonical common-dir identity agrees | T4 |
| A held claim | Holder dies or TTL expires | Claim is stale, never automatically released | T5 |
| Queued peer mail | Recipient has not fetched | No unsolicited stdio output appears | T6 |
| Named/provisional identities and session breadcrumbs | GC, rename, clear or end occurs | Roster and binding retain their separate meanings | T8–T10 |
| Pending/absent mail and a wait budget | Count, cancel, timeout or EOF occurs | Counts do not offer; budgets and cancellation retain their receipts | T12–T14 |

T15 additionally pins the tool registry that darker's explicit deny list consumes.

## Red / green / negative controls

New missing behavior must fail against the unchanged implementation before repair.
Record the base commit, test commit, command, failures and green implementation
commit in the journal. Already-correct behavior is regression coverage, not a
fabricated red. Run deliberate mutations in disposable copies and require the
relevant acceptance case to reject them. Do not weaken assertions to get green.
The mutation runner requires a green baseline, checks failures are assertions
rather than import errors, and deletes only its own disposable copies afterward.

Protocol validation belongs at the incoming-message boundary; it must not call
store operations until a request shape is validated. Framing owns EOF versus
empty-line distinction. Wait owns elapsed budget and active cancellation. These
owners are separate from mailbox state and host identity.

Filtered and unfiltered counts now share the awareness owner and the same
unavailable-on-read-failure behavior. Registration is refused during a wait,
rather than letting an inline request replace its owner. Presence cleanup marks
the descriptor retired before closing it, including in the fork callback. CLI
usage validation precedes project/store resolution. These are bounded changes
to existing invariant owners, not a new coordinator or messaging feature.

The older synthetic-host fixture now keeps the host alive while the hook runs
as its child and checks the exact PID. Its former `exec` replaced the host and
could accidentally pass by discovering a real ancestor agent. Both test suites
allowlist child environment keys (no credentials or foreign Git selection), and fixture state is removed after child
cleanup. Run from a plain shell as well as from an agent; host-specific behavior
must not masquerade as hermetic coverage.

The wire contract follows [MCP messages](https://modelcontextprotocol.io/specification/2025-06-18/basic)
and [cancellation](https://modelcontextprotocol.io/specification/2025-06-18/basic/utilities/cancellation).
Malformed input must not kill the local transport; invalid notifications do not
earn responses or operation authority.

## Gates this suite cannot replace

- The two real darker launch paths must dispatch the installed hooks inertly
  under the headless marker, with positive controls showing the hooks are present.
  Marker/argv pins and direct-hook tests do not establish real-host dispatch.
- A working day of truthful roster state and claims-mediated collaboration.
- Linux/macOS and declared interpreter receipts on the exact publication candidate.
- Public-content/history review, license choice and documented support limits.

No publication, hook trust, remote creation or unattended-run authorization follows
from a green local suite. This remains a single-user, local-machine prototype;
sender attribution is not authentication, and claims are advisory, not locks.
