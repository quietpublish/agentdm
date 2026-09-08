"""Plant bounded regressions in disposable copies; each must redden its contract.

Never edits the candidate or installed server. Requires a green baseline first.
The cases are an explicit contract sample, not a coverage percentage.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from acceptance_support import isolated_environment

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = [
    ("scalar-json", "agentdm/protocol.py", "if not isinstance(raw, dict):", "if False:",
     "ProtocolAcceptance.test_ac01_non_object_json_cannot_end_the_server"),
    ("notification-authority", "agentdm/protocol.py", 'if rid is None and method != "notifications/cancelled":', "if False:",
     "ProtocolAcceptance.test_ac04_notification_shaped_tool_call_never_mutates"),
    ("blank-eof", "agentdm/server.py", "if line is _EOF:", 'if line is _EOF or line == "":',
     "ProtocolAcceptance.test_ac03_empty_lines_are_not_transport_eof"),
    ("zero-default", "agentdm/server.py", 'a.get("timeout_s", 30.0)', 'a.get("timeout_s") or 30.0',
     "ProtocolAcceptance.test_ac06_explicit_zero_wait_is_a_nonblocking_check"),
    ("renewed-deadline", "agentdm/server.py", "remaining = deadline - time.monotonic()", "remaining = timeout",
     "ProtocolAcceptance.test_ac07_deadline_preserves_fragmented_request"),
    ("ignored-cancel", "agentdm/server.py", "and target == self._waiting_rid):", "and False):",
     "ProtocolAcceptance.test_ac08_cancel_has_no_late_reply_and_does_not_kill_server"),
    ("session-hook-leak", "hooks/agentdm-session-hook.py", "if any(os.environ.get(k) for k in UNATTENDED_MARKERS):", "if False:",
     "HookAcceptance.test_ac09_headless_hooks_leave_no_output_or_new_store"),
    ("prompt-hook-leak", "hooks/agentdm-prompt-hook.py", "if any(os.environ.get(k) for k in UNATTENDED_MARKERS):", "if False:",
     "HookAcceptance.test_ac10_nudge_counts_without_offering_and_disables_on_existing_store"),
    ("sender-substring", "agentdm/awareness.py", 'sender != from_alias + "@agentdm"', 'from_alias not in sender',
     "ProtocolAcceptance.test_ac12_sender_filter_matches_alias_not_substring_or_family"),
    ("wait-owner-replaced", "agentdm/server.py", 'if self._waiting_rid is not None:', 'if False:',
     "ProtocolAcceptance.test_ac13_register_cannot_replace_identity_during_wait"),
    ("nonfinite-timeout", "agentdm/server.py", 'or timeout < 0 or not math.isfinite(timeout)', 'or timeout < 0',
     "ProtocolAcceptance.test_ac14_invalid_wait_arguments_are_refused_without_waiting"),
    ("decoder-recursion", "agentdm/protocol.py", 'ValueError, RecursionError', 'ValueError',
     "ProtocolAcceptance.test_ac15_deeply_nested_json_cannot_end_the_server"),
    ("closed-descriptor-reused", "agentdm/presence.py", 'fd, self.fd = self.fd, None', 'fd = self.fd',
     "test_presence_lifetime.PresenceLifetimeAcceptance.test_pl02_fork_callback_leaves_reused_descriptor_open"),
    ("cli-usage-side-effects", "agentdm/cli.py", 'if invalid:', 'if False:',
     "test_cli_contract.CliAcceptance.test_cl01_invalid_arguments_refuse_before_creating_store"),
    ("broken-reader-link", "README.md", '](docs/USAGE.md)', '](docs/not-a-guide.md)',
     "test_documentation.DocumentationAcceptance.test_doc02_local_markdown_links_resolve"),
    ("wrong-hook-event", "docs/HOOKS.md", '"UserPromptSubmit": [{', '"BeforeAgent": [{',
     "test_documentation.DocumentationAcceptance.test_doc03_hook_examples_are_parseable_and_run_inert_when_disabled"),
]


def run(root, selector):
    env = isolated_environment(None, root / "tests")
    selectors = [selector] if isinstance(selector, str) else selector
    return subprocess.run([sys.executable, "-m", "unittest", *selectors], cwd=root,
                          env=env, capture_output=True, text=True, timeout=30)


def main():
    baseline = run(ROOT, ["test_acceptance", "test_presence_lifetime", "test_cli_contract", "test_documentation"])
    if baseline.returncode:
        print(baseline.stdout + baseline.stderr)
        print("REFUSED: mutation checks require green acceptance baseline")
        return 1
    failures = []
    for name, rel, before, after, test in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix="agentdm-mutation-") as temporary:
            copy = Path(temporary) / "candidate"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
            path = copy / rel
            source = path.read_text()
            if before not in source:
                raise RuntimeError("mutation target drifted: " + name)
            path.write_text(source.replace(before, after))
            result = run(copy, test if test.startswith("test_") else "test_acceptance." + test)
            # A syntax/import crash or harness timeout is not a killed behavior mutation.
            rejected = result.returncode == 1 and "FAIL:" in result.stderr and "ERROR:" not in result.stderr
            print(json.dumps({"mutation": name, "test": test, "rejected_by_assertion": rejected}), flush=True)
            if not rejected:
                failures.append(name)
                print(result.stdout + result.stderr)
    print(json.dumps({"mutations": len(MUTATIONS), "survived_or_invalid": failures}))
    return bool(failures)


if __name__ == "__main__":
    sys.exit(main())
