# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: MIT
"""Make `fl_meshlib` importable when the tests are run without installing the package."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
