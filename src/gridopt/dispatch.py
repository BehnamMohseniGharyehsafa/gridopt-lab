"""Energy/reserve co-optimization with empirical conditional value at risk."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd

from .linear import LinearModel


@dataclass
class DispatchResult:
    objective: float
    energy_cost: float
    reserve_cost: float
    dispatch: np.ndarray
    reserve: np.ndarray
    scenario_shortfall: np.ndarray
    cvar_mw: float
    spill: float
    unserved: float
    max_violation: float


def empirical_cvar(values, alpha=0.9) -> float:
    """Exact finite-sample CVaR, including fractional mass at the quantile."""
    values = np.asarray(values, dtype=float)
    if len(values) == 0 or not 0 < alpha < 1:
        raise ValueError("Nonempty values and 0 < alpha < 1 are required")
    eta = np.quantile(values, alpha)
    return float(eta + np.maximum(values - eta, 0).mean() / (1 - alpha))


def solve_dispatch(
    generators: pd.DataFrame,
    demand: float,
    errors,
    *,
    risk_weight=40.0,
    alpha=0.9,
    shortfall_price=50.0,
    deterministic=False,
) -> DispatchResult:
    """Hourly copperplate ED. Reserve exceedance is a procurement-risk proxy, not load shedding."""
    errors = np.asarray(errors, dtype=float)
    if errors.ndim != 1 or len(errors) == 0 or not np.isfinite(errors).all():
        raise ValueError("A nonempty finite vector of forecast errors is required")
    if not 0 < alpha < 1 or risk_weight < 0 or shortfall_price < 0:
        raise ValueError("Invalid CVaR or penalty parameters")
    g, n, s = generators, len(generators), len(errors)
    m = LinearModel()
    p = m.variables(n, cost=g.cost_per_mwh, upper=g.pmax)
    reserve_price = 4 + 0.05 * g.cost_per_mwh.to_numpy()
    r = m.variables(
        n, cost=reserve_price, upper=np.minimum(g.pmax, 15 * g.ramp_mw_min) if not deterministic else 0
    )
    spill = m.variables(1, cost=1.0)
    shed = m.variables(1, cost=10_000.0, upper=max(0.0, demand))
    q = m.variables(s, cost=shortfall_price / s)
    eta = m.variables(1, cost=risk_weight)
    z = m.variables(s, cost=risk_weight / ((1 - alpha) * s))
    m.constraint([(p, 1), (shed, 1), (spill, -1)], lower=demand, upper=demand)
    for i in range(n):
        m.constraint([(p[i], 1), (r[i], 1)], upper=g.pmax.iloc[i])
    for j in range(s):
        m.constraint([(r, -1), (q[j], -1)], upper=-errors[j])
        m.constraint([(q[j], 1), (eta, -1), (z[j], -1)], upper=0)
    result = m.solve()
    x = result.x
    # Compute risk from the chosen reserve to avoid arbitrary slack in unpriced variables.
    short = np.maximum(errors - x[r].sum(), 0.0)
    return DispatchResult(
        float(result.fun),
        float(g.cost_per_mwh @ x[p]),
        float(reserve_price @ x[r]),
        x[p],
        x[r],
        short,
        empirical_cvar(short, alpha),
        float(x[spill][0]),
        float(x[shed][0]),
        result.max_violation,
    )
