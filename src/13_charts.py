#!/usr/bin/env python3
"""
Step 14 (Batch C) — Charts + per-chart data tables (verified real policy).

Produces 7 PNGs under charts/ and the matching underlying data table under
tables/ for each. Every chart plots ONLY data that already exists upstream
(data/processed/*.csv, tables/*.csv from Batches A+B) — no re-estimation of
causal exhibits. The corrected bids series (catA_bids_received_clean,
reconstructed from data/raw/coe_results_raw.csv by src/00_data.py) is used
everywhere the corrupted panel column would otherwise appear.

Honest-findings rule: the charts VISUALLY show the negative-control verdicts
(chart 2: 2022-01 market-wide shock, Cat C/D/E vs A, per scope) and the
bounded / associational nature of the headline estimates (charts 6, 7).
Nothing here is presented as a clean causal effect.

Layout (7 charts):
  01  Cat A price (nominal + real) with the REAL policy markers (2018-01,
      2021-01, 2024-01) + the 2022-01 97->110kW confounder marker.
  02  negative-control check: % price jump by category, per scope
      (2022-01 full window + 2024-01 EV era), with the verdict rows.
  03  EV registrations + EV share (descriptive; lower-bound note).
  04  dual-axis Cat A price vs CORRECTED Cat A bids received.
  05  price-vs-demand scatter with fitted line + 95% CI band.
  06  mediation path diagram with effect sizes for BOTH scopes (full window
      + 2022+ EV era).
  07  event-study coefficients with CIs for the 4 verified-policy events
      (2018-01, 2021-01, 2022-01, 2024-01); pre-trend contamination annotated.

Layering contract (read-only upstream):
  READS  data/processed/{panel_joint,cpi_deflated,ev_registrations}.csv,
         data/raw/coe_results_raw.csv (via the 00_data correction),
         tables/{negative_controls,event_study_coefficients,
                 event_study_prechecks,mediation_effects,
                 demand_bidding_channel,price_equation,
                 price_equation_2022plus_robustness,dose_summary,
                 rebate_timeline}.csv
  WRITES charts/01..07 PNGs + tables/chart01..chart07 CSVs
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
from matplotlib.transforms import blended_transform_factory
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
# Policy marker months (verified real Singapore policy); the 2022-01
# confounder is added separately in chart01.
POLICY_MARKS = ["2018-01", "2021-01", "2024-01"]


def _p(s: str) -> pd.Timestamp:
    return MONTH(s)


# ===========================================================================
# Chart 1 — Cat A clearing price (nominal + real) with REAL policy markers
#            and the Jan-2022 confounder (ARF floor + 97->110kW threshold).
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

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7))
    ax1.plot(df["ts"], df["nominal"], color="#1f4e79", lw=1.6,
             label="Cat A clearing price — nominal S$")
    ax1.set_ylabel("Nominal S$")
    ax1.set_title(
        "Chart 1 — Category A COE clearing price, 2016-01..2025-05 (verified policy)\n"
        "Dotted lines: EV-rebate changes.   Dashed red line: Jan 2022 tax + "
        "threshold change (not a rebate)",
        pad=12,
    )
    ax2.plot(df["ts"], df["real"], color="#b23b3b", lw=1.6,
             label="Cat A clearing price — real S$ (2024 base; CPI All Items)")
    ax2.set_ylabel("Real S$")
    ax2.set_xlabel("Month")

    # Headroom above the data line so the marker labels have their own band
    # and never touch (or get hidden behind) the price line.
    for ax, ycol in ((ax1, "nominal"), (ax2, "real")):
        ymin, ymax = df[ycol].min(), df[ycol].max()
        ax.set_ylim(ymin - 0.05 * (ymax - ymin), ymax * 1.18)
        for m in POLICY_MARKS:
            ax.axvline(_p(m), color="gray", ls=":", lw=1, alpha=0.8)
        # confounder marker (2022-01), emphasised
        ax.axvline(_p("2022-01"), color="#b23b3b", ls="--", lw=1.4, alpha=0.9)

    # Marker labels — top panel only (the lines continue on the bottom
    # panel). x in data units, y in axes fraction, staggered so no two
    # labels share a row.
    blend = blended_transform_factory(ax1.transData, ax1.transAxes)
    ax1.text(_p("2018-01"), 0.95, "Jan 2018 — VES starts (rebate ~S$25k)",
             transform=blend, fontsize=7.5, color="#444444", ha="left")
    ax1.text(_p("2024-01"), 0.95, "Jan 2024 — EEAI cap cut (rebate → S$40k)",
             transform=blend, fontsize=7.5, color="#444444", ha="right")
    ax1.text(_p("2021-01"), 0.87,
             "Jan 2021 — Enhanced VES + EEAI (rebate → S$45k)",
             transform=blend, fontsize=7.5, color="#444444", ha="left")
    ax1.annotate(
        "Jan 2022 — EV tax cut + engine-threshold change (not a rebate)",
        xy=(_p("2022-01"), 0.30 * ax1.get_ylim()[1]),
        xytext=(_p("2022-01"), 0.22),
        xycoords="data", textcoords=blend,
        fontsize=8, color="#b23b3b", ha="left",
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.9),
        arrowprops=dict(arrowstyle="->", color="#b23b3b", lw=1,
                        shrinkA=3, shrinkB=1),
    )
    ax1.legend(loc="lower left")
    ax2.legend(loc="lower right")
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
# Chart 2 — negative-control comparison: % price jump by category, per scope
#            (2022-01 full window + 2024-01 EV era), with the verdict rows.
# ===========================================================================
def chart02() -> None:
    panel = pd.read_csv(ROOT / "data/processed/panel_joint.csv")
    df = panel[["month", "catC_clearing_price", "catD_clearing_price",
                "catE_clearing_price"]].copy()
    df.to_csv(TABLES / "chart02_negative_controls.csv", index=False)

    nc = pd.read_csv(TABLES / "negative_controls.csv")
    colours = ["#1f4e79", "#8a8a8a", "#b23b3b", "#b23b3b", "#b23b3b"]
    labels = [
        "A (EV-eligible, MAIN)", "B (contaminated upper bound)",
        "C — CLEAN control (no EV rebate)", "D — CLEAN control (no EV rebate)",
        "E — CLEAN control (no EV rebate)",
    ]

    def nc_panel(ax, term, title):
        rows = [r for r in nc.itertuples()
                if str(r.term) == term and str(r.scope) == "full_window"
                and str(r.spec) == "dummy"]
        if not rows and term == "reg_eeai_cap15k_202401":
            rows = [r for r in nc.itertuples()
                    if str(r.term) == term and str(r.scope) == "ev_era_2022plus"
                    and str(r.spec) == "dummy"]
        cats = [r.category for r in rows]
        pcts = [r.coef_pct_of_mean for r in rows]
        ax.bar(cats, pcts, width=0.6, color=colours, alpha=0.85, zorder=3)
        ax.set_xticks(range(len(cats)), labels)
        ax.set_ylabel("% jump")
        ax.set_title(title, fontsize=10)
        for i, v in enumerate(pcts):
            ax.annotate(
                f"{v:+.1f}%", xy=(i, v),
                xytext=(0, 6 if v >= 0 else -14), textcoords="offset points",
                ha="center", fontsize=8.5,
            )

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 6.5))
    ax1.set_title(
        "Chart 2 — Negative-control check: % price jump by category\n"
        "2022-01 (full window; $0 ARF floor + 97->110kW threshold, market-wide) "
        "and 2024-01 (EV era; the pure EV-rebate variation)",
    )
    nc_panel(ax1, "reg_arffloor_zero_202201",
             "2022-01 price jump by category (full window)")
    nc_panel(ax2, "reg_eeai_cap15k_202401",
             "2024-01 EEAI cap-cut step by category (2022+ EV era, dose 45000->40000)")
    verdicts = []
    for line in (TABLES / "negative_controls.csv").read_text().splitlines():
        if line.startswith("# VERDICT"):
            verdicts.append(line)
    verdict_txt = "  ".join(v[len("# VERDICT "):] for v in verdicts)
    ax2.annotate(
        verdict_txt[:380],
        xy=(0.01, 0.02), xycoords="axes fraction", ha="left", va="bottom",
        fontsize=7.0, color="#222222",
        bbox=dict(boxstyle="round", fc="white", ec="#888888", alpha=0.95),
    )
    fig.tight_layout()
    fig.savefig(CHARTS / "02_negative_controls.png")
    plt.close(fig)
    print("[chart02] wrote charts/02_negative_controls.png + tables/chart02_negative_controls.csv")


# ===========================================================================
# Chart 3 — EV registrations + EV share, 2022-07..2025-05 (observed BEV window)
# ===========================================================================
def chart03() -> None:
    ev = pd.read_csv(TABLES / "ev_registrations_descriptive.csv")
    ev = ev[~ev["month"].astype(str).str.startswith("SUMMARY")].copy()
    ev = ev[ev["is_bev_observed"] == 1]
    ev["ts"] = ev["month"].map(_p)
    ev.to_csv(TABLES / "chart03_ev_demand.csv", index=False)

    fig, ax1 = plt.subplots(figsize=(11, 5))
    ax1.bar(ev["ts"], ev["ev_reg"], width=22, color="#2e7d32", alpha=0.85,
            label="EV (BEV) registrations — LOWER BOUND (right axis = left)")
    ax1.set_ylabel("EV registrations (per month)")
    ax1.set_title(
        "Chart 3 — EV registrations & EV share of registrations, 2022-07..2025-05\n"
        "DESCRIPTIVE ONLY — observed window: combined dose flat 45000 (2022-01..2023-12) "
        "then 40000 (2024-01+); series too short/censored for a coefficient; ev_reg is a lower bound",
    )
    ax2 = ax1.twinx()
    ax2.plot(ev["ts"], ev["ev_share"] * 100, color="#1f4e79", lw=1.8,
             marker="o", ms=3, label="EV share of registrations (%)")
    ax2.set_ylabel("EV share of registrations (%)")
    # mark the 2024-01 dose step
    ax1.axvline(_p("2024-01"), color="#b26a00", ls="--", lw=1.2, alpha=0.8)
    ax1.annotate("2024-01: EEAI cap 20k->15k (dose 45000->40000)",
                 xy=(_p("2024-02"), ax1.get_ylim()[1] * 0.97), fontsize=7.5,
                 color="#b26a00")
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
    fig.savefig(CHARTS / "03_ev_demand.png")
    plt.close(fig)
    print("[chart03] wrote charts/03_ev_demand.png + tables/chart03_ev_demand.csv")


# ===========================================================================
# Chart 4 — dual-axis Cat A price vs Cat A bids received (CORRECTED series)
# ===========================================================================
def chart04() -> None:
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
    df.to_csv(TABLES / "chart04_price_demand_dual.csv", index=False)

    fig, ax1 = plt.subplots(figsize=(11, 5.5))
    ax1.plot(df["ts"], df["nominal"], color="#1f4e79", lw=1.6,
             label="Cat A clearing price (nominal S$, left)")
    ax1.set_ylabel("Cat A clearing price (nominal S$)")
    ax1.set_title(
        "Chart 4 — Cat A clearing price vs Cat A bids received (CORRECTED bids series)\n"
        "Bids series = catA_bids_received_clean (reconstructed from raw; panel column "
        "was corrupted/zero for 19 months incl. all of 2023-10..2025-05)",
    )
    ax2 = ax1.twinx()
    ax2.plot(df["ts"], df["catA_bids_received_clean"], color="#b23b3b", lw=1.4,
             label="Cat A bids received (corrected, right)")
    ax2.set_ylabel("Cat A bids received")
    # shade the 2022+ EV era (also an ESTIMATION scope)
    ax1.axvspan(_p("2022-01"), df["ts"].max(), color="orange", alpha=0.07, zorder=0)
    ax1.axvline(_p("2024-01"), color="#b26a00", ls="--", lw=1.0, alpha=0.7)
    ax1.annotate(
        "2022-01+ EV era = ALSO an estimation scope\n"
        "(verified dose varies 45000->40000 at 2024-01)",
        xy=(_p("2022-05"), ax1.get_ylim()[1] * 0.97), fontsize=8, color="#b26a00",
    )
    ax1.legend(loc="upper left")
    ax2.legend(loc="lower right")
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax1.xaxis.set_major_locator(mdates.YearLocator())
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(CHARTS / "04_price_demand_dual.png")
    plt.close(fig)
    print("[chart04] wrote charts/04_price_demand_dual.png + tables/chart04_price_demand_dual.csv")


# ===========================================================================
# Chart 5 — price-vs-demand scatter with fitted line + 95% CI band
#          (bivariate descriptive fit on the CORRECTED series, 110 COE months)
# ===========================================================================
def chart05() -> None:
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
    with open(TABLES / "chart05_scatter_fit_ci.csv", "w") as fh:
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
        "Chart 5 — Cat A price vs demand: scatter + fitted line + 95% CI\n"
        "BIVARIATE association only (no controls); see the price equation for the "
        "demand term's own (lags, controls) significance",
    )
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(CHARTS / "05_scatter_fit_ci.png")
    plt.close(fig)
    print("[chart05] wrote charts/05_scatter_fit_ci.png + tables/chart05_scatter_fit_ci.csv")


# ===========================================================================
# Chart 6 — mediation path diagram with effect sizes (BOTH scopes)
# ===========================================================================
def chart06() -> None:
    med = pd.read_csv(TABLES / "mediation_effects.csv")
    # drop embedded comment/metadata rows (columns parsed as str because of them)
    med = med[med["effect"].astype(str).str.strip()
              .str.match(r"^(total|indirect|direct|mediated_share)$")].copy()
    for c in ("estimate", "ci_lo", "ci_hi"):
        med[c] = pd.to_numeric(med[c], errors="coerce")
    bid = pd.read_csv(TABLES / "demand_bidding_channel.csv")
    pe = pd.read_csv(TABLES / "price_equation.csv")
    pe22 = pd.read_csv(TABLES / "price_equation_2022plus_robustness.csv")
    med.to_csv(TABLES / "chart06_mediation_effects.csv", index=False)

    def get(df, term, spec=None, price_def=None, scope=None):
        sub = df[df["term"] == term]
        if spec:
            sub = sub[sub["spec"] == spec]
        if price_def:
            sub = sub[sub["price_def"] == price_def]
        if scope:
            sub = sub[sub["scope"] == scope]
        return sub.iloc[0]

    # full window: a = dose -> demand (bidding channel, dose spec),
    # b = demand_l1 -> price (M1 primary, nominal)
    a = get(bid, "dose_1000", spec="dose")
    a_hac = get(bid, "dose_1000", spec="dose_HAC")
    b = get(pe, "demand_l1", spec="M1_primary_lagged_dum", price_def="nominal")
    # EV era: E1 dose specs (price side in the 2022+ table)
    e1_bid = get(bid, "dose_1000", spec="E1_ev_era_dose")
    e1_price = get(pe22, "dose_1000", spec="E1_ev_era_lagged_dose", price_def="nominal")
    m_full = med[med["scope"] == "full_window"].set_index("effect")
    m_ev = med[med["scope"] == "ev_era_2022plus"].set_index("effect")

    fig, ax = plt.subplots(figsize=(12, 9))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title(
        "Chart 6 — Mediation path: rebate → Cat A bidding demand → Cat A price (BOTH scopes)\n"
        "Full window (primary; 2016-01..2025-05) AND 2022+ EV era (2022-01..2025-05; 41 obs; "
        "dose 45000->40000 at 2024-01 → estimable). Effect sizes copied from tables/.",
        fontsize=10,
    )

    def node(x, y, w, h, lab, color="#e8f0fe"):
        ax.add_patch(plt.Rectangle((x - w / 2, y - h / 2), w, h,
                                   fc=color, ec="#1f4e79", lw=1.5))
        ax.text(x, y, lab, ha="center", va="center", fontsize=8)

    def arrow(x1, y1, x2, y2, color):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2),
                                     arrowstyle="-|>", mutation_scale=18,
                                     lw=2, color=color))

    # --- FULL-WINDOW block (top) ---
    ax.text(5.0, 9.5, "FULL WINDOW (primary) — 2016-01..2025-05, ~109 obs, "
            "dose 20000/25000/45000/40000", ha="center", fontsize=9,
            fontweight="bold", color="#1f4e79")
    node(1.3, 7.6, 2.2, 1.8,
         "EV rebate\n(dose, S$)\n4 levels: 20k (CEVS est.),\n25k (VES), 45k (stack),\n40k (cap 15k)")
    node(5.0, 7.6, 2.3, 1.8,
         "Cat A bidding\ndemand\n(catA_bids_received_clean)\nTOTAL (non-EV-dominated)")
    node(8.7, 7.6, 2.0, 1.8, "Cat A COE\nclearing\nprice\n(nominal S$)")
    # a
    arrow(2.4, 8.0, 3.9, 8.0, "#b23b3b")
    ax.text(3.15, 8.45,
            f"a = {a['coef']:+.1f} bids/1000S$\n(HAC p={a_hac['p']:.3f}; "
            f"HC1 p={a['p']:.3f})",
            ha="center", fontsize=7.4, color="#b23b3b",
            bbox=dict(boxstyle="round", fc="white", ec="#b23b3b", alpha=0.9))
    # b
    arrow(6.15, 8.0, 7.7, 8.0, "#1f4e79")
    ax.text(6.95, 8.45,
            f"b = {b['coef']:+.2f} S$/bid (lag-1)\n[{b['ci_lo']:+.2f}, "
            f"{b['ci_hi']:+.2f}] p={b['p']:.3f}",
            ha="center", fontsize=7.4, color="#1f4e79",
            bbox=dict(boxstyle="round", fc="white", ec="#1f4e79", alpha=0.9))
    # total (top arrow)
    arrow(2.4, 8.5, 7.7, 8.5, "#2e7d32")
    ax.text(5.0, 8.95,
            f"TOTAL (full) = {m_full.loc['total','estimate']:+.0f} S$/1000S$ "
            f"[{m_full.loc['total','ci_lo']:+.0f}, {m_full.loc['total','ci_hi']:+.0f}]",
            ha="center", fontsize=8, color="#2e7d32",
            bbox=dict(boxstyle="round", fc="white", ec="#2e7d32", alpha=0.95))
    # direct (bottom arrow)
    arrow(2.4, 7.2, 7.7, 7.2, "gray")
    ax.text(5.0, 6.85,
            f"direct (full) = {m_full.loc['direct','estimate']:+.0f} S$/1000S$ "
            f"(point est.)",
            ha="center", fontsize=7.4, color="gray",
            bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=0.9))
    # verdict full
    ax.text(
        5.0, 6.35,
        f"MEDIATED SHARE (full) = {m_full.loc['mediated_share','estimate']:+.3f} "
        f"(CI95 [{m_full.loc['mediated_share','ci_lo']:+.3f}, "
        f"{m_full.loc['mediated_share','ci_hi']:+.3f}]); "
        f"indirect = {m_full.loc['indirect','estimate']:+.1f} "
        f"[{m_full.loc['indirect','ci_lo']:+.1f}, {m_full.loc['indirect','ci_hi']:+.1f}]. "
        "VERDICT: see report (CI spans 0 ⇒ NOT routed through bidding).",
        ha="center", fontsize=7.6, color="#b23b3b",
        bbox=dict(boxstyle="round", fc="#fff5f5", ec="#b23b3b", lw=1.5, alpha=0.97),
    )

    # --- EV-ERA block (bottom) ---
    ax.text(5.0, 5.6, "2022+ EV ERA — 2022-01..2025-05, 41 obs, dose 45000 -> 40000 "
            "at 2024-01 (estimable: 2 dose levels in window)",
            ha="center", fontsize=9, fontweight="bold", color="#b26a00")
    node(1.3, 3.7, 2.2, 1.8,
         "EV rebate\n(dose, S$)\n2 levels:\n45000 (2022-23),\n40000 (2024+)")
    node(5.0, 3.7, 2.3, 1.8,
         "Cat A bidding\ndemand\n(catA_bids_received_clean)\nTOTAL (non-EV-dominated)")
    node(8.7, 3.7, 2.0, 1.8, "Cat A COE\nclearing\nprice\n(nominal S$)")
    arrow(2.4, 4.1, 3.9, 4.1, "#b23b3b")
    ax.text(3.15, 4.55,
            f"a = {e1_bid['coef']:+.1f} bids/1000S$\n(p={e1_bid['p']:.3f})",
            ha="center", fontsize=7.4, color="#b23b3b",
            bbox=dict(boxstyle="round", fc="white", ec="#b23b3b", alpha=0.9))
    arrow(6.15, 4.1, 7.7, 4.1, "#1f4e79")
    ax.text(6.95, 4.55,
            f"dose->price (E1) = {e1_price['coef']:+.1f} S$/1000S$\n"
            f"[{e1_price['ci_lo']:+.1f}, {e1_price['ci_hi']:+.1f}] "
            f"p={e1_price['p']:.3f}",
            ha="center", fontsize=7.4, color="#1f4e79",
            bbox=dict(boxstyle="round", fc="white", ec="#1f4e79", alpha=0.9))
    arrow(2.4, 4.6, 7.7, 4.6, "#2e7d32")
    ax.text(5.0, 5.05,
            f"TOTAL (EV era) = {m_ev.loc['total','estimate']:+.0f} S$/1000S$ "
            f"[{m_ev.loc['total','ci_lo']:+.0f}, {m_ev.loc['total','ci_hi']:+.0f}]",
            ha="center", fontsize=8, color="#2e7d32",
            bbox=dict(boxstyle="round", fc="white", ec="#2e7d32", alpha=0.95))
    arrow(2.4, 3.3, 7.7, 3.3, "gray")
    ax.text(5.0, 2.95,
            f"direct (EV era) = {m_ev.loc['direct','estimate']:+.0f} S$/1000S$ "
            f"(point est.)",
            ha="center", fontsize=7.4, color="gray",
            bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=0.9))
    ax.text(
        5.0, 2.45,
        f"MEDIATED SHARE (EV era) = {m_ev.loc['mediated_share','estimate']:+.3f} "
        f"(CI95 [{m_ev.loc['mediated_share','ci_lo']:+.3f}, "
        f"{m_ev.loc['mediated_share','ci_hi']:+.3f}]); "
        f"indirect = {m_ev.loc['indirect','estimate']:+.1f} "
        f"[{m_ev.loc['indirect','ci_lo']:+.1f}, {m_ev.loc['indirect','ci_hi']:+.1f}]. "
        "41 obs, 2 dose levels → LOW POWER: wide CIs; associational, not causal.",
        ha="center", fontsize=7.6, color="#b26a00",
        bbox=dict(boxstyle="round", fc="#fffaf0", ec="#b26a00", lw=1.5, alpha=0.97),
    )
    fig.tight_layout()
    fig.savefig(CHARTS / "06_mediation_diagram.png")
    plt.close(fig)
    print("[chart06] wrote charts/06_mediation_diagram.png + tables/chart06_mediation_effects.csv")


# ===========================================================================
# Chart 7 — event-study coefficients with CIs (4 verified-policy events)
# ===========================================================================
def chart07() -> None:
    es = pd.read_csv(TABLES / "event_study_coefficients.csv")
    pre = pd.read_csv(TABLES / "event_study_prechecks.csv")
    es.to_csv(TABLES / "chart07_event_study.csv", index=False)

    # term -> integer x position (lead -k at -k, onset at 0, lag groups ordered)
    def xpos(term: str) -> int:
        if term.startswith("lead_-"):
            return -int(term.split("_")[-1])
        if term == "onset_0":
            return 0
        m = {
            "lag_1_6": 1, "lag_7_12": 4, "lag_13_plus": 8,
            "lag_1_12": 4, "lag_13_plus": 8,
            "lag_7_plus": 6,
        }
        return m.get(term, 1)

    episodes = [
        ("2018-01_cevs_lapse_VES_onset",
         "Event 1 — CEVS lapse / VES onset (2018-01): dose 20000 (CEVS est.) "
         "-> 25000 (VES A1, verified)"),
        ("2021-01_enhanced_VES_EEAI_stack",
         "Event 2 — Enhanced VES + EEAI (2021-01): dose 25000 -> 45000 "
         "(verified stack); EV-relevant from here on"),
        ("2022-01_ARF_floor_zero_PLUS_threshold_bounded",
         "Event 3 — $0 ARF floor (TAX; dose unchanged) + 97->110kW threshold "
         "(confounder) (2022-01) [COMBINED / BOUNDED]"),
        ("2024-01_eeai_cap15k_step",
         "Event 4 — EEAI cap cut 20k -> 15k (2024-01): dose 45000 -> 40000 "
         "(verified; the EV-era step)"),
    ]
    fig, axes = plt.subplots(4, 1, figsize=(11, 13), sharex=True)
    for ax, (ep, title) in zip(axes, episodes):
        sub = es[es["episode"] == ep].copy()
        sub["x"] = sub["term"].map(xpos)
        sub = sub.sort_values("x")
        for r in sub.itertuples():
            if r.role == "lead":
                c = "#b23b3b"   # contaminated pre-trend
            elif r.role == "onset":
                c = "#2e7d32"
            else:
                c = "#1f4e79"
            ax.errorbar(
                r.x, r.coef / 1000,
                yerr=[[r.coef / 1000 - r.ci_lo / 1000], [r.ci_hi / 1000 - r.coef / 1000]],
                fmt="o", color=c, ecolor=c, elinewidth=1.2, capsize=4, ms=5,
            )
            ax.annotate(
                f"{r.term}\np={r.p:.1e}", xy=(r.x, r.coef / 1000),
                xytext=(0, 12 if r.coef >= 0 else -18), textcoords="offset points",
                ha="center", fontsize=6.4, color=c,
            )
        ax.axhline(0, color="black", lw=0.8)
        ax.axvline(0, color="gray", ls="--", lw=1)
        ax.set_title(title, fontsize=9.5)
        ax.set_ylabel("coef (S$ thousands)")

    # pre-trend verdicts (from prechecks, verbatim) — annotate each panel
    for ax, (ep, _title) in zip(axes, episodes):
        p = pre[pre["episode"] == ep]
        if not len(p):
            continue
        p = p.iloc[0]
        onset = es[(es["episode"] == ep) & (es["term"] == "onset_0")]
        onset_txt = ""
        if len(onset):
            o = onset.iloc[0]
            onset_txt = (f" onset {o['coef']/1000:+.1f}k S$ "
                         f"[{o['ci_lo']/1000:+.1f}k, {o['ci_hi']/1000:+.1f}k]")
        ax.annotate(
            f"pre_trend_clean={p['pre_trend_clean']}{onset_txt}; "
            + p["pre_trend_interpretation"][:120],
            xy=(0.99, 0.03), xycoords="axes fraction", ha="right", va="bottom",
            fontsize=7.4,
            color="#b23b3b" if not p["pre_trend_clean"] else "#2e7d32",
            bbox=dict(boxstyle="round", fc="white",
                      ec="#b23b3b" if not p["pre_trend_clean"] else "#2e7d32",
                      alpha=0.95),
        )
    axes[-1].set_xlabel("Relative month to onset (leads < 0 = before, 0 = onset, lags > 0 = after)")
    fig.tight_layout()
    fig.savefig(CHARTS / "07_event_study.png")
    plt.close(fig)
    print("[chart07] wrote charts/07_event_study.png + tables/chart07_event_study.csv")


def main() -> None:
    chart01()
    chart02()
    chart03()
    chart04()
    chart05()
    chart06()
    chart07()
    print("[charts] all 7 charts written.")


if __name__ == "__main__":
    main()
