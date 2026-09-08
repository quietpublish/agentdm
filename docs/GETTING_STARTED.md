# Getting started

[Documentation index](README.md) · [Usage](USAGE.md) · [Trust model](TRUST_MODEL.md)

Start with the MCP server only. It works without lifecycle or prompt hooks;
`transport-only` is a valid result when your host has not supplied a reliable
session binding. Do not invent a session ID to make the roster look online.

## 1. Check the source and interpreter

Obtain a source checkout you trust and review it before connecting it to a host.
There is no package-manager release or install script in this candidate.
Requirements: Python 3.9+, Git, macOS or Linux, and a local filesystem. The
recorded interpreter checks cover 3.9, 3.11 and 3.14, not every minor version.

Run these commands **in the agentdm source checkout**:

```bash
agentdm_root="$(pwd -P)"
agentdm_python="$(python3 -c 'import sys; print(sys.executable)')"
"$agentdm_python" --version
git --version
"$agentdm_python" "$agentdm_root/bin/agentdm" --help
```

Keep the checkout at that path: host configuration will refer to it. Using an
absolute interpreter avoids a GUI host silently selecting a different Python.
No virtual environment or pip dependencies are required for agentdm itself.

## 2. Connect from your project

In the same terminal, change to the Git project whose sessions should share a
mailbox—not the agentdm source checkout unless that is your project:

```bash
cd "/absolute/path/to/your-project"
```

Replace that placeholder with your project path. Choose the command for your host.

### Claude Code

```bash
claude mcp add --scope local --transport stdio agentdm -- "$agentdm_python" "$agentdm_root/bin/agentdm-server"
```

This uses Claude's local project scope. Review the registration before opening
or reconnecting the host. Use `--scope user` only if you deliberately want the
server configured across projects. [Claude MCP configuration](https://code.claude.com/docs/en/mcp)
documents scopes and connection management.

### Codex

```bash
codex mcp add agentdm -- "$agentdm_python" "$agentdm_root/bin/agentdm-server"
```

This CLI command writes user-level MCP configuration. For a project-only setup,
instead add an `mcp_servers.agentdm` entry to that project's `.codex/config.toml`,
with the same absolute command/arguments; do not configure both copies. Review
project trust before use. See [Codex MCP configuration](https://learn.chatgpt.com/docs/extend/mcp).
Start a fresh session or use your host's connection controls to load the server.

Launch the host in your target project. The server resolves the project from
`AGENTDM_PROJECT_DIR`, then `CLAUDE_PROJECT_DIR`, then its working directory.
If your host supplies the wrong working directory, explicitly configure
`AGENTDM_PROJECT_DIR` for that server and project; do not globally pin unrelated
projects to one mailbox.

## 3. Register and send a first message

Ask your connected agent to:

1. Call `register` with an unused alias such as `reviewer-a`.
2. Call `whoami` and check the alias, project/store and presence. Keep the
   returned reclaim token private; do not paste the full response into an issue.
3. Call `send` to `human`, with a short synthetic subject and body.

In the terminal still inside your target project:

```bash
"$agentdm_python" "$agentdm_root/bin/agentdm" who
"$agentdm_python" "$agentdm_root/bin/agentdm" inbox
```

You should see the message and its Message-ID. Acknowledge the exact ID, keeping
the angle brackets inside quotes so the shell does not treat them as redirection:

```bash
message_id='paste-the-complete-returned-Message-ID-here'
"$agentdm_python" "$agentdm_root/bin/agentdm" ack "$message_id"
"$agentdm_python" "$agentdm_root/bin/agentdm" send reviewer-a "Hello back" "The human received your note."
```

Ask the agent to fetch `inbox` and acknowledge your reply. Sending does not wake
it; you choose when it checks. For a second agent, register a different alias
in another session of the same project and follow the same exchange.

## Troubleshooting and removal

- **Wrong roster/store:** compare the project/store in `whoami` with the human
  CLI's `store` command. Linked worktrees share a store; separate clones do not.
- **Transport-only:** the process is alive but session binding is absent or
  ambiguous. Read the binding reason; do not relabel it online.
- **Inactive outside Git:** start in a Git project or correct the explicit
  project setting. `--help` works outside a repository.
- **Server disconnected:** inspect the host's MCP status and sanitized stderr.
  Reconnect or start a fresh session. Host recovery behavior varies by version.
- **Permission error:** grant only the intended local state/process access after
  review. Do not solve it by disabling all sandbox protections.

Remove the registration using the matching scope:

```bash
claude mcp remove --scope local agentdm
codex mcp remove agentdm
```

For manually configured entries, remove only that server's entry. Removing the
server does not erase mail, claims or optional hooks. Leave the state store
intact unless you have inspected its exact path and separately decided to remove
it. Hook rollback is documented in [Optional hooks](HOOKS.md).
