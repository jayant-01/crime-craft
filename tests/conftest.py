"""Pytest sees this file first and uses it to set up sys.path so tests can
import the top-level modules (`services`, `models`, `auth`, ...) without an
installed package."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
