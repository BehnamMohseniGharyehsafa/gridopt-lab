"""Small sparse matrix builder shared by the LP and MILP formulations."""

from __future__ import annotations

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, linprog, milp
from scipy.sparse import coo_matrix


class LinearModel:
    def __init__(self) -> None:
        self.cost, self.lower, self.upper, self.integer = [], [], [], []
        self.rows, self.cols, self.values, self.lo, self.hi = [], [], [], [], []

    def variables(self, shape, cost=0.0, lower=0.0, upper=np.inf, integer=False) -> np.ndarray:
        shape = (shape,) if isinstance(shape, int) else tuple(shape)
        size, start = int(np.prod(shape)), len(self.cost)
        for collection, value in [
            (self.cost, cost),
            (self.lower, lower),
            (self.upper, upper),
            (self.integer, int(integer)),
        ]:
            collection.extend(np.broadcast_to(value, shape).ravel().tolist())
        return np.arange(start, start + size).reshape(shape)

    def constraint(self, terms, lower=-np.inf, upper=np.inf) -> int:
        row = len(self.lo)
        for indices, coefficients in terms:
            indices = np.asarray(indices).ravel()
            coefficients = np.broadcast_to(coefficients, indices.shape).ravel()
            self.rows.extend([row] * len(indices))
            self.cols.extend(indices.tolist())
            self.values.extend(coefficients.tolist())
        self.lo.append(lower)
        self.hi.append(upper)
        return row

    def matrix(self):
        return coo_matrix((self.values, (self.rows, self.cols)), shape=(len(self.lo), len(self.cost))).tocsr()

    def solve(self, *, relax=False, mip_gap=1e-4, time_limit=120.0, accept_incumbent=False):
        a, lo, hi = self.matrix(), np.array(self.lo), np.array(self.hi)
        if any(self.integer) and not relax:
            result = milp(
                np.array(self.cost),
                integrality=np.array(self.integer),
                bounds=Bounds(self.lower, self.upper),
                constraints=LinearConstraint(a, lo, hi),
                options={"mip_rel_gap": mip_gap, "time_limit": time_limit},
            )
        else:
            equal = np.isfinite(lo) & (lo == hi)
            upper, lower = np.isfinite(hi) & ~equal, np.isfinite(lo) & ~equal
            from scipy.sparse import vstack

            result = linprog(
                self.cost,
                A_ub=vstack([a[upper], -a[lower]], format="csr"),
                b_ub=np.r_[hi[upper], -lo[lower]],
                A_eq=a[equal],
                b_eq=lo[equal],
                bounds=list(zip(self.lower, self.upper)),
                method="highs",
            )
            result.equal_rows = np.flatnonzero(equal)
            result.upper_rows = np.flatnonzero(upper)
            result.lower_rows = np.flatnonzero(lower)
        feasible_incumbent = accept_incumbent and result.status == 1 and result.x is not None
        if not result.success and not feasible_incumbent:
            raise RuntimeError(f"Optimization failed (status {result.status}): {result.message}")
        result.max_violation = self.violation(result.x)
        if any(self.integer) and not relax:
            selected = result.x[np.array(self.integer, dtype=bool)]
            result.max_violation = max(result.max_violation, float(abs(selected - np.rint(selected)).max()))
        if result.max_violation > 1e-4:
            raise RuntimeError(f"Solution violates constraints by {result.max_violation:g}")
        return result

    def violation(self, x) -> float:
        ax = self.matrix() @ x
        errors = np.r_[
            np.array(self.lo) - ax, ax - np.array(self.hi), np.array(self.lower) - x, x - np.array(self.upper)
        ]
        return float(max(0.0, errors.max(initial=0.0)))
