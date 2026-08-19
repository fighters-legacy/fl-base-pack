#!/usr/bin/env python3
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Headless acceptance for the campaign seed (fl-base-pack#14).

    python3 tools/missiontest/probe_campaign.py --server <fl-server>

Drives `fl-server --campaign` through four sequential sorties from one working directory (the
campaign persists to cache/*.flsave in CWD) and asserts the engine #1036 Stage-4 campaign
acceptance end to end:

  1. the opening STORY mission flies first (campaign_start) and, completed, ADVANCES THE
     FRONTLINE — the .flsave's theater line must point at the post-s01 raster;
  2. the DYNAMIC war generates sorties from templates once unlocked — each must materialize into
     a real mission (a sortie with unresolved placeholders parses to nothing and spawns nothing,
     so `spawned > 0` + a success outcome is the proof) and apply ATTRITION to the red order of
     battle;
  3. after two dynamic sorties the second STORY INJECTS AT ITS TRIGGER (after_sorties: 2), and
     completing it advances the frontline again.

Outcomes are forced the same way probe_strike.py forces them — `kill <idx>` admin triggers and
timer mission_success lines appended to the RUN COPY — because no AI in this pack can fly a
sortie to completion; what is under test here is the CAMPAIGN spine, not the flying.

⚠ REQUIRES AN fl-server WITH THE GEODETIC TEMPLATE FILLS (engine #1222). Against an older server
every airborne object in a dynamic sortie spawns at an unresolved or sea-level position and the
dynamic legs fail loudly. Pack CI therefore gates campaign content on validate-campaign only;
run this against an engine release that carries #1222 (or a main build).
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

# Pool indices are spawn order, which is object order with unoccupied player slots skipped.
# s01: battery=0 flak1=1 · s02: bandit1=0 bandit2=1. Reordering those missions breaks this map —
# loudly: the wrong entity dies and the sortie fails its outcome assertion.
S01_KILL = "  - on: timer(20)\n    do: kill 0\n"
S02_KILL = "  - on: timer(20)\n    do: kill 0\n"
TEMPLATE_WIN = "  - on: timer(30)\n    do: mission_success\n"


def run_sortie(server, run_root, seq, timeout=300):
    report = run_root.parent / f"sortie_{seq}.json"
    proc = subprocess.run(
        [server, "--assets", str(run_root),
         "--campaign", "mods/fl-base-pack/missions/campaign_nttr.yaml",
         "--mission-report", str(report), "--no-discovery"],
        capture_output=True, text=True, timeout=timeout, cwd=run_root)
    if not report.exists():
        tail = "\n".join((proc.stdout + proc.stderr).splitlines()[-8:])
        raise RuntimeError(f"sortie {seq}: no mission report — server said:\n{tail}")
    m = re.search(r"flying sortie '([^']+)'", proc.stdout)
    return json.loads(report.read_text()), (m.group(1) if m else ""), proc.stdout


def flsave(run_root):
    saves = list((run_root / "cache").glob("campaign_*.flsave"))
    return saves[0].read_text() if saves else ""


def red_strength(save_text):
    m = re.search(r"theater=nttr;[^\n]*", save_text)
    return sum(int(n) for n in re.findall(r"red/\w+=(\d+)", m.group(0))) if m else -1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--server", default=shutil.which("fl-server"))
    args = ap.parse_args()
    if not args.server:
        print("fl-server not found on PATH", file=sys.stderr)
        return 2

    failures = []

    def check(cond, what):
        print(f"  [{'ok' if cond else 'FAIL'}] {what}")
        if not cond:
            failures.append(what)

    with tempfile.TemporaryDirectory(prefix="fl-campaign-") as tmp:
        run_root = Path(tmp) / "flrun"
        pack = run_root / "mods" / "fl-base-pack"
        pack.parent.mkdir(parents=True)
        shutil.copytree(PACK_ROOT, pack, ignore=shutil.ignore_patterns(".git", "*.glb", "*.ogg"))

        # Force every outcome: story missions die to a kill trigger, templates win on a timer.
        for stem, extra in (("s01_first_light", S01_KILL), ("s02_line_holds", S02_KILL)):
            p = pack / "missions" / f"{stem}.yaml"
            p.write_text(p.read_text() + extra)
        for t in (pack / "templates").glob("*.yaml"):
            t.write_text(t.read_text() + TEMPLATE_WIN)

        # Sortie 1: the opening story, then the first frontline advance.
        rep, sid, _ = run_sortie(args.server, run_root, 1)
        check(sid == "s01_first_light", f"sortie 1 is the campaign_start story (got '{sid}')")
        check(rep["outcome"] == "success", "sortie 1 completes")
        save = flsave(run_root)
        check("completed=" in save and "s01_first_light" in save, "s01 recorded complete")
        check("frontlines/nttr_after_s01.png" in save,
              "FRONTLINE ADVANCED after objective completion (post-s01 raster active)")
        red_before = red_strength(save)

        # Sorties 2-3: the dynamic war. Materialized templates must spawn and win; red attrits.
        for seq in (2, 3):
            rep, sid, _ = run_sortie(args.server, run_root, seq)
            check(sid.startswith("dynamic:nttr:"), f"sortie {seq} is a generated sortie ('{sid}')")
            check(rep["spawned_objects"] >= 1, f"sortie {seq} materialized real spawns")
            check(rep["outcome"] == "success", f"sortie {seq} completes")
            check(rep["entity_cap_refusals"] == 0, f"sortie {seq} no cap refusals")
        red_after = red_strength(flsave(run_root))
        check(red_after == red_before - 2, f"attrition applied ({red_before} -> {red_after})")

        # Sortie 4: the second story injects at after_sorties: 2, and advances the line again.
        rep, sid, _ = run_sortie(args.server, run_root, 4)
        check(sid == "s02_line_holds", f"STORY INJECTS AT TRIGGER after two sorties (got '{sid}')")
        check(rep["outcome"] == "success", "sortie 4 completes")
        check("frontlines/nttr_after_s02.png" in flsave(run_root),
              "frontline advanced again (post-s02 raster active)")

    # The AIRBORNE geodetic fill, exercised for real. The campaign's RNG is not persisted, so a
    # one-sortie-per-process war redraws the same template every run (strike, here — ground
    # objects only). Force the intercept template by handing the run copy a campaign that lists
    # nothing else: its bandit spawns airborne from lat/lon + alt, and a spawn that resolved to
    # sea level (under the basin floor) dies within a couple of seconds — alive at the 30 s
    # timer is the proof the geodetic fills work in a real sortie, not just the engine's unit test.
    with tempfile.TemporaryDirectory(prefix="fl-campaign-air-") as tmp:
        run_root = Path(tmp) / "flrun"
        pack = run_root / "mods" / "fl-base-pack"
        pack.parent.mkdir(parents=True)
        shutil.copytree(PACK_ROOT, pack, ignore=shutil.ignore_patterns(".git", "*.glb", "*.ogg"))
        p = pack / "missions" / "s01_first_light.yaml"
        p.write_text(p.read_text() + S01_KILL)
        for t in (pack / "templates").glob("*.yaml"):
            t.write_text(t.read_text() + TEMPLATE_WIN)
        camp = pack / "missions" / "campaign_nttr.yaml"
        body = "".join(l for l in camp.read_text().splitlines(keepends=True)
                       if "nttr_cap.yaml" not in l and "nttr_strike.yaml" not in l
                       and "nttr_sead.yaml" not in l)
        camp.write_text(body)
        run_sortie(args.server, run_root, 90)   # s01, auto-won
        rep, sid, _ = run_sortie(args.server, run_root, 91)
        check(sid.startswith("dynamic:nttr:intercept"),
              f"forced-intercept sortie generated ('{sid}')")
        check(rep["spawned_objects"] == 1 and rep["live_entities"] == 1,
              "the airborne geodetic spawn is alive at mission end "
              f"(spawned={rep['spawned_objects']} live={rep['live_entities']})")

    print()
    if failures:
        print(f"{len(failures)} problem(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("campaign seed: the story leads, the frontline advances, the dynamic war attrits.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
