"""Create a compact offline benchmark from the immutable upstream CSVs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DAYS = ["2020-02-15", "2020-05-15", "2020-08-15", "2020-11-15"]


def hourly(path: Path, realtime: bool = False) -> pd.DataFrame:
    df = pd.read_csv(path)
    dates = pd.to_datetime(df[["Year", "Month", "Day"]].rename(columns=str.lower))
    hour = (df.Period - 1) // (12 if realtime else 1)
    df.index = pd.DatetimeIndex(dates + pd.to_timedelta(hour, unit="h"), name="timestamp")
    return df.drop(columns=["Year", "Month", "Day", "Period"]).groupby(level=0).mean()


def main() -> None:
    raw, target = ROOT / "data/raw", ROOT / "data/processed"
    source_manifest = json.loads((ROOT / "data/source_manifest.json").read_text(encoding="utf-8"))
    for name, record in source_manifest["files"].items():
        if hashlib.sha256((raw / name).read_bytes()).hexdigest() != record["sha256"]:
            raise ValueError(f"Raw source checksum mismatch: {name}")
    target.mkdir(parents=True, exist_ok=True)
    buses = pd.read_csv(raw / "bus.csv")
    branches = pd.read_csv(raw / "branch.csv")
    source = pd.read_csv(raw / "gen.csv")
    # A transparent one-block linearization; upstream heat rates are Btu/kWh.
    thermal = source[source.Fuel.isin(["Oil", "Coal", "NG", "Nuclear"])].copy()
    heat_rate = thermal["HR_incr_1"].where(thermal["HR_incr_1"] > 0, thermal["HR_avg_0"])
    thermal["cost_per_mwh"] = heat_rate / 1000 * thermal["Fuel Price $/MMBTU"] + thermal.VOM
    thermal["no_load_per_h"] = np.maximum(
        0,
        thermal["PMin MW"]
        * (thermal["HR_avg_0"] / 1000 * thermal["Fuel Price $/MMBTU"] + thermal.VOM - thermal.cost_per_mwh),
    )
    thermal["startup_cost"] = (
        thermal["Start Heat Hot MBTU"] * thermal["Fuel Price $/MMBTU"] + thermal["Non Fuel Start Cost $"]
    )
    names = {
        "GEN UID": "id",
        "Bus ID": "bus",
        "PMax MW": "pmax",
        "PMin MW": "pmin",
        "Ramp Rate MW/Min": "ramp_mw_min",
        "Min Up Time Hr": "min_up",
        "Min Down Time Hr": "min_down",
        "Fuel": "fuel",
    }
    generators = thermal.rename(columns=names)[
        [*names.values(), "cost_per_mwh", "no_load_per_h", "startup_cost"]
    ]
    assert generators.notna().all().all(), "Unexpected missing thermal parameters"
    generators.to_csv(target / "generators.csv", index=False, float_format="%.8f")
    buses.to_csv(target / "buses.csv", index=False)
    branches.to_csv(target / "branches.csv", index=False)
    series = {}
    for kind in ["load", "wind", "pv", "rtpv"]:
        for mode in ["DAY_AHEAD", "REAL_TIME"]:
            series[kind, mode] = hourly(raw / f"{kind}_{mode}.csv", mode == "REAL_TIME")
    hydro = hourly(raw / "hydro_DAY_AHEAD.csv")
    profiles = pd.DataFrame(index=series["load", "DAY_AHEAD"].index)
    for (kind, mode), frame in series.items():
        assert frame.index.equals(profiles.index), f"Misaligned {kind}/{mode}"
        profiles[f"{kind}_{'da' if mode == 'DAY_AHEAD' else 'rt'}"] = frame.sum(axis=1)
    profiles["hydro"] = hydro.sum(axis=1)
    for mode in ["da", "rt"]:
        profiles[f"net_{mode}"] = (
            profiles[f"load_{mode}"]
            - profiles[[f"{k}_{mode}" for k in ["wind", "pv", "rtpv"]]].sum(axis=1)
            - profiles.hydro
        )
    profiles["net_error"] = profiles.net_rt - profiles.net_da
    profiles.to_csv(target / "profiles.csv", float_format="%.6f")
    # Only the four operational days need nodal data. Training errors retain the full year.
    selected = profiles.index.strftime("%Y-%m-%d").isin(DAYS)
    rows = []
    source_bus = source.set_index("GEN UID")["Bus ID"].to_dict()
    for stamp in profiles.index[selected]:
        regional = series["load", "DAY_AHEAD"].loc[stamp]
        for _, bus in buses.iterrows():
            area = int(bus.Area)
            weight = bus["MW Load"] / buses.loc[buses.Area == area, "MW Load"].sum()
            renewable = {
                kind: sum(
                    float(frame.loc[stamp, uid])
                    for uid in frame.columns
                    if source_bus.get(uid) == bus["Bus ID"]
                )
                for kind, frame in [(k, series[k, "DAY_AHEAD"]) for k in ["wind", "pv", "rtpv"]]
                + [("hydro", hydro)]
            }
            rows.append(
                {
                    "timestamp": stamp,
                    "bus": int(bus["Bus ID"]),
                    "load": regional[str(area)] * weight,
                    **renewable,
                }
            )
    pd.DataFrame(rows).to_csv(target / "nodal.csv", index=False, float_format="%.6f")
    notice = (
        (raw / "upstream_README.md").read_text(encoding="utf-8").split("## DATA USE DISCLAIMER AGREEMENT")[1]
    )
    (ROOT / "data/LICENSE-RTS-GMLC.md").write_text(
        "# DATA USE DISCLAIMER AGREEMENT\n" + notice.rstrip() + "\n", encoding="utf-8"
    )
    manifest = {
        "selected_days": DAYS,
        "hourly_rows": len(profiles),
        "thermal_generators": len(generators),
        "pv_nameplate_mw": float(source.loc[source["Unit Type"] == "PV", "PMax MW"].sum()),
        "wind_nameplate_mw": float(source.loc[source["Unit Type"] == "WIND", "PMax MW"].sum()),
        "buses": len(buses),
        "ac_branches": len(branches),
        "base_mva": 100,
        "excluded_assets": [
            "CSP (thermal storage model omitted)",
            "battery storage",
            "synchronous condensers",
        ],
        "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(target.glob("*.csv"))},
    }
    (ROOT / "data/processed_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in manifest.items() if k != "files"}, indent=2))


if __name__ == "__main__":
    main()
