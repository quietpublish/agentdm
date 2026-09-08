"""Documentation contracts: navigation and examples are part of the interface."""
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
from urllib.parse import unquote, urlsplit

from acceptance_support import AcceptanceCase, ROOT


class DocumentationAcceptance(AcceptanceCase):
    def test_doc01_reader_has_user_and_contributor_entrypoints(self):
        """Given a fresh reader; when following README routes; then each audience has a guide."""
        readme = (ROOT / "README.md").read_text()
        for name in ("docs/GETTING_STARTED.md", "docs/USAGE.md", "docs/HOOKS.md",
                     "docs/TRUST_MODEL.md", "docs/README.md", "CONTRIBUTING.md", "LICENSE"):
            with self.subTest(path=name):
                self.assertTrue("](" + name + ")" in readme, "missing reader route: " + name)
                self.assertTrue((ROOT / name).is_file(), name)

    def test_doc02_local_markdown_links_resolve(self):
        """Given checked-in Markdown; when a local document/file link is followed; then it exists."""
        for path in [ROOT / "README.md", ROOT / "CONTRIBUTING.md", *sorted((ROOT / "docs").rglob("*.md"))]:
            if not path.exists():
                continue  # DOC-01 owns missing audience entrypoints.
            for link in re.findall(r"\]\(([^)]+)\)", path.read_text()):
                target = urlsplit(link.strip("<>"))
                if target.scheme or target.netloc or not target.path:
                    continue
                with self.subTest(document=str(path.relative_to(ROOT)), target=target.path):
                    self.assertTrue((path.parent / unquote(target.path)).exists())

    def test_doc03_hook_examples_are_parseable_and_run_inert_when_disabled(self):
        """Given the published hook examples; when disabled; then real commands emit/create nothing."""
        path = ROOT / "docs" / "HOOKS.md"
        self.assertTrue(path.is_file(), "hook guide must exist")
        examples = [json.loads(block) for block in re.findall(r"```json\n(.*?)\n```", path.read_text(), re.S)]
        events = {}
        for example in examples:
            for event, groups in example["hooks"].items():
                self.assertNotIn(event, events, "guide must not install the same event twice")
                command = shlex.split(groups[0]["hooks"][0]["command"])
                self.assertEqual(len(command), 2)
                script = ROOT / "hooks" / Path(command[1]).name
                self.assertTrue(script.is_file())
                events[event] = script
        self.assertEqual(set(events), {"SessionStart", "SessionEnd", "UserPromptSubmit"})
        self.assertEqual({event: script.name for event, script in events.items()}, {
            "SessionStart": "agentdm-session-hook.py",
            "SessionEnd": "agentdm-session-hook.py",
            "UserPromptSubmit": "agentdm-prompt-hook.py"})
        for event, script in events.items():
            payload = json.dumps({"session_id": "documentation-session", "cwd": str(self.project),
                                  "hook_event_name": event})
            for marker in ("DARKER_HEADLESS", "AGENTDM_DISABLE"):
                result = subprocess.run([sys.executable, str(script)], input=payload, text=True,
                                        capture_output=True, cwd=self.project,
                                        env=dict(self.env, **{marker: "1"}), timeout=3)
                self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))
                self.assertFalse(self.state.exists())
        # Positive control proves the SessionStart example points at a working session hook.
        result = self.hook(events["SessionStart"].name,
                           {"session_id": "documentation-session", "cwd": str(self.project),
                            "hook_event_name": "SessionStart"})
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(list(self.state.glob("agentdm/*/bindings/host/*.json"))), 1)

    def test_doc04_mit_license_has_notice_and_disclaimer(self):
        """Given the selected license; when the source is distributed; then MIT terms travel with it."""
        path = ROOT / "LICENSE"
        self.assertTrue(path.is_file(), "selected MIT license must be present")
        license_text = path.read_text()
        self.assertTrue(license_text.startswith("MIT License\n"))
        self.assertIn("Copyright (c) 2026 Matthew Wright", license_text)
        self.assertIn("The above copyright notice and this permission notice", license_text)
        self.assertIn('THE SOFTWARE IS PROVIDED "AS IS"', license_text)

    def test_doc05_published_document_tree_uses_portable_path_examples(self):
        """Given current documentation; when published; then personal home/scratch paths are absent."""
        personal = re.compile(r"/(?:Users|home)/[^/\s]+/|/private/tmp/claude-[^/\s]+/")
        for path in [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]:
            self.assertFalse(bool(personal.search(path.read_text())),
                             "personal path in " + str(path.relative_to(ROOT)))
