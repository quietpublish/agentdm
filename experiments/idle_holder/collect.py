#!/usr/bin/env python3
"""Copy run summaries and debriefs from a results directory into results/<arm>/, scrubbing sandbox
paths, and print one table row per run. Usage: collect.py <results-dir> <arm-name>"""
import json, re, sys
from pathlib import Path

src, arm = Path(sys.argv[1]), sys.argv[2]
dst = Path(__file__).resolve().parent / "results" / arm
dst.mkdir(parents=True, exist_ok=True)
scrub = lambda t: re.sub(r"/(?:private/)?(?:tmp|Users)/[^\s`'\")]*", "<path>", t)
for line in open(src / "results.jsonl"):
    s = json.loads(line)
    s["debrief"] = scrub(s.get("debrief", ""))
    (dst / f"{s['run']}.json").write_text(json.dumps(s, indent=1))
    d = src / s["run"] / "debrief.txt"
    if d.exists():
        (dst / f"{s['run']}.debrief.md").write_text(scrub(d.read_text()))
    r = s["request"]
    print(f"| {s['run']} | {s['wall_s']:.0f} | {s['tests_pass']} | {r['queued_at'] and round(r['queued_at'])} | "
          f"{s['hook_emitted']} | {s['hook_first_emit_after_request']} | {s['debrief_saw_count']} | "
          f"{r['offered_at'] and round(r['offered_at'])} | {r['outcome']} | {(s['result'] or {}).get('total_cost_usd', 0):.2f} |")
