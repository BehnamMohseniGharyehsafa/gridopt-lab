# Research protocol and extension roadmap

## The integrated research idea

Explore whether an empirical forecast-to-decision workflow can make dispatch and commitment more robust while retaining verifiable optimization certificates for network and planning experiments. The novelty under investigation is the integration and evaluation protocol, not the classical optimization algorithms. A literature review and larger out-of-sample study would be required before claiming a novel algorithm or publishable performance result.

## Questions this release can answer

| Hypothesis | Ablation / reference | Metric | Interpretation boundary |
| :-- | :-- | :-- | :-- |
| Tail-aware reserve procurement reduces held-out upward exceedance | Zero-reserve and risk-neutral ED | Mean daily exceedance, daily CVaR, reserve cost | Seven-day holdouts and four fixed dates; no outage simulation |
| Same-hour forecast quantiles alter reserve scheduling | Fixed 3% UC | Reserve MW, starts, cost interval, realized exceedance | One realized day per season; finite MIP gaps |
| Few line limits may suffice for these DC operating points | Full-limit OPF | Objective agreement, active limits, final maximum overload | No universal scaling or speedup claim |
| Scenario decomposition can recover the same planning objective | Extensive LP | Lower/upper bounds and relative objective error | Continuous generation planning; no AC/UC recourse |
| A carbon policy changes illustrative capacity choices | $0, $75 and $150/t cases | Solar/wind/gas MW, annualized objective | Costs and policy are disclosed assumptions |

## Fixed experiment design

- Four operational dates: 2020-02-15, 2020-05-15, 2020-08-15 and 2020-11-15.
- ED uses 30 prior same-hour forecast errors. Hyperparameters are fixed in advance; the next seven days are reserved for evaluation. Days are separated far enough that their evaluation windows do not overlap.
- UC evaluates both reserve policies on every date. Read each policy's feasible cost and lower bound before interpreting their difference.
- OPF uses each day's peak day-ahead net-demand hour, with base and 0.65 branch-rating scenarios.
- Expansion uses all four dates at three load-growth levels, with equal seasonal day weights. All three carbon cases solve both Benders and extensive formulations.
- No random sampling is used. Runtime is a single observed run, with no repeated-run speedup claim.
- CSV/JSON exports preserve hourly decisions, commitment matrices, flows, convergence traces, solver outcomes, versions and input hashes.

## What the correctness checks establish

The tests include analytical merit order, fractional-tail CVaR, an independently enumerated small UC, chronological leakage resistance, nodal aggregation, Kirchhoff flow equations and nodal power balance, full-versus-screened OPF, supporting-cut validity, and Benders/extensive objective agreement with monotone bounds. These establish implementation consistency for the tested cases; they do not validate the modeling assumptions against actual utility operations.

## Next experiments worth doing

1. **Larger chronological evaluation.** Use many rolling-origin days across multiple years, with separate calibration, hyperparameter-selection and final evaluation periods. Report sampling uncertainty and seasonal/sub-hourly performance.
2. **Conditional risk calibration.** Condition error distributions on renewable forecast, weather regimes and ramps, with conformal calibration or distributional robustness. Compare to the same-hour quantile baseline, preserving held-out evaluation.
3. **Deploy the reserves.** Add two-stage or rolling-horizon real-time dispatch with upward/downward activation, ramp deliverability and network constraints. Measure actual unserved energy rather than the reserve-exceedance proxy.
4. **Stronger commitment.** Add piecewise heat-rate blocks, hot/warm/cold starts, realistic initial histories and longer chronological windows. Compare valid inequality families using gaps and runtimes over repeated runs.
5. **Network realism.** Validate DC decisions using an AC reference; add credible N−1 contingency separation, losses and reserve deliverability. Compare decomposition to a full security-constrained formulation.
6. **Planning realism.** Use validated representative weeks, inter-day storage, retirement alternatives, transmission candidates and siting limits. Verify integer investment variants against tractable extensive MILPs.
7. **Adaptive scenario cuts.** Compare multicut, aggregated cuts, and dual-based adaptive grouping. Never remove scenarios merely because they are inconvenient; preserve valid lower bounds and full recourse checks.

Each extension should publish its unsuccessful cases and computational costs as well as its gains.
