"""Safe test defaults: tests never make a live provider call."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_database = Path(tempfile.gettempdir()) / "reverse-business-failure-test.db"
try:
    _database.unlink()
except FileNotFoundError:
    pass

os.environ["DEMO_MODE"] = "replay"
os.environ["DATABASE_URL"] = f"sqlite:///{_database.as_posix()}"
os.environ["FIXTURES_DIR"] = str(Path(__file__).resolve().parents[2] / "fixtures")
