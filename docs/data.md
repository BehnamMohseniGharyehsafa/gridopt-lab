# Data card and provenance

## What is observed, modeled, or assumed?

| Input | Status | Source |
| :-- | :-- | :-- |
| Network, generator capacities, fuel costs, heat rates, ramps and minimum times | Published synthetic benchmark parameters | RTS-GMLC `SourceData` |
| 2020 day-ahead load, wind, utility PV, rooftop PV and hydro | Published modeled time series | RTS-GMLC hourly files |
| Real-time load, wind and solar | Published modeled 5-minute time series, averaged hourly here | RTS-GMLC real-time files |
| Solar $1,865/kW, wind $1,882/kW, gas combustion turbine $841/kW | Reported capacity-weighted construction costs for 2024 installations | [U.S. EIA construction-cost data](https://www.eia.gov/electricity/generatorcosts/), accessed October 22, 2026 |
| O&M, financing, carbon factors/prices, new gas fuel cost, retirements and growth | Explicit illustrative assumptions | [`planning_assumptions.json`](../data/planning_assumptions.json) |
| ED reserve prices and exceedance penalties | Experimental decision-risk assumptions | `dispatch.py`, `experiments.py` |

RTS-GMLC assigns a synthetic network to the southwestern United States to align weather, renewable and load behavior. It does not reveal an actual utility topology or reproduce actual market settlements. The public laboratory [dataset description](https://nrel.sitefinity.cloud/grid/reliability-test-system) explains this geographic assignment.

## Immutable upstream snapshot

Repository: <https://github.com/GridMod/RTS-GMLC>

Commit: `3ece0d3725c844056132393ee252b3083dd4eab4`

[`source_manifest.json`](../data/source_manifest.json) records the full source URLs, byte sizes and SHA-256 hashes. [`processed_manifest.json`](../data/processed_manifest.json) records the offline fixture hashes and asset counts. Every `SystemData.load()` validates the processed checksums. The raw download folder is ignored by Git; the compact processed inputs are committed so a user can reproduce results offline after installing dependencies.

## Transformations

1. Parse `Year`, `Month`, `Day` and one-based `Period`. The source year is a complete leap year: 8,784 hours. Treat timestamps as benchmark local clock labels with no daylight-saving conversion.
2. For real-time series, average each group of twelve 5-minute MW values into one hourly MW value. No energy sum or interpolated timestamps are used.
3. Sum each renewable category across its source generators. Hydro uses the published day-ahead hourly output and is treated as a fixed injection, without reservoir scheduling.
4. Define net thermal demand as gross load minus wind, utility PV, rooftop PV and hydro. Define net forecast error as real-time net demand minus day-ahead net demand. Hydro cancels from that difference.
5. Preserve full-year aggregate profiles for calibration. For each operational hour, train on the preceding 30 calendar days at that same hour, excluding the entire target day. Require at least seven observations; the selected days have 30.
6. Bundle nodal profiles for February 15, May 15, August 15 and November 15. Allocate each area's hourly gross load to buses by their share of the area's static `MW Load`, as prescribed by the upstream schema. Map renewables and hydro to source generator buses and sum them.
7. Keep the 73 thermal generators with fuel Oil, Coal, NG or Nuclear. Approximate each unit by its first incremental heat-rate block and a nonnegative no-load intercept. If that incremental heat rate is zero, use the average minimum-output heat rate (notably nuclear). Heat-rate values in Btu/kWh are divided by 1,000 to obtain MMBtu/MWh. Marginal cost equals that heat rate times fuel price plus VOM. The no-load intercept reproduces the source minimum-output cost when nonnegative. Higher heat-rate blocks are omitted.
8. Startup cost is hot-start heat consumption times fuel price plus non-fuel startup cost. No hot/warm/cold state classification is modeled.
9. Omit CSP, battery storage and synchronous condensers. Include all 120 AC branches; DC links, if present in other upstream formats, are not modeled.

`scripts/prepare_data.py` performs these steps. Tests verify nodal and aggregate profiles agree. `scripts/fetch_data.py` downloads the immutable source files and verifies them against the committed manifest.

## Units and economic vintage

Power and reserve: MW. Hourly energy: MWh. Dispatch cost: USD per modeled hour/day. Planning capacity: MW. Investment: annualized USD/year. EIA construction values are USD/kW, multiplied by 1,000 and annualized with a 30-year, 7% capital recovery factor. O&M and other planning quantities are assumptions.

Upstream fuel prices and recent construction observations have different vintages. The model does not adjust inflation, tax credits, regional labor costs, or interconnection costs. Planning dollar totals therefore describe a mixed-vintage illustrative experiment and cannot be read as a current project valuation.

The four representative days receive 91.25 days each and are crossed with three growth scenarios with probabilities 0.25, 0.5 and 0.25. Expected weights sum to 8,760 hours, deliberately using a conventional planning year despite the leap-year source data. The dates are hand-selected seasonal illustrations, not clustered or statistically validated representative days.

## Redistribution and attribution

Credit **DOE/NREL/ALLIANCE and the RTS-GMLC contributors** for the benchmark. The complete source data-use notice is preserved in [`LICENSE-RTS-GMLC.md`](../data/LICENSE-RTS-GMLC.md), including the upstream snapshot's ending as supplied. It applies to the derived CSV files. The project's MIT license covers project code and original documentation, not a relicensing of upstream data. No endorsement is implied.
