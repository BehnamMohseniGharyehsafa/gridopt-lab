# Reference experiment artifacts

This directory records an actual run of `gridopt run --output results/reference`. It contains 42 model comparisons: three ED methods, two UC reserve policies, and two OPF methods at two rating levels for each of four days, plus two planning formulations at three carbon prices.

| Artifact | Contents |
| :-- | :-- |
| `metrics.csv` | Method-level objectives, reserve-risk measures, solver gaps, bounds, timings and maximum violations |
| `dispatch_hourly.csv` | Each method's hourly reserve purchase, training CVaR and held-out exceedance |
| `commitment_hourly.csv` | Aggregate dispatch, committed capacity, reserves, spill and unserved demand |
| `network_flows.csv` | Final screened flows and ratings for all branches and scenarios |
| `convergence.csv` | OPF separation iterations and planning lower/upper bounds |
| `details.json` | Full summer calibrated UC arrays and stressed summer OPF arrays, in the source generator/bus/branch order |
| `metadata.json` | Environment versions, settings, calibration/evaluation protocol and input hashes |
| `analysis.md` | Generated interpretation, tradeoffs and limitations |

Blank cells in `metrics.csv` mean a field does not apply to that problem. Currency is illustrative USD: ED/UC totals cover a modeled operating day; OPF totals cover one hour; planning objectives are annualized under the published weighting assumptions. Reserve capacity is MW; exceedance over hourly intervals is MWh. `holdout_mean_daily_exceedance_mwh` averages seven future daily outcomes. Its sum over seasonal cases is a comparison aggregate, not annual energy. The seven-sample 90% daily CVaR equals the largest future daily exceedance.

`mip_gap` is a fraction; multiply by 100 for percent. `gap-target-reached` means the requested relative gap was attained, not a proof of zero-gap optimality. `feasible-time-limit` explicitly identifies a validated incumbent after 45 seconds. Maximum violations combine constraint/bound residuals and integrality residuals; most rows are in MW but UC's combined maximum can include dimensionless binary residuals.

Runtimes are single-run wall-clock measurements on the platform in `metadata.json`; they are not controlled performance benchmarks. The extensive planning LP is faster on this small fixture. New runs can produce different feasible UC schedules and bounds under the same time limit. Keep reference outputs immutable when comparing new methods, and write experiments under the ignored `results/runs/` folder.
