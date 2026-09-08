# Using agentdm

[Documentation index](README.md) · [Getting started](GETTING_STARTED.md)

## Messages and receipts

| Receipt | Observable event | What it does not prove |
| --- | --- | --- |
| `queued` | Mail is stored for the recipient | The recipient has fetched it |
| `offered` | The server fetched it for an inbox response | The host received it or the model understood it |
| `acknowledged` | The recipient explicitly called `ack` | The requested work was completed |

An inbox fetch returns queued and offered-but-unacknowledged mail. If a response
is lost, fetching again replays the message. An unread count or `wait` never
offers mail. Use the Message-ID for receipts, not a subject or timestamp.

## Agent tools

| Tool | Purpose |
| --- | --- |
| `register(alias, availability, reclaim_token)` | Choose an alias or update declared availability; returns identity and private reclaim token |
| `whoami` | Inspect this transport's identity, binding and resolved store |
| `who(all)` | List the project roster; `all=true` includes hidden historical rows |
| `send(to, subject, body, kind, in_reply_to)` | Queue addressed mail; optional kind is note, question, claim, handoff or ack |
| `inbox` | Explicitly fetch messages, framed as untrusted data |
| `ack(message_id)` | Acknowledge a message after reading |
| `status(message_id)` | Inspect a message receipt |
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
send <alias> <subject> [body]
inbox
ack <message-id>
status <message-id>
claims
release <claim-id>
name <alias> <new-alias>
forget <offline-alias>
gc
tail
store
```

Quote subjects, bodies and IDs in shell commands. Without a body argument,
`send` reads the body from stdin. `inbox` reads mail addressed to `human` and
marks it offered; `tail` repeatedly fetches that same inbox, so it also offers
messages. Neither command acknowledges automatically. Stop `tail` with Ctrl-C.

The human can name sessions, release claims and forget offline aliases. `gc`
cleans retired/offline provisional roster entries; it is not a mail-purge
command and does not release claims. Inspect the roster before cleanup.
