# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: MIT
"""Airfoil section maths. Pure Python; no Blender."""

import math


def naca_symmetric(x: float, t: float) -> float:
    """Half-thickness of a symmetric NACA section at chord fraction x, thickness ratio t.

    The standard NACA thickness distribution. A symmetric N-series section (e.g. NASA's 65A004.8
    for the F-5E) is reproduced closely enough for a game mesh; the 6-series' exact camber-line
    mathematics buy nothing a player can see.
    """
    x = min(max(x, 0.0), 1.0)
    return 5.0 * t * (0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * x * x
                      + 0.2843 * x ** 3 - 0.1015 * x ** 4)
