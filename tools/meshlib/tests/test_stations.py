# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: MIT
"""Pure-math tests for the station-table interpolator. No Blender required."""

import math

from fl_meshlib.stations import interp_table

# (key, a, b) rows
TABLE = [
    (0.0, 10.0, 100.0),
    (0.5, 20.0, 200.0),
    (1.0, 30.0, 300.0),
]


def test_exact_rows():
    assert interp_table(TABLE, 0.0) == (10.0, 100.0)
    assert interp_table(TABLE, 0.5) == (20.0, 200.0)
    assert interp_table(TABLE, 1.0) == (30.0, 300.0)


def test_midpoint_interpolation():
    a, b = interp_table(TABLE, 0.25)
    assert math.isclose(a, 15.0)
    assert math.isclose(b, 150.0)


def test_clamps_to_table_range():
    assert interp_table(TABLE, -5.0) == (10.0, 100.0)
    assert interp_table(TABLE, 5.0) == (30.0, 300.0)


def test_explicit_columns():
    # Select only the second value column.
    assert interp_table(TABLE, 0.5, cols=(2,)) == (200.0,)


def test_matches_legacy_fus_at_formula():
    # The old _fus_at clamped to [0,1] and interpolated columns (1,2,3) of a 4-wide row. Reproduce
    # that exact arithmetic to guard the byte-identical F-5E build.
    rows = [
        (0.00, 0.015, -0.015, 0.038),
        (0.03, 0.008, -0.307, 0.060),
        (0.06, -0.008, -0.369, 0.161),
    ]

    def legacy(t):
        t = min(max(t, 0.0), 1.0)
        for i in range(len(rows) - 1):
            a, b = rows[i], rows[i + 1]
            if a[0] <= t <= b[0]:
                u = (t - a[0]) / (b[0] - a[0]) if b[0] > a[0] else 0.0
                return tuple(a[k] + (b[k] - a[k]) * u for k in (1, 2, 3))
        return rows[-1][1:]

    for t in (0.0, 0.015, 0.03, 0.045, 0.06):
        assert interp_table(rows, t) == legacy(t)
