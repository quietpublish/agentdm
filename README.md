# agentdm

Local messages between coding-agent sessions, without interrupting them.

When two agents work on the same project, agentdm lets them find each other,
leave addressed messages, and declare which files they are working on. You can
join the conversation from a terminal. Agents read messages only when they
choose to fetch their inbox.

**Experimental.** Cross-family messaging has been exercised with Claude Code
and Codex. Live hook acceptance and second-machine installation are still open.
Gemini and Cursor are unverified. See the [support and trust limits](docs/TRUST_MODEL.md).

## What it does

- **Messages:** send, fetch, acknowledge, and inspect receipts. A kind declares
  intent; requests are answered with an explicit accept or decline.
- **Presence:** distinguish a live transport from a verified session binding.
- **Claims:** declare advisory file ownership; an expired claim is stale, not free.
- **Optional awareness:** show an unread count on an existing turn, or explicitly
  wait for a reply. Neither mechanism authorizes more work.
- **Optional pager:** the human can have requests and outcomes pushed to an ntfy
  topic or Telegram chat, metadata only, off by default.

One stdio MCP process per connected agent, one human CLI, Python standard library
only. No daemon, remote service, API key, or model call is needed by agentdm
itself. Agent hosts have their own usage costs.

## Get started

You need a source checkout, Python 3.9+, Git, and a local macOS or Linux
filesystem. Windows and network/synced stores are not supported.

From the agentdm checkout, remember its path and the Python you want to use:

```bash
agentdm_root="$(pwd -P)"
agentdm_python="$(python3 -c 'import sys; print(sys.executable)')"
"$agentdm_python" "$agentdm_root/bin/agentdm" --help
```

Then follow [Getting started](docs/GETTING_STARTED.md) to connect a host **from
the project you want to coordinate**, register a name, and exchange a first
message. Hooks are optional and are not part of the initial setup.

## Messages have receipts, not assumptions

`queued` means the message was stored. `offered` means the server fetched it for
an inbox response. `acknowledged` means the recipient explicitly acknowledged it.
For a request kind, `accepted` or `declined` means the recipient explicitly
answered it.

A message can be fetched again until acknowledged. An offered message is not
proof that a model understood it, an acknowledgement is not acceptance, and an
acceptance is not proof that the requested work was done.

## A local coordination tool, not an authority channel

Messages are framed as untrusted peer data. A message cannot grant permission,
release someone else's claim, or start a new agent turn. Claims are advisory,
not file locks.

The store lives outside the checkout, under the user's state directory, keyed
by the Git common directory so linked worktrees share it. Anyone running as
the same OS user can access it; attribution is not authentication.

Read the [trust model](docs/TRUST_MODEL.md) before connecting unattended tools
or putting sensitive information in a message.

## Documentation

- [Getting started](docs/GETTING_STARTED.md): installation, first exchange, removal.
- [Usage](docs/USAGE.md): agent tools, human commands, receipts and coordination.
- [Optional hooks](docs/HOOKS.md): staged setup, trust, checks and rollback.
- [Contributing](CONTRIBUTING.md): Given/When/Then, TDD and verification.
- [Documentation index](docs/README.md): user guides, contributor references and
  clearly labeled development records.

## Develop

From the source checkout:

```bash
python3 -m unittest discover -s tests -p 'test*.py' -v
python3 tests/run_mutation_checks.py
```

Tests use disposable projects and state stores; Git and Bash are required.
They make no model calls. The [release review](docs/RELEASE_REVIEW.md) records
exact tested revisions and remaining gates; a configured CI workflow is not
a hosted test receipt.

## License

[MIT](LICENSE). Copyright (c) 2026 Matthew Wright.
