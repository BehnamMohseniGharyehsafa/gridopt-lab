"""Lossless DC OPF with exact, iterative thermal-limit constraint generation."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd

from .data import SystemData
from .linear import LinearModel


@dataclass
class OPFResult:
    objective: float
    dispatch: np.ndarray
    renewable: np.ndarray
    unserved: np.ndarray
    flows: np.ndarray
    angles: np.ndarray
    prices: np.ndarray
    iterations: list[dict]
    active_lines: list[int]
    max_violation: float


def solve_opf(data: SystemData, stamp, *, screening=True, rating_factor=1.0, tolerance=1e-5) -> OPFResult:
    if rating_factor <= 0:
        raise ValueError("rating_factor must be positive")
    nodal = data.nodal.loc[data.nodal.timestamp == pd.Timestamp(stamp)].set_index("bus")
    bus_ids = data.buses["Bus ID"].tolist()
    if set(nodal.index) != set(bus_ids):
        raise ValueError("Nodal profiles are bundled only for the four documented benchmark days")
    nodal = nodal.loc[bus_ids]
    g, branches = data.generators, data.branches
    nb, nl = len(bus_ids), len(branches)
    lookup = {b: i for i, b in enumerate(bus_ids)}
    from_bus = branches["From Bus"].map(lookup).to_numpy()
    to_bus = branches["To Bus"].map(lookup).to_numpy()
    gen_bus = g.bus.map(lookup).to_numpy()
    tap = branches["Tr Ratio"].to_numpy()
    tap = np.where(tap == 0, 1, tap)
    susceptance = 100 / (branches.X.to_numpy() * tap)
    ratings = branches["Cont Rating"].to_numpy() * rating_factor
    availability = nodal[["wind", "pv", "rtpv", "hydro"]].sum(axis=1).to_numpy()
    active = set() if screening else set(range(nl))
    history = []
    for iteration in range(nl + 1):
        m = LinearModel()
        p = m.variables(len(g), cost=g.cost_per_mwh, upper=g.pmax)
        renewable = m.variables(nb, upper=availability)
        shed = m.variables(nb, cost=10_000.0, upper=nodal.load.to_numpy())
        angle = m.variables(nb, lower=-np.inf)
        flow = m.variables(
            nl,
            lower=[-ratings[i] if i in active else -np.inf for i in range(nl)],
            upper=[ratings[i] if i in active else np.inf for i in range(nl)],
        )
        balance_rows = []
        for b in range(nb):
            balance_rows.append(
                m.constraint(
                    [
                        (p[gen_bus == b], 1),
                        (renewable[b], 1),
                        (shed[b], 1),
                        (flow[from_bus == b], -1),
                        (flow[to_bus == b], 1),
                    ],
                    lower=nodal.load.iloc[b],
                    upper=nodal.load.iloc[b],
                )
            )
        m.constraint([(angle[0], 1)], lower=0, upper=0)
        for line in range(nl):
            m.constraint(
                [
                    (flow[line], 1),
                    (angle[from_bus[line]], -susceptance[line]),
                    (angle[to_bus[line]], susceptance[line]),
                ],
                lower=0,
                upper=0,
            )
        result = m.solve()
        violation = np.maximum(abs(result.x[flow]) - ratings, 0)
        violated = set(np.flatnonzero(violation > tolerance).tolist())
        history.append(
            {
                "iteration": iteration + 1,
                "active_lines": len(active),
                "new_lines": len(violated - active),
                "objective": float(result.fun),
                "max_overload_mw": float(violation.max(initial=0)),
            }
        )
        if not violated:
            duals = dict(zip(result.equal_rows, result.eqlin.marginals))
            return OPFResult(
                float(result.fun),
                result.x[p],
                result.x[renewable],
                result.x[shed],
                result.x[flow],
                result.x[angle],
                np.array([duals[row] for row in balance_rows]),
                history,
                sorted(active),
                max(result.max_violation, float(violation.max(initial=0))),
            )
        if violated <= active:
            raise RuntimeError("Screening stalled above the feasibility tolerance")
        active |= violated
    raise RuntimeError("Constraint generation failed to converge")
