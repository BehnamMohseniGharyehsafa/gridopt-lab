"""Publication figures and an offline, accessible HTML research report."""

from __future__ import annotations

import base64
from html import escape
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon
from matplotlib.collections import LineCollection
import numpy as np
import pandas as pd

from .data import SystemData, repository_root

INK, TEAL, ORANGE, BLUE, MUTED, PAPER = "#14283d", "#007f79", "#c85c32", "#526cba", "#5c6f80", "#f3f6f7"
REPO_URL = "https://github.com/BehnamMohseniGharyehsafa/gridopt-lab"


def style():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.titlepad": 16,
            "axes.labelcolor": MUTED,
            "text.color": INK,
            "axes.edgecolor": "#d3dce1",
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "grid.alpha": 0.18,
            "svg.fonttype": "none",
            "savefig.facecolor": "white",
        }
    )


def save(fig, folder: Path, name: str):
    fig.savefig(folder / f"{name}.png", dpi=170, bbox_inches="tight", pad_inches=0.25)
    fig.savefig(folder / f"{name}.svg", bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)


def box(ax, x, y, w, h, heading, body, color=TEAL):
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.015,rounding_size=.025",
            facecolor="white",
            edgecolor="#cad6dc",
            linewidth=1.3,
        )
    )
    ax.text(x + 0.025, y + h - 0.055, heading, color=color, fontsize=13, weight="bold", va="top")
    ax.text(x + 0.025, y + h - 0.125, body, color=INK, fontsize=10, va="top", linespacing=1.65)


def arrow(ax, a, b, color=TEAL):
    ax.add_patch(
        FancyArrowPatch(
            a, b, arrowstyle="-|>", mutation_scale=16, lw=1.7, color=color, connectionstyle="arc3,rad=0"
        )
    )


def diagrams(folder: Path):
    fig, ax = plt.subplots(figsize=(15, 5.1))
    fig.patch.set_facecolor(INK)
    ax.set_facecolor(INK)
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis("off")
    ax.text(
        0.015, 0.89, "GRIDOPT / RESEARCH LAB", color="#72ddd0", size=12, weight="bold", fontfamily="monospace"
    )
    ax.text(
        0.015,
        0.62,
        "Power systems.\nDecisions, explained.",
        color="white",
        size=34,
        weight="bold",
        linespacing=1.2,
    )
    ax.text(0.015, 0.25, "Development of power system optimization algorithms", color="#c4d4e0", size=13)
    ax.text(
        0.015, 0.08, "ED  /  UC  /  DC-OPF  /  EXPANSION", color="#72ddd0", size=12, fontfamily="monospace"
    )
    points = np.array(
        [
            [0.72, 0.15],
            [0.84, 0.23],
            [0.96, 0.16],
            [0.67, 0.39],
            [0.79, 0.48],
            [0.93, 0.47],
            [0.72, 0.74],
            [0.88, 0.8],
            [0.99, 0.69],
        ]
    )
    edges = [
        (0, 1),
        (1, 2),
        (0, 3),
        (1, 4),
        (2, 5),
        (3, 4),
        (4, 5),
        (3, 6),
        (4, 6),
        (4, 7),
        (5, 7),
        (5, 8),
        (6, 7),
        (7, 8),
    ]
    for i, j in edges:
        ax.plot(*points[[i, j]].T, color="#3c6177", lw=1.6, zorder=1)
    ax.scatter(
        *points.T,
        s=[90, 160, 90, 100, 280, 100, 90, 190, 80],
        color="#64d9c6",
        edgecolors=INK,
        lw=3,
        zorder=2,
    )
    ax.text(0.77, 0.02, "OPEN DATA · OPEN METHODS", color="#95afc2", size=9, ha="center")
    save(fig, folder, "hero")

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5), gridspec_kw={"width_ratios": [1, 1.25]})
    ax = axes[0]
    vertices = np.array([[0, 0], [2.25, 0], [1.5, 1.5], [0, 2.25]])
    ax.add_patch(Polygon(vertices, facecolor="#d8eeea", edgecolor=TEAL, alpha=0.8))
    x, y = np.meshgrid(np.arange(4), np.arange(4))
    feasible = (2 * x + y <= 4.5) & (x + 2 * y <= 4.5)
    ax.scatter(x[~feasible], y[~feasible], color="#d9dfe4", s=30, label="Infeasible integer points")
    ax.scatter(x[feasible], y[feasible], color=INK, s=42, label="Feasible integer points")
    ax.scatter([1.5], [1.5], marker="*", s=220, color=ORANGE, zorder=4, label="LP optimum = 3")
    ax.scatter(
        [1], [1], s=100, facecolors="none", edgecolors=TEAL, lw=2.5, zorder=4, label="One MILP optimum = 2"
    )
    ax.annotate(
        "Fractional relaxation\n(1.5, 1.5)",
        (1.5, 1.5),
        (1.9, 2.35),
        arrowprops={"arrowstyle": "->", "color": ORANGE},
        fontsize=10,
    )
    ax.set(xlim=(-0.2, 3.4), ylim=(-0.2, 3.4), xlabel="Integer decision x", ylabel="Integer decision y")
    ax.set_aspect("equal")
    ax.set_title("01 / Why integer decisions matter", loc="left")
    ax.legend(loc="upper right", bbox_to_anchor=(1.0, -0.16), frameon=False, fontsize=9)
    ax = axes[1]
    ax.axis("off")
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.set_title("02 / From unit commitment to MILP", loc="left")
    box(
        ax,
        0.02,
        0.60,
        0.94,
        0.28,
        "Choose the schedule",
        "Binary u: unit on/off  ·  v: startup  ·  w: shutdown\nContinuous p: generation  ·  r: spinning reserve",
    )
    arrow(ax, (0.5, 0.58), (0.5, 0.49))
    box(
        ax,
        0.02,
        0.18,
        0.94,
        0.28,
        "Solve with branch and bound",
        "LP relaxation supplies a lower bound on cost.\nFeasible integer schedules supply upper bounds.\nStop at the reported relative optimality gap.",
        BLUE,
    )
    ax.text(
        0.03,
        0.035,
        "Toy geometry: maximize x+y subject to 2x+y ≤ 4.5, x+2y ≤ 4.5.\nThe UC formulation minimizes cost; its bound direction is reversed.",
        size=9,
        color=MUTED,
    )
    save(fig, folder, "milp")

    fig, ax = plt.subplots(figsize=(14, 6.5))
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis("off")
    ax.text(0.01, 0.96, "DECOMPOSITION / SMALLER PROBLEMS, CHECKABLE BOUNDS", size=17, weight="bold")
    box(
        ax,
        0.03,
        0.43,
        0.30,
        0.35,
        "01  Investment master",
        "Choose solar, wind and gas MW.\nApproximate scenario costs with θ.\nInvestment + weighted θ = lower bound.",
    )
    box(
        ax,
        0.63,
        0.60,
        0.32,
        0.25,
        "02  Operating subproblems",
        "12 season × growth scenarios\nHourly dispatch at fixed capacity",
        BLUE,
    )
    box(
        ax,
        0.63,
        0.20,
        0.32,
        0.25,
        "03  Dual information",
        "Daily operating cost Q(x)\nCapacity subgradient from LP duals",
        ORANGE,
    )
    arrow(ax, (0.35, 0.7), (0.60, 0.72))
    ax.text(0.40, 0.76, "trial capacity x", size=10, color=TEAL)
    arrow(ax, (0.79, 0.58), (0.79, 0.47), BLUE)
    arrow(ax, (0.61, 0.29), (0.35, 0.51), ORANGE)
    ax.text(
        0.35,
        0.32,
        "valid supporting cuts\nθ ≥ Q(xᵏ) + gᵀ(x − xᵏ)",
        size=11,
        color=ORANGE,
        ha="center",
        va="top",
    )
    ax.text(
        0.04,
        0.10,
        "Evaluate a feasible build → upper bound.  Repeat until the relative bound gap closes.",
        size=12,
        weight="bold",
    )
    ax.text(
        0.04,
        0.025,
        "Exact benchmark: solve the same continuous investment problem as one extensive LP and compare objectives.",
        size=10,
        color=MUTED,
    )
    save(fig, folder, "decomposition")


def result_figures(folder: Path, source: Path, metrics: pd.DataFrame, data: SystemData):
    ed = pd.read_csv(source / "dispatch_hourly.csv")
    uc = pd.read_csv(source / "commitment_hourly.csv")
    curves = pd.read_csv(source / "convergence.csv")
    details = json.loads((source / "details.json").read_text())
    seasons = [s for s in ["winter", "spring", "summer", "autumn"] if s in ed.season.unique()]
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 9))
    colors = [MUTED, BLUE, TEAL]
    for i, method in enumerate(["deterministic", "risk-neutral", "cvar"]):
        frame = (
            metrics[(metrics.problem == "ED") & (metrics.method == method)].set_index("season").loc[seasons]
        )
        axes[0, 0].bar(
            np.arange(len(seasons)) + (i - 1) * 0.24,
            frame.holdout_mean_daily_exceedance_mwh,
            0.24,
            label=method,
            color=colors[i],
        )
    axes[0, 0].set_xticks(np.arange(len(seasons)), [s.title() for s in seasons])
    axes[0, 0].set_title("ED / Held-out reserve exceedance", loc="left")
    axes[0, 0].set_ylabel("Mean daily MWh above procured reserve")
    axes[0, 0].legend(frameon=False, fontsize=8)
    for method, color in [("fixed-3pct", MUTED), ("calibrated-95pct", TEAL)]:
        frame = uc[(uc.season == "summer") & (uc.method == method)]
        axes[0, 1].plot(frame.hour, frame.reserve_mw, label=method, color=color, lw=2)
    axes[0, 1].set(xlabel="Hour of day", ylabel="Procured upward reserve (MW)", xticks=[0, 6, 12, 18, 23])
    axes[0, 1].set_title("UC / Summer reserve schedules", loc="left")
    axes[0, 1].legend(frameon=False, fontsize=8)
    hist = curves[(curves.problem == "Expansion") & (curves.carbon_usd_t == 75)]
    axes[1, 0].plot(hist.iteration, hist.upper_bound / 1e9, color=TEAL, lw=2, label="Upper bound")
    axes[1, 0].plot(hist.iteration, hist.lower_bound / 1e9, color=ORANGE, lw=2, label="Lower bound")
    axes[1, 0].set(xlabel="Benders iteration", ylabel="Illustrative annual cost ($ billion)")
    axes[1, 0].set_title("Expansion / Certified bound convergence", loc="left")
    axes[1, 0].legend(frameon=False, fontsize=8)
    plan = metrics[(metrics.problem == "Expansion") & (metrics.method == "benders")].sort_values(
        "carbon_usd_t"
    )
    x = np.arange(len(plan))
    bottom = np.zeros(len(plan))
    for tech, color in [("solar", ORANGE), ("wind", TEAL), ("gas", BLUE)]:
        values = plan[f"{tech}_build_mw"].to_numpy()
        axes[1, 1].bar(x, values, bottom=bottom, color=color, label=tech.title())
        bottom += values
    axes[1, 1].set_xticks(x, [f"${c:g}/t" for c in plan.carbon_usd_t])
    axes[1, 1].set(xlabel="Assumed carbon price", ylabel="New capacity (MW)")
    axes[1, 1].set_title("Expansion / Policy changes the build", loc="left")
    axes[1, 1].legend(frameon=False, fontsize=8)
    for ax in axes.flat:
        ax.grid(axis="y")
        ax.set_axisbelow(True)
    fig.suptitle(
        "Measured results, from the same public benchmark", x=0.07, ha="left", weight="bold", size=19
    )
    fig.text(
        0.07,
        0.012,
        "Four illustrative operating days · ED holdout: following seven days · Planning: four weighted days, not an adequacy study",
        size=9,
        color=MUTED,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.95), h_pad=3, w_pad=3)
    save(fig, folder, "results-overview")

    # Geolocated network: no inferred geographic basemap or proprietary map tiles.
    fig, ax = plt.subplots(figsize=(12, 7))
    bus = data.buses.set_index("Bus ID")
    lines = data.branches
    points = bus[["lng", "lat"]]
    segments = [points.loc[[row["From Bus"], row["To Bus"]]].to_numpy() for _, row in lines.iterrows()]
    flows = np.array(details["summer_opf"]["flows"])
    ratio = abs(flows) / (0.65 * lines["Cont Rating"].to_numpy())
    collection = LineCollection(segments, array=ratio, cmap="YlOrRd", linewidths=1.4 + ratio * 2, clim=(0, 1))
    ax.add_collection(collection)
    ax.scatter(
        points.lng, points.lat, c=bus.Area, cmap="viridis", s=22, edgecolors="white", linewidths=0.5, zorder=3
    )
    ax.autoscale()
    for name, bid in [("Area 1", 101), ("Area 2", 201), ("Area 3", 301)]:
        ax.annotate(
            name, points.loc[bid], xytext=(10, -18), textcoords="offset points", weight="bold", size=11
        )
    colorbar = fig.colorbar(collection, ax=ax, shrink=0.7, pad=0.04)
    colorbar.set_label("Absolute flow / stressed continuous rating")
    ax.set(xlabel="Longitude (degrees)", ylabel="Latitude (degrees)")
    ax.set_title("DC-OPF / Transmission utilization in the U.S. Southwest benchmark", loc="left", pad=24)
    fig.text(
        0.08,
        0.015,
        "RTS-GMLC synthetic geography · Summer peak-net-load hour · Line ratings × 0.65 is an explicit stress assumption",
        color=MUTED,
        size=9,
    )
    save(fig, folder, "network")

    fig, axes = plt.subplots(2, 1, figsize=(13, 8), gridspec_kw={"height_ratios": [1, 1.5]})
    day = data.day("2020-08-15")
    axes[0].stackplot(
        np.arange(24),
        day.wind_da,
        day.pv_da + day.rtpv_da,
        day.hydro,
        labels=["Wind", "Solar + rooftop PV", "Hydro"],
        colors=[TEAL, ORANGE, BLUE],
        alpha=0.8,
    )
    axes[0].plot(np.arange(24), day.load_da, color=INK, label="Gross load", lw=2)
    axes[0].plot(np.arange(24), day.net_da, color=MUTED, label="Thermal net load", lw=1.8, ls="--")
    axes[0].set(ylabel="Power (MW)", xlim=(0, 23), xticks=[0, 6, 12, 18, 23])
    axes[0].legend(ncol=3, frameon=False, fontsize=9, loc="upper left")
    axes[0].set_title("UC / Summer input profiles and calibrated commitment", loc="left")
    order = data.generators.sort_values(["fuel", "id"]).index.to_numpy()
    matrix = np.array(details["summer_uc"]["commitment"])[:, order].T
    axes[1].imshow(
        matrix,
        aspect="auto",
        interpolation="nearest",
        cmap="GnBu",
        vmin=0,
        vmax=1,
        extent=(-0.5, 23.5, len(order) - 0.5, -0.5),
    )
    labels = data.generators.loc[order, "fuel"].to_numpy()
    ticks = []
    names = []
    for fuel in dict.fromkeys(labels):
        indices = np.flatnonzero(labels == fuel)
        ticks.append(indices.mean())
        names.append(f"{fuel} ({len(indices)} units)")
        if indices[0] > 0:
            axes[1].axhline(indices[0] - 0.5, color="white", lw=2)
    axes[1].set_yticks(ticks, names)
    axes[1].set(xlabel="Hour of day", xticks=[0, 6, 12, 18, 23])
    fig.text(
        0.09,
        0.015,
        "Each row is one thermal generator. Dark = committed; light = off. Minimum up/down time and ramp constraints are enforced.",
        size=9,
        color=MUTED,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1), h_pad=2)
    save(fig, folder, "commitment")


def table_html(frame: pd.DataFrame, caption: str) -> str:
    return (
        '<div class="table-wrap">'
        + frame.to_html(
            index=False, border=0, classes="data-table", float_format=lambda x: f"{x:,.3f}"
        ).replace("<table ", f'<table aria-label="{escape(caption)}" ')
        + "</div>"
    )


def analysis_text(metrics: pd.DataFrame) -> str:
    ed = metrics[metrics.problem == "ED"]
    neutral = ed[ed.method == "risk-neutral"]
    cvar = ed[ed.method == "cvar"]
    baseline = ed[ed.method == "deterministic"]
    total0 = baseline.holdout_mean_daily_exceedance_mwh.sum()
    total1 = cvar.holdout_mean_daily_exceedance_mwh.sum()
    reduction = 100 * (1 - total1 / total0) if total0 else 0
    opf = metrics[(metrics.problem == "DC-OPF") & (metrics.method == "constraint-generation")]
    plan = metrics[(metrics.problem == "Expansion") & (metrics.method == "benders")]
    base = plan[plan.carbon_usd_t == 75].iloc[0]
    uc = metrics[metrics.problem == "UC"]
    high = plan[plan.carbon_usd_t == 150]
    sensitivity = ""
    if not high.empty:
        row = high.iloc[0]
        sensitivity = (
            f"At $150/t, the build changed to {row.solar_build_mw:,.1f} MW solar, "
            f"{row.wind_build_mw:,.1f} MW wind and {row.gas_build_mw:,.1f} MW gas. "
        )
    extensive = metrics[(metrics.problem == "Expansion") & (metrics.method == "extensive")]
    return (
        f"CVaR dispatch reduced the sum of mean daily held-out reserve exceedances by {reduction:.1f}% "
        f"relative to zero-reserve dispatch across the included seasonal cases ({total0:,.1f} to {total1:,.1f} MWh). "
        f"Reserve procurement costs increased by ${cvar.reserve_cost_usd.sum() - baseline.reserve_cost_usd.sum():,.0f} "
        f"over the modeled operating days. Risk-neutral procurement produced {neutral.holdout_mean_daily_exceedance_mwh.sum():,.1f} MWh "
        f"on the same aggregate exceedance measure. On the common $50/MWh exceedance-price metric, "
        f"CVaR's summed held-out proxy cost was ${cvar.holdout_proxy_cost_usd.sum():,.0f}, "
        f"versus ${neutral.holdout_proxy_cost_usd.sum():,.0f} for risk-neutral procurement. "
        f"The lower tail risk therefore has a visible procurement-cost tradeoff in this run. "
        f"These exceedances are a procurement-risk proxy; they are not measured blackouts.\n\n"
        f"All screened DC-OPF objectives matched their full-limit counterparts within the experiment tolerance. "
        f"Screened solves retained {int(opf.active_line_limits.min())}–{int(opf.active_line_limits.max())} of 120 line-limit pairs, "
        f"and every final flow was checked against every rating. Constraint reduction alone does not establish a runtime advantage.\n\n"
        f"UC schedules had a maximum reported relative MIP gap of {uc.mip_gap.max():.3%}. "
        f"{int((uc.solver_status == 'feasible-time-limit').sum())} solves returned a validated incumbent at the time limit. "
        f"Small cost differences between reserve policies should be interpreted alongside their solver bounds.\n\n"
        f"At the assumed $75/t carbon price, planning built {base.solar_build_mw:,.1f} MW solar, "
        f"{base.wind_build_mw:,.1f} MW wind and {base.gas_build_mw:,.1f} MW gas, at an illustrative annual objective "
        f"of ${base.objective_usd_year / 1e9:.3f} billion. Benders and extensive LP objectives agreed for every tested carbon price. "
        f"The base result can favor gas because existing low-cost generation supplies much of the sampled energy and new capacity "
        f"covers residual peaks. {sensitivity}"
        f"Mean observed planning runtime was {plan.runtime_s.mean():.2f}s for Benders and "
        f"{extensive.runtime_s.mean():.2f}s for the extensive LP; decomposition was slower on this small benchmark. "
        f"Four hand-selected days, simplified retirements, and mixed-vintage cost assumptions limit any investment interpretation."
    )


def create_report(source: Path) -> None:
    root = repository_root()
    folder = root / "docs/assets"
    folder.mkdir(parents=True, exist_ok=True)
    metrics = pd.read_csv(source / "metrics.csv")
    data = SystemData.load()
    style()
    diagrams(folder)
    result_figures(folder, source, metrics, data)
    analysis = analysis_text(metrics)
    (source / "analysis.md").write_text(
        "# Interpretation of the reference experiments\n\n" + analysis + "\n", encoding="utf-8"
    )
    metadata = json.loads((source / "metadata.json").read_text())

    # Embed images and tables: the report works offline without fetch, a CDN, or tracking.
    def img(name, alt):
        payload = base64.b64encode((folder / f"{name}.png").read_bytes()).decode()
        return f'<img src="data:image/png;base64,{payload}" alt="{escape(alt)}" loading="lazy">'

    panels = []
    cols = {
        "ED": [
            "season",
            "method",
            "reserve_cost_usd",
            "holdout_mean_daily_exceedance_mwh",
            "holdout_daily_cvar90_mwh",
        ],
        "UC": [
            "season",
            "method",
            "objective_usd",
            "mip_gap",
            "solver_status",
            "realized_reserve_exceedance_mwh",
        ],
        "DC-OPF": ["season", "method", "rating_factor", "objective_usd", "active_line_limits", "iterations"],
        "Expansion": [
            "method",
            "carbon_usd_t",
            "solar_build_mw",
            "wind_build_mw",
            "gas_build_mw",
            "objective_usd_year",
        ],
    }
    for i, (problem, columns) in enumerate(cols.items()):
        frame = metrics.loc[metrics.problem == problem, columns]
        panels.append(
            f'<section id="panel-{i}" class="result-panel" aria-labelledby="tab-{i}" role="tabpanel" {"hidden" if i else ""}><h3>{escape(problem)} / recorded results</h3>{table_html(frame, problem + " results")}</section>'
        )
    paragraphs = "".join(f"<p>{escape(p)}</p>" for p in analysis.split("\n\n"))
    tabs = "".join(
        f'<button id="tab-{i}" role="tab" aria-controls="panel-{i}" aria-selected="{str(i == 0).lower()}" tabindex="{0 if i == 0 else -1}">{escape(problem)}</button>'
        for i, problem in enumerate(cols)
    )
    html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="An open research lab for economic dispatch, unit commitment, DC optimal power flow and generation expansion using U.S. RTS-GMLC data.">
<meta name="color-scheme" content="light"><title>GridOpt Lab — Power systems, decisions explained</title>
<style>
:root{{--ink:{INK};--teal:{TEAL};--muted:{MUTED};--paper:{PAPER};--line:#d4dfe4}}*{{box-sizing:border-box}}
body{{margin:0;background:#fff;color:var(--ink);font:16px/1.7 system-ui,-apple-system,Segoe UI,sans-serif}}
a{{color:var(--teal);text-underline-offset:4px}}a:focus-visible,button:focus-visible{{outline:3px solid #c85c32;outline-offset:4px}}
.skip{{position:absolute;left:1rem;top:-100px;background:white;padding:1rem;z-index:5}}.skip:focus{{top:1rem}}
.wrap{{max-width:1160px;margin:auto;padding:0 32px}}header{{border-bottom:1px solid var(--line)}}nav{{display:flex;justify-content:space-between;align-items:center;padding:20px 0;gap:20px;flex-wrap:wrap}}
.wordmark{{font-weight:800;letter-spacing:-.6px;font-size:22px}}.wordmark b{{color:var(--teal)}}nav a{{font-size:14px;margin-left:20px;text-decoration:none}}
.hero{{background:var(--ink);color:white;padding:72px 0 56px;position:relative;overflow:hidden}}.eyebrow{{font:12px ui-monospace,monospace;letter-spacing:2px;color:#70ded0;text-transform:uppercase}}
h1{{font-size:clamp(40px,6vw,72px);line-height:1.08;letter-spacing:-2.8px;max-width:800px;margin:22px 0}}.hero p{{max-width:680px;font-size:19px;color:#c8d8e4}}
.links{{display:flex;gap:16px;flex-wrap:wrap;margin-top:28px}}.pill{{padding:10px 20px;border-radius:6px;background:#73dece;color:#102c39;font-weight:700;text-decoration:none;font-size:14px}}.pill.secondary{{background:transparent;color:white;border:1px solid #5d788c}}
.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:24px;border-bottom:1px solid var(--line);padding:30px 0}}
.stats strong{{font-size:30px;display:block;letter-spacing:-1px}}.stats span{{font-size:13px;color:var(--muted)}}
main section{{padding:52px 0 28px}}h2{{font-size:32px;line-height:1.2;letter-spacing:-1px;margin:10px 0 20px}}h3{{font-size:19px;line-height:1.4}}.kicker{{font:12px ui-monospace,monospace;color:var(--teal);letter-spacing:1.7px;text-transform:uppercase}}
.lead{{font-size:18px;max-width:820px;color:var(--muted)}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;margin:32px 0}}
.card{{border:1px solid var(--line);border-top:3px solid var(--teal);padding:22px;border-radius:5px}}.card em{{font-style:normal;font:12px ui-monospace,monospace;color:var(--teal)}}.card p{{font-size:14px;color:var(--muted)}}
figure{{margin:28px 0}}img{{display:block;width:100%;height:auto;border:1px solid var(--line);border-radius:6px}}figcaption{{color:var(--muted);font-size:13px;margin-top:10px}}
.note{{background:var(--paper);border-left:3px solid var(--teal);padding:18px 24px;font-size:14px;margin:24px 0}}
.table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:5px;margin:20px 0}}table{{border-collapse:collapse;white-space:nowrap;width:100%;font-size:12px}}th,td{{padding:12px 14px;border-bottom:1px solid #e4eaed;text-align:left}}th{{background:var(--paper);font-weight:650}}tr:last-child td{{border:0}}
[role=tablist]{{display:flex;gap:8px;flex-wrap:wrap}}button{{cursor:pointer;border:1px solid var(--line);background:white;border-radius:5px;font:inherit;font-size:14px;padding:9px 18px;color:var(--ink)}}button[aria-selected=true]{{background:var(--ink);border-color:var(--ink);color:white}}.result-panel{{padding:20px 0 0}}.result-panel[hidden]{{display:none}}
pre{{background:var(--ink);color:#c6f6ec;overflow:auto;padding:24px;border-radius:6px;font:14px/1.8 ui-monospace,monospace}}.two{{display:grid;grid-template-columns:1fr 1fr;gap:36px}}
footer{{margin-top:56px;background:var(--paper);border-top:1px solid var(--line);padding:32px 0;font-size:13px;color:var(--muted)}}
@media(max-width:800px){{.cards{{grid-template-columns:repeat(2,1fr)}}.two{{grid-template-columns:1fr}}.wrap{{padding:0 20px}}.hero{{padding:48px 0}}.stats{{gap:12px}}.stats strong{{font-size:26px}}}}
@media(max-width:480px){{.cards{{grid-template-columns:1fr}}.stats{{grid-template-columns:repeat(2,1fr)}}nav a{{margin-left:10px}}h1{{letter-spacing:-1.6px}}}}
@media print{{header,.links,[role=tablist]{{display:none}}.hero{{background:white;color:var(--ink);padding:20px 0}}.hero p{{color:var(--muted)}}.result-panel[hidden]{{display:block}}figure,.card{{break-inside:avoid}}}}
</style></head><body>
<a class="skip" href="#main">Skip to content</a><header><nav class="wrap" aria-label="Main"><span class="wordmark">gridopt<b>.</b>lab</span><div><a href="#methods">Methods</a><a href="#results">Results</a><a href="#reproduce">Reproduce</a><a href="{REPO_URL}">GitHub ↗</a></div></nav></header>
<div class="hero"><div class="wrap"><span class="eyebrow">Open power systems research / v0.1</span><h1>Power systems.<br>Decisions, explained.</h1><p>Development of power system optimization algorithms, from hourly dispatch to long-term investment. Realistic U.S. benchmark data. Runnable models. Inspectable evidence.</p><div class="links"><a class="pill" href="{REPO_URL}">Explore the repository ↗</a><a class="pill secondary" href="#results">Read the experiments ↓</a></div></div></div>
<main id="main" class="wrap"><div class="stats" aria-label="Benchmark scale"><div><strong>73</strong><span>network buses</span></div><div><strong>120</strong><span>AC branches</span></div><div><strong>73</strong><span>thermal generators</span></div><div><strong>8,784</strong><span>hourly profiles · 2020</span></div></div>
<section id="methods"><span class="kicker">01 / The research stack</span><h2>Four decisions. One reproducible lab.</h2><p class="lead">The project combines established optimization techniques with empirical forecast calibration and explicit reference formulations. It proposes an integrated experimental workflow; it does not claim a new theorem or priority over the literature.</p>
<div class="cards"><article class="card"><em>01 / DISPATCH</em><h3>Price the tail risk.</h3><p>Co-optimize energy and upward reserves using expected exceedance and CVaR. Evaluate on the following seven days.</p></article><article class="card"><em>02 / COMMITMENT</em><h3>Schedule the fleet.</h3><p>A thermal MILP with startup costs, minimum on/off times, ramps and reserves calibrated from prior forecast errors.</p></article><article class="card"><em>03 / NETWORK</em><h3>Add limits as needed.</h3><p>DC-OPF constraint generation adds violated thermal limits, then validates all branches against a full formulation.</p></article><article class="card"><em>04 / EXPANSION</em><h3>Separate build and operate.</h3><p>Multicut Benders chooses continuous generation capacity under seasonal and demand-growth scenarios.</p></article></div>
<figure>{img("milp", "MILP illustration: continuous feasible polygon, integer points, fractional LP optimum, and the unit commitment branch-and-bound process.")}<figcaption>MILP connects continuous dispatch to discrete decisions. The left panel is a labeled toy example.</figcaption></figure>
<figure>{img("decomposition", "Benders decomposition flow: investment master sends capacity to twelve operating subproblems, whose LP duals return supporting cuts; upper and lower bounds converge.")}<figcaption>Every Benders bound comes from a solved optimization problem; the extensive LP supplies an independent reference formulation.</figcaption></figure></section>
<section id="results"><span class="kicker">02 / Evidence, with limits</span><h2>What the models actually found.</h2><div class="note">RTS-GMLC is a synthetic test system geographically assigned to the U.S. Southwest. Its load and renewable series model 2020. It is not a record of an actual utility's dispatch. Costs combine upstream fuel assumptions and 2024 EIA construction observations; scenario parameters are disclosed separately.</div>
<figure>{img("results-overview", "Four measured result panels: held-out ED reserve exceedance, summer UC reserve schedule, Benders bound convergence, and capacity builds at each tested carbon price.")}<figcaption>Reference experiments generated with SciPy {escape(metadata["scipy"])} and HiGHS. Numerical tables below give the actual values.</figcaption></figure>
<div class="two"><article><h3>Interpretation</h3>{paragraphs}</article><aside><h3>How to read the evidence</h3><p>ED exceedance is the amount by which a forecast error exceeds a purchased upward-reserve quantity. The experiment does not simulate reserve deployment or claim an outage probability.</p><p>UC reports a solver bound and actual relative MIP gap. OPF is lossless DC and excludes voltage, reactive power, contingencies and dynamic security.</p><p>Planning uses 12 scenarios: four fixed seasonal days crossed with three growth levels. Equal day weights sum to 8,760 annual hours. This demonstrates decomposition rather than a validated investment forecast.</p><p><a href="{REPO_URL}/blob/main/docs/formulations.md">Read the equations and assumptions ↗</a></p><p><a href="{REPO_URL}/tree/main/results/reference">Download CSV, JSON and run metadata ↗</a></p></aside></div>
<h3>Inspect the recorded metrics</h3><div role="tablist" aria-label="Optimization problem">{tabs}</div>{"".join(panels)}<noscript><style>.result-panel[hidden]{{display:block}}</style><p>All result tables are shown below; JavaScript adds tab switching.</p></noscript>
<figure>{img("network", "Geolocated RTS-GMLC network with branch color and width representing absolute flow divided by the stressed line rating.")}<figcaption>The 0.65 rating multiplier deliberately creates a constrained operating case. It is a scenario assumption.</figcaption></figure>
<figure>{img("commitment", "Summer load, renewable and net-load profiles above a heatmap of the 73 thermal units commitments, grouped by fuel.")}<figcaption>Summer commitment: one row per generator, with on/off decisions recorded alongside dispatch and reserves.</figcaption></figure></section>
<section id="reproduce"><span class="kicker">03 / Start here</span><h2>Run it. Inspect it. Extend it.</h2><p>The compact benchmark is included. No API key, commercial solver or data download is required for the experiments.</p>
<pre><code>git clone {REPO_URL}.git
cd gridopt-lab
python -m venv .venv
# Activate .venv for your operating system (see README).
python -m pip install -e ".[dev]"
gridopt validate
python -m pytest -q
gridopt run --output results/runs/my-run
gridopt report --input results/runs/my-run</code></pre>
<p><a href="{REPO_URL}/blob/main/docs/data.md">Data provenance</a> · <a href="{REPO_URL}/blob/main/docs/research.md">Research questions</a> · <a href="{REPO_URL}/blob/main/CONTRIBUTING.md">Contributing</a> · <a href="{REPO_URL}/blob/main/docs/references.bib">References</a></p></section></main>
<footer><div class="wrap">GridOpt Lab · Behnam Mohseni Gharyehsafa · MIT code license · RTS-GMLC data retain the upstream DOE/NREL/ALLIANCE notice. No endorsement is implied.<br>Run recorded {escape(metadata["generated_at_utc"])} · Source commit {escape(metadata["source_commit"][:12])} · Report embeds all figures and tables for offline reading.</div></footer>
<script>
const tabs=[...document.querySelectorAll('[role=tab]')];
function activate(i){{tabs.forEach((t,j)=>{{t.setAttribute('aria-selected',j===i?'true':'false');t.tabIndex=j===i?0:-1;document.getElementById(t.getAttribute('aria-controls')).hidden=j!==i}})}}
tabs.forEach((t,i)=>{{t.addEventListener('click',()=>activate(i));t.addEventListener('keydown',e=>{{let j=i;if(e.key==='ArrowRight')j=(i+1)%tabs.length;else if(e.key==='ArrowLeft')j=(i+tabs.length-1)%tabs.length;else if(e.key==='Home')j=0;else if(e.key==='End')j=tabs.length-1;else return;e.preventDefault();activate(j);tabs[j].focus()}})}});
</script></body></html>'''
    (root / "docs/index.html").write_text(html, encoding="utf-8")
    print(f"Report: {root / 'docs/index.html'}")
