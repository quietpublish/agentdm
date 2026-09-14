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
    ("unattended-startup-writes", "agentdm/server.py", "if self.disabled:", "if False:",
     "test_unattended.UnattendedAcceptance.test_ua01_disabled_startup_creates_no_state"),
    ("disabled-tools-exposed", "agentdm/server.py", "[] if self.disabled else TOOLS", "TOOLS",
     "test_unattended.UnattendedAcceptance.test_ua04_disabled_startup_does_not_require_a_git_project"),
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
    ("second-outcome-overwrites", "agentdm/store.py", 'if os.path.exists(self._p("outcomes", f"{key}.json")):\n            raise', 'if False:\n            raise',
     "test_intents.IntentAcceptance.test_in01_decline_is_a_receipt_separate_from_ack_and_replies_to_the_sender"),
    ("outcome-on-informational-kind", "agentdm/store.py", 'if m["kind"] not in REQUEST_KINDS:', 'if False:',
     "test_intents.IntentAcceptance.test_in02_outcomes_need_an_offered_request_kind"),
    ("outcome-without-offer", "agentdm/store.py", 'if not offer or offer["alias"] != alias:\n            raise AgentdmError("message was never offered to that alias")\n        if offer["offered_to"] != (inc or HUMAN):\n            raise AgentdmError("message was offered to a different incarnation; fetch it first")\n        if os.path.exists(self._p("outcomes"',
     'if False:\n            raise AgentdmError("message was never offered to that alias")\n        if offer and offer["offered_to"] != (inc or HUMAN):\n            raise AgentdmError("message was offered to a different incarnation; fetch it first")\n        if os.path.exists(self._p("outcomes"',
     "test_intents.IntentAcceptance.test_in02_outcomes_need_an_offered_request_kind"),
    ("notify-cap-ignored", "agentdm/notify.py", 'if len(recent) >= cap:', 'if False:',
     "test_notify.NotifyCapAcceptance.test_nt06_pushes_are_capped_per_sender_per_hour"),
    ("notify-off-keeps-setting", "agentdm/notify.py", 'os.remove(path)\n        except FileNotFoundError:', 'pass\n        except FileNotFoundError:',
     "test_notify.NotifyAcceptance.test_nt05_human_cli_owns_the_setting"),
    ("notify-leaks-subject", "agentdm/notify.py", 'if config.get("subject") and event.get("subject"):', 'if event.get("subject"):',
     "test_notify.NotifyAcceptance.test_nt02_ntfy_push_carries_metadata_only_and_never_delays_the_send"),
    ("notify-peer-notes", "agentdm/notify.py", 'return event["to"] == HUMAN or event["kind"] in REQUEST_KINDS', 'return True',
     "test_notify.NotifyAcceptance.test_nt02_ntfy_push_carries_metadata_only_and_never_delays_the_send"),
    ("notify-blocks-send", "agentdm/notify.py", 'if sync:\n        run()', 'if True:\n        run()',
     "test_notify.NotifyAcceptance.test_nt04_unreachable_or_stalled_endpoint_cannot_fail_or_stall_the_send"),
]


def run(root, selector):
    env = isolated_environment(None, root / "tests")
    selectors = [selector] if isinstance(selector, str) else selector
    return subprocess.run([sys.executable, "-m", "unittest", *selectors], cwd=root,
                          env=env, capture_output=True, text=True, timeout=30)


def main():
    baseline = run(ROOT, ["test_acceptance", "test_presence_lifetime", "test_cli_contract", "test_documentation",
                          "test_unattended", "test_intents", "test_notify"])
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
