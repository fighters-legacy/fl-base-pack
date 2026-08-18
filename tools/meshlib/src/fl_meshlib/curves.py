# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: MIT
"""Scalar interpolation and planar-section helpers. Pure Python; no Blender."""

import math


def smoothstep(u: float) -> float:
    """Hermite smoothstep, clamped to [0, 1]."""
    u = min(max(u, 0.0), 1.0)
    return u * u * (3.0 - 2.0 * u)


def lerp(a: float, b: float, u: float) -> float:
    """Smoothstep-eased interpolation from a to b."""
    return a + (b - a) * smoothstep(u)


def circle_points(radius: float, segments: int, phase: float = 0.0):
    """`segments` points on a circle of `radius`, counter-clockwise from `phase` radians.

    Pure math so it is unit-testable without Blender, and deterministic: the point order is a
    plain range, never a set or dict iteration. `prims.cylinder` builds its rings from this.
    """
    if segments < 3:
        raise ValueError("a circle needs at least 3 segments")
    out = []
    for i in range(segments):
        a = phase + 2.0 * math.pi * i / segments
        out.append((radius * math.cos(a), radius * math.sin(a)))
    return out
