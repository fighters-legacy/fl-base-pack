#!/usr/bin/env python3
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Headless acceptance for the training syllabus (fl-base-pack#15).

    python3 tools/missiontest/probe_training.py            # needs fl-server on PATH

Every other check in this pack is a VALIDATOR: it proves a file is well formed. None of them can
tell you that a lesson actually runs — that its script loaded, that the instructor found the student,
that a step scored. A training mission whose script died at load looks identical to a healthy one
from the outside: the mission loads, the entities spawn, and nothing ever happens.

That is not hypothetical. Writing these six lessons produced exactly three such failures, and this
harness is what caught all of them:

  * every lesson script failed at `require('instructor')` (engine #1210 — see the CWD note below);
  * the instructor adopted a parked LANDMARK TRUCK as its student and waited forever for it to get
    airborne;
  * and when that was "fixed" by taking the fastest friendly, it adopted a truck again, because at
    tick 0 nothing has moved yet and every candidate ties at zero.

WHAT THIS CANNOT DO. A lesson's student is a human. No AI script in this pack takes off from a
parked start or lands, so the harness stands in for the pilot by stripping `player: true` (an
unoccupied slot is never spawned) and putting the jet in the air. Steps that need a pilot — landing,
strafing a convoy — are therefore exercised as PREDICATES against fixtures rather than as flown
lessons. Completion-testing the syllabus by flying it is the gameplay audit's job, not CI's.

⚠ THE SERVER RUNS WITH ITS CWD SET TO THE CONTENT ROOT, deliberately: pack `require()` resolves the
pack directory against the process working directory rather than the assets root (engine #1210), so
a run from anywhere else loses every lesson script to a require error and then reports a clean,
healthy, entirely inert mission. When #1210 lands this stops mattering; until then it is load-bearing.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[2]

LESSONS = ("t38a_first_flight", "t38a_navigation", "f5e_gunnery",
           "f5e_ir_missile", "f16a_radar_missile", "f5e_defensive")

# The navigation lesson is the one whose middle steps a stand-in CAN fly, so it gets a route through
# its own waypoints. The rest only reach "airborne" without a pilot, which is the honest limit.
ROUTES = {
    "t38a_navigation": "    route: [[4000, 3500, -22000], [20000, 3500, -14000], [22000, 3500, 6000]]\n",
}

FIXTURE_SCRIPT = """local ins = require('instructor')
local reported = false
function compute_control(state, tick, dt)
    if tick == 120 and not reported then
        reported = true
        local subject
        for _, near in ipairs(nearby_entities(__SX__, __SZ__, 500)) do
            local e = get_entity(near.idx)
            if e and math.abs(e.pos.x - __SX__) < 60 and math.abs(e.pos.z - __SZ__) < 60 then
                subject = e
            end
        end
        if subject then
            print(string.format("PRED landed=%s live=%d", tostring(ins.landed(subject)),
                                ins.live_near(state, { { 14000, 0, -9000 } }, 400.0)))
        else
            print("PRED subject=nil")
        end
    end
    return {}
end
"""

FIXTURE_MISSION = """# SPDX-License-Identifier: CC-BY-4.0
name: "predicate fixture"
map: world
layer: world_clear
time: { hour: 12, minute: 0 }
wind: { heading: 250, speed: 0 }
sides: [blue, red]
objects:
  - type: fl-base:t38a
    id: subject
    side: blue
    pos: [__SX__, 0, __SZ__]
    heading: 90
    start: ground
  - type: fl-base:ural375
    id: ops
    side: blue
    pos: [4120, 0, 900]
    heading: 90
    start: ground
    ai: "lua pred_fixture"
__CONVOY__
triggers:
  - on: timer(4)
    do: mission_success
"""

CONVOY = """  - type: fl-base:ural375
    id: t1
    side: red
    pos: [14000, 0, -9000]
    heading: 0
    start: ground"""


def run_server(server, run_root, mission, timeout=300):
    report = run_root.parent / f"{mission}.json"
    proc = subprocess.run(
        [server, "--assets", str(run_root), "--mission", mission,
         "--mission-report", str(report), "--no-discovery"],
        capture_output=True, text=True, timeout=timeout, cwd=run_root)  # cwd: see the module note
    return json.loads(report.read_text()), proc.stdout


def probe_lesson(server, run_root, pack, stem):
    src = (pack / "missions" / f"{stem}.yaml").read_text()
    body = src.replace("    player: true\n", "").replace(
        "    pos: [4000, 0, 1200]\n    heading: 90\n    start: ground\n",
        "    pos: [4000, 0, 1200]\n    heading: 90\n    alt: 3500\n    speed: 220\n"
        + ROUTES.get(stem, ""))
    (pack / "missions" / "probe.yaml").write_text(body)
    report, out = run_server(server, run_root, "probe")
    steps = [m[2] for m in re.findall(r"LESSON step (\d+)/(\d+) complete: (\S+)", out)]
    errors = [l for l in out.splitlines() if "LUA" in l or "lua script" in l]
    return report, steps, ("LESSON start" in out), errors


def probe_predicate(server, run_root, pack, sx, sz, convoy):
    (pack / "ai" / "pred_fixture.lua").write_text(
        FIXTURE_SCRIPT.replace("__SX__", str(sx)).replace("__SZ__", str(sz)))
    (pack / "missions" / "pred.yaml").write_text(
        FIXTURE_MISSION.replace("__SX__", str(sx)).replace("__SZ__", str(sz))
                       .replace("__CONVOY__", CONVOY if convoy else ""))
    _, out = run_server(server, run_root, "pred", timeout=120)
    line = next((l for l in out.splitlines() if l.startswith("PRED")), "")
    return line


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--server", default=shutil.which("fl-server"),
                    help="path to fl-server (default: the one on PATH)")
    args = ap.parse_args()
    if not args.server:
        print("fl-server not found on PATH — see .github/actions/engine-validators", file=sys.stderr)
        return 2

    failures = []
    with tempfile.TemporaryDirectory(prefix="fl-training-") as tmp:
        run_root = Path(tmp) / "flrun"
        pack = run_root / "mods" / "fl-base-pack"
        pack.parent.mkdir(parents=True)
        shutil.copytree(PACK_ROOT, pack, ignore=shutil.ignore_patterns(".git", "*.glb", "*.ogg"))

        for stem in LESSONS:
            report, steps, started, errors = probe_lesson(args.server, run_root, pack, stem)
            problems = []
            if errors:
                problems.append(f"lua: {errors[0][:110]}")
            if not started:
                problems.append("the lesson script never ran")
            if not steps:
                problems.append("no step ever scored")
            if report["entity_cap_refusals"]:
                problems.append(f"entity_cap_refusals={report['entity_cap_refusals']}")
            status = "ok" if not problems else "FAIL"
            print(f"  [{status}] {stem:<20} spawned={report['spawned_objects']} steps={steps}")
            for p in problems:
                print(f"          {p}")
                failures.append(f"{stem}: {p}")

        # Predicates a stand-in pilot cannot reach. Landing is the syllabus's most-used step and the
        # one no headless lesson can ever prove, so it is proven here instead — in both directions,
        # because a predicate that is always true is worse than one that is always false.
        cases = [((4000, 1200, False), "landed=true"),      # parked on the runway
                 ((7000, 1200, False), "landed=false"),     # parked 3 km off-field
                 ((4000, 1200, True), "live=1")]            # convoy standing
        for (sx, sz, convoy), expect in cases:
            line = probe_predicate(args.server, run_root, pack, sx, sz, convoy)
            ok = expect in line
            print(f"  [{'ok' if ok else 'FAIL'}] predicate {sx},{sz} convoy={convoy}: {line or '(no output)'}")
            if not ok:
                failures.append(f"predicate {sx},{sz}: expected {expect}, got {line!r}")

    print()
    if failures:
        print(f"{len(failures)} problem(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("training syllabus: every lesson runs, every predicate behaves.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
