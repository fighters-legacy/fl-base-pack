#!/usr/bin/env python3
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: MIT
"""Verify the NTTR theater tiles against ground truth (fl-base-pack#2).

    python3 tools/terrain/verify_nttr_theater.py --server <fl-server>

The #2 acceptance is behavioural — "renders as high-detail tiles overriding the coarse global
base; heightAt returns correct elevation over the theater" — and no validator tests it: a tile
tree can be perfectly well-formed PNG and encode noise. So this probe measures the one thing the
tiles are FOR, the terrain the simulation actually stands entities on:

  * spawn a row of ground-started trucks at surveyed points inside the theater (object-level
    lat/lon placement, so the numbers below are checkable against any map);
  * a witness script reports each one's resolved MSL altitude (guidance.altitude — never pos.y);
  * run once WITHOUT terrain/world in the pack copy (the engine's bundled level 0-5 base, ~5 km/px
    at best) and once WITH the theater tiles (levels 6-10, ~76 m/px at L10);
  * the WITH run must land inside each point's GLO-30 truth band, and must beat the WITHOUT run
    on sharp relief — that improvement is what proves the engine is actually reading the pack's
    tiles rather than its own base.

EXPECTED values are GLO-30 samples (gdallocationinfo on the source mosaic, recorded per point
below). Tolerances are honest about resolution: a 129-px L10 tile smooths a peak, so summits get
a wide band and basin floors a tight one.
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

# (name, lat, lon, GLO-30 elevation m, tolerance m). Elevations are gdallocationinfo samples of
# the build mosaic AT THESE EXACT COORDINATES (see tools/terrain/build_nttr_theater.sh for the
# mosaic's provenance) — the check is "does the engine return what the DEM says here", so the
# truth is the DEM's own value, not a gazetteer's summit figure. Flat ground gets a tight band;
# mountain slopes a wide one (a 76 m/px L10 lattice moves metres of height per pixel of slope).
POINTS = [
    ("vegas_valley", 36.3000, -115.0300, 665.0, 40.0),
    ("frenchman_lake", 36.8000, -115.9350, 939.0, 40.0),
    ("sheep_range_slope", 36.7500, -115.2000, 1921.0, 150.0),
    ("spring_mtns_slope", 36.2716, -115.6425, 2575.0, 200.0),
]

WITNESS = """function compute_control(state, tick, dt)
    if tick == 300 then
        for _, near in ipairs(nearby_entities(state.pos.x, state.pos.z, 300000)) do
            local e = get_entity(near.idx)
            if e and not e.dead then
                local g = guidance.geodetic(e.pos)
                print(string.format("TERR lat=%.4f lon=%.4f alt=%.1f", g.lat, g.lon, g.alt))
            end
        end
    end
    return {}
end
"""


def mission_yaml():
    objs = "".join(
        f"  - type: fl-base:ural375\n    id: p{i}\n    side: blue\n    pos: [0, 0, 0]\n"
        f"    lat: {lat}\n    lon: {lon}\n    heading: 0\n    start: ground\n"
        for i, (_, lat, lon, _, _) in enumerate(POINTS))
    return ("name: \"terrain probe\"\nmap: world\nlayer: world_clear\n"
            "time: { hour: 12, minute: 0 }\nwind: { heading: 0, speed: 0 }\n"
            "sides: [blue]\nobjects:\n" + objs +
            "  - type: fl-base:ural375\n    id: witness\n    side: blue\n    pos: [0, 0, 0]\n"
            "    lat: 36.5\n    lon: -115.5\n    heading: 0\n    start: ground\n"
            "    ai: \"lua terr_witness\"\n"
            "triggers:\n  - on: timer(8)\n    do: mission_success\n")


def run(server, run_root):
    report = run_root.parent / "terr.json"
    report.unlink(missing_ok=True)
    proc = subprocess.run(
        [server, "--assets", str(run_root), "--mission", "terr_probe",
         "--mission-report", str(report), "--no-discovery"],
        capture_output=True, text=True, timeout=300, cwd=run_root)
    if not report.exists():
        raise RuntimeError("no report:\n" + "\n".join(proc.stdout.splitlines()[-6:]))
    alts = {}
    for m in re.finditer(r"TERR lat=([-\d.]+) lon=([-\d.]+) alt=([-\d.]+)", proc.stdout):
        alts[(round(float(m.group(1)), 3), round(float(m.group(2)), 3))] = float(m.group(3))
    return alts


def lookup(alts, lat, lon):
    return alts.get((round(lat, 3), round(lon, 3)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--server", default=shutil.which("fl-server"))
    args = ap.parse_args()
    if not args.server:
        print("fl-server not found on PATH", file=sys.stderr)
        return 2

    failures = []
    with tempfile.TemporaryDirectory(prefix="fl-terr-") as tmp:
        results = {}
        for arm in ("base", "theater"):
            run_root = Path(tmp) / f"flrun_{arm}"
            pack = run_root / "mods" / "fl-base-pack"
            pack.parent.mkdir(parents=True)
            ignore = [".git", "*.glb", "*.ogg"] + (["terrain"] if arm == "base" else [])
            shutil.copytree(PACK_ROOT, pack, ignore=shutil.ignore_patterns(*ignore))
            (pack / "ai" / "terr_witness.lua").write_text(WITNESS)
            (pack / "missions" / "terr_probe.yaml").write_text(mission_yaml())
            results[arm] = run(args.server, run_root)

        print(f"  {'point':<16} {'truth':>7} {'base':>8} {'theater':>8}  band")
        improved = 0
        for name, lat, lon, truth, tol in POINTS:
            base = lookup(results["base"], lat, lon)
            thea = lookup(results["theater"], lat, lon)
            if thea is None or base is None:
                print(f"  {name:<16} MISSING from probe output")
                failures.append(f"{name}: no altitude reported")
                continue
            ok = abs(thea - truth) <= tol
            better = abs(thea - truth) <= abs(base - truth) + 1.0
            improved += abs(thea - truth) + 5.0 < abs(base - truth)
            print(f"  {name:<16} {truth:>7.0f} {base:>8.1f} {thea:>8.1f}  "
                  f"±{tol:.0f} [{'ok' if ok and better else 'FAIL'}]")
            if not ok:
                failures.append(f"{name}: theater height {thea:.1f} outside {truth}±{tol}")
            if not better:
                failures.append(f"{name}: theater tiles made the height WORSE than the base")
        if improved == 0:
            failures.append("no point improved over the base — are the tiles being read at all?")

    print()
    if failures:
        print(f"{len(failures)} problem(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("nttr theater: the engine stands entities on the pack's tiles, at the right heights.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
