"""Small I/O helpers for project datasets."""

import json
from pathlib import Path
from typing import Any

import pandas as pd


def ensure_parent(path: Path) -> None:
    """Create the parent directory for a file path if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> pd.DataFrame:
    """Load a CSV file into a DataFrame."""
    return pd.read_csv(path)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    """Write a DataFrame to CSV, creating parent directories when needed."""
    ensure_parent(path)
    df.to_csv(path, index=False)


def read_json(path: Path) -> Any:
    """Load JSON from disk."""
    return json.loads(path.read_text())


def write_json(payload: Any, path: Path) -> None:
    """Write JSON to disk."""
    ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2))
