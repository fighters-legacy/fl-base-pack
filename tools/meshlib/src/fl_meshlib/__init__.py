# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: MIT
"""fl_meshlib — shared procedural-aircraft mesh helpers.

Deliberately does NOT import its submodules here. The pure-math modules (``airfoil``, ``curves``,
``stations``, ``check``) import with no dependencies and are unit-testable without Blender; the
Blender-facing modules (``loft``, ``scene``, ``uvatlas``, ``damage``, ``export``) import ``bpy`` /
``bmesh`` / ``mathutils`` and only load inside Blender. Import what you need explicitly, e.g.
``from fl_meshlib import airfoil`` or ``from fl_meshlib import loft``.

Determinism is a contract of this library (fl-base-pack regenerates aircraft byte-for-byte as a
regression check): pass seeds explicitly, never read the wall clock, and keep export options fixed.
"""

__version__ = "0.1.0"
