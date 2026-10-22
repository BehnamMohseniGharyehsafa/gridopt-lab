"""24-hour thermal UC: binary transitions, minimum times, ramping and spinning reserve."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd

from .linear import LinearModel


@dataclass
class CommitmentResult:
    objective: float
    dispatch: np.ndarray
    commitment: np.ndarray
    starts: np.ndarray
    stops: np.ndarray
    reserve: np.ndarray
    spill: np.ndarray
    unserved: np.ndarray
    reserve_shortfall: np.ndarray
    mip_gap: float
    lower_bound: float
    max_violation: float
    solver_status: str


def solve_commitment(
    g: pd.DataFrame, demand, reserve_requirement, *, relax=False, mip_gap=1e-3, time_limit=45.0
) -> CommitmentResult:
    demand, requirement = np.asarray(demand), np.asarray(reserve_requirement)
    if demand.ndim != 1 or requirement.shape != demand.shape or (requirement < 0).any():
        raise ValueError("Demand and nonnegative reserve must have the same vector shape")
    t_count, n = len(demand), len(g)
    cap, minimum, ramp = g.pmax.to_numpy(), g.pmin.to_numpy(), g.ramp_mw_min.to_numpy() * 60
    initial = g.fuel.isin(["Coal", "Nuclear"]).astype(float).to_numpy()
    previous_p = minimum * initial
    m = LinearModel()
    p = m.variables((t_count, n), cost=g.cost_per_mwh.to_numpy(), upper=cap)
    u = m.variables((t_count, n), cost=g.no_load_per_h.to_numpy(), upper=1, integer=True)
    start = m.variables((t_count, n), cost=g.startup_cost.to_numpy(), upper=1, integer=True)
    stop = m.variables((t_count, n), upper=1, integer=True)
    r = m.variables((t_count, n), cost=(4 + 0.05 * g.cost_per_mwh.to_numpy()), upper=cap)
    spill = m.variables(t_count, cost=1.0)
    shed = m.variables(t_count, cost=10_000.0, upper=np.maximum(demand, 0))
    short = m.variables(t_count, cost=5_000.0)
    for t in range(t_count):
        m.constraint([(p[t], 1), (shed[t], 1), (spill[t], -1)], lower=demand[t], upper=demand[t])
        m.constraint([(r[t], 1), (short[t], 1)], lower=requirement[t])
        for i in range(n):
            m.constraint([(p[t, i], 1), (u[t, i], -cap[i]), (r[t, i], 1)], upper=0)
            m.constraint([(p[t, i], -1), (u[t, i], minimum[i])], upper=0)
            m.constraint([(r[t, i], 1), (u[t, i], -min(cap[i], ramp[i] / 4))], upper=0)
            transition = [(u[t, i], 1), (start[t, i], -1), (stop[t, i], 1)]
            if t:
                transition.append((u[t - 1, i], -1))
            rhs = initial[i] if t == 0 else 0.0
            m.constraint(transition, lower=rhs, upper=rhs)
            m.constraint([(start[t, i], 1), (stop[t, i], 1)], upper=1)
            up, down = max(1, int(np.ceil(g.min_up.iloc[i]))), max(1, int(np.ceil(g.min_down.iloc[i])))
            m.constraint([(start[max(0, t - up + 1) : t + 1, i], 1), (u[t, i], -1)], upper=0)
            m.constraint([(stop[max(0, t - down + 1) : t + 1, i], 1), (u[t, i], 1)], upper=1)
            if t:
                m.constraint(
                    [(p[t, i], 1), (p[t - 1, i], -1), (u[t - 1, i], -ramp[i]), (start[t, i], -cap[i])],
                    upper=0,
                )
                m.constraint(
                    [(p[t - 1, i], 1), (p[t, i], -1), (u[t, i], -ramp[i]), (stop[t, i], -cap[i])], upper=0
                )
            else:
                m.constraint(
                    [(p[t, i], 1), (start[t, i], -cap[i])], upper=previous_p[i] + ramp[i] * initial[i]
                )
                m.constraint(
                    [(p[t, i], -1), (u[t, i], -ramp[i]), (stop[t, i], -cap[i])], upper=-previous_p[i]
                )
    # Identical copperplate units may be globally permuted. Order their total online hours
    # to remove some label symmetry without imposing potentially invalid per-hour ordering.
    columns = [
        "pmax",
        "pmin",
        "cost_per_mwh",
        "ramp_mw_min",
        "fuel",
        "no_load_per_h",
        "startup_cost",
        "min_up",
        "min_down",
    ]
    groups = g.reset_index(drop=True).groupby(columns, dropna=False, sort=False).groups
    for group in groups.values():
        indices = list(group)
        for first, second in zip(indices, indices[1:]):
            m.constraint([(u[:, first], 1), (u[:, second], -1)], lower=0)
    result = m.solve(relax=relax, mip_gap=mip_gap, time_limit=time_limit, accept_incumbent=True)
    x = result.x
    return CommitmentResult(
        float(result.fun),
        x[p],
        x[u],
        x[start],
        x[stop],
        x[r],
        x[spill],
        x[shed],
        x[short],
        float(getattr(result, "mip_gap", 0)),
        float(getattr(result, "mip_dual_bound", result.fun)),
        result.max_violation,
        "gap-target-reached" if result.success else "feasible-time-limit",
    )
