#!/usr/bin/env python3
"""
Step 14 (Batch C) — Charts + per-chart data tables.

Produces 6 PNGs under charts/ and the matching underlying data table under
tables/ for each. Every chart plots ONLY data that already exists upstream
(data/processed/*.csv, tables/*.csv from Batches A+B) — no re-estimation of
causal exhibits. The corrected bids series (catA_bids_received_clean,
reconstructed from data/raw/coe_results_raw.csv by src/00_data.py) is used
everywhere the corrupted panel column would otherwise appear.

Honest-findings rule: the charts VISUALLY show the negative-control failure
(chart 1: market-wide 2022-01 shock, Cat C/D/E vs A) and the bounded /
associational nature of the headline estimates (charts 5, 6). Nothing here is
presented as a clean causal effect.

Layering contract (read-only upstream):
  READS  data/processed/{panel_joint,cpi_deflated,ev_registrations}.csv,
         data/raw/coe_results_raw.csv (via the 00_data correction),
         tables/{negative_controls,event_study_coefficients,
                 event_study_prechecks,mediation_effects,
                 demand_bidding_channel,price_equation,dose_summary,
                 rebate_timeline}.csv
  WRITES charts/01..06 PNGs + tables/chart01..chart06 CSVs
  (writes NOTHING to data/ or to any earlier batch's file).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import FancyArrowPatch
from statsmodels.stats.api import anova_lm  # noqa: F401  (band via OLS below)

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
TABLES = ROOT / "tables"
CHARTS = ROOT / "charts"
CHARTS.mkdir(exist_ok=True)

# load the shared data layer (00_data.py) by path — it provides the corrected
# bid-count columns without writing anything to disk.
_spec = importlib.util.spec_from_file_location("_data_layer", SRC / "00_data.py")
D = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(D)

plt.rcParams.update(
    {
        "figure.dpi": 110,
        "font.size": 9,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
    }
)

MONTH = lambda s: pd.Period(s, freq="M").to_timestamp()  # noqa: E731
REGIME_MARKS = [
    ("2016-11", "CEVS uplift\n(plan; not corroborated as a step)"),
    ("2018-01", "CEVS lapse\n(corroborated: ran thru 2017)"),
    ("2018-09", "VES 'revival'\n(plan; VES actually from 2018-01)"),
    ("2022-01", "EEAI/45% ARF rebate\n($7,500 anchor; real policy differs)"),
]


def _p(s: str) -> pd.Timestamp:
    return MONTH(s)


# ===========================================================================
# Chart 1 — Cat A clearing price (nominal + real) with regime + confounder
#            markers, and the negative-control (C/D/E vs A) comparison.
# ===========================================================================
def chart01() -> None:
    panel = pd.read_csv(ROOT / "data/processed/panel_joint.csv")
    cpi = pd.read_csv(ROOT / "data/processed/cpi_deflated.csv").set_index("month")
    df = panel[["month"]].copy()
    df["nominal"] = cpi.reindex(df["month"])["catA_clearing_price"].to_numpy()
    df["real"] = cpi.reindex(df["month"])["catA_clearing_price_real"].to_numpy()
    df["catC"] = panel["catC_clearing_price"]
    df["catD"] = panel["catD_clearing_price"]
    df["catE"] = panel["catE_clearing_price"]
    df["ts"] = df["month"].map(_p)
    df = df[df["nominal"].notna()]  # drop 3 pandemic months
    df.to_csv(TABLES / "chart01_price_regime.csv", index=False)

    fig, (ax1, ax2, ax3) = plt.subplots(
        3, 1, figsize=(11, 9), sharex=False,
        gridspec_kw={"height_ratios": [1, 1, 0.8]},
    )
    ax1.plot(df["ts"], df["nominal"], color="#1f4e79", lw=1.6,
             label="Cat A clearing price — nominal S$ (left)")
    ax1.set_ylabel("Nominal S$")
    ax1.set_title(
        "Chart 1 — Category A COE clearing price, 2016-01..2025-05\n"
        "Regime step markers + Jan-2022 confounder; 2022-01 shock is MARKET-WIDE "
        "(negative-control FAIL)",
    )
    ax2.plot(df["ts"], df["real"], color="#b23b3b", lw=1.6,
             label="Cat A clearing price — real S$ (2024 base; CPI All Items)")
    ax2.set_ylabel("Real S$")
    ax2.set_xlabel("Month")

    for ax in (ax1, ax2):
        for m, lab in REGIME_MARKS:
            x = _p(m)
            ax.axvline(x, color="gray", ls=":", lw=1, alpha=0.8)
        # confounder marker, emphasised
        x = _p("2022-01")
        ax.axvline(x, color="#b23b3b", ls="--", lw=1.4, alpha=0.9)
        ax.annotate(
            "CONFUNDER: 97→110kW Cat A threshold change,\nco-timed 2022-01 (market-wide)",
            xy=(x, ax.get_ylim()[1] * 0.97), xytext=(x, ax.get_ylim()[1] * 0.88),
            fontsize=8, color="#b23b3b",
            arrowprops=dict(arrowstyle="->", color="#b23b3b", lw=1),
            ha="left",
        )
    ax1.legend(loc="upper left")
    ax2.legend(loc="upper left")

    # --- negative-control comparison: % 2022-01 jump per category (dedicated panel) ---
    nc = pd.read_csv(TABLES / "negative_controls.csv")
    rows = [r for r in nc.itertuples() if str(r.term) == "reg_eeai_202201"]
    cats = [r.category for r in rows]
    pcts = [r.coef_pct_of_mean for r in rows]
    colours = ["#1f4e79", "#8a8a8a", "#b23b3b", "#b23b3b", "#b23b3b"]
    labels = [
        "A (EV-eligible, MAIN)", "B (contaminated upper bound)",
        "C — CLEAN control (no EV rebate)", "D — CLEAN control (no EV rebate)",
        "E — CLEAN control (no EV rebate)",
    ]
    ax3.bar(cats, pcts, width=0.6, color=colours, alpha=0.85, zorder=3)
    ax3.set_xticks(range(len(cats)), labels)
    ax3.set_ylabel("% 2022-01 jump")
    ax3.set_title("Negative-control check — 2022-01 price jump by category (from negative_controls.csv)")
    for i, v in enumerate(pcts):
        ax3.annotate(
            f"{v:+.1f}%", xy=(i, v),
            xytext=(0, 6 if v >= 0 else -14), textcoords="offset points",
            ha="center", fontsize=8.5,
        )
    ax3.annotate(
        "NEGATIVE-CONTROL FAIL:\nclean controls C/D/E show the SAME or LARGER\n"
        "2022-01 jump (13.7 / 41.8 / 36.4%) vs A (10.1%)\n→ market-wide common shock, "
        "NOT an EV-rebate-specific effect",
        xy=(0.01, 0.03), xycoords="axes fraction", ha="left", va="bottom",
        fontsize=8.5, color="#b23b3b",
        bbox=dict(boxstyle="round", fc="white", ec="#b23b3b", alpha=0.95),
    )
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax1.xaxis.set_major_locator(mdates.YearLocator())
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax2.xaxis.set_major_locator(mdates.YearLocator())
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(CHARTS / "01_price_regime.png")
    plt.close(fig)
    print("[chart01] wrote charts/01_price_regime.png + tables/chart01_price_regime.csv")


# ===========================================================================
# Chart 2 — EV registrations + EV share, 2022-07..2025-05 (observed BEV window)
# ===========================================================================
def chart02() -> None:
    ev = pd.read_csv(TABLES / "ev_registrations_descriptive.csv")
    ev = ev[~ev["month"].astype(str).str.startswith("SUMMARY")].copy()
    ev = ev[ev["is_bev_observed"] == 1]
    ev["ts"] = ev["month"].map(_p)
    ev.to_csv(TABLES / "chart02_ev_demand.csv", index=False)

    fig, ax1 = plt.subplots(figsize=(11, 5))
    ax1.bar(ev["ts"], ev["ev_reg"], width=22, color="#2e7d32", alpha=0.85,
            label="EV (BEV) registrations — LOWER BOUND (right axis = left)")
    ax1.set_ylabel("EV registrations (per month)")
    ax1.set_title(
        "Chart 2 — EV registrations & EV share of registrations, 2022-07..2025-05\n"
        "DESCRIPTIVE ONLY — no within-window rebate variation (EEAI constant); "
        "ev_reg is a lower bound",
    )
    ax2 = ax1.twinx()
    ax2.plot(ev["ts"], ev["ev_share"] * 100, color="#1f4e79", lw=1.8,
             marker="o", ms=3, label="EV share of registrations (%)")
    ax2.set_ylabel("EV share of registrations (%)")
    ax1.legend(loc="upper left")
    ax2.legend(loc="center left")
    # coverage lower-bound note
    cov = ev["coverage_rate"]
    ax1.annotate(
        f"coverage_rate (share of raw rows with an observed count) decays "
        f"{cov.min()*100:.0f}% → {cov.max()*100:.0f}% over the window "
        f"(mean {cov.mean()*100:.0f}%) ⇒ ev_reg is a LOWER BOUND that weakens over time.\n"
        "First BEV label appears 2022-07; the series is right-truncated at 2025-05 "
        "(joint window end).",
        xy=(0.99, 0.98), xycoords="axes fraction", ha="right", va="top", fontsize=8,
        bbox=dict(boxstyle="round", fc="#f5f5f5", ec="gray", alpha=0.95),
    )
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 7)))
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(CHARTS / "02_ev_demand.png")
    plt.close(fig)
    print("[chart02] wrote charts/02_ev_demand.png + tables/chart02_ev_demand.csv")


# ===========================================================================
# Chart 3 — dual-axis Cat A price vs Cat A bids received (CORRECTED series)
# ===========================================================================
def chart03() -> None:
    frame = D.load_estimation_frame()
    panel = pd.read_csv(ROOT / "data/processed/panel_joint.csv")
    df = frame[frame["n_obs"] == 1].copy()  # 110 COE months
    df["nominal"] = (
        panel.set_index("month").reindex(df["month"])["catA_clearing_price"].to_numpy()
    )
    df = df[
        ["month", "catA_bids_received_clean", "nominal", "in_interpretation_window"]
    ].copy()
    df["ts"] = df["month"].map(_p)
    df["series"] = "corrected"
    df.to_csv(TABLES / "chart03_price_demand_dual.csv", index=False)

    fig, ax1 = plt.subplots(figsize=(11, 5.5))
    ax1.plot(df["ts"], df["nominal"], color="#1f4e79", lw=1.6,
             label="Cat A clearing price (nominal S$, left)")
    ax1.set_ylabel("Cat A clearing price (nominal S$)")
    ax1.set_title(
        "Chart 3 — Cat A clearing price vs Cat A bids received (CORRECTED bids series)\n"
        "Bids series = catA_bids_received_clean (reconstructed from raw; panel column "
        "was corrupted/zero for 19 months incl. all of 2023-10..2025-05)",
    )
    ax2 = ax1.twinx()
    ax2.plot(df["ts"], df["catA_bids_received_clean"], color="#b23b3b", lw=1.4,
             label="Cat A bids received (corrected, right)")
    ax2.set_ylabel("Cat A bids received")
    # shade the 2022+ interpretation window
    ax1.axvspan(_p("2022-01"), df["ts"].max(), color="orange", alpha=0.07, zorder=0)
    ax1.annotate(
        "2022-01 EV-relevant\ninterpretation window",
        xy=(_p("2022-06"), ax1.get_ylim()[1] * 0.97), fontsize=8, color="#b26a00",
    )
    ax1.legend(loc="upper left")
    ax2.legend(loc="lower right")
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax1.xaxis.set_major_locator(mdates.YearLocator())
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(CHARTS / "03_price_demand_dual.png")
    plt.close(fig)
    print("[chart03] wrote charts/03_price_demand_dual.png + tables/chart03_price_demand_dual.csv")


# ===========================================================================
# Chart 4 — price-vs-demand scatter with fitted line + 95% CI band
#          (bivariate descriptive fit on the CORRECTED series, 110 COE months)
# ===========================================================================
def chart04() -> None:
    import statsmodels.api as sm

    frame = D.load_estimation_frame()
    panel = pd.read_csv(ROOT / "data/processed/panel_joint.csv")
    df = frame[frame["n_obs"] == 1].copy()
    df["price"] = (
        panel.set_index("month").reindex(df["month"])["catA_clearing_price"].to_numpy()
    )
    df = df[["month", "catA_bids_received_clean", "price"]].dropna().reset_index(drop=True)
    df["x"] = df["catA_bids_received_clean"]
    X = sm.add_constant(df["x"])
    res = sm.OLS(df["price"], X).fit(cov_type="HC1")
    # 95% CI for the MEAN response on a dense x-grid
    grid = np.linspace(df["x"].min(), df["x"].max(), 400)
    Xg = sm.add_constant(pd.Series(grid))
    fit = res.get_prediction(Xg)
    pf = fit.summary_frame(alpha=0.05)
    mean = pf["mean"].to_numpy()
    lo = pf["mean_ci_lower"].to_numpy()
    hi = pf["mean_ci_upper"].to_numpy()

    out = pd.DataFrame(
        {
            "x_bids_received": grid,
            "fitted_price": mean,
            "ci95_lo": lo,
            "ci95_hi": hi,
        }
    )
    meta = pd.DataFrame(
        [
            {"item": "n_obs", "value": int(len(df))},
            {"item": "slope_per_bid", "value": float(res.params["x"])},
            {
                "item": "slope_ci95_lo",
                "value": float(res.conf_int().loc["x", 0]),
            },
            {
                "item": "slope_ci95_hi",
                "value": float(res.conf_int().loc["x", 1]),
            },
            {"item": "slope_p", "value": float(res.pvalues["x"])},
            {
                "item": "note",
                "value": (
                    "BIVARIATE descriptive fit (price ~ bids_received) on the CORRECTED "
                    "series, 110 COE months, HC1 SEs. NOT a causal exhibit; no regime "
                    "dummies / trend / controls. Association only."
                ),
            },
        ]
    )
    with open(TABLES / "chart04_scatter_fit_ci.csv", "w") as fh:
        out.to_csv(fh, index=False)
        fh.write("\n# --- fit metadata ---\n")
        meta.to_csv(fh, index=False)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(df["x"], df["price"], s=18, alpha=0.55, color="#1f4e79",
               label="monthly obs (2016-01..2025-05, n=110)")
    ax.plot(grid, mean, color="#b23b3b", lw=2,
            label=f"OLS fit: slope={res.params['x']:.2f} S$/bid "
                  f"(CI95 [{res.conf_int().loc['x',0]:.2f}, {res.conf_int().loc['x',1]:.2f}])")
    ax.fill_between(grid, lo, hi, color="#b23b3b", alpha=0.15,
                    label="95% CI for the mean response")
    ax.set_xlabel("Cat A bids received (CORRECTED series)")
    ax.set_ylabel("Cat A clearing price (nominal S$)")
    ax.set_title(
        "Chart 4 — Cat A price vs demand: scatter + fitted line + 95% CI\n"
        "BIVARIATE association only (no controls); price equation's own demand "
        "regressor is lagged & not significant (demand_l1 p=0.225)",
    )
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(CHARTS / "04_scatter_fit_ci.png")
    plt.close(fig)
    print("[chart04] wrote charts/04_scatter_fit_ci.png + tables/chart04_scatter_fit_ci.csv")


# ===========================================================================
# Chart 5 — event-study coefficients with CIs (episode structure per Batch B)
# ===========================================================================
def chart05() -> None:
    es = pd.read_csv(TABLES / "event_study_coefficients.csv")
    pre = pd.read_csv(TABLES / "event_study_prechecks.csv")
    es.to_csv(TABLES / "chart05_event_study.csv", index=False)

    # term -> integer x position (lead -k at -k, onset at 0, lag groups ordered)
    def xpos(term: str) -> int:
        if term.startswith("lead_-"):
            return -int(term.split("_")[-1])
        if term == "onset_0":
            return 0
        # lag groups
        m = {
            "lag_1_9": 1, "lag_10_22": 4, "lag_23_plus": 8,
            "lag_1_6": 1, "lag_7_17": 4, "lag_18_plus": 9,
        }
        return m[term]

    episodes = [
        ("2016-2018_episode_total_low_emission",
         "Episode 1 — TOTAL/low-emission demand (2016-11 onset)\n[NOT EV-specific]"),
        ("2022-01_eeai_rebate_PLUS_threshold_bounded",
         "Episode 2 — EEAI rebate + 97→110kW threshold (2022-01 onset)\n[COMBINED / BOUNDED — co-timed confounder]"),
    ]
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
    for ax, (ep, title) in zip(axes, episodes):
        sub = es[es["episode"] == ep].copy()
        sub["x"] = sub["term"].map(xpos)
        sub = sub.sort_values("x")
        cols = []
        for r in sub.itertuples():
            if r.role == "lead":
                c = "#b23b3b"   # contaminated pre-trend
            elif r.role == "onset":
                c = "#2e7d32"
            else:
                c = "#1f4e79"
            cols.append(c)
            ax.errorbar(
                r.x, r.coef / 1000,
                yerr=[[r.coef / 1000 - r.ci_lo / 1000], [r.ci_hi / 1000 - r.coef / 1000]],
                fmt="o", color=c, ecolor=c, elinewidth=1.2, capsize=4, ms=5,
            )
            ax.annotate(
                f"{r.term}\np={r.p:.1e}", xy=(r.x, r.coef / 1000),
                xytext=(0, 12 if r.coef >= 0 else -18), textcoords="offset points",
                ha="center", fontsize=6.6, color=c,
            )
        ax.axhline(0, color="black", lw=0.8)
        ax.axvline(0, color="gray", ls="--", lw=1)
        ax.set_title(title, fontsize=9.5)
        ax.set_ylabel("coef (S$ thousands)")

    # pre-trend contamination verdict (from prechecks + onset coef, verbatim)
    onset22 = es[(es["episode"] == "2022-01_eeai_rebate_PLUS_threshold_bounded")
                 & (es["term"] == "onset_0")].iloc[0]
    p22 = pre[pre["episode"] == "2022-01_eeai_rebate_PLUS_threshold_bounded"].iloc[0]
    axes[-1].annotate(
        f"PRE-TREND CONTAMINATED (pre_trend_clean={p22['pre_trend_clean']}; leads ≠ 0; "
        "a secular COE trend is present) ⇒ the 2022-01 "
        f"onset +{onset22['coef']/1000:.1f}k S$ [CI95 {onset22['ci_lo']/1000:.1f}k, "
        f"{onset22['ci_hi']/1000:.1f}k] is co-timed with the 97→110kW threshold change: "
        "a BOUND, not a clean causal jump. Reported honestly.",
        xy=(0.99, 0.03), xycoords="axes fraction", ha="right", va="bottom", fontsize=8,
        color="#b23b3b",
        bbox=dict(boxstyle="round", fc="white", ec="#b23b3b", alpha=0.95),
    )
    axes[0].annotate(
        "CONTAMINATED pre-trend (leads significant & non-zero) ⇒ onset effect is a "
        "BOUND relative to a moving pre-trend. Reported honestly.",
        xy=(0.99, 0.04), xycoords="axes fraction", ha="right", va="bottom", fontsize=8,
        color="#b23b3b",
        bbox=dict(boxstyle="round", fc="white", ec="#b23b3b", alpha=0.95),
    )
    axes[-1].set_xlabel("Relative month to onset (leads < 0 = before, 0 = onset, lags > 0 = after)")
    fig.tight_layout()
    fig.savefig(CHARTS / "05_event_study.png")
    plt.close(fig)
    print("[chart05] wrote charts/05_event_study.png + tables/chart05_event_study.csv")


# ===========================================================================
# Chart 6 — mediation path diagram with effect sizes (numbers from tables)
# ===========================================================================
def chart06() -> None:
    med = pd.read_csv(TABLES / "mediation_effects.csv")
    # drop embedded comment/metadata rows (columns parsed as str because of them)
    med = med[med["effect"].astype(str).str.strip().str.match(r"^(total|indirect|direct|mediated_share)$")].copy()
    for c in ("estimate", "ci_lo", "ci_hi"):
        med[c] = pd.to_numeric(med[c], errors="coerce")
    bid = pd.read_csv(TABLES / "demand_bidding_channel.csv")
    pe = pd.read_csv(TABLES / "price_equation.csv")
    med.to_csv(TABLES / "chart06_mediation_effects.csv", index=False)

    def get(df, term, spec=None, price_def=None):
        sub = df[df["term"] == term]
        if spec:
            sub = sub[sub["spec"] == spec]
        if price_def:
            sub = sub[sub["price_def"] == price_def]
        return sub.iloc[0]

    a = get(bid, "reg_eeai_202201", spec="dummy")            # rebate -> demand (HC1)
    a_hac = get(bid, "reg_eeai_202201", spec="dummy_HAC")    # same, HAC SEs
    dose_a = get(bid, "dose_1000", spec="dose")
    b = get(pe, "demand_l1", spec="M1_primary_lagged_dum", price_def="nominal")
    total = med[med["effect"] == "total"].iloc[0]
    indirect = med[med["effect"] == "indirect"].iloc[0]
    direct = med[med["effect"] == "direct"].iloc[0]
    share = med[med["effect"] == "mediated_share"].iloc[0]

    fig, ax = plt.subplots(figsize=(11, 6.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")
    ax.set_title(
        "Chart 6 — Mediation path: rebate → Cat A bidding demand → Cat A price\n"
        "Full-window estimable scope 2016-01..2025-05; headline read = 2022+ interpretation "
        "(NEVER a 2022+-only estimate). Effect sizes copied from tables/.",
        fontsize=10,
    )

    # nodes
    nodes = {
        "rebate": (1.2, 3.5, "EV rebate\n(dose, S$)\n4 regime steps;\ndose flat 7500\n2022-01..2025-05"),
        "demand": (5.0, 3.5, "Cat A bidding\ndemand\n(catA_bids_received_clean)\nTOTAL (non-EV-dominated)"),
        "price": (8.8, 3.5, "Cat A COE\nclearing\nprice\n(nominal S$)"),
    }
    for k, (x, y, lab) in nodes.items():
        ax.add_patch(plt.Rectangle((x - 1.15, y - 1.0), 2.3, 2.0,
                                   fc="#e8f0fe", ec="#1f4e79", lw=1.5))
        ax.text(x, y, lab, ha="center", va="center", fontsize=8)

    def arrow(x1, y1, x2, y2, color):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2),
                                     arrowstyle="-|>", mutation_scale=18,
                                     lw=2, color=color))

    # a: rebate -> demand (mediator path)
    arrow(2.35, 4.2, 3.85, 4.2, "#b23b3b")
    ax.text(3.1, 4.55,
            f"a = {a['coef']:+.0f} bids\n(dose/1000: {dose_a['coef']:+.1f} bids)\n"
            f"HAC p={a_hac['p']:.3f} → NOT robust (HC1 p={a['p']:.3f})",
            ha="center", fontsize=8, color="#b23b3b",
            bbox=dict(boxstyle="round", fc="white", ec="#b23b3b", alpha=0.9))
    # b: demand -> price
    arrow(6.15, 4.2, 7.65, 4.2, "#1f4e79")
    ax.text(6.9, 4.55,
            f"b = {b['coef']:+.2f} S$/bid (lag-1)\nCI95 [{b['ci_lo']:.2f}, {b['ci_hi']:.2f}]\n"
            f"p={b['p']:.3f} → not significant",
            ha="center", fontsize=8, color="#1f4e79",
            bbox=dict(boxstyle="round", fc="white", ec="#1f4e79", alpha=0.9))
    # total: rebate -> price (direct, top)
    arrow(2.35, 4.7, 7.65, 4.7, "#2e7d32")
    ax.text(5.0, 5.15,
            f"TOTAL (rebate → price) = {total['estimate']:+.0f} S$/1000S$ dose\n"
            f"CI95 [{total['ci_lo']:+.0f}, {total['ci_hi']:+.0f}]  "
            f"(indirect CI [{indirect['ci_lo']:+.0f}, {indirect['ci_hi']:+.0f}])",
            ha="center", fontsize=9, color="#2e7d32",
            bbox=dict(boxstyle="round", fc="white", ec="#2e7d32", alpha=0.95))
    # direct (holding demand fixed), bottom
    arrow(2.35, 2.6, 7.65, 2.6, "gray")
    ax.text(5.0, 2.15,
            f"direct (holding demand fixed) = {direct['estimate']:+.0f} S$/1000S$ "
            f"(point estimate)",
            ha="center", fontsize=8, color="gray",
            bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=0.9))
    # mediated share verdict
    ax.text(
        5.0, 0.75,
        f"MEDIATED SHARE (indirect/total) = {share['estimate']:+.3f}  "
        f"(CI95 [{share['ci_lo']:+.3f}, {share['ci_hi']:+.3f}]) → CI spans 0.\n"
        "VERDICT: the price effect is NOT routed through Cat A bidding demand "
        "(bidding-channel mediation is NULL). Grade: not detectable.",
        ha="center", fontsize=9, color="#b23b3b",
        bbox=dict(boxstyle="round", fc="#fff5f5", ec="#b23b3b", lw=1.5, alpha=0.97),
    )
    fig.tight_layout()
    fig.savefig(CHARTS / "06_mediation_diagram.png")
    plt.close(fig)
    print("[chart06] wrote charts/06_mediation_diagram.png + tables/chart06_mediation_effects.csv")


def main() -> None:
    chart01()
    chart02()
    chart03()
    chart04()
    chart05()
    chart06()
    print("[charts] all 6 charts written.")


if __name__ == "__main__":
    main()
