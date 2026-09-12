# Acceptance trial record — 2026-09-12

Maintainer record for the [acceptance trial protocol](ACCEPTANCE_TRIAL.md).
Evidence is written as found, in the order observed, with local timestamps
(CDT, UTC-5). Nothing here is cleaned to look green. Paths use placeholders:
`<checkout>` is the agentdm source checkout, `<state>` is
`${XDG_STATE_HOME:-~/.local/state}/agentdm`.

## Preconditions as found (14:05)

| Precondition | State | Evidence |
| --- | --- | --- |
| 1. Unattended runs protected | Met for the deny list; hook inertness has local receipts only | darker `d3d94417` denies the thirteen-name family on both surfaces (P0h and headless gate green 2026-09-10); AR-01 hook/server inertness receipts; the real-launcher hook receipt is still open |
| 2a. Session hook (Claude Code) | Installed at **user scope**, not darker-scoped: `SessionStart`, `SessionEnd`, bare `python3`, timeout 5 | `~/.claude-personal/settings.json`, modified 2026-09-10 20:33 |
| 2b. Prompt hook (Claude Code) | Installed at user scope: `UserPromptSubmit`, timeout 5 | same file |
| 2c. Hooks (Codex) | **Not installed**; MCP server only | `~/.codex/config.toml` has `[mcp_servers.agentdm]` and no agentdm hooks; no `.codex/hooks.json` in darker |
| 3. Private backup remote | **Unconfirmed** | The known remote is the public clean-history export; no private remote was verified |

Both hook steps were therefore not activated in the two-step, darker-scoped
order the protocol asks for. They were already live at user scope before this
record began. Recorded, not corrected.

### Hosts, interpreters, revisions

| Item | Value |
| --- | --- |
| Claude Code | 2.1.269 |
| Codex | codex-cli 0.154.0 |
| agentdm checkout (both hosts launch it) | `<checkout>/bin/agentdm-server`, HEAD `611c802`; runtime code is `5a55b45` (0.0.3) |
| Interpreter MCP servers actually run | pyenv Python 3.11.15 (host-launched PATH) |
| Interpreter a login shell resolves for the hooks' bare `python3` | Homebrew Python 3.14.6 |
| Hook scripts are launched with bare `python3` | so the hook interpreter follows the host's environment, which was not captured from inside a hook run |

### Loaded server revisions

Servers load code at spawn. 0.0.3 was committed 2026-09-10 17:49. Live servers
at 14:05, by start time:

| Store | Alias | Server started | Code | Note |
| --- | --- | --- | --- | --- |
| darker | `claude-code-50a2d416` | 2026-09-10 16:39 | pre-0.0.3 | no `accept`/`decline`; needs host reconnect |
| darker | `codex-94925` | 2026-09-12 13:53 | 0.0.3 | |
| agentdm (this recorder) | `claude-code-86d5e74e` | 2026-09-10 17:12 | pre-0.0.3 | confirmed: tool list lacks `accept`/`decline` |

Eleven agentdm servers were alive machine-wide, spawned 2026-09-10 to 09-12
by various hosts; six of the darker roster's rows belong to dead processes.

### Roster snapshot, darker store (14:05)

```text
claude-code-14c615fe   offline         provisional  pid dead
claude-code-3449fb0e   offline         provisional  pid dead
claude-code-50a2d416   transport-only  provisional  pid 89700 alive, session=None
claude-code-754e124d   offline         provisional  pid dead
claude-code-c412bdd6   offline         provisional  pid dead
codex-87463            offline         provisional  pid dead
codex-94925            transport-only  provisional  pid 94925 alive, session=None
codex-darker           offline  busy   named        pid dead
darker-22              offline         named        pid dead, session 50108472…
```

No claims. No mail pending for `human`. `gc` was **not** run before the
snapshot so the litter is visible as found; it hides by default (`who`
without `--all`).

### Presence observation P-1 (14:05): a resumed Claude session reads transport-only

Host breadcrumb `bindings/host/89408.json` in the darker store:

```text
50a2d416…  hook:SessionStart:startup  bound 21:39:54Z  ended 21:40:02Z  hook:SessionEnd
c412bdd6…  hook:SessionStart:resume   bound 21:40:02Z  ended None
```

The host process started session `50a2d416`, ended it eight seconds later, and
resumed `c412bdd6` in the same process. The MCP server spawned at startup
carries `50a2d416` as its own env binding. `binding()` follows only
`cleared-by:` successions, so an own session that ended for real yields
`session_id: None` and the row reads `transport-only` although the session is
live and interactive. This is the fail-closed rule (DM-05) doing what it says:
truthful, not wrong. It also means **any session started with `--resume` or
resumed inside the same host never reads `online`** until its server is
respawned. Recorded as a presence limitation, not a bug to fix during the
trial. Feature freeze holds.

The Codex row is `transport-only` because Codex has no hooks installed; that
is the expected ceiling for that host in this configuration.

## Working day plan

Two live agents in the darker checkout: the Claude Code session in the
`darker` directory and the Codex session in the same directory. The recorder
(this session, bound to the agentdm store) does not participate in darker's
roster and relays nothing; it reads the darker store through the human CLI
only when asked, and records.

The darker working tree is already dirty with another session's uncommitted
work (`docs/GLOSSARY.md`, `docs/BELIEFS.md`, `docs/knowledge/`, a work-order
adoptions file). The task must not touch those paths.

- Task A (Claude): a small documentation change in `docs/COMPATIBILITY.md`.
- Task B (Codex): a small documentation change in `CLAUDE.md`.
- Deliberate conflict: Task B is also told to update `docs/COMPATIBILITY.md`
  after Task A has claimed it. Codex must find the claim, stop, and negotiate
  by message; Claude answers with `accept` or `decline`. No overwrite; a stale
  claim is not ownership.

Each agent, in its own session and with its own user's authorization: check
`git status`, `who`, `claims`; claim paths before editing; checkpoint-commit;
release explicitly; send handoffs through agentdm.

## Observations (append as found)

| Time | Kind | Observation |
| --- | --- | --- |
| 14:05 | presence | P-1 above |
| 14:16 | presence | A **new** Claude Code session was started in darker (host pid 99115, server 99936, 0.0.3). It registered as `claude-a` and reads `online` with session `fb96837e…`: startup binding, no resume, hooks dispatched. The earlier darker session (host 89408) is still alive and still `transport-only` (P-1 stands). Codex registered `codex-b` at 14:21:56 on its 13:53 server (0.0.3); `transport-only`, no hooks, as expected. |
| 14:17–14:22 | claims | Timeline from the store: `claude-a` claimed `docs/COMPATIBILITY.md` 14:17:57, checkpoint-committed `f1c7af59` 14:18:15, **released 14:21:26**. `codex-b` claimed `CLAUDE.md` 14:21:56, committed `478ec752` 14:22:06, claimed `docs/COMPATIBILITY.md` 14:22:21, released both 14:22:37–40. No claim was ever held by two agents at once. |
| 14:24 | conflict | **The deliberate conflict did not occur.** The second agent was started about four minutes after the first; the first agent's three waits (about 165 s plus overhead) expired and it released before the second registered. Recorder's sequencing error, not tool behaviour. Rerun needed (plan below). |
| 14:24 | messages | **Zero messages were exchanged today.** No handoff, no claim request, no outcome. The last message in the darker store is dated 2026-09-09. `claude-a` was told to send `codex-b` a handoff note after releasing; none exists. At 14:21:26 the alias `codex-b` was not yet registered, so a send would have been refused as unknown recipient; whether that happened, or the step was skipped, is only visible in that session's transcript (pending operator report). |
| 14:24 | claims | `codex-b` edited `docs/COMPATIBILITY.md` under its claim and **released the claim with the edit still uncommitted** (working tree shows the change; no commit). The recorder's instruction said to edit only after release and did not say to commit, so this is instruction-shaped; still, a release does not check for uncommitted work in the claimed paths, and nothing warned. Worth a decision later, not a fix now. |
| 14:24 | relays | No manual relay was needed, because nothing was sent. |
| 14:21 | messages (operator report) | Claude transcript: after three `wait` timeouts (55.01 s, 55.0 s, 55.0 s, each `unread: 0`), `claude-a` released and tried the handoff; `send` returned `AgentdmError: unknown recipient alias 'codex-b'`. By design: an alias that never registered has no mailbox. The agent reported it as a finding rather than retrying blindly. |
| 14:26 | messages | The operator typed "codex-b registered" into the Claude session. `claude-a` then re-sent the handoff: `<d5e74972…@agentdm>`, kind `handoff`, `expects_outcome: true`, `state: queued`. Confirmed in the store at 14:48: still `queued`, body describes the commit and release. This is the day's first real message. One pager push ("claude-a -> codex-b: handoff") expected at 14:26; operator to confirm. |
| 14:26 | authority | `claude-a` ran a **fourth** wait after the three authorized, and said so unprompted ("a fourth wait beyond the three you authorized, since you re-engaged"). The operator's two-word prompt was read as re-engagement. Disclosed, bounded, and charged to the budget; recorded because "extend on an ambiguous prompt" is exactly the edge the protocol watches. No peer message extended anything. |
| 14:26 | hygiene (operator report) | The Claude transcript prints the **full** reclaim token from `register`, again because of the "verbatim" instruction. Same leak path as Codex, on the second host. The token authorizes reclaiming `claude-a` only while that incarnation is live and only for a same-OS-user caller, so exposure in an operator-only transcript is low risk; still, two for two says the return shape invites it. |
| 14:33–14:38 | checkout | Darker main advanced under the trial: `a05f3f94` (14:33, committed codex-b's previously uncommitted compatibility edit; committing session not identified from the store), then a wo-b7d2 completion and a wo-9a4e fast-forward by the other Claude session. `claude-a`'s commit survived; it first misread a short log as a rebase, then corrected itself. Three sessions were writing to one checkout; no claim overlapped because the trial paths and the other session's paths were disjoint by luck, not by claims: the other session held no claim. |
| 14:38 | parallel channel | The two Claude sessions in darker exchanged two questions over Claude Code's native cross-session messaging, not over agentdm, to settle who owned the dirty `docs/GLOSSARY.md`. Push-delivered, single-vendor, and it worked; the Codex session could not have been asked that way. Recorded as the pull-only channel being bypassed for convenience when both ends were Claude. |
| 14:48 | messages | `codex-b` has not fetched its inbox since the handoff was queued; the receipt is still `queued`, so the pager push is the only thing that reached anyone. |
| 14:26 | pager (operator report) | Operator confirms the phone received "claude-a -> codex-b: handoff" at 14:26. First real push of the day; it arrived before the recipient had fetched anything, which is the pager's intended job (tell the human, not the agent). |
| 14:50 | rerun step 1 | Operator reports the Codex holder step "done". The darker store shows **no change**: no held claim, no offer record, the handoff still `queued`, no new incarnation. The only file modified in any store in the last 15 minutes is the other Claude session's host breadcrumb. Codex's server is unchanged (pid 94925, cwd darker, same store). So the step produced no agentdm tool call that wrote anything: either the tools were not called, or they errored. Pending the Codex transcript. |
| 15:05 | rerun step 1 (correction) | The 14:50 "done" was a clarifying question typed into the Codex session ("were you supposed to send a handoff?"), not the holder prompt. Codex answered correctly that no claim message was required because the claim had been released. The store was untouched because no holder step had run. Operator sequencing again, not tool behaviour. |
| 15:19 | rerun step 1 | Codex holder step executed. Store: Claude's handoff `<d5e74972…>` is now `acknowledged` **and** `accepted` (decided 15:19:11); an `ack`-kind reply from `codex-b` to `claude-a`, `in_reply_to` the handoff, is `queued` with a note stating the accepted scope. Claim `1810b8098b24` on `docs/COMPATIBILITY.md` held by `codex-b` since 15:19:15; no edit, no wait, turn ended as asked. First outcome receipt of the day, produced by a Codex session, on a message from a Claude session. Codex reported "no reclaim tokens were returned", which is true: it never called `register` or `whoami` in that turn. One pager push expected: "codex-b accepted handoff from claude-a". |
| 15:19 | pager (operator report) | Operator confirms the push "codex-b accepted handoff from claude-a". Second push of the day; both so far were correct and on time. |
| 14:33 | claims (correction) | The store shows a further `codex-b` claim `fd82f3c0e03c` on `docs/COMPATIBILITY.md` held 14:33:33–14:33:51, bracketing commit `a05f3f94` (14:33:44). So Codex itself committed its earlier uncommitted edit, under a fresh claim, during a later turn. The 14:33 row above saying "committing session not identified" is resolved: it was `codex-b`, and it re-claimed before committing. |
| 15:22 | rerun step 2 | Claude requester step (operator transcript): the **prompt hook nudge fired** ("The hook says I have one unread message") on the first turn with mail pending, once, with no subject. Claude fetched, acked Codex's acceptance reply, saw the held claim, did not edit, sent a `claim`-kind request `<7198a534…>` (`expects_outcome: true`), waited 55.01/55.0/55.0 s, stopped after the third timeout as instructed, and reported the request still `queued`. No overwrite; a held claim was honoured. Push "claude-a -> codex-b: claim" confirmed by the operator at 15:22. |
| 15:26 | rerun step 3 | Operator reports Codex's "continue" turn done. Store: the claim request is still `queued`, never offered; claim `1810b8098b24` still held. **Codex did not fetch its inbox on a bare "continue".** With no hooks on that host there is no unread signal, and the pull-only design means nothing else can tell it. This is the "missing nudge" the protocol asks to record, and it is structural for Codex in this configuration, not a fault of the session. Pending the Codex transcript for what it did instead. |
| 15:31 | rerun step 3 (operator nudge) | The operator typed "check your agentdm inbox" into Codex, **pasting the recorder's explanatory paragraph along with it** (what Codex "should" do). Manual intervention #1 of the day: no message content was carried, but the expected behaviour was. Codex then: `inbox` (one message, framed untrusted, with the outcome guidance line), `ack`, `accept` with a note that itself records the operator nudge, `release 1810b8098b24`. Store at 15:32: request `<7198a534…>` `acknowledged` + `accepted` (15:31:45), reply `<5447bf9c…>` queued to `claude-a`, claim released 15:31:48, no claims held. Codex did not claim it had chosen freely; the accept was instructed-shaped and the note says so. |
| 15:31 | conflict | **The deliberate conflict is now complete on the holder's side:** a held claim, a request by message, an explicit outcome, an explicit release, no overwrite, no stale-claim shortcut. Total wall time from request to release: 9 min 24 s, of which all but a few seconds was Codex not knowing it had mail. |
| 16:07 | rerun step 4 | Claude requester turn (operator transcript): fetched Codex's acceptance reply, acked it, saw the claim released, claimed `7e621ec5868b`, added one line, committed `28d8dd76` (that file only), released, and sent a `note` ("done") to `codex-b`. Store at 16:08: no claims held; the request `<7198a534…>` reads `acknowledged` with outcome `accepted`; the done note is `queued`. **The conflict is complete end to end.** |
| 16:07 | misreading | Claude reported that "codex-b's acceptance came as kind ack rather than as an accept outcome, so the status of my request would still read queued with no recorded outcome." **Wrong, and unverified**: it did not call `status`; the request carries outcome `accepted` since 15:31:45. The design puts the outcome on the original message's receipt and sends the reply as kind `ack`; the reply's subject even begins "accepted:". A capable model still inferred the opposite from the reply's kind. The receipt shape is right; the reply's framing does not make it obvious enough. Candidate change after the freeze: mark the reply body/frame with "outcome accepted recorded on <message-id>". |

## Summary as of 16:10

What the day showed, in the protocol's own categories:

- **Wrong presence:** none. Every row matched a real state or read the
  fail-closed `transport-only`. Two structural limits recorded: a resumed
  Claude session never reads `online` (P-1), and Codex without hooks never
  reads better than `transport-only`.
- **Missing or duplicate nudges:** the Claude prompt hook fired once, on the
  right turn, with a count and nothing else. Codex has no nudge at all; a
  bare "continue" did not drain its inbox, and both halves of the conflict
  waited on that.
- **Manual relays:** one intervention, not a relay: the operator told Codex
  to check its inbox, and the pasted instruction carried the expected
  behaviour with it.
- **Claim disagreements:** one, deliberate, resolved by message: request,
  accept, release, then claim, edit, commit, release. No overwrite, no
  stale-claim shortcut. Earlier, a claim was released with an uncommitted
  edit; the holder later re-claimed and committed it.
- **Unauthorized work from messages:** none. One agent extended its waiting
  on a two-word operator prompt and said so.

Other findings: a send to a never-registered alias is refused (by design,
handled well); `register`/`whoami` return the reclaim token and a "report
verbatim" instruction put it in both transcripts; Claude-to-Claude questions
went over the native cross-session channel instead of agentdm; three sessions
wrote to one checkout with disjoint paths by luck, since only the trial agents
held claims.

Pager: four pushes, all confirmed on the operator's phone at 16:18, correct
and on time, none redundant (handoff 14:26, accepted 15:19, claim 15:22,
accepted 15:31), titled with the project name. Its value on this day was real
but narrow: the human learned that requests existed before any agent did,
and the human's own turn was still what moved Codex. Whether it becomes a
nudge to an agent by another route is the thing to watch, not the pushes.

The preconditions were not met in the protocol's order (hooks were already
live at user scope; no Codex hooks; no verified private backup remote), so
this is a working-session record with one negotiated conflict, not the
protocol's acceptance day. The feature freeze holds until the maintainer
decides what to do with the candidates above.
| 14:40 | claims (operator report) | Codex transcript confirms: `codex-b` called `claims` before editing, saw `claude-a`'s claim with `released` set, and proceeded without a request. Correct reading: released is free; only a stale claim must be treated as owned. It left the second edit uncommitted by choice and said so. |
| 14:40 | hygiene (operator report) | The Codex transcript shows the `register` result, including the leading characters of the reclaim token, because the recorder asked for every tool result verbatim. `register` returns the token by design; the usage guide says to keep it out of chat excerpts. Instruction-shaped, but a real leak path: a "report verbatim" instruction plus `register` puts the token in the transcript. Consider whether `whoami`/`register` should redact the token after first return. Not changed during the trial. |
| 14:24 | nudges | No mail was pending for any Claude session, so no nudge was expected. None to record yet. |
| 14:24 | pager | No request-kind message and no outcome occurred, so zero pushes were expected. Operator to confirm the phone showed none. |
| 14:24 | authority | No message started or extended work: none existed. Both tasks were authorized in their own sessions. |

## Rerun plan for the conflict (pending operator authorization)

Sequencing rather than waiting: the holder claims and **ends its turn**, so the
claim persists (ttl 20 min) without a wait budget running. The requester then
sends a `claim`-kind message and waits. The operator starts an ordinary turn in
the holder's session; the prompt hook should show one unread line, the holder
fetches, answers with `accept` or `decline`, and releases if it accepted. That
exercises the nudge, the outcome receipt, both pager pushes and the no-overwrite
rule in one pass, and it needs no relay.
