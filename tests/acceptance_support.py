"""Owned, zero-model process fixtures for executable acceptance scenarios.

No ambient agent identity, hooks, mailbox or credentials are needed. Every child
is bounded and reaped before its temporary project/state directory is removed.
"""
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


def isolated_environment(state, root=ROOT):
    # Inherit execution essentials, never credentials, Git repository selection,
    # injected shell startup or the supervising agent's identity/markers.
    allowed = ("PATH", "TMPDIR", "TMP", "TEMP", "LANG", "LC_ALL", "LC_CTYPE", "SYSTEMROOT", "WINDIR")
    env = {key: os.environ[key] for key in allowed if key in os.environ}
    env.update(PYTHONPATH=str(root), PYTHONDONTWRITEBYTECODE="1",
               GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)
    if state is not None:
        env["XDG_STATE_HOME"] = str(state)
    return env


class StdioPeer:
    def __init__(self, case, alias="acceptance"):
        self.case = case
        self.buffer = b""
        self.messages = []
        self.stderr = tempfile.TemporaryFile()
        env = dict(case.env, AGENTDM_PROJECT_DIR=str(case.project),
                   AGENTDM_ALIAS=alias, AGENTDM_SESSION_ID="acceptance-session",
                   AGENTDM_WAIT_BUDGET_S="2")
        self.process = subprocess.Popen(
            [sys.executable, "-m", "agentdm.server"], cwd=case.project, env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr)
        case.addCleanup(self.close)
        self.send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                   "params": {"protocolVersion": "2025-06-18"}})
        self.response(1)

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)
        self.process.stdin.close()
        self.process.stdout.close()
        self.stderr.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def raw(self, data):
        self.process.stdin.write(data)
        self.process.stdin.flush()

    def send(self, obj):
        self.raw((json.dumps(obj) + "\n").encode())

    def call(self, rid, name, **arguments):
        self.send({"jsonrpc": "2.0", "id": rid, "method": "tools/call",
                   "params": {"name": name, "arguments": arguments}})

    def response(self, rid, timeout=2):
        deadline = time.monotonic() + timeout
        while True:
            for response in self.messages:
                if response.get("id") == rid:
                    return response
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self.case.fail("no response for request %r; received IDs %r" %
                               (rid, [m.get("id") for m in self.messages]))
            ready, _, _ = select.select([self.process.stdout], [], [], remaining)
            if not ready:
                continue
            chunk = os.read(self.process.stdout.fileno(), 65536)
            if not chunk:
                self.case.fail("server closed stdout before request %r completed" % rid)
            self.buffer += chunk
            while b"\n" in self.buffer:
                line, self.buffer = self.buffer.split(b"\n", 1)
                self.messages.append(json.loads(line))

    @staticmethod
    def payload(response):
        return json.loads(response["result"]["content"][0]["text"])


class AcceptanceCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="agentdm-acceptance-")
        self.addCleanup(self.temporary.cleanup)
        self.scratch = Path(self.temporary.name)
        self.project = self.scratch / "project"
        self.project.mkdir()
        self.state = self.scratch / "state"
        self.env = isolated_environment(self.state)
        subprocess.run(["git", "init", "-q", str(self.project)], check=True,
                       capture_output=True, timeout=5, env=self.env)

    def peer(self):
        return StdioPeer(self)

    def hook(self, name, payload, markers=None):
        return subprocess.run([sys.executable, str(ROOT / "hooks" / name)],
                              input=json.dumps(payload), text=True, capture_output=True,
                              env=dict(self.env, **(markers or {})), cwd=self.project,
                              timeout=2)
