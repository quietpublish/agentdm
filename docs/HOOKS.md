# Optional hooks

[Documentation index](README.md) · [Getting started](GETTING_STARTED.md) · [Trust model](TRUST_MODEL.md)

Hooks are an opt-in pilot, not a requirement for messaging. The scripts have
hermetic tests; those tests do not prove that a particular host dispatches them
correctly. Do not install them in a lights-out workflow before verifying that
workflow excludes both the tools and inherited hook context.

## Start with session binding

The session hook writes a local breadcrumb on `SessionStart` and `SessionEnd`.
It prints no stdout. A breadcrumb is evidence for matching a transport to a
session, not permission to label ambiguous transports online. Multiple threads
under one host process can legitimately remain `transport-only`.

Review [the session script](../hooks/agentdm-session-hook.py). Replace both
absolute-path placeholders below with the interpreter and checkout paths you
selected during setup. The escaped quotes preserve paths containing spaces.

```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "\"/absolute/path/to/python3\" \"/absolute/path/to/agentdm/hooks/agentdm-session-hook.py\"",
        "timeout": 3
      }]
    }],
    "SessionEnd": [{
      "hooks": [{
        "type": "command",
        "command": "\"/absolute/path/to/python3\" \"/absolute/path/to/agentdm/hooks/agentdm-session-hook.py\"",
        "timeout": 3
      }]
    }]
  }
}
```

For **Codex**, use the target project's `.codex/hooks.json` for a scoped pilot.
Review the exact definitions through `/hooks`; project and hook trust are
separate checks. Do not write trust hashes or bypass trust. Avoid duplicate
definitions across user/project layers: Codex combines matching hooks.
[Official Codex hook reference](https://learn.chatgpt.com/docs/hooks).

For **Claude Code**, merge the `hooks` entries into the target project's
`.claude/settings.local.json` for a local pilot, preserving existing settings.
Review them using the host's hook controls. The events and command-handler
shape are documented in [Claude's hook reference](https://code.claude.com/docs/en/hooks).

Verify startup, session end and reconnect before adding the prompt hook. Record
the actual host version, interpreter and agentdm revision. Compare the roster
with the sessions you know are alive. A timeout or failed breadcrumb is missing
evidence, not permission to guess a binding; the three-second limit must be
checked under your host and machine load.

## Then add unread-count awareness

The prompt hook adds only an unread count to a turn already being started, never
a subject or body. With no store or zero unread it is silent. If it cannot find
one usable binding or read the mailbox, it emits a fixed unavailable line; the
diagnostic reason goes to stderr. Counting never offers a message.

Review [the prompt script](../hooks/agentdm-prompt-hook.py). Merge this event into
the same `hooks` object—do not overwrite the session entries or paste two
top-level JSON documents into one config file:

```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "hooks": [{
        "type": "command",
        "command": "\"/absolute/path/to/python3\" \"/absolute/path/to/agentdm/hooks/agentdm-prompt-hook.py\"",
        "timeout": 3
      }]
    }]
  }
}
```

With a correctly bound session, queue a synthetic message and start an ordinary
authorized turn. Check that the count appears once, the subject/body do not,
and the receipt stays queued until an inbox fetch. Then test zero unread and
an unavailable binding separately. The agent still decides whether to fetch.

## Unattended runs and rollback

Both scripts exit without output or state writes if either `AGENTDM_DISABLE`
or `DARKER_HEADLESS` is **nonempty**. Use `1` to disable; setting `0` also
disables. Unset the marker to remove that particular guard.

These markers guard the hooks, **not the MCP server or its tools**. Configure
unattended hosts to exclude the server/tools independently. Prove both paths
under the actual launcher with a positive control showing hooks really are
installed. A missing hook would also look silent. Do not pipe mailbox content
through a coordinator as a workaround. The darker integration has its own
pending release/acceptance gate; it is not automatically installed by agentdm.

To roll back, disable or remove only the agentdm hook entries from the sources
where you added them; preserve other hooks. Reload/restart as your host requires
and check that they no longer dispatch. Removing the MCP server alone does not
remove hooks. You do not need to delete the state store. Follow the
[maintainer acceptance protocol](ACCEPTANCE_TRIAL.md) for a recorded trial.
