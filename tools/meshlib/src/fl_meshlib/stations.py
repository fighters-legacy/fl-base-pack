# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: MIT
"""Station-table interpolation. Pure Python; no Blender.

A "station table" is a list of rows keyed by a monotonic parameter (a fuselage x/L, a span
fraction). This is the generic linear-interpolation kernel; aircraft-specific blend logic (canopy
spans, radome body-of-revolution constraints) stays in the per-aircraft build script.
"""


def interp_table(table, t, key=0, cols=None):
    """Linearly interpolate `table` at parameter `t`.

    Each row is a tuple whose element `key` is the monotonic parameter. Returns a tuple of the
    interpolated values for the columns in `cols` (default: every column except the key). `t` is
    clamped to the table's range; a table with fewer than two rows returns its lone row's columns.
    """
    if cols is None:
        ncol = len(table[0])
        cols = tuple(c for c in range(ncol) if c != key)
    t = min(max(t, table[0][key]), table[-1][key])
    for i in range(len(table) - 1):
        a, b = table[i], table[i + 1]
        if a[key] <= t <= b[key]:
            span = b[key] - a[key]
            u = (t - a[key]) / span if span > 0 else 0.0
            return tuple(a[c] + (b[c] - a[c]) * u for c in cols)
    return tuple(table[-1][c] for c in cols)
