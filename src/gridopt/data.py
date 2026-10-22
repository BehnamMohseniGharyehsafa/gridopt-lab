"""Validated, offline RTS-GMLC data access and chronological error calibration."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass
class SystemData:
    generators: pd.DataFrame
    buses: pd.DataFrame
    branches: pd.DataFrame
    profiles: pd.DataFrame
    nodal: pd.DataFrame

    @classmethod
    def load(cls, root: Path | None = None) -> "SystemData":
        root = root or repository_root()
        folder = root / "data/processed"
        manifest = json.loads((root / "data/processed_manifest.json").read_text())
        for name, expected in manifest["files"].items():
            if hashlib.sha256((folder / name).read_bytes()).hexdigest() != expected:
                raise ValueError(f"Data checksum mismatch: {name}")
        data = cls(
            pd.read_csv(folder / "generators.csv"),
            pd.read_csv(folder / "buses.csv"),
            pd.read_csv(folder / "branches.csv"),
            pd.read_csv(folder / "profiles.csv", index_col=0, parse_dates=True),
            pd.read_csv(folder / "nodal.csv", parse_dates=["timestamp"]),
        )
        if not data.profiles.index.is_unique or data.profiles.isna().any().any():
            raise ValueError("Profiles must be complete and uniquely indexed")
        return data

    def day(self, date: str) -> pd.DataFrame:
        frame = self.profiles.loc[date]
        if len(frame) != 24:
            raise ValueError("A complete 24-hour day is required")
        return frame

    def errors(self, stamp: pd.Timestamp, days: int = 30) -> np.ndarray:
        """Same-hour errors strictly before the target day; no target-day leakage."""
        end = stamp.normalize()
        frame = self.profiles.loc[
            (self.profiles.index >= end - pd.Timedelta(days=days)) & (self.profiles.index < end)
        ]
        errors = frame.loc[frame.index.hour == stamp.hour, "net_error"].to_numpy()
        if len(errors) < 7:
            raise ValueError("At least seven preceding same-hour observations are required")
        return errors

    def reserve(self, stamps: pd.DatetimeIndex, quantile: float = 0.95) -> np.ndarray:
        if not 0 < quantile < 1:
            raise ValueError("quantile must lie strictly between zero and one")
        return np.array([max(0.0, np.quantile(self.errors(t), quantile)) for t in stamps])
