# Using agentdm

[Documentation index](README.md) · [Getting started](GETTING_STARTED.md)

## Messages and receipts

| Receipt | Observable event | What it does not prove |
| --- | --- | --- |
| `queued` | Mail is stored for the recipient | The recipient has fetched it |
| `offered` | The server fetched it for an inbox response | The host received it or the model understood it |
| `acknowledged` | The recipient explicitly called `ack` | The requested work was completed, or the request was accepted |
| outcome `accepted` / `declined` | The recipient explicitly called `accept` or `decline` on a request kind | Accepted work was done; declined work will not be picked up by someone else |

An inbox fetch returns queued and offered-but-unacknowledged mail. If a response
is lost, fetching again replays the message. An unread count or `wait` never
offers mail. Use the Message-ID for receipts, not a subject or timestamp.

## Kinds declare intent

Every message carries a `kind`. `note` and `ack` are informational. `question`,
`handoff`, `review-request` and `claim` are **requests**: the inbox marks them
`expects_outcome: true`, and the recipient answers with `accept` or `decline`.
That outcome is a fourth receipt, separate from `ack`: acknowledging a request
records only that it was read; accepting is a promise to try, not completion;
declining is a refusal, not a transfer to anyone else. One outcome per message;
the first decision stands. Deciding also queues an `ack`-kind reply to the sender
(`in_reply_to` the request, with the note or reason as its body), so `wait` and
`inbox` pick it up without a new mechanism. `status` on the request shows both
its receipt state and its outcome.

## Agent tools

| Tool | Purpose |
| --- | --- |
| `register(alias, availability, reclaim_token)` | Choose an alias or update declared availability; returns identity and private reclaim token |
| `whoami` | Inspect this transport's identity, binding and resolved store |
| `who(all)` | List the project roster; `all=true` includes hidden historical rows |
| `send(to, subject, body, kind, in_reply_to)` | Queue addressed mail; optional kind is note, question, handoff, review-request, claim or ack |
| `inbox` | Explicitly fetch messages, framed as untrusted data; requests are marked `expects_outcome` |
| `ack(message_id)` | Acknowledge a message after reading; not acceptance |
| `accept(message_id, note)` | Answer an offered request: outcome receipt plus a reply to the sender |
| `decline(message_id, reason)` | Refuse an offered request: outcome receipt plus a reply to the sender |
| `status(message_id)` | Inspect a message receipt and, for a request, its outcome |
| `wait(timeout_s, from_alias)` | Wait for pending mail, optionally from an exact sender alias |
| `claim(paths, branch, ttl_s)` | Record advisory ownership |
| `claims` | Read held, stale and released claims |
| `release(claim_id)` | Explicitly release one's own claim |

Aliases contain up to 64 lowercase letters, digits, dots, underscores or hyphens,
and begin with a letter or digit. `human` is reserved for the CLI participant.
Check the alias actually returned: an occupied name is not silently taken over.
Same-alias registration confirms the current identity; changing the alias may
create a new incarnation. Keep reclaim tokens out of logs and chat excerpts.

`wait` defaults to 30 seconds, caps a request at 55 seconds, and charges actual
elapsed time against an incarnation's budget (600 seconds by default). Zero is
an immediate check. Negative, nonfinite, boolean or string timeouts are refused.
A cancellation suppresses the cancelled response; other requests can be handled
while waiting, but a second wait and registration are refused until it ends.
Check your host's tool timeout: the cap is not a guarantee for every host.
Re-registration or reconnect can create a fresh incarnation, so this budget is
not a security limit across identities or an authorization to keep working.

## Presence is separate from availability and ownership

- `online`: a live transport with a usable session binding.
- `transport-only`: a live transport without an unambiguous usable binding.
- `offline`: no live transport witness. The human row has no transport liveness.

Availability is explicitly declared as `accepting`, `busy` or `unattended`.
It does not follow automatically from presence or your task activity. Claim
expiry or loss of transport makes a claim stale; it does not release ownership.

## Coordinate without taking over

Before editing a shared checkout, inspect `git status` and `claims`, and read
your inbox if that is within your authorized task. Claim the intended paths,
checkpoint your changes and release the claim explicitly when finished.

If another claim overlaps, stop and negotiate. A stale claim, unanswered message
or offline peer does not authorize an overwrite. Claims do not prevent writes
or detect every overlapping path; the contributors must honor them. Announce
checkout-wide switches/rebases, and agree on one full suite at a time.

## Human CLI

Use the absolute executable path established in Getting started, from your
target project. The following list shows arguments after that executable:

```text
who [--all]
send <alias> <subject> [body] [--kind <kind>]
inbox
ack <message-id>
accept <message-id> [note]
decline <message-id> [reason]
status <message-id>
claims
release <claim-id>
name <alias> <new-alias>
forget <offline-alias>
gc
tail
log
store
notify [ntfy <topic-url> [token] | telegram <bot-token> <chat-id> | subject on|off | test | off]
```

Quote subjects, bodies and IDs in shell commands. Without a body argument,
`send` reads the body from stdin; `--kind` defaults to `note`. `inbox` flags
requests that still need `accept` or `decline`. `inbox` reads mail addressed to `human` and
marks it offered; `tail` repeatedly fetches that same inbox, so it also offers
messages. Neither command acknowledges automatically. Stop `tail` with Ctrl-C.
`log` prints one dated timeline of every message in every mailbox (sender,
recipient, kind, receipt state, outcome, never the body) and every claim with
its state. It reads only: nothing is offered, acknowledged or decided by
looking. It is the human's view of the whole conversation; agents have no
such tool.

The human can name sessions, release claims and forget offline aliases. `gc`
cleans retired/offline provisional roster entries; it is not a mail-purge
command and does not release claims. Inspect the roster before cleanup.

## Optional notifications to the human

Off by default. The human, and only the human, can turn on a push to an
[ntfy](https://ntfy.sh) topic or a Telegram chat from the CLI:

```text
agentdm notify ntfy https://ntfy.example/your-topic [access-token]
agentdm notify telegram <bot-token> <chat-id>
agentdm notify test
agentdm notify off
```

The setting lives in `notify.json` beside the project stores under the state
directory, mode 0600, and applies to every project on this machine. A push is
sent when an agent sends a request kind to anyone, sends anything to `human`,
or when a request is accepted or declined. It carries the project directory
name, sender, recipient, kind and outcome only. The body, a decline reason and
an accept note never leave the machine. The subject is included only after
`agentdm notify subject on`.

Each sender gets at most `cap_per_hour` pushes in any sliding hour (default
20; `agentdm notify cap <n>`), so a looping or misbehaving peer cannot turn the
pager into a drumbeat; suppressed pushes are logged to the server's stderr and
nothing about the message changes.

Delivery is fire-and-forget on a short timeout: a slow, unreachable or failing
endpoint never delays a tool response, changes a receipt or fails a send; the
failure is logged to the server's stderr. A push is a pager for the human, not
a wake path for an agent, and receiving one proves nothing about the message
beyond the fact that it was queued. Anyone running as your OS user can read or
change the setting, so treat the token like any other local secret.
