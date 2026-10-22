"""Independent invariants, small analytical cases and decomposition equivalence."""

import itertools
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from gridopt.data import SystemData
from gridopt.dispatch import solve_dispatch, empirical_cvar
from gridopt.commitment import solve_commitment
from gridopt.opf import solve_opf
from gridopt.expansion import PlanningProblem, Scenario, recourse, solve_benders, solve_extensive


def fleet():
    return pd.DataFrame(
        {
            "pmax": [100.0, 100.0],
            "pmin": [20.0, 20.0],
            "cost_per_mwh": [10.0, 30.0],
            "ramp_mw_min": [10.0, 10.0],
            "fuel": ["NG", "NG"],
            "no_load_per_h": [5.0, 5.0],
            "startup_cost": [100.0, 100.0],
            "min_up": [2, 2],
            "min_down": [1, 1],
        }
    )


def test_dispatch_merit_order_and_balance():
    result = solve_dispatch(fleet(), 150.0, [0.0], deterministic=True)
    np.testing.assert_allclose(result.dispatch, [100, 50])
    assert result.energy_cost == pytest.approx(2500.0)
    assert result.max_violation < 1e-7


def test_cvar_fractional_tail_and_risk_response():
    assert empirical_cvar([0, 0, 0, 0, 10], 0.8) == pytest.approx(10)
    assert empirical_cvar([0, 0, 0, 0, 10], 0.7) == pytest.approx(10 / 1.5)
    errors = [0] * 19 + [80]
    neutral = solve_dispatch(fleet(), 50, errors, risk_weight=0)
    risk = solve_dispatch(fleet(), 50, errors, risk_weight=40)
    assert risk.reserve.sum() > neutral.reserve.sum() + 1
    assert risk.cvar_mw < neutral.cvar_mw
    assert (risk.dispatch + risk.reserve <= fleet().pmax + 1e-7).all()


def test_uc_matches_independent_enumeration():
    # Enumerate one unit's 16 binary schedules independently of the matrix builder.
    g = fleet().iloc[:1]
    demand = np.array([0.0, 50.0, 50.0, 0.0])
    candidates = []
    for status in itertools.product([0, 1], repeat=4):
        u = np.array(status)
        starts = np.maximum(u - np.r_[0, u[:-1]], 0)
        if ((demand > 0) & (u == 0)).any():
            continue
        if any(starts[t] and u[t : min(t + 2, 4)].sum() < min(2, 4 - t) for t in range(4)):
            continue
        p = np.maximum(demand, 20 * u)
        # Spill is charged $1/MWh, exactly as specified in the economic formulation.
        candidates.append(10 * p.sum() + 5 * u.sum() + 100 * starts.sum() + (p - demand).sum())
    result = solve_commitment(g, demand, np.zeros(4))
    assert result.objective == pytest.approx(min(candidates))
    np.testing.assert_allclose(result.commitment.ravel(), [0, 1, 1, 0], atol=1e-7)
    assert result.unserved.sum() < 1e-7
    relaxation = solve_commitment(g, demand, np.zeros(4), relax=True)
    assert relaxation.objective <= result.objective + 1e-7


@pytest.fixture(scope="module")
def system():
    return SystemData.load()


def test_data_and_chronological_calibration(system):
    assert len(system.profiles) == 8784
    stamp = pd.Timestamp("2020-08-15 18:00")
    original = system.errors(stamp)
    modified = replace(system, profiles=system.profiles.copy())
    modified.profiles.loc[stamp.normalize() :, "net_error"] = 1e9
    np.testing.assert_array_equal(original, modified.errors(stamp))
    assert len(original) == 30
    for date in ["2020-02-15", "2020-05-15", "2020-08-15", "2020-11-15"]:
        nodal = system.nodal.loc[system.nodal.timestamp.dt.strftime("%Y-%m-%d") == date]
        grouped = nodal.groupby("timestamp")
        day = system.day(date)
        np.testing.assert_allclose(grouped.load.sum(), day.load_da, atol=1e-3)
        for column in ["wind", "pv", "rtpv", "hydro"]:
            expected = day[column if column == "hydro" else f"{column}_da"]
            np.testing.assert_allclose(grouped[column].sum(), expected, atol=1e-3)


@pytest.mark.parametrize("factor", [1.0, 0.65])
def test_network_physics_and_screening(system, factor):
    screened = solve_opf(system, "2020-08-15 18:00", rating_factor=factor)
    full = solve_opf(system, "2020-08-15 18:00", screening=False, rating_factor=factor)
    assert screened.objective == pytest.approx(full.objective, rel=1e-8)
    assert (abs(screened.flows) <= system.branches["Cont Rating"] * factor + 1e-5).all()
    lookup = {b: i for i, b in enumerate(system.buses["Bus ID"])}
    branch = system.branches
    angles = screened.angles
    tap = np.where(branch["Tr Ratio"] == 0, 1, branch["Tr Ratio"])
    expected = (
        100
        / (branch.X.to_numpy() * tap)
        * (angles[branch["From Bus"].map(lookup)] - angles[branch["To Bus"].map(lookup)])
    )
    np.testing.assert_allclose(screened.flows, expected, atol=1e-5)
    nodal = system.nodal.loc[system.nodal.timestamp == pd.Timestamp("2020-08-15 18:00")].set_index("bus")
    injection = screened.renewable + screened.unserved - nodal.loc[system.buses["Bus ID"]].load.to_numpy()
    np.add.at(injection, system.generators.bus.map(lookup), screened.dispatch)
    np.add.at(injection, branch["From Bus"].map(lookup), -screened.flows)
    np.add.at(injection, branch["To Bus"].map(lookup), screened.flows)
    np.testing.assert_allclose(injection, 0.0, atol=1e-5)


def small_planning():
    scenarios = [
        Scenario("low", np.array([80.0, 160.0]), np.array([[1.0, 0.5, 1.0], [0.1, 0.8, 1.0]]), 100.0),
        Scenario("high", np.array([130.0, 190.0]), np.array([[0.8, 0.3, 1.0], [0.0, 0.7, 1.0]]), 100.0),
    ]
    return PlanningProblem(
        np.array([100.0]),
        np.array([40.0]),
        np.array([1000.0, 2000.0, 500.0]),
        np.array([0.0, 0.0, 70.0]),
        np.array([200.0, 200.0, 200.0]),
        scenarios,
    )


def test_benders_matches_extensive_and_bounds():
    problem = small_planning()
    benders, extensive = solve_benders(problem), solve_extensive(problem)
    assert benders.objective == pytest.approx(extensive.objective, rel=1e-7)
    history = pd.DataFrame(benders.history)
    assert (np.diff(history.lower_bound) >= -1e-3).all()
    assert (np.diff(history.upper_bound) <= 1e-3).all()
    assert (history.lower_bound <= history.upper_bound + 1e-3).all()
    assert history.relative_gap.iloc[-1] <= 1e-7


def test_dual_cut_is_a_global_lower_support():
    problem = small_planning()
    x = np.array([20.0, 10.0, 10.0])
    q, gradient, _, _ = recourse(problem, problem.scenarios[0], x)
    for y in [np.zeros(3), np.array([100.0, 50.0, 25.0]), np.array([0.0, 0.0, 100.0])]:
        q_y = recourse(problem, problem.scenarios[0], y)[0]
        assert q + gradient @ (y - x) <= q_y + 1e-5


def test_bad_inputs_fail_explicitly(system):
    with pytest.raises(ValueError):
        solve_dispatch(fleet(), 50, [])
    with pytest.raises(ValueError):
        solve_opf(system, "2020-08-16", rating_factor=0.65)
    with pytest.raises(ValueError):
        solve_benders(small_planning(), max_iterations=0)
