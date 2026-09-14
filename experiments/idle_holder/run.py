#!/usr/bin/env python3
"""Idle-holder experiment (design note 2026-09-13): did the holder not know, or know and not act?

Each run: a fresh sandbox Git repo with the task under ./task, an isolated agentdm state directory, a
`claude -p` holder session whose prompt says nothing about mail, and a scripted peer that registers as
`requester` and sends one `claim`-kind request at --minute. Records when the request was queued, every
holder tool call (from stream-json), whether/when the request was offered (fetched) and decided, what
the experimental PostToolUse hook logged, and the run's cost. Nothing here reads the holder's mailbox.

  python3 experiments/idle_holder/run.py --hook on --runs 1 --model sonnet
"""
import argparse, json, os, shutil, subprocess, sys, tempfile, threading, time, uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from agentdm.store import resolve_store, _mid_key, _read_json          # noqa: E402
from agentdm.presence import PresenceHold                               # noqa: E402

PROMPT = ("Implement every function in calc/ so that `python3 -m unittest` passes from this directory. "
          "This checkout is shared with other agents: before editing any file, call the agentdm `claim` tool "
          "with the paths you are about to edit (ttl_s 1200), and call `release` for each of your claims when you "
          "are done with those paths. Work one module at a time and run the tests after each. Do not commit.")

DEBRIEF = ("The task is over; this is a debrief, not more work. During the task, did any tool result carry extra "
           "hook context beginning with 'agentdm:'? If yes, quote each such line verbatim and say after which tool "
           "call you first saw it and why you did or did not act on it. If you saw none, reply exactly NONE.")

REQUEST_BODY = ("I need {path} for a one-line change (a docstring fix) and it is under your claim {claim}. "
                "May I take it now, or would you rather finish first? Please answer with accept or decline.")


def run_one(args, idx, out_dir):
    run_dir = out_dir / (f"run-{idx:02d}-hook-{args.hook}" + (f"-{args.wording}" if args.wording != "default" else ""))
    run_dir.mkdir(parents=True)
    sandbox = run_dir / "sandbox"
    shutil.copytree(ROOT / "experiments" / "idle_holder" / "task", sandbox)
    state = run_dir / "state"
    env = dict(os.environ, XDG_STATE_HOME=str(state), AGENTDM_ALIAS="holder",
               AGENTDM_HOOK_LOG=str(run_dir / "hook.log"), AGENTDM_HOOK_WORDING=args.wording)
    for k in ("DARKER_HEADLESS", "AGENTDM_DISABLE", "AGENTDM_PROJECT_DIR", "AGENTDM_SESSION_ID", "CLAUDE_CODE_SESSION_ID"):
        env.pop(k, None)
    subprocess.run(["git", "init", "-q", str(sandbox)], check=True, env=env)
    subprocess.run(["git", "-C", str(sandbox), "-c", "user.email=x@x", "-c", "user.name=x", "add", "-A"], check=True, env=env)
    subprocess.run(["git", "-C", str(sandbox), "-c", "user.email=x@x", "-c", "user.name=x", "commit", "-q", "-m", "task"], check=True, env=env)
    # A user-scope Claude Code hook on the maintainer's machine refuses writes on 'main' (it aborted
    # matrix run 05); sandboxes work on a branch so that guard never fires.
    subprocess.run(["git", "-C", str(sandbox), "checkout", "-q", "-b", "work"], check=True, env=env)
    py = sys.executable
    mcp = {"mcpServers": {"agentdm": {"command": py, "args": [str(ROOT / "bin" / "agentdm-server")],
                                      "env": {"XDG_STATE_HOME": str(state), "AGENTDM_ALIAS": "holder"}}}}
    (run_dir / "mcp.json").write_text(json.dumps(mcp))
    session_id = str(uuid.uuid4())
    cmd = ["claude", "-p", PROMPT, "--output-format", "stream-json", "--verbose", "--model", args.model,
           "--dangerously-skip-permissions", "--strict-mcp-config", "--mcp-config", str(run_dir / "mcp.json"),
           "--session-id", session_id]
    if args.hook == "on":
        settings = {"hooks": {"PostToolUse": [{"matcher": "", "hooks": [{"type": "command", "timeout": 5,
                    "command": f'"{py}" "{ROOT / "hooks" / "agentdm-posttool-hook.py"}"'}]}]}}
        (run_dir / "settings.json").write_text(json.dumps(settings))
        cmd += ["--settings", str(run_dir / "settings.json")]
    t0 = time.time()
    proc = subprocess.Popen(cmd, cwd=sandbox, env=env, stdout=subprocess.PIPE, stderr=open(run_dir / "stderr.txt", "w"), text=True)
    events, tool_calls, result = [], [], {}

    def reader():
        for line in proc.stdout:
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            ev["_t"] = time.time() - t0
            events.append(ev)
            if ev.get("type") == "assistant":
                for block in (ev.get("message") or {}).get("content", []):
                    if block.get("type") == "tool_use":
                        tool_calls.append({"t": ev["_t"], "name": block.get("name"), "input": {k: v for k, v in (block.get("input") or {}).items() if k in ("message_id", "paths", "claim_id", "to", "kind")}})
            elif ev.get("type") == "result":
                result.update({k: ev.get(k) for k in ("total_cost_usd", "duration_ms", "num_turns", "is_error", "subtype")})
    threading.Thread(target=reader, daemon=True).start()

    # --- scripted requester -------------------------------------------------------------------
    store = None
    while proc.poll() is None and store is None:
        try:
            store = resolve_store(str(sandbox), state_home=str(state))
        except Exception:
            time.sleep(1)
    req = {"queued_at": None, "message_id": None, "offered_at": None, "decided_at": None, "outcome": None,
           "target_path": None, "claim_id": None}
    hold = None
    seen_claims = []
    while proc.poll() is None and req["queued_at"] is None:
        elapsed = time.time() - t0
        held = [c for c in store.claims() if c["state"] == "held" and c["alias"] == "holder"]
        for c in store.claims():
            if c["alias"] == "holder" and c["id"] not in seen_claims:
                seen_claims.append(c["id"])
        # Fire on the Nth distinct claim the holder has taken (mid-task by construction), not on a clock:
        # the dry run showed a strong model reaching its last module before minute two.
        if len(seen_claims) >= args.nth_claim and held and elapsed >= args.minute * 60:
            c = held[0]
            reg = store.register("requester", family="claude-code", pid=os.getpid(), ppid=os.getppid(),
                                 session_id=str(uuid.uuid4()), session_source="experiment")
            hold = PresenceHold(store._presence_path(reg["incarnation_id"]), reg)
            path = c["paths"][0]
            mid = store.send("requester", reg["incarnation_id"], "holder", f"request: {path} for a one-line change",
                             REQUEST_BODY.format(path=path, claim=c["id"]), "claim")
            req.update(queued_at=time.time() - t0, message_id=mid, target_path=path, claim_id=c["id"])
        else:
            time.sleep(2)
    key = _mid_key(req["message_id"]) if req["message_id"] else None
    while proc.poll() is None:
        if key:
            if req["offered_at"] is None and os.path.exists(store._p("offers", f"{key}.json")):
                req["offered_at"] = time.time() - t0
            oc = _read_json(store._p("outcomes", f"{key}.json"))
            if oc and req["decided_at"] is None:
                req.update(decided_at=time.time() - t0, outcome=oc["outcome"])
        if time.time() - t0 > args.timeout:
            proc.kill(); result["killed"] = True
        time.sleep(1)
    proc.wait()
    time.sleep(1)
    if key:
        if req["offered_at"] is None and os.path.exists(store._p("offers", f"{key}.json")):
            req["offered_at"] = time.time() - t0
        oc = _read_json(store._p("outcomes", f"{key}.json"))
        if oc and req["decided_at"] is None:
            req.update(decided_at=time.time() - t0, outcome=oc["outcome"])
    if hold:
        hold.close()
    tests = subprocess.run([sys.executable, "-m", "unittest"], cwd=sandbox, capture_output=True, text=True)
    # Debrief AFTER the task: resume the same session and ask what hook context it received. stream-json
    # does not show PostToolUse additionalContext (verified by probe 2026-09-13), so the transcript itself
    # is the only witness of whether the count reached the model. Asking afterwards cannot change what
    # the holder did during the task.
    debrief = subprocess.run(["claude", "-p", "--resume", session_id, "--model", args.model,
                              "--strict-mcp-config", "--mcp-config", str(run_dir / "mcp.json"),
                              "--dangerously-skip-permissions", "--output-format", "json",
                              DEBRIEF], cwd=sandbox, env=env, capture_output=True, text=True, timeout=300)
    try:
        debrief_text = json.loads(debrief.stdout).get("result", "")
    except ValueError:
        debrief_text = debrief.stdout
    (run_dir / "debrief.txt").write_text(debrief_text)
    saw_count = "unread" in debrief_text.lower() and "none" not in debrief_text.lower()[:20]
    hook_log = [json.loads(l) for l in (run_dir / "hook.log").read_text().splitlines()] if (run_dir / "hook.log").exists() else []
    emitted = [h for h in hook_log if h.get("emitted")]
    calls_after = [c for c in tool_calls if req["queued_at"] is not None and c["t"] >= req["queued_at"]]
    first_inbox = next((c for c in calls_after if c["name"] == "mcp__agentdm__inbox"), None)
    summary = {
        "run": run_dir.name, "hook": args.hook, "wording": args.wording, "model": args.model, "wall_s": round(time.time() - t0, 1),
        "tests_pass": tests.returncode == 0, "claims_seen": len([c for c in store.claims()]),
        "request": req,
        "tool_calls_total": len(tool_calls),
        "tool_calls_after_request": len(calls_after),
        "tool_calls_before_first_inbox": (len([c for c in calls_after if c["t"] < first_inbox["t"]]) if first_inbox else None),
        "hook_invocations": len(hook_log), "hook_emitted": len(emitted),
        "hook_first_emit_after_request": (round(emitted[0]["t"] - (t0 + req["queued_at"]), 1) if emitted and req["queued_at"] is not None else None),
        "hook_statuses": sorted({str(h.get("status")) for h in hook_log}),
        "debrief_saw_count": saw_count, "debrief": debrief_text[:600],
        "result": result,
    }
    (run_dir / "events.jsonl").write_text("\n".join(json.dumps(e) for e in events))
    (run_dir / "tool_calls.json").write_text(json.dumps(tool_calls, indent=1))
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=1))
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hook", choices=("on", "off"), required=True)
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--minute", type=float, default=0.0, help="earliest minute to inject (default: no clock gate)")
    ap.add_argument("--nth-claim", type=int, default=2, help="inject once the holder has taken its Nth distinct claim")
    ap.add_argument("--timeout", type=float, default=900.0)
    ap.add_argument("--out", default=None)
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--wording", choices=("default", "claims"), default="default")
    args = ap.parse_args()
    out = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix="idle-holder-"))
    print("results:", out, flush=True)
    for i in range(args.start, args.start + args.runs):
        s = run_one(args, i, out)
        with open(out / "results.jsonl", "a") as f:
            f.write(json.dumps(s) + "\n")
        print(json.dumps({k: s[k] for k in ("run", "wall_s", "tests_pass", "tool_calls_after_request",
                                            "tool_calls_before_first_inbox", "hook_emitted", "hook_first_emit_after_request",
                                            "debrief_saw_count")}
                         | {"offered": s["request"]["offered_at"], "outcome": s["request"]["outcome"],
                            "cost": (s["result"] or {}).get("total_cost_usd")}), flush=True)


if __name__ == "__main__":
    main()
