"""Deterministic experiment protocol and machine-readable artifact exports."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import time

import numpy as np
import pandas as pd
import scipy

from .data import SystemData, repository_root
from .dispatch import solve_dispatch, empirical_cvar
from .commitment import solve_commitment
from .opf import solve_opf
from .expansion import build_problem, solve_benders, solve_extensive, TECHNOLOGIES

DAYS = ["2020-02-15", "2020-05-15", "2020-08-15", "2020-11-15"]
SEASONS = ["winter", "spring", "summer", "autumn"]


def save_json(path: Path, value) -> None:
    def convert(x):
        if isinstance(x, np.ndarray):
            return x.tolist()
        if isinstance(x, np.generic):
            return x.item()
        raise TypeError(type(x).__name__)

    path.write_text(json.dumps(value, indent=2, default=convert, allow_nan=False) + "\n", encoding="utf-8")


def run(output: Path, *, quick=False) -> dict:
    data = SystemData.load()
    output.mkdir(parents=True, exist_ok=True)
    days = [DAYS[2]] if quick else DAYS
    records, ed_rows, uc_rows, opf_rows, convergence = [], [], [], [], []
    details = {}
    for date in days:
        season = SEASONS[DAYS.index(date)]
        day = data.day(date)
        print(f"[{season}] dispatch / commitment / network", flush=True)
        for method, risk, deterministic in [
            ("deterministic", 0.0, True),
            ("risk-neutral", 0.0, False),
            ("cvar", 40.0, False),
        ]:
            start = time.perf_counter()
            holdout_short = np.zeros(7)
            energy, reserve_cost, violation = 0.0, 0.0, 0.0
            for stamp, row in day.iterrows():
                result = solve_dispatch(
                    data.generators,
                    row.net_da,
                    data.errors(stamp),
                    risk_weight=risk,
                    deterministic=deterministic,
                )
                future = [stamp + pd.Timedelta(days=k) for k in range(1, 8)]
                errors = data.profiles.loc[future, "net_error"].to_numpy()
                q = np.maximum(errors - result.reserve.sum(), 0)
                holdout_short += q
                energy += result.energy_cost
                reserve_cost += result.reserve_cost
                violation = max(violation, result.max_violation)
                ed_rows.append(
                    {
                        "season": season,
                        "date": date,
                        "hour": stamp.hour,
                        "method": method,
                        "net_demand_mw": row.net_da,
                        "reserve_mw": result.reserve.sum(),
                        "reserve_cost_usd": result.reserve_cost,
                        "training_cvar_mw": result.cvar_mw,
                        "holdout_mean_exceedance_mw": q.mean(),
                        "unserved_mw": result.unserved,
                        "spill_mw": result.spill,
                    }
                )
            records.append(
                {
                    "problem": "ED",
                    "season": season,
                    "method": method,
                    "energy_cost_usd": energy,
                    "reserve_cost_usd": reserve_cost,
                    "holdout_mean_daily_exceedance_mwh": holdout_short.mean(),
                    "holdout_daily_cvar90_mwh": empirical_cvar(holdout_short),
                    "holdout_proxy_cost_usd": energy + reserve_cost + 50 * holdout_short.mean(),
                    "runtime_s": time.perf_counter() - start,
                    "max_violation": violation,
                }
            )
        for method in ["fixed-3pct", "calibrated-95pct"]:
            requirement = 0.03 * day.load_da.to_numpy()
            if method == "calibrated-95pct":
                requirement = np.maximum(requirement, data.reserve(day.index))
            start = time.perf_counter()
            result = solve_commitment(data.generators, day.net_da, requirement)
            records.append(
                {
                    "problem": "UC",
                    "season": season,
                    "method": method,
                    "objective_usd": result.objective,
                    "mip_gap": result.mip_gap,
                    "solver_status": result.solver_status,
                    "lower_bound_usd": result.lower_bound,
                    "starts": result.starts.sum(),
                    "unserved_mwh": result.unserved.sum(),
                    "reserve_shortfall_mwh": result.reserve_shortfall.sum(),
                    "realized_reserve_exceedance_mwh": np.maximum(
                        day.net_error.to_numpy() - result.reserve.sum(axis=1), 0
                    ).sum(),
                    "runtime_s": time.perf_counter() - start,
                    "max_violation": result.max_violation,
                }
            )
            for t, stamp in enumerate(day.index):
                uc_rows.append(
                    {
                        "season": season,
                        "date": date,
                        "hour": t,
                        "method": method,
                        "dispatch_mw": result.dispatch[t].sum(),
                        "committed_capacity_mw": result.commitment[t] @ data.generators.pmax,
                        "reserve_mw": result.reserve[t].sum(),
                        "requirement_mw": requirement[t],
                        "spill_mw": result.spill[t],
                        "unserved_mw": result.unserved[t],
                    }
                )
            if season == "summer" and method == "calibrated-95pct":
                details["summer_uc"] = asdict(result)
        stamp = day.net_da.idxmax()
        for factor in [1.0, 0.65]:
            pair = []
            for screening in [False, True]:
                start = time.perf_counter()
                result = solve_opf(data, stamp, screening=screening, rating_factor=factor)
                pair.append(result.objective)
                method = "constraint-generation" if screening else "full-limits"
                records.append(
                    {
                        "problem": "DC-OPF",
                        "season": season,
                        "method": method,
                        "timestamp": stamp.isoformat(),
                        "rating_factor": factor,
                        "objective_usd": result.objective,
                        "iterations": len(result.iterations),
                        "active_line_limits": len(result.active_lines),
                        "unserved_mw": result.unserved.sum(),
                        "runtime_s": time.perf_counter() - start,
                        "max_violation": result.max_violation,
                    }
                )
                if screening:
                    for row in result.iterations:
                        convergence.append(
                            {"problem": "DC-OPF", "season": season, "rating_factor": factor, **row}
                        )
                    for i, branch in data.branches.iterrows():
                        opf_rows.append(
                            {
                                "season": season,
                                "rating_factor": factor,
                                "line": branch.UID,
                                "flow_mw": result.flows[i],
                                "rating_mw": factor * branch["Cont Rating"],
                            }
                        )
                    if season == "summer" and factor == 0.65:
                        details["summer_opf"] = asdict(result)
            if not np.isclose(*pair, rtol=1e-8, atol=1e-3):
                raise AssertionError("Screened and full OPF objectives disagree")
    print("[planning] Benders / extensive LP / carbon sensitivity", flush=True)
    for carbon in [75] if quick else [0, 75, 150]:
        problem = build_problem(data, carbon_price=carbon)
        objective_pair = []
        for method, solver in [("extensive", solve_extensive), ("benders", solve_benders)]:
            start = time.perf_counter()
            result = solver(problem)
            objective_pair.append(result.objective)
            records.append(
                {
                    "problem": "Expansion",
                    "method": method,
                    "carbon_usd_t": carbon,
                    "objective_usd_year": result.objective,
                    "investment_usd_year": result.investment,
                    "operation_usd_year": result.operating,
                    "unserved_mwh_year": result.unserved_mwh,
                    **{f"{k}_build_mw": result.build[j] for j, k in enumerate(TECHNOLOGIES)},
                    "iterations": len(result.history),
                    "runtime_s": time.perf_counter() - start,
                    "max_violation": result.max_violation,
                }
            )
            if method == "benders":
                for row in result.history:
                    convergence.append({"problem": "Expansion", "carbon_usd_t": carbon, **row})
        if not np.isclose(*objective_pair, rtol=2e-7, atol=1):
            raise AssertionError("Benders and extensive planning objectives disagree")
    frames = {
        "metrics": records,
        "dispatch_hourly": ed_rows,
        "commitment_hourly": uc_rows,
        "network_flows": opf_rows,
        "convergence": convergence,
    }
    for name, rows in frames.items():
        pd.DataFrame(rows).to_csv(output / f"{name}.csv", index=False, float_format="%.9f")
    save_json(output / "details.json", details)
    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "pandas": pd.__version__,
        "solver": "HiGHS via scipy.optimize",
        "quick": quick,
        "seed": "No random sampling; deterministic chronological protocol",
        "training": "Previous 30 days, same hour, strictly before target day",
        "ed_holdout": "Seven days after each operational date; fixed hyperparameters",
        "alpha": 0.9,
        "risk_weight_usd_mwh": 40,
        "shortfall_proxy_usd_mwh": 50,
        "uc_mip_relative_gap_target": 1e-3,
        "uc_time_limit_seconds": 45,
        "uc_incumbent_policy": "Accept a validated feasible time-limit incumbent and report its actual gap",
        "benders_relative_gap_target": 1e-7,
        "source_commit": json.loads((repository_root() / "data/source_manifest.json").read_text())["commit"],
        "input_sha256": {
            str(p.relative_to(repository_root())): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((repository_root() / "data/processed").glob("*.csv"))
        },
        "planning_config_sha256": hashlib.sha256(
            (repository_root() / "data/planning_assumptions.json").read_bytes()
        ).hexdigest(),
    }
    save_json(output / "metadata.json", metadata)
    return {"metadata": metadata, "metrics": records}
