# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: MIT
"""Pure-math tests for the airfoil module. No Blender required."""

import math

from fl_meshlib.airfoil import naca_symmetric


def test_zero_thickness_at_endpoints():
    # A NACA thickness distribution is zero at the leading edge and (very nearly) at the trailing.
    assert naca_symmetric(0.0, 0.12) == 0.0
    assert abs(naca_symmetric(1.0, 0.12)) < 0.012  # small non-zero TE thickness by the polynomial


def test_max_near_thirty_percent_chord():
    # The classic 4-digit section peaks around x/c ~ 0.30.
    xs = [i / 100 for i in range(1, 100)]
    peak = max(xs, key=lambda x: naca_symmetric(x, 0.10))
    assert 0.25 <= peak <= 0.35


def test_scales_linearly_with_thickness():
    x = 0.3
    assert math.isclose(naca_symmetric(x, 0.20), 2.0 * naca_symmetric(x, 0.10), rel_tol=1e-12)


def test_clamps_out_of_range():
    assert naca_symmetric(-1.0, 0.1) == naca_symmetric(0.0, 0.1)
    assert naca_symmetric(2.0, 0.1) == naca_symmetric(1.0, 0.1)
