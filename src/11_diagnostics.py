#!/usr/bin/env python3
"""
Step 12 — diagnostics: negative controls, stationarity, residual
autocorrelation, and sensitivity.

Outputs:
    tables/negative_controls.csv                 (price equation re-run on the
                                                 clean controls C, D, E --
                                                 expect ~zero rebate effect --
                                                 and B, the contaminated upper
                                                 bound where high-power EVs sit)
    tables/diagnostics_stationarity_autocorr.csv (ADF on levels vs first
                                                 differences; residual
                                                 autocorrelation: Durbin-Watson,
                                                 Ljung-Box, Breusch-Godfrey on
                                                 the primary price equation)
    tables/sensitivity_analysis.csv              (drop-one confounder
                                                 re-estimation; alternative
                                                 demand definitions
                                                 bids_received vs bids_success;
                                                 lag-order variants)

Negative-control taxonomy (per the saturated Dory spec):
    * C, D, E = CLEAN negative controls (goods, large-goods, motorcycles).
      The EV rebate does not apply to these, so a well-specified model must
      show a ~ZERO rebate coefficient here. A non-zero rebate effect on a
      clean control would indicate the "effect" is a data artifact (the trend,
      the quota, the corruption) rather than a genuine rebate channel.
    * B = CONTAMINATED upper bound: high-power EVs fall in Cat B, so B is
      allowed to show a (bounded, upper) rebate effect.
    * A = the main effect category (low-power cars; the EV-relevant one).

All controls use the CORRECTED per-category bid counts (see 00_data.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bootstrap as B  # noqa: E402

from statsmodels.tsa.stattools import adfuller  # noqa: E402
from statsmodels.stats.diagnostic import (  # noqa: E402
    acorr_ljungbox, acorr_breusch_godfrey,
)
from statsmodels.stats.stattools import durbin_watson  # noqa: E402

D = B.D
OUT_DIR = D.ROOT / "tables"
OUT_NC = OUT_DIR / "negative_controls.csv"
OUT_DIAG = OUT_DIR / "diagnostics_stationarity_autocorr.csv"
OUT_SENS = OUT_DIR / "sensitivity_analysis.csv"

REGIME_DUMMIES = [
    "reg_cevs_uplift_201611", "reg_cevs_lapse_201801",
    "reg_ves_revival_201809", "reg_eeai_202201",
]
CONTROLS = ["catA_quota", "trend", "cpi_all_items"]

NC_TAXONOMY = {
    "A": "MAIN effect (low-power cars; EV-relevant)",
    "B": "CONTAMINATED upper bound (high-power EVs fall here)",
    "C": "CLEAN negative control (goods vehicles; no EV rebate)",
    "D": "CLEAN negative control (large goods; no EV rebate)",
    "E": "CLEAN negative control (motorcycles; no EV rebate)",
}


def build():
    frame = D.load_estimation_frame()
    sample = D.listwise_sample(frame)
    return frame, sample


def _price_spec_for_cat(df, K, price_def="nominal"):
    """The price-equation structure re-aimed at category K. Demand regressor is
    K's own (corrected) bids_received; quota is K's quota; the 4 regime dummies
    + continuous dose are the rebate intensity terms. threshold_dummy is NOT
    added (identical to reg_eeai_202201)."""
    price = (f"cat{K}_clearing_price_real"
             if price_def == "real" else f"cat{K}_clearing_price")
    demand = df[f"cat{K}_bids_received_clean"]
    out = df.copy()
    out["demand_l1"] = D.lag(demand, 1)
    out["demand_l2"] = D.lag(demand, 2)
    out["dose_1000"] = df["dose_nominal_sgd"] / 1000.0

    X = pd.DataFrame({
        "demand_l1": out["demand_l1"], "demand_l2": out["demand_l2"],
        **{d: df[d] for d in REGIME_DUMMIES},
        f"cat{K}_quota": df[f"cat{K}_quota"],
        "trend": df["trend"], "cpi_all_items": df["cpi_all_items"],
    })
    res_dum = D.ols(out[price], X, cov_type="HC1")

    Xd = pd.DataFrame({
        "demand_l1": out["demand_l1"], "demand_l2": out["demand_l2"],
        "dose_1000": out["dose_1000"],
        f"cat{K}_quota": df[f"cat{K}_quota"],
        "trend": df["trend"], "cpi_all_items": df["cpi_all_items"],
    })
    res_dose = D.ols(out[price], Xd, cov_type="HC1")
    return out, price, res_dum, res_dose


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base, sample = build()
    df = D.make_lags(sample, D.catA_demand_column(sample, "bids_received"))

    # =========================================================================
    # NEGATIVE CONTROLS
    # =========================================================================
    nc_rows = []
    for K, tax in NC_TAXONOMY.items():
        out, price, res_dum, res_dose = _price_spec_for_cat(df, K, "nominal")
        # rebate terms: the 2022 dummy (EV-relevant) + the 3 pre-2022 dummies +
        # the continuous dose
        rebate_terms = ["reg_eeai_202201", "reg_cevs_uplift_201611",
                        "reg_cevs_lapse_201801", "reg_ves_revival_201809"]
        for t in rebate_terms:
            r = D.coef_of(res_dum, t)
            r.update(category=K, spec="dummy", term=t,
                     classification=tax,
                     expect=("zero" if K in "CDE" else "n/a"))
            nc_rows.append(r)
        rd = D.coef_of(res_dose, "dose_1000")
        rd.update(category=K, spec="dose", term="dose_1000",
                  classification=tax,
                  expect=("zero" if K in "CDE" else "n/a"))
        nc_rows.append(rd)
    nc = pd.DataFrame(nc_rows)
    # Cross-category COMPARABLE view: the raw S$ rebate coefficients are on
    # different price scales (Cat D is a large-goods COE ~10k, Cat B/E ~100k+),
    # so a verdict on "does a clean control show the same 2022-01 jump?" needs
    # the jump as a FRACTION of that category's mean price.
    mean_price = {}
    for K in "ABCDE":
        mean_price[K] = df[f"cat{K}_clearing_price"].mean()
    nc["cat_mean_price"] = nc["category"].map(mean_price)
    nc["coef_pct_of_mean"] = nc["coef"] / nc["cat_mean_price"] * 100.0

    # Explicit negative-control verdict (the KEY diagnostic for the causal claim):
    ee = nc[(nc.term == "reg_eeai_202201") & (nc.spec == "dummy")]
    a22 = ee[ee.category == "A"]["coef_pct_of_mean"].iloc[0]
    c22 = ee[ee.category == "C"]["coef_pct_of_mean"].iloc[0]
    d22 = ee[ee.category == "D"]["coef_pct_of_mean"].iloc[0]
    e22 = ee[ee.category == "E"]["coef_pct_of_mean"].iloc[0]
    clean_jump = (c22, d22, e22)
    # A clean control "shows the same effect" if its 2022-01 % jump is in the
    # same direction and at least half the size of A's (A is the EV-eligible one).
    same_effect = all(
        (x > 0 and a22 > 0 and x > 0.5 * a22) or
        (x < 0 and a22 < 0 and x < 0.5 * a22) for x in clean_jump
    )
    verdict = (
        f"NEGATIVE-CONTROL {'FAIL' if same_effect else 'PASS'}: clean controls "
        f"C/D/E 2022-01 % jumps = {c22:.1f}/{d22:.1f}/{e22:.1f}% vs A "
        f"(EV-eligible) {a22:.1f}%. "
        + (
            "Clean controls show the SAME 2022-01 price jump despite NO EV "
            "rebate applying to them -> the apparent 'rebate -> price' effect "
            "is a MARKET-WIDE COMMON SHOCK (co-timed 97->110kW threshold + COE "
            "market dynamics), NOT an EV-rebate-specific channel. The rebate "
            "cannot be credited with the 2022 price increase."
            if same_effect else
            "Clean controls show a smaller/absent 2022-01 jump -> the 2022 "
            "price effect is consistent with (but not proven to be) an "
            "EV-rebate channel."
        )
    )
    # append the verdict as a commented block for Batch C (machine-readable).
    # Written BEFORE the table so re-runs stay idempotent (the table to_csv
    # overwrites the file; the verdict is appended after it each run).
    verdict_lines = [
        "# ---- negative-control verdict ----",
        f"# same_effect_on_clean_controls = {same_effect}",
        f"# A(EV-eligible) 2022-01 % jump = {a22:.2f}%",
        f"# clean control C 2022-01 % jump = {c22:.2f}%",
        f"# clean control D 2022-01 % jump = {d22:.2f}%",
        f"# clean control E 2022-01 % jump = {e22:.2f}%",
        f"# VERDICT: {verdict}",
    ]
    nc.to_csv(OUT_NC, index=False)
    with open(OUT_NC, "a") as fh:
        for line in verdict_lines:
            fh.write(line + "\n")

    # =========================================================================
    # STATIONARITY + AUTOCORR
    # =========================================================================
    diag = []

    def adf_row(series, label, diff=0):
        s = series.dropna()
        if diff == 1:
            s = s.diff().dropna()
        try:
            stat, p, usedlag, nobs, crit, _ = adfuller(
                s.to_numpy(), autolag="AIC", result_object=False)
            res_stat, res_p = float(stat), float(p)
        except Exception:
            res_stat, res_p = np.nan, np.nan
        diag.append({
            "variable": label, "form": ("level" if diff == 0 else "1st diff"),
            "adf_stat": res_stat, "adf_p": res_p,
            "stationary_005": (res_p < 0.05) if not np.isnan(res_p)
            else "INDETERMINATE",
            "note": "ADF, AIC lag",
        })

    for col, lab in [
        ("catA_clearing_price", "catA_clearing_price (nominal)"),
        ("catA_clearing_price_real", "catA_clearing_price (real)"),
        ("catA_bids_received_clean", "catA_bids_received_clean (demand)"),
        ("cpi_all_items", "cpi_all_items (CPI)"),
    ]:
        adf_row(df[col], lab, 0)
        adf_row(df[col], lab, 1)

    # ---- residual autocorrelation on the PRIMARY price equation (nominal) ----
    # primary spec M1: demand_l1 + demand_l2 + 4 regime dummies + controls
    demand = df["catA_bids_received_clean"]
    out = df.copy()
    out["demand_l1"] = D.lag(demand, 1)
    out["demand_l2"] = D.lag(demand, 2)
    X = pd.DataFrame({
        "demand_l1": out["demand_l1"], "demand_l2": out["demand_l2"],
        **{d: df[d] for d in REGIME_DUMMIES}, **{c: df[c] for c in CONTROLS},
    })
    res = D.ols(out["catA_clearing_price"], X, cov_type="HC1")
    # res.resid is already aligned to the effective (listwise) rows
    resid = np.asarray(res.resid)

    dw = float(durbin_watson(resid))
    lb = acorr_ljungbox(resid, lags=[1, 2, 3, 4], return_df=True)
    bg = acorr_breusch_godfrey(res, nlags=3)
    bg_stat, bg_p, bg_f, bg_fp = float(bg[0]), float(bg[1]), float(bg[2]), float(bg[3])

    diag.append({
        "variable": "primary price eq. residuals", "form": "residual",
        "adf_stat": np.nan, "adf_p": np.nan,
        "stationary_005": np.nan,
        "note": f"Durbin-Watson = {dw:.4f}",
    })
    for lag in [1, 2, 3, 4]:
        diag.append({
            "variable": "primary price eq. residuals", "form": "residual",
            "adf_stat": float(lb.loc[lag, "lb_stat"]),
            "adf_p": float(lb.loc[lag, "lb_pvalue"]),
            "stationary_005": ("significant" if lb.loc[lag, "lb_pvalue"] < 0.05
                                else "ns"),
            "note": f"Ljung-Box Q({lag})",
        })
    diag.append({
        "variable": "primary price eq. residuals", "form": "residual",
        "adf_stat": bg_stat, "adf_p": bg_p,
        "stationary_005": ("significant" if bg_p < 0.05 else "ns"),
        "note": f"Breusch-Godfrey (nlags=3): F={bg_f:.4f}",
    })

    diagdf = pd.DataFrame(diag)
    diagdf.to_csv(OUT_DIAG, index=False)

    # =========================================================================
    # SENSITIVITY
    # =========================================================================
    sens = []

    def primary_spec(demand_def="bids_received", lags=(1, 2),
                     drop_control=None, price_def="nominal"):
        price = ("catA_clearing_price_real" if price_def == "real"
                 else "catA_clearing_price")
        dem = D.catA_demand_column(df, demand_def)
        o = df.copy()
        lagg = {}
        for k in lags:
            o[f"l{k}"] = D.lag(dem, k)
            lagg[f"l{k}"] = o[f"l{k}"]
        cols = dict(lagg)
        for c in CONTROLS:
            if c != drop_control:
                cols[c] = df[c]
        X = pd.DataFrame({**{d: df[d] for d in REGIME_DUMMIES}, **cols})
        res = D.ols(o[price], X, cov_type="HC1")
        return res

    def grab(res, term, spec, note):
        r = D.coef_of(res, term)
        r.update(spec=spec, term=term, note=note)
        sens.append(r)

    # S1: drop-one CONTROL (from the full primary spec, nominal)
    for drop in ["catA_quota", "trend", "cpi_all_items"]:
        res = primary_spec("bids_received", (1, 2), drop_control=drop)
        grab(res, "reg_eeai_202201", f"drop_control_{drop}",
             f"primary spec w/o {drop}")
        grab(res, "l1", f"drop_control_{drop}",
             f"primary spec w/o {drop} (demand_l1)")

    # S2: alternative DEMAND definitions (bids_received primary vs bids_success)
    for dem in ["bids_received", "bids_success"]:
        res = primary_spec(dem, (1, 2))
        grab(res, "reg_eeai_202201", f"demand_{dem}",
             f"demand def = {dem}")
        grab(res, "l1", f"demand_{dem}", f"demand def = {dem} (demand_l1)")

    # S3: lag-order variants (lag1 only, lag2 only, lag1+2 primary, contemp)
    for lags, lab in [((1,), "lag1_only"), ((2,), "lag2_only"),
                      ((1, 2), "lag1_plus_lag2_primary"), ((0,), "contemporaneous")]:
        res = primary_spec("bids_received", lags)
        grab(res, "reg_eeai_202201", f"lag_{lab}", f"lag order = {lab}")
        grab(res, f"l{lags[0]}", f"lag_{lab}", f"lag order = {lab} (demand)")

    # S4: nominal vs REAL price (rebate coefficient must not reverse)
    for pdef in ["nominal", "real"]:
        res = primary_spec("bids_received", (1, 2), price_def=pdef)
        grab(res, "reg_eeai_202201", f"price_{pdef}", f"price def = {pdef}")
        grab(res, "l1", f"price_{pdef}", f"price def = {pdef} (demand_l1)")

    sensdf = pd.DataFrame(sens)
    sensdf.to_csv(OUT_SENS, index=False)

    B.register_exhibit(
        name="negative_controls_diagnostics", kind="diagnostics",
        est_scope="2016-01..2025-05",
        key_regressor="catA_bids_received_clean (A) / per-category corrected "
                      "demand for C,D,E,B",
        interpretation_scope="2022-01..2025-05",
        n_obs=len(df.dropna(subset=["catA_clearing_price"])),
        notes="C,D,E = clean negative controls (expect ~0 rebate effect); "
              "B = contaminated upper bound; A = main effect. ADF levels vs "
              "diffs; residual DW/Ljung-Box/BG; sensitivity: drop-one control, "
              "demand def, lag order, nominal vs real.",
    )

    print(f"[diagnostics] wrote {OUT_NC}  rows={len(nc)}")
    print(f"[diagnostics] wrote {OUT_DIAG}  rows={len(diagdf)}")
    print(f"[diagnostics] wrote {OUT_SENS}  rows={len(sensdf)}")
    print("\n  --- negative control rebate effects (2022 dummy, dose/1000) ---")
    for K in "ABCDE":
        ee = nc[(nc.category == K) & (nc.term == "reg_eeai_202201")].iloc[0]
        do = nc[(nc.category == K) & (nc.term == "dose_1000")].iloc[0]
        print(f"  cat{K} [{NC_TAXONOMY[K][:20]}]: eeai={ee['coef']:+.0f} "
              f"(p={ee['p']:.2f})  dose={do['coef']:+.0f} (p={do['p']:.2f})")


if __name__ == "__main__":
    main()
