#!/usr/bin/env bash
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: MIT
#
# Build the NTTR theater terrain tiles (fl-base-pack#2) — the runbook as a script, because this
# runs rarely enough that nobody will remember the traps.
#
#   tools/terrain/build_nttr_theater.sh <src-dir> <engine-repo>
#
# <src-dir> holds the downloaded inputs (kept OUT of the repo — they are gigabytes and other
# people's data):
#   <src-dir>/glo30/Copernicus_DSM_COG_10_N{35..38}_00_W{114..118}_00_DEM.tif   (20 tiles)
#     from https://copernicus-dem-30m.s3.amazonaws.com/<name>/<name>.tif
#   <src-dir>/worldcover/ESA_WorldCover_10m_2021_v200_{N33,N36}{W120,W117,W114}_Map.tif (6 tiles)
#     from https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/<name>.tif
#
# WHAT IT BUILDS: terrain/world/ height + land-cover tiles, LEVELS 6-10, over the theater bounds
# shared with theaters/nttr.toml — 35.0..38.5 N, -117.5..-113.5 E. Levels 0-5 are the engine's
# bundled base (builtin:base-terrain); the pack's tiles override it inside the box at mod
# priority. L10 is ~76 m/px, comfortably inside GLO-30's 30 m and a repo-sized output; deeper
# levels are a hosting decision nobody has needed yet.
#
# ⚠ THE #1217 TRAP: gen_terrain_tiles.py reads an input window per tile, and a LOW-level tile
# over a HIGH-resolution source reads a huge one (a level-0 tile over 15-arc-sec GEBCO was
# 14.9 GB x cpu_count workers — it took the build box down). At levels 6-10 over these sources
# the windows are hundreds of MB, not GB, but the bound stays: run under systemd-run with a
# MemoryMax and few workers, and never "fix" a slow build by raising --workers first.
#
# ⚠ LAND COVER IS CATEGORICAL: the WorldCover mosaic is downsampled with -r mode (majority
# class), never bilinear/average — averaging class 10 (trees) with class 80 (water) yields
# class 45, which is nothing.
set -euo pipefail

SRC=${1:?usage: build_nttr_theater.sh <src-dir> <engine-repo>}
ENGINE=${2:?usage: build_nttr_theater.sh <src-dir> <engine-repo>}
PACK_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
BBOX=(35.0 -117.5 38.5 -113.5)
WORK=$(mktemp -d /tmp/nttr-theater.XXXXXX)
trap 'rm -rf "$WORK"' EXIT

echo "── mosaics"
gdalbuildvrt -q "$WORK/glo30.vrt" "$SRC"/glo30/*.tif
# Crop the DEM to the box with a margin (tile lattices sample slightly past the bbox edge).
gdal_translate -q -projwin -117.6 38.6 -113.4 34.9 \
    -co COMPRESS=DEFLATE -co PREDICTOR=2 -co TILED=YES \
    "$WORK/glo30.vrt" "$WORK/dem_nttr.tif"
gdalbuildvrt -q "$WORK/wc.vrt" "$SRC"/worldcover/*.tif
# WorldCover 10 m -> ~75 m, majority class, cropped the same way. 10 m source windows at level 6
# are exactly the #1217 shape; the downsample removes the hazard and L10 cannot use the extra
# resolution anyway.
gdalwarp -q -r mode -tr 0.000833 0.000833 -te -117.6 34.9 -113.4 38.6 \
    -co COMPRESS=DEFLATE -co TILED=YES \
    "$WORK/wc.vrt" "$WORK/lc_nttr.tif"

echo "── tiles (levels 6-10, bounded)"
systemd-run --user --scope -p MemoryMax=20G -p MemorySwapMax=0 -- \
    python3 "$ENGINE/tools/gen_terrain_tiles.py" \
    --input "$WORK/dem_nttr.tif" \
    --landcover-source "$WORK/lc_nttr.tif" \
    --terrain-id world \
    --output-dir "$PACK_ROOT" \
    --bbox "${BBOX[@]}" \
    --min-level 6 --max-level 10 \
    --workers 4 --skip-existing

echo "── result"
H=$(find "$PACK_ROOT/terrain/world" -name 'tile_*.png' ! -name '*_lc.png' | wc -l)
L=$(find "$PACK_ROOT/terrain/world" -name '*_lc.png' | wc -l)
echo "height tiles: $H   land-cover tiles: $L   ($(du -sh "$PACK_ROOT/terrain/world" | cut -f1))"
[ "$H" -gt 0 ] && [ "$H" -eq "$L" ] || { echo "ERROR: height/landcover tile counts differ"; exit 1; }
echo "Rerun tools/terrain/verify_nttr_theater.py against a server build before shipping."
