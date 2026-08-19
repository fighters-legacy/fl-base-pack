#!/usr/bin/env python3
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Headless acceptance for the strike / instant-action set (fl-base-pack#3).

    python3 tools/missiontest/probe_strike.py            # needs fl-server on PATH

The same argument probe_training.py makes for the syllabus: validators prove the files are well
formed, and nothing else proves the missions DO anything. A strike mission whose director died at
load, whose SAM faces the wrong way, or whose objective radii swallow the wrong entities looks
identical to a healthy one from the outside.

WHAT A HEADLESS RUN CANNOT DO: fly the strike. A stripped player slot becomes an AI on
ai/fighter.lua, which is air-to-air only — no script in this pack drops a bomb on a depot. So the
probes prove each half separately instead:

  * the DEFENCE, by feeding it the one approach the briefs call fatal: a route-flown jet straight
    into the SA-6's face at 3,000 m. The measured envelope (v0.3.18, at the anchor) says that dies
    in 73-99 s from engagement — if it survives, the siting or facing has rotted;
  * the SCORING, by killing the objective entities with the `kill <idx>` admin command from timer
    triggers in a run copy, and requiring the director to score each group and end the mission.

⚠ THE kill TRIGGERS ARE WIRED BY POOL INDEX, which is spawn order, which is object order in the
mission file. Reordering a mission's `objects:` will break the index maps below — LOUDLY: the wrong
entity dies, the director never completes, and the probe fails. Update the maps with the file.

Flying the mission for real is the #1065 gameplay audit's job, not CI's.
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

WITNESS = """local last_n = -1
local function spd(e) return math.sqrt(e.vel.x*e.vel.x + e.vel.y*e.vel.y + e.vel.z*e.vel.z) end
function compute_control(state, tick, dt)
    local n = 0
    for _, near in ipairs(nearby_entities(state.pos.x, state.pos.z, 60000)) do
        local e = get_entity(near.idx)
        if e and not e.dead and spd(e) > 400 then n = n + 1 end
    end
    if n ~= last_n then print(string.format("WITNESS t=%d missiles=%d", tick, n)) end
    last_n = n
    return {}
end
"""

# The ia_sead player slot, replaced wholesale for the defence probe: same id (the destroy trigger
# references it), no `player:`, and a route straight through the battery's face.
SEAD_INGRESS = """  - type: fl-base:f16a
    id: player1
    side: blue
    pos: [32000, 3000, 14000]
    heading: 245
    speed: 230
    route: [[-2000, 3000, -3800]]
"""


_run_seq = 0


def run_server(server, run_root, mission, timeout=300):
    # A unique report per run, and a hard failure when the server dies before writing one — a
    # stale report from the PREVIOUS run reads as a convincing wrong answer otherwise (hit while
    # writing this file: a bad run copy "passed" with the prior mission's numbers).
    global _run_seq
    _run_seq += 1
    report = run_root.parent / f"{mission}_{_run_seq}.json"
    proc = subprocess.run(
        [server, "--assets", str(run_root), "--mission", mission,
         "--mission-report", str(report), "--no-discovery"],
        capture_output=True, text=True, timeout=timeout, cwd=run_root)
    if not report.exists():
        tail = "\n".join((proc.stdout + proc.stderr).splitlines()[-6:])
        raise RuntimeError(f"no mission report written — server said:\n{tail}")
    return json.loads(report.read_text()), proc.stdout


def kill_triggers(idx_times):
    return "".join(f"  - on: timer({t})\n    do: kill {i}\n" for i, t in idx_times)


def probe(server, run_root, pack, name, mutate, checks, failures):
    src = (pack / "missions" / f"{name}.yaml").read_text()
    (pack / "missions" / "probe.yaml").write_text(mutate(src))
    report, out = run_server(server, run_root, "probe")
    errors = [l for l in out.splitlines() if "LUA" in l or "lua script" in l]
    problems = [f"lua: {errors[0][:110]}"] if errors else []
    if report["entity_cap_refusals"]:
        problems.append(f"entity_cap_refusals={report['entity_cap_refusals']}")
    problems += checks(report, out)
    status = "ok" if not problems else "FAIL"
    print(f"  [{status}] {name:<12} outcome={report['outcome']} "
          f"elapsed={report['elapsed_seconds']} spawned={report['spawned_objects']}")
    for p in problems:
        print(f"          {p}")
        failures.append(f"{name}: {p}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--server", default=shutil.which("fl-server"))
    args = ap.parse_args()
    if not args.server:
        print("fl-server not found on PATH — see .github/actions/engine-validators", file=sys.stderr)
        return 2

    failures = []
    with tempfile.TemporaryDirectory(prefix="fl-strike-") as tmp:
        run_root = Path(tmp) / "flrun"
        pack = run_root / "mods" / "fl-base-pack"
        pack.parent.mkdir(parents=True)
        shutil.copytree(PACK_ROOT, pack, ignore=shutil.ignore_patterns(".git", "*.glb", "*.ogg"))
        (pack / "ai" / "probe_witness.lua").write_text(WITNESS)

        # coop_strike scoring path. Pool indices by object order:
        # 0 player1  1 player2  2 ops  3 depot  4 sam1  5 flak1  6 truck1  7 truck2  8 cap1
        probe(args.server, run_root, pack, "coop_strike",
              lambda s: s.replace("    player: true\n", "")
                         + kill_triggers([(4, 20), (5, 30), (3, 40)]),
              lambda r, out: (
                  (["spawned != 9"] if r["spawned_objects"] != 9 else []) +
                  (["director never ran"] if "DIRECTOR start" not in out else []) +
                  ([f"objectives scored {out.count('objective complete')}/3"]
                   if out.count("objective complete") != 3 else []) +
                  (["scoring path did not complete the mission"]
                   if r["outcome"] != "success" else [])),
              failures)

        # ia_sead A: the defence proves itself against the fatal approach. The mission "failing"
        # IS the pass condition — the ingress jet dies to the battery, well before the draw timer.
        def sead_defence(s):
            s2 = re.sub(r"  - type: fl-base:f16a\n.*?fl-base:lau3\]\n", SEAD_INGRESS, s,
                        count=1, flags=re.S)
            assert s2 != s, "ia_sead player block not found — the probe's regex has rotted"
            witness = ("  - type: fl-base:ural375\n    id: witness\n    side: red\n"
                       "    pos: [15300, 0, 6200]\n    heading: 0\n    start: ground\n"
                       "    ai: \"lua probe_witness\"\n")
            return s2.replace("triggers:\n", witness + "\ntriggers:\n", 1)

        probe(args.server, run_root, pack, "ia_sead", sead_defence,
              lambda r, out: (
                  (["no missile ever flew"] if "missiles=1" not in out else []) +
                  (["the fatal approach survived — check battery facing/siting"]
                   if not (r["outcome"] == "failure" and r["elapsed_seconds"] < 500) else [])),
              failures)

        # ia_sead B: the success trigger. Indices: 0 player1  1 battery  2 flak1
        probe(args.server, run_root, pack, "ia_sead",
              lambda s: s.replace("    player: true\n", "") + kill_triggers([(1, 20)]),
              lambda r, out: (["destroy(battery) did not succeed the mission"]
                              if r["outcome"] != "success" else []),
              failures)

        # ia_dogfight: a live AI-vs-AI engagement; any decided outcome inside the timer is honest.
        probe(args.server, run_root, pack, "ia_dogfight",
              lambda s: s.replace("    player: true\n", ""),
              lambda r, out: (
                  (["spawned != 2"] if r["spawned_objects"] != 2 else []) +
                  (["no trigger ever fired"] if r["triggers_fired"] < 1 else [])),
              failures)

        # ia_gun_run scoring path. Indices: 0 player1  1 ops  2..4 trucks  5 flak1
        probe(args.server, run_root, pack, "ia_gun_run",
              lambda s: s.replace("    player: true\n", "")
                         + kill_triggers([(2, 20), (3, 25), (4, 30)]),
              lambda r, out: (
                  (["director never ran"] if "DIRECTOR start" not in out else []) +
                  (["convoy objective did not complete the mission"]
                   if r["outcome"] != "success" else [])),
              failures)

    print()
    if failures:
        print(f"{len(failures)} problem(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("strike set: the defence kills, the objectives score, every mission ends.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
