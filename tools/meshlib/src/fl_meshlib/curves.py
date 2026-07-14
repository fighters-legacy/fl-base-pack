# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: MIT
"""Scalar interpolation helpers. Pure Python; no Blender."""


def smoothstep(u: float) -> float:
    """Hermite smoothstep, clamped to [0, 1]."""
    u = min(max(u, 0.0), 1.0)
    return u * u * (3.0 - 2.0 * u)


def lerp(a: float, b: float, u: float) -> float:
    """Smoothstep-eased interpolation from a to b."""
    return a + (b - a) * smoothstep(u)
