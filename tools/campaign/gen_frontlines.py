#!/usr/bin/env python3
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: MIT
"""Regenerate the campaign frontline rasters (fl-base-pack#14).

    python3 tools/campaign/gen_frontlines.py        # writes frontlines/*.png, deterministic

The frontline contract (engine docs/modding/formats.md "Frontline Raster"): 8-bit grayscale PNG,
no alpha, dimensions exactly the campaign's `frontline_grid`, pixel (0,0) = the theater bounds'
NORTH-WEST corner. Values: 0 unclaimed, 1-127 side A (blue) by strength, 128-254 side B (red),
255 contested.

The NTTR theater grid is 36 x 39 over bounds (35.0..38.5 N, -117.5..-113.5 E) — about 10 km per
pixel, the band the format doc recommends. The war is painted as full-width east-west lines
because that is what the seed needs: red holds the north (the ranges), blue holds the south
(the home field), and each raster moves the boundary a few rows north as the campaign's story
beats land. Row r covers latitude 38.5 - (r + 0.5) * 3.5 / 39.

Pure stdlib on purpose (struct + zlib): these three small rasters should not cost the repo a
Pillow dependency, and a deterministic byte-identical output is what makes the committed PNGs
reviewable — rerun the script, `git diff` must be empty.
"""
import struct
import sys
import zlib
from pathlib import Path

COLS, ROWS = 36, 39
BLUE, RED, CONTESTED = 100, 200, 255

# (filename, first blue row). Rows above the line are red, with a two-row contested band at its
# southern edge. The line moves NORTH as the story advances — blue is winning the seed war.
RASTERS = [
    ("nttr_start.png", 16),      # line ~37.2 N: red holds the ranges, blue the basin
    ("nttr_after_s01.png", 13),  # s01 (the opening SEAD strike) buys ~27 km
    ("nttr_after_s02.png", 10),  # s02 (the line holds) buys the next ridge line
]


def write_png_gray8(path: Path, cols: int, rows: int, pixels: bytes) -> None:
    assert len(pixels) == cols * rows
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    ihdr = struct.pack(">IIBBBBB", cols, rows, 8, 0, 0, 0, 0)  # 8-bit, color type 0 = grayscale
    raw = b"".join(b"\x00" + pixels[r * cols:(r + 1) * cols] for r in range(rows))
    idat = zlib.compress(raw, 9)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat)
                     + chunk(b"IEND", b""))


def paint(first_blue_row: int) -> bytes:
    px = bytearray()
    for r in range(ROWS):
        if r >= first_blue_row:
            v = BLUE
        elif r >= first_blue_row - 2:
            v = CONTESTED
        else:
            v = RED
        px.extend([v] * COLS)
    return bytes(px)


def main() -> int:
    out_dir = Path(__file__).resolve().parents[2] / "frontlines"
    out_dir.mkdir(exist_ok=True)
    for name, first_blue in RASTERS:
        write_png_gray8(out_dir / name, COLS, ROWS, paint(first_blue))
        print(f"wrote {name} (blue from row {first_blue})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
