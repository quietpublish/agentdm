# Idle-holder experiment (2026-09-13)

Owner: the [design note](../../docs/IDLE_HOLDER_DESIGN_NOTE_2026_09_13.md), "The question
the trial did not settle": did a holder not know a request arrived, or know and choose not to act?

`run.py` runs one `claude -p` holder per run in a fresh sandbox Git repo with an isolated state
directory, a scripted peer that sends one `claim`-kind request once the holder has taken its second
claim, and, with `--hook on`, the experimental `hooks/agentdm-posttool-hook.py`. It records the
holder's tool calls (stream-json), the request's receipts (offered, outcome), the hook's own log, the
run's cost, and a post-task debrief obtained by resuming the session and asking what `agentdm:`
context it received. Verified 2026-09-13: PostToolUse `additionalContext` reaches the model but is
NOT shown in `--output-format stream-json`, so the debrief is the only witness of delivery.

The holder's prompt says nothing about mail. Nothing here reads the holder's mailbox. Results land in
`results/`; the dry runs used the cheap model to validate the harness and are not part of the matrix.
