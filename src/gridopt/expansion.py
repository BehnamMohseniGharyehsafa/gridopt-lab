"""Continuous generation expansion with multicut Benders and an extensive-form oracle."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import numpy as np

from .data import SystemData, repository_root
from .linear import LinearModel

TECHNOLOGIES = ["solar", "wind", "gas"]


@dataclass
class Scenario:
    name: str
    demand: np.ndarray
    capacity_factors: np.ndarray
    weight: float


@dataclass
class PlanningProblem:
    existing_capacity: np.ndarray
    existing_cost: np.ndarray
    investment_cost: np.ndarray
    new_variable_cost: np.ndarray
    maximum_build: np.ndarray
    scenarios: list[Scenario]
    unserved_cost: float = 10_000.0


@dataclass
class PlanningResult:
    objective: float
    build: np.ndarray
    investment: float
    operating: float
    unserved_mwh: float
    history: list[dict]
    max_violation: float


def build_problem(data: SystemData, config_path: Path | None = None, *, carbon_price=None) -> PlanningProblem:
    cfg = json.loads((config_path or repository_root() / "data/planning_assumptions.json").read_text())
    rate, years = cfg["discount_rate"], cfg["lifetime_years"]
    crf = rate * (1 + rate) ** years / ((1 + rate) ** years - 1) if rate else 1 / years
    investment = np.array(
        [
            1000 * (cfg["overnight_usd_per_kw"][k] * crf + cfg["fixed_om_usd_per_kw_year"][k])
            for k in TECHNOLOGIES
        ]
    )
    carbon = cfg["carbon_usd_per_tonne"] if carbon_price is None else carbon_price
    existing_cost = (
        data.generators.cost_per_mwh.to_numpy()
        + carbon * data.generators.fuel.map(cfg["co2_tonnes_per_mwh"]).to_numpy()
    )
    # Nameplate totals from the pinned original generator inventory.
    meta = json.loads((repository_root() / "data/processed_manifest.json").read_text())
    solar_capacity = meta["pv_nameplate_mw"]
    wind_capacity = meta["wind_nameplate_mw"]
    scenarios = []
    for date in cfg["representative_days"]:
        day = data.day(date)
        cf = np.column_stack(
            [
                np.clip(day.pv_da.to_numpy() / solar_capacity, 0, 1),
                np.clip(day.wind_da.to_numpy() / wind_capacity, 0, 1),
                np.ones(24),
            ]
        )
        existing_renewable = day[["wind_da", "pv_da", "rtpv_da", "hydro"]].sum(axis=1).to_numpy()
        for growth, prob in zip(cfg["load_multipliers"], cfg["probabilities"]):
            scenarios.append(
                Scenario(
                    f"{date}/load-{growth:g}",
                    growth * day.load_da.to_numpy() - existing_renewable,
                    cf,
                    prob * cfg["days_per_representative_day"],
                )
            )
    if not np.isclose(sum(s.weight * len(s.demand) for s in scenarios), 8760):
        raise ValueError("Scenario weights must represent 8,760 expected hours")
    return PlanningProblem(
        data.generators.pmax.to_numpy() * cfg["existing_capacity_fraction"],
        existing_cost,
        investment,
        np.array([0.0, 0.0, cfg["new_gas_variable_usd_per_mwh"] + carbon * cfg["co2_tonnes_per_mwh"]["NG"]]),
        np.array(cfg["candidate_max_mw"]),
        scenarios,
        cfg["unserved_usd_per_mwh"],
    )


def _operating_block(
    m: LinearModel,
    problem: PlanningProblem,
    scenario: Scenario,
    *,
    fixed_build=None,
    build_indices=None,
    objective_weight=1.0,
):
    hours = len(scenario.demand)
    p = m.variables(
        (hours, len(problem.existing_capacity)),
        cost=objective_weight * problem.existing_cost,
        upper=problem.existing_capacity,
    )
    new = m.variables((hours, 3), cost=objective_weight * problem.new_variable_cost)
    shed = m.variables(
        hours, cost=objective_weight * problem.unserved_cost, upper=np.maximum(scenario.demand, 0)
    )
    spill = m.variables(hours)
    capacity_rows = np.empty((hours, 3), dtype=int)
    for h in range(hours):
        m.constraint(
            [(p[h], 1), (new[h], 1), (shed[h], 1), (spill[h], -1)],
            lower=scenario.demand[h],
            upper=scenario.demand[h],
        )
        for k in range(3):
            if fixed_build is None:
                capacity_rows[h, k] = m.constraint(
                    [(new[h, k], 1), (build_indices[k], -scenario.capacity_factors[h, k])], upper=0
                )
            else:
                capacity_rows[h, k] = m.constraint(
                    [(new[h, k], 1)], upper=scenario.capacity_factors[h, k] * fixed_build[k]
                )
    return capacity_rows, shed


def recourse(problem: PlanningProblem, scenario: Scenario, build):
    """Return daily value and a globally valid capacity subgradient from LP duals."""
    m = LinearModel()
    rows, shed = _operating_block(m, problem, scenario, fixed_build=build)
    result = m.solve()
    dual_by_row = dict(zip(result.upper_rows, result.ineqlin.marginals[: len(result.upper_rows)]))
    dual = np.array([[dual_by_row[row] for row in hour] for hour in rows])
    gradient = (dual * scenario.capacity_factors).sum(axis=0)
    return float(result.fun), gradient, float(result.x[shed].sum()), result.max_violation


def solve_extensive(problem: PlanningProblem) -> PlanningResult:
    m = LinearModel()
    build = m.variables(3, cost=problem.investment_cost, upper=problem.maximum_build)
    shed_blocks = []
    for scenario in problem.scenarios:
        _, shed = _operating_block(
            m, problem, scenario, build_indices=build, objective_weight=scenario.weight
        )
        shed_blocks.append((scenario.weight, shed))
    result = m.solve()
    investment = float(problem.investment_cost @ result.x[build])
    return PlanningResult(
        float(result.fun),
        result.x[build],
        investment,
        float(result.fun - investment),
        sum(w * float(result.x[shed].sum()) for w, shed in shed_blocks),
        [],
        result.max_violation,
    )


def solve_benders(problem: PlanningProblem, *, tolerance=1e-7, max_iterations=150) -> PlanningResult:
    """Exact LP recourse; complete recourse comes from explicit unserved-energy variables."""
    if tolerance <= 0 or max_iterations < 1:
        raise ValueError("Positive tolerance and iteration limit required")
    m = LinearModel()
    build = m.variables(3, cost=problem.investment_cost, upper=problem.maximum_build)
    theta = m.variables(len(problem.scenarios), cost=[s.weight for s in problem.scenarios])
    upper, best_build, best_q, best_shed = np.inf, None, None, None
    history, max_violation = [], 0.0
    for iteration in range(1, max_iterations + 1):
        master = m.solve()
        trial = master.x[build]
        lower = float(master.fun)
        values = [recourse(problem, s, trial) for s in problem.scenarios]
        candidate = float(
            problem.investment_cost @ trial + sum(s.weight * v[0] for s, v in zip(problem.scenarios, values))
        )
        if candidate < upper:
            upper, best_build = candidate, trial.copy()
            best_q = sum(s.weight * v[0] for s, v in zip(problem.scenarios, values))
            best_shed = sum(s.weight * v[2] for s, v in zip(problem.scenarios, values))
        gap = max(0.0, upper - lower) / max(1.0, abs(upper))
        max_violation = max(max_violation, master.max_violation, max(v[3] for v in values))
        history.append(
            {
                "iteration": iteration,
                "lower_bound": lower,
                "upper_bound": upper,
                "relative_gap": gap,
                "cuts": len(problem.scenarios) * (iteration - 1),
            }
        )
        if lower > upper + max(1.0, abs(upper)) * 1e-7:
            raise RuntimeError("Invalid Benders bounds: lower exceeds upper")
        if gap <= tolerance:
            return PlanningResult(
                upper,
                best_build,
                float(problem.investment_cost @ best_build),
                float(best_q),
                float(best_shed),
                history,
                max_violation,
            )
        for j, (q, gradient, _, _) in enumerate(values):
            m.constraint([(build, gradient), (theta[j], -1)], upper=float(gradient @ trial - q))
    raise RuntimeError(f"Benders did not converge in {max_iterations} iterations; gap={gap:.3g}")
