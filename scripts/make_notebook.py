"""Regenerate the small guided notebook without requiring Jupyter at build time."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def cell(kind, source):
    item = {"cell_type": kind, "metadata": {}, "source": source.splitlines(keepends=True)}
    if kind == "code":
        item.update(execution_count=None, outputs=[])
    return item


cells = [
    cell(
        "markdown",
        "# GridOpt Lab / explore the decisions\n\nRun after `pip install -e .`. "
        "This notebook uses the production model functions and bundled public data. "
        "RTS-GMLC is a synthetic U.S. Southwest benchmark, not an actual utility dispatch record.",
    ),
    cell(
        "code",
        "import pandas as pd\nimport matplotlib.pyplot as plt\n"
        "from gridopt.data import SystemData\nfrom gridopt.dispatch import solve_dispatch\n"
        "from gridopt.opf import solve_opf\nfrom gridopt.expansion import build_problem, solve_benders, solve_extensive\n"
        "system = SystemData.load()\nsystem.generators.groupby('fuel')[['pmax', 'cost_per_mwh']].agg(['count', 'mean'])",
    ),
    cell(
        "markdown",
        "## 1. Read the renewable and net-load shape\n\nThese profiles model 2020. "
        "Real-time 5-minute MW values were averaged to hourly MW before calculating forecast errors.",
    ),
    cell(
        "code",
        "day = system.day('2020-08-15')\n"
        "day[['load_da', 'wind_da', 'pv_da', 'net_da']].plot(figsize=(11, 4), ylabel='MW')\nplt.show()",
    ),
    cell(
        "markdown",
        "## 2. Price upward forecast risk\n\n"
        "Compare identical energy forecasts and calibration samples. Reserve exceedance is a procurement proxy, not load shedding.",
    ),
    cell(
        "code",
        "t = pd.Timestamp('2020-08-15 18:00')\nerrors = system.errors(t)\n"
        "rows = []\nfor weight in [0, 10, 40, 80]:\n"
        "    r = solve_dispatch(system.generators, system.profiles.loc[t, 'net_da'], errors, risk_weight=weight)\n"
        "    rows.append({'risk_weight': weight, 'reserve_MW': r.reserve.sum(), 'reserve_cost_USD': r.reserve_cost, 'training_CVaR_MW': r.cvar_mw})\n"
        "pd.DataFrame(rows)",
    ),
    cell(
        "markdown",
        "## 3. Separate line limits and verify the answer\n\n"
        "A 0.65 rating factor is a deliberate transmission-stress scenario. All final lines are checked.",
    ),
    cell(
        "code",
        "screened = solve_opf(system, t, screening=True, rating_factor=.65)\n"
        "full = solve_opf(system, t, screening=False, rating_factor=.65)\n"
        "print('Objective difference:', screened.objective - full.objective)\n"
        "pd.DataFrame(screened.iterations)",
    ),
    cell(
        "markdown",
        "## 4. Watch Benders close its bounds\n\n"
        "The continuous generation investment problem uses four representative days, stylized retirement/growth and a disclosed carbon price. "
        "It is not an adequacy study or investment forecast.",
    ),
    cell(
        "code",
        "problem = build_problem(system, carbon_price=150)\n"
        "benders = solve_benders(problem)\nextensive = solve_extensive(problem)\n"
        "print('Build MW [solar, wind, gas]:', benders.build)\n"
        "print('Relative objective error:', abs(benders.objective-extensive.objective)/extensive.objective)\n"
        "history = pd.DataFrame(benders.history)\n"
        "history.plot(x='iteration', y=['lower_bound', 'upper_bound'], figsize=(10, 4), ylabel='Annualized USD')\nplt.show()",
    ),
    cell(
        "markdown",
        "## Continue with the complete experiment protocol\n\n"
        "Run `gridopt run --output results/runs/my-run` then `gridopt report --input results/runs/my-run`. "
        "The full run includes UC, solver gaps, chronological ED holdouts and carbon sensitivity. "
        "See `docs/formulations.md` and `docs/research.md` before interpreting results.",
    ),
]
notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.13"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}
for i, entry in enumerate(cells):
    entry["id"] = f"gridopt-{i:02d}"
(ROOT / "notebooks/01_explore_gridopt.ipynb").write_text(
    json.dumps(notebook, indent=2) + "\n", encoding="utf-8"
)
