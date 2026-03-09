"""
Data loader – read / write data tables from the synthetic data layer.

All persistence goes through this module so the rest of the code is
agnostic to file format.
"""

import pandas as pd
from pathlib import Path
from src.config import DATA_SYNTHETIC, DATA_RAW, DATA_PROCESSED


def _csv_path(folder: Path, name: str) -> Path:
    return folder / f"{name}.csv"


# ── Writers ──────────────────────────────────────────────────────
def save_synthetic(df: pd.DataFrame, name: str) -> Path:
    path = _csv_path(DATA_SYNTHETIC, name)
    df.to_csv(path, index=False)
    return path


def save_processed(df: pd.DataFrame, name: str) -> Path:
    path = _csv_path(DATA_PROCESSED, name)
    df.to_csv(path, index=False)
    return path


# ── Readers ──────────────────────────────────────────────────────
def load_synthetic(name: str) -> pd.DataFrame:
    return pd.read_csv(_csv_path(DATA_SYNTHETIC, name), parse_dates=["date"]
                       if "date" in pd.read_csv(_csv_path(DATA_SYNTHETIC, name), nrows=0).columns
                       else [])


def load_processed(name: str) -> pd.DataFrame:
    return pd.read_csv(_csv_path(DATA_PROCESSED, name), parse_dates=["date"]
                       if "date" in pd.read_csv(_csv_path(DATA_PROCESSED, name), nrows=0).columns
                       else [])


def load_raw(name: str) -> pd.DataFrame:
    return pd.read_csv(_csv_path(DATA_RAW, name))


def table_exists(name: str, layer: str = "synthetic") -> bool:
    folder = {"synthetic": DATA_SYNTHETIC,
              "processed": DATA_PROCESSED,
              "raw": DATA_RAW}[layer]
    return _csv_path(folder, name).exists()
