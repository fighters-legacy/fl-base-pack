# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: MIT
"""Pure-math tests for the curves module. No Blender required."""

import math

from fl_meshlib.curves import lerp, smoothstep


def test_smoothstep_endpoints_and_midpoint():
    assert smoothstep(0.0) == 0.0
    assert smoothstep(1.0) == 1.0
    assert math.isclose(smoothstep(0.5), 0.5)


def test_smoothstep_clamps():
    assert smoothstep(-3.0) == 0.0
    assert smoothstep(3.0) == 1.0


def test_smoothstep_is_flat_at_ends():
    # Zero first derivative at both ends is what makes it "smooth"; approximate numerically.
    eps = 1e-6
    assert smoothstep(eps) < eps          # slope ~0 near 0
    assert (1.0 - smoothstep(1.0 - eps)) < eps


def test_lerp_uses_eased_parameter():
    assert lerp(10.0, 20.0, 0.0) == 10.0
    assert lerp(10.0, 20.0, 1.0) == 20.0
    assert math.isclose(lerp(10.0, 20.0, 0.5), 15.0)
