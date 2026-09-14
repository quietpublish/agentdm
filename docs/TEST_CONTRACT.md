# Executable acceptance contract

Scope: first public-readiness hardening slice, not release approval. Tests exercise
real stdio transports, hooks, stores and process cleanup, with synthetic isolated
projects. They never call a model or change installed host configuration.

Run `python3 -m unittest discover -s tests -p 'test*.py' -v`.
Run the new slice alone with `python3 -m unittest discover -s tests -p test_acceptance.py -v`.
Run thirty-two deliberate regressions with `python3 tests/run_mutation_checks.py`.

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
| UA-01 | No store | Server starts with either nonempty disable marker, including `0` | No state, tools or startup output; all tool calls refused; ping and EOF work | Real stdio and complete state inventory |
| UA-02 | A live bound peer with queued mail | Disabled peers start with the same alias | All state contents and file mtimes unchanged, including bindings and presence; mail stays queued | Real stdio and complete state inventory |
| UA-03 | Unset or empty markers | Server starts | Tools exposed and bound registration online | Enabled real-process control |
| UA-04 | Directory outside Git | Disabled server starts | Same inert protocol; no project-resolution error or state | Real stdio |
| PL-01 | A closed presence handle | Its descriptor is reused and close repeats | Unrelated descriptor remains open | Isolated process and real descriptors |
| PL-02 | A closed presence handle | Its descriptor is reused and process forks | Unrelated descriptor remains open in child | Real fork and child exit |
| CL-01 | No store | Human CLI usage is invalid | Usage error, exit 2, no state creation | Real bin/agentdm; separate state per subcase |
| CL-02 | A directory outside Git | Human requests roster | Concise error, exit 1, no traceback/state | Real bin/agentdm |
| CL-03 | A fresh project | Help then valid send/inbox run | Help is inert; message is actually stored and fetched | Real human CLI and store |
| CL-04 | Messages with receipts and outcomes, a held claim, a queued request | Human runs `log` | One date-ordered timeline, each item once with state and outcome, no body; offers/acks/outcomes unchanged; extra args exit 2 | Real bin/agentdm and store inventory |
| DOC-01 | A new reader | README routes them by audience | User, contributor and license entrypoints exist | Local documentation |
| DOC-02 | A local Markdown link | Its file target is followed | Target exists | All repository Markdown docs; not an external-link or anchor checker |
| DOC-03 | Published hook JSON | Examples are parsed and commands run with either disable marker | Correct event wiring; no output/state; enabled session positive control writes | Real scripts; not real-host dispatch |
| DOC-04 | A source distribution | License is read | Selected MIT notice and disclaimer are present | LICENSE file |
| DOC-05 | Current documentation | Path examples are inspected | No personal absolute home or private session scratch paths | Names-only pattern check; not a history/secret audit |
| IN-01 | An offered handoff | Recipient declines | Outcome receipt is separate from ack; the sender's inbox holds the reply; a second decision is refused | Real stdio, status and inbox |
| IN-02 | A note and an unfetched handoff | Accept or decline is attempted | Refused; no outcome; no reply queued | Real stdio, status and zero-wait |
| IN-03 | A review-request and a note | Fetched | Only the request expects an outcome; the frame says ack is not acceptance | Real inbox text |
| IN-04 | A live sender | Kind is outside the vocabulary | Refused; nothing queued | Real stdio |
| IN-05 | An agent's question to the human | Human accepts from the CLI | Reply reaches the agent; status shows accepted; a note cannot be answered; `--kind` is validated | Real bin/agentdm and stdio |
| IN-06 | A held claim and a queued request | Any tool is called | Every result carries unread and pending counts, the claims sentence only when a claim is held and a request pending, never a subject or body; the outcome drops pending to zero without acknowledging | Real stdio |
| IN-07 | A mailbox that cannot be listed | Any tool is called | `awareness` is `unavailable`; the tool still answers; no zero is invented | Real stdio and filesystem permissions |
| IN-08 | A request to a peer and a wait on it | The wait times out | The result names the peer's presence and availability and the message's receipt, outcome and meaning; an unknown alias reads `unknown`; no diagnosis without those arguments | Real stdio |
| IN-09 | An accepted request | The requester fetches the reply | The reply's metadata and frame name the decided message and its outcome | Real inbox text |
| AC-16 | Pending mail; then a held claim and a pending request | The prompt hook runs | One count line; the claims sentence only in the second case; never a subject or body | Real hook subprocess |
| NT-01 | No notify setting | A request is sent | No HTTP request; no setting file | Loopback HTTP sink |
| NT-02 | ntfy enabled at a loopback sink | Requests, notes and a decline occur | One titled POST per wanted event with sender, recipient, kind and outcome; no subject unless enabled; never a body or reason; send returns at once | Loopback HTTP sink and timing |
| NT-03 | Telegram enabled at a loopback API | Human declines | One JSON POST to sendMessage with the chat id and metadata only | Loopback HTTP sink |
| NT-04 | ntfy at a stalling endpoint, then a closed port | A request is sent | Receipt queued; response under one second; transport survives | Loopback HTTP sink and timing |
| NT-05 | The human CLI | Configure, test, turn off | Invalid forms exit 2; test reaches the sink and prints its status; off removes the file | Real bin/agentdm |
| NT-06 | ntfy enabled with a cap of 3 per sender per hour | One sender queues five requests, another one | Exactly three pushes from the first sender, one from the second; every send still queued; a non-numeric cap exits 2 | Loopback HTTP sink |

UA IDs map to `tests/test_unattended.py`, AC to `tests/test_acceptance.py`, PL to `tests/test_presence_lifetime.py`,
CL to `tests/test_cli_contract.py`, DOC to `tests/test_documentation.py`, IN to `tests/test_intents.py`,
and NT to `tests/test_notify.py`; assertions use externally
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
A fixture whose premise depends on the interpreter derives it at run time and
fails when it cannot be met: AC-15 probes the depth at which this Python's JSON
decoder raises `RecursionError` (about 2,000 on 3.9/3.11, 32,000 on 3.13,
256,000 on 3.14) instead of naming one, so a more permissive decoder cannot
turn the scenario vacuous and let the recursion mutation survive.

The outcome receipt is owned by the store beside offers and acks: it requires a
prior offer to the same alias and incarnation, a request kind, and no earlier
outcome, and it queues its reply through the ordinary send path so no second
delivery mechanism exists. The notifier owns nothing about mail state: it reads
the human's setting, decides whether an event is wanted, renders metadata only,
and pushes on a daemon thread from the server or inline from the short-lived
CLI. Loopback HTTP sinks stand in for ntfy and Telegram; no test reaches the
network.

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
