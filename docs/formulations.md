# Mathematical formulations

All models use SciPy's HiGHS interfaces, sparse matrices, and explicit feasibility checks. One operational interval is one hour. The 15-minute reserve bound uses the source ramp rate in MW/minute. Code symbols and output columns retain physical units.

## Economic dispatch with forecast-risk reserves

Let $p_g$ be energy, $r_g$ upward reserve, $d$ day-ahead thermal net demand, and $e_s$ an empirical net-load forecast error. Variables $\ell$ and $k$ represent unserved forecast demand and excess fixed renewable injection. With scenario reserve exceedance $q_s$:

$$\min \sum_g c_gp_g+a_gr_g + 10000\ell+k
+\frac{50}{S}\sum_s q_s
+\lambda\left(\eta+\frac{1}{(1-\alpha)S}\sum_s z_s\right).$$

$$\sum_g p_g+\ell-k=d,\quad 0\le p_g,\quad 0\le r_g\le15\,Ramp_g,$$
$$p_g+r_g\le P_g^{max},\quad q_s\ge e_s-\sum_g r_g,\quad q_s\ge0,$$
$$z_s\ge q_s-\eta,\quad z_s\ge0,\quad\eta\ge0.$$

Reserve capacity price $a_g=4+0.05c_g$ is an assumption, in USD/MW for one hour. Exceedance has a $50/MWh balancing-risk proxy price, not a value of lost load. The risk-aware setting uses $\lambda=40$ USD/MWh and $\alpha=0.9$. The risk-neutral ablation sets $\lambda=0$; deterministic ED fixes all $r_g=0$. All methods use identical forecast demand and generator costs.

ED relaxes commitment, minimum output, no-load costs and time coupling. It measures energy and upward-capacity procurement only; reserves are not actually deployed in scenario dispatch. Negative errors need no upward reserve. Seven future errors at the same hour evaluate the fixed reserve decision. Daily exceedance sums across the 24 hours within each future day; its seven-sample CVaR at 90% equals the largest daily outcome. This is a small holdout, with no statistical significance claim.

## Thermal unit commitment MILP

The continuous variables are $p_{tg}$ and $r_{tg}$. Binary $u_{tg}$ is commitment, $v_{tg}$ startup, and $w_{tg}$ shutdown. The objective adds thermal variable cost, no-load cost $n_gu_{tg}$, hot-start cost $s_gv_{tg}$, the same reserve price, spill at $1/MWh, forecast unserved demand at $10,000/MWh, and reserve-requirement shortfall at $5,000/MWh.

$$P_g^{min}u_{tg}\le p_{tg},\qquad p_{tg}+r_{tg}\le P_g^{max}u_{tg},$$
$$r_{tg}\le\min(P_g^{max},15\,Ramp_g)u_{tg},$$
$$u_{tg}-u_{t-1,g}=v_{tg}-w_{tg},\qquad v_{tg}+w_{tg}\le1,$$
$$\sum_{\tau=t-U_g+1}^{t}v_{\tau g}\le u_{tg},\quad
\sum_{\tau=t-D_g+1}^{t}w_{\tau g}\le1-u_{tg}.$$

Rolling windows are truncated at the horizon boundary. Hourly online ramp limits are $60Ramp_g$; startup and shutdown may reach full unit capacity within the hour. Source minimum times are rounded upward to whole hours.

$$p_{tg}-p_{t-1,g}\le60Ramp_g u_{t-1,g}+P_g^{max}v_{tg},$$
$$p_{t-1,g}-p_{tg}\le60Ramp_g u_{tg}+P_g^{max}w_{tg}.$$

Initial coal and nuclear units are online at minimum output. Gas and oil units start offline. Pre-horizon minimum times are assumed satisfied; no future terminal commitment obligation is imposed beyond hour 24. These boundary assumptions can affect daily costs. Identical units in this copperplate model may be globally relabeled, so ordering their total committed hours removes some symmetry. No potentially invalid per-hour ordering is imposed.

The fixed policy requires $0.03L_t$ upward reserve. The calibrated policy uses $\max(0.03L_t,\widehat Q_{0.95}(e\mid hour(t)))$ from the preceding 30 days. It does not include a largest-generator contingency or claim compliance with any balancing-area reserve rule. All reserves are copperplate; deliverability is not modeled.

The MIP target gap is 0.1%, with a 45-second time limit per solve. A time-limited incumbent is returned only after checking bounds, rows and integrality, with its actual gap, lower bound and status preserved. The solver's status is not silently promoted to exact optimality.

## Lossless DC optimal power flow

Each bus has thermal generation, aggregate available renewable/hydro injection $a_b$, curtailed renewable decision $0\le y_b\le a_b$, demand $L_b$, and possible unserved load $0\le\ell_b\le L_b$.

$$\min\sum_gc_gp_g+10000\sum_b\ell_b,$$
$$\sum_{g\in b}p_g+y_b+\ell_b-\sum_{l\in out(b)}f_l+\sum_{l\in in(b)}f_l=L_b,$$
$$f_l=\frac{100}{X_l\tau_l}(\theta_{from(l)}-\theta_{to(l)}),\qquad -F_l\le f_l\le F_l.$$

The 100 MVA base converts per-unit susceptance to MW per radian. Zero transformer ratios in the source mean unity; other tap ratios are retained. One reference angle is zero. Angles otherwise have no artificial bounds. The network is connected in the bundled case.

Constraint generation starts with all nodal and line-flow equations but no thermal line limits. Solve, check all 120 absolute flows, add both bounds for every violated branch, and repeat. Stop only when all line ratings pass. This is exact separation for the stated LP: a feasible optimum of a relaxation is then also optimal for the full model. Tests and experiment comparisons check that equivalence to numerical tolerance. Base ratings and an explicitly stressed 0.65 multiplier are both tested.

Bus-balance duals give marginal prices in this simplified LP, not observed LMPs. Thermal minimum output and UC are relaxed. Aggregate rooftop PV and hydro can be curtailed here, unlike their fixed injections in ED/UC; this simplification is visible in the formulation. No losses, reactive power, voltage magnitudes, AC feasibility, N−1 limits or dynamic security are represented.

## Continuous generation expansion and multicut Benders

First-stage variables $x_k$ build continuous MW of solar, wind and gas. Existing thermal capacities are uniformly reduced to 60% in a stylized retirement case. Three gross-demand multipliers (1.1, 1.25, 1.4) cross four fixed days, giving twelve operating subproblems with weights $w_s$. The investment problem is:

$$\min_{0\le x\le\bar x} C^Tx+\sum_sw_sQ_s(x).$$

Each $Q_s$ is a 24-hour copperplate dispatch LP with existing thermal output, new generation $h_{stk}$, explicit unserved energy and surplus. Candidate capacity constraints are $h_{stk}\le CF_{stk}x_k$. Wind/PV capacity factors use their aggregate day-ahead profiles divided by upstream nameplate capacity; gas has $CF=1$. They preserve sampled hourly variability but assume no geographic diversification of new renewable sites.

Construction costs use EIA's 2024 installation observations. Investment annualization uses
$CRF=r(1+r)^n/((1+r)^n-1)$, plus assumed fixed O&M. Fuel-specific CO₂ intensities and $0/$75/$150 per tonne are explicit policy assumptions, added to variable cost. There are no tax credits, carbon caps, emissions constraints or lifecycle emissions.

The master has one nonnegative recourse approximation $\theta_s$ per scenario. At a trial $x^j$, solve each LP and collect its capacity-constraint duals $\mu_{stk}\le0$. A subgradient is $g_{sk}=\sum_t\mu_{stk}CF_{stk}$ and the supporting cut is:

$$\theta_s\ge Q_s(x^j)+g_s^T(x-x^j).$$

The master optimum is a lower bound. Investment plus evaluated recourse at any feasible build is an upper bound. Retain the best feasible build and stop at $(UB-LB)/\max(1,|UB|)\le10^{-7}$. Nonnegative costs justify the initial $\theta_s\ge0$. Unserved energy ensures complete recourse, so only optimality cuts are needed. Hitting the iteration cap raises an error. The extensive LP uses the identical coefficients and scenario weights as an independent formulation oracle.

This release plans generation capacity only. It omits integer project sizes, transmission expansion, storage, chronological inter-day coupling, reserve adequacy, capacity credit constraints and endogenous retirement. No annual reliability or build recommendation follows from the illustrative sample.
