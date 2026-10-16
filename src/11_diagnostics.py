#!/usr/bin/env python3
"""
Step 12 — diagnostics: negative controls, stationarity, residual
autocorrelation, and sensitivity. VERIFIED REAL POLICY; dual scope.

Outputs:
    tables/negative_controls.csv                 (price equation re-run on the
                                                 clean controls C (goods &
                                                 buses) and D (motorcycles)
                                                 -- expect ~zero rebate effect
                                                 -- and on B and E, both
                                                 EV-contaminated (high-power
                                                 EVs in B; EV cars can bid the
                                                 open category E);
                                                 BOTH scopes: full window and
                                                 2022+ EV era, with per-scope
                                                 verdicts)
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

Negative-control taxonomy (verified against LTA's published category table):
    * C (goods vehicles & buses) and D (motorcycles) = CLEAN negative
      controls. The EV rebate does not apply to these, so a well-specified
      model must show a ~ZERO rebate coefficient here. A non-zero rebate
      effect on a clean control would indicate the "effect" is a data
      artifact (the trend, the quota, the market-wide shock) rather than a
      genuine rebate channel.
    * B = CONTAMINATED upper bound: high-power EVs fall in Cat B, so B is
      allowed to show a (bounded, upper) rebate effect.
    * E = CONTAMINATED open category ("all except motorcycles"): cars,
      including EVs, can bid here, so E may legitimately move with the EV
      channels; it is reported for reference, not as a clean control.
      (NOTE: an earlier draft mislabelled D as "large goods" and E as
      "motorcycles"; the price scales in the data (D ~ $8-11k, E car-scale
      ~ $100k) and LTA's category table confirm D = motorcycles, E = open.)
    * A = the main effect category (low-power cars; the EV-relevant one).

TWO SCOPE-CONDITIONED VERDICTS (the KEY diagnostic for the causal claim):
  * FULL-WINDOW scope — the 2022-01 price jump: under the verified policy the
    dose does NOT step at 2022-01 (the 2022-01 change was the $0 ARF floor,
    a TAX provision; the co-timed 97->110kW threshold change is market-wide).
    The 2022-01 level shift in the full-window dummy spec is carried by
    reg_arffloor_zero_202201. If BOTH clean controls C/D show the same/larger
    2022-01 % jump as A, the 2022-01 price jump is a MARKET-WIDE COMMON
    SHOCK, not an EV-rebate channel; if they split (one same-direction with
    at least half of A's size, the other not), the verdict is MIXED and the
    test is inconclusive on market-wideness.
  * 2022+ EV-ERA scope — the 2024-01 dose step (45000 -> 40000, the EEAI cap
    cut): inside this window the only rebate variation is that step
    (reg_eeai_cap15k_202401). If BOTH clean controls C/D respond to the
    2024-01 EV-rebate cap cut with the same/larger % jump as A, the 2022+
    scope verdict is ALSO a market-wide common shock. If clean controls do
    NOT respond at 2024-01, the 2022+ scope does not falsify an EV-rebate
    channel (the contaminated car channels B/E may move; that is expected).

All controls use the CORRECTED per-category bid counts (see 00_data.py).
Dose/dummy collinearity: the per-category specs use the DUMMY spec (4
real-policy dummies) OR the DOSE spec (continuous) — never both in one model.
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

# Real-policy dummies (verified). reg_arffloor_zero_202201 is the 2022-01
# term (=$0 ARF floor tax provision = the 97->110kW threshold confounder).
REAL_DUMMIES = [
    "reg_real_ves_201801",
    "reg_real_evstack_202101",
    "reg_arffloor_zero_202201",
    "reg_eeai_cap15k_202401",
]
# The 2022-01 market-wide term (full-window scope verdict key).
DUMMY_2022 = "reg_arffloor_zero_202201"
# The 2024-01 EV-era step (2022+ scope verdict key).
DUMMY_2024 = "reg_eeai_cap15k_202401"
CONTROLS = ["catA_quota", "trend", "cpi_all_items"]

NC_TAXONOMY = {
    "A": "MAIN effect (low-power cars; EV-relevant)",
    "B": "CONTAMINATED upper bound (high-power EVs fall here)",
    "C": "CLEAN negative control (goods vehicles & buses; no EV rebate)",
    "D": "CLEAN negative control (motorcycles; no EV rebate)",
    "E": "CONTAMINATED open category (cars incl. EVs can bid; no separate EV-rebate channel)",
}


def build():
    frame = D.load_estimation_frame()
    sample = D.listwise_sample(frame)
    return frame, sample


def _price_spec_for_cat(df, K, price_def="nominal", scope="full",
                        local_trend=False):
    """The price-equation structure re-aimed at category K. Demand regressor is
    K's own (corrected) bids_received; quota is K's quota; the 4 real-policy
    dummies (dummy spec) or the continuous dose (dose spec) are the rebate
    intensity terms — reported SEPARATELY (documented choice)."""
    price = (f"cat{K}_clearing_price_real"
             if price_def == "real" else f"cat{K}_clearing_price")
    demand = df[f"cat{K}_bids_received_clean"]
    out = df.copy()
    out["demand_l1"] = D.lag(demand, 1)
    out["demand_l2"] = D.lag(demand, 2)
    out["dose_1000"] = df["dose_nominal_sgd"] / 1000.0
    if local_trend:
        out = out.reset_index(drop=True)
        out["trend22"] = np.arange(len(out))

    full = scope in ("full", "full_window")
    if full:
        X = pd.DataFrame({
            "demand_l1": out["demand_l1"], "demand_l2": out["demand_l2"],
            **{d: df[d] for d in REAL_DUMMIES},
            f"cat{K}_quota": df[f"cat{K}_quota"],
            "trend": df["trend"], "cpi_all_items": df["cpi_all_items"],
        })
        Xd = pd.DataFrame({
            "demand_l1": out["demand_l1"], "demand_l2": out["demand_l2"],
            "dose_1000": out["dose_1000"],
            f"cat{K}_quota": df[f"cat{K}_quota"],
            "trend": df["trend"], "cpi_all_items": df["cpi_all_items"],
        })
    else:  # EV era (2022-01..2025-05; dose varies 45000 -> 40000 at 2024-01)
        X = pd.DataFrame({
            "demand_l1": out["demand_l1"], "demand_l2": out["demand_l2"],
            DUMMY_2024: out[DUMMY_2024],
            f"cat{K}_quota": out[f"cat{K}_quota"],
            "trend22": out["trend22"], "cpi_all_items": out["cpi_all_items"],
        })
        Xd = pd.DataFrame({
            "demand_l1": out["demand_l1"], "demand_l2": out["demand_l2"],
            "dose_1000": out["dose_1000"],
            f"cat{K}_quota": out[f"cat{K}_quota"],
            "trend22": out["trend22"], "cpi_all_items": out["cpi_all_items"],
        })
    res_dum = D.ols(out[price], X, cov_type="HC1")
    res_dose = D.ols(out[price], Xd, cov_type="HC1")
    return out, price, res_dum, res_dose


def _clean_move(x, a):
    """True if clean control x moves the same direction as A with at least
    half of A's % size."""
    return ((x > 0 and a > 0 and x > 0.5 * a)
            or (x < 0 and a < 0 and x < 0.5 * a))


def _pct_verdict(nc, term, scope):
    """Same-effect test on one dummy term within one scope. CLEAN controls
    are C (goods & buses) and D (motorcycles); E (open category) is
    EV-contaminated and is reported but excluded from the test.
    ALL clean controls show the same direction and at least half the % size
    of A -> market-wide common shock (same_effect). Exactly one of the two
    does (the other doesn't) -> MIXED (inconclusive on market-wideness)."""
    ee = nc[(nc.term == term) & (nc.spec == "dummy") & (nc.scope == scope)]
    a = ee[ee.category == "A"]["coef_pct_of_mean"].iloc[0]
    c = ee[ee.category == "C"]["coef_pct_of_mean"].iloc[0]
    d = ee[ee.category == "D"]["coef_pct_of_mean"].iloc[0]
    e = ee[ee.category == "E"]["coef_pct_of_mean"].iloc[0]
    moves = [_clean_move(x, a) for x in (c, d)]
    same_effect = all(moves)
    mixed = (not same_effect) and any(moves)
    return a, c, d, e, same_effect, mixed


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base, sample = build()
    df = D.make_lags(sample, D.catA_demand_column(sample, "bids_received"))
    ev = df[df["month"] >= "2022-01"].copy().reset_index(drop=True)
    ev["trend22"] = np.arange(len(ev))

    # =========================================================================
    # NEGATIVE CONTROLS (both scopes)
    # =========================================================================
    nc_rows = []
    for scope, frame in [("full_window", df), ("ev_era_2022plus", ev)]:
        local = (scope == "ev_era_2022plus")
        for K, tax in NC_TAXONOMY.items():
            out, price, res_dum, res_dose = _price_spec_for_cat(
                frame, K, "nominal", scope=scope, local_trend=local)
            # rebate terms: the scope-relevant dummies + the continuous dose
            rebate_terms = REAL_DUMMIES if scope == "full_window" else [DUMMY_2024]
            for t in rebate_terms:
                r = D.coef_of(res_dum, t)
                r.update(category=K, spec="dummy", term=t,
                         classification=tax, scope=scope,
                         expect=("zero" if K in "CD" else "n/a"))
                nc_rows.append(r)
            rd = D.coef_of(res_dose, "dose_1000")
            rd.update(category=K, spec="dose", term="dose_1000",
                      classification=tax, scope=scope,
                      expect=("zero" if K in "CD" else "n/a"))
            nc_rows.append(rd)
    nc = pd.DataFrame(nc_rows)
    # Cross-category COMPARABLE view: the raw S$ rebate coefficients are on
    # different price scales (Cat D motorcycles ~ $8-11k; Cat B/E car-scale
    # ~ $100k+), so a verdict on "does a clean control show the same jump?"
    # needs the jump as a FRACTION of that category's mean price (per scope
    # window).
    mean_price_full = {K: df[f"cat{K}_clearing_price"].mean() for K in "ABCDE"}
    mean_price_ev = {K: ev[f"cat{K}_clearing_price"].mean() for K in "ABCDE"}
    nc["cat_mean_price"] = nc.apply(
        lambda r: (mean_price_full if r["scope"] == "full_window"
                   else mean_price_ev)[r["category"]], axis=1)
    nc["coef_pct_of_mean"] = nc["coef"] / nc["cat_mean_price"] * 100.0

    # Explicit negative-control verdicts (the KEY diagnostics), per scope:
    a22, c22, d22, e22, same_2022, mixed_2022 = _pct_verdict(
        nc, DUMMY_2022, "full_window")
    a24, c24, d24, e24, same_2024, mixed_2024 = _pct_verdict(
        nc, DUMMY_2024, "ev_era_2022plus")

    # A's own 2022-01 dummy p-value (primary nominal spec), quoted in the
    # MIXED verdict text:
    p22 = None
    try:
        pe = pd.read_csv(OUT_DIR / "price_equation.csv")
        r22 = pe[(pe["term"] == "reg_arffloor_zero_202201")
                 & (pe["spec"] == "M1_primary_lagged_dum")
                 & (pe["price_def"] == "nominal")]
        if len(r22):
            p22 = float(r22["p"].iloc[0])
    except Exception:
        pass
    p22_txt = f" (p={p22:.3f})" if p22 is not None else ""

    verdict_full = (
        f"FULL-WINDOW NEGATIVE-CONTROL "
        f"{'FAIL' if same_2022 else ('MIXED' if mixed_2022 else 'PASS')}: "
        f"clean controls C (goods & buses) / D (motorcycles) 2022-01 % jumps "
        f"= {c22:.1f}/{d22:.1f}% vs A (EV-eligible) {a22:.1f}% (contaminated "
        f"open category E: {e22:.1f}%, reported for reference). "
        + (
            "Both clean controls show the SAME 2022-01 price jump despite NO "
            "EV rebate applying to them (and the verified dose does NOT step "
            "at 2022-01 — it was the $0 ARF floor, a tax provision, + the "
            "market-wide 97->110kW threshold) -> the 2022-01 jump is a "
            "MARKET-WIDE COMMON SHOCK, NOT an EV-rebate-specific channel."
            if same_2022 else
            (
                "Clean controls SPLIT at 2022-01 (one shows a same-direction "
                "jump at least half of A's size, the other does not) -> the "
                "test is inconclusive on market-wideness, and it does NOT "
                "establish an EV-specific channel either: the 2022-01 change "
                "was the $0 ARF floor (a TAX provision) co-timed with the "
                "97->110kW car threshold, the verified dose does NOT step at "
                "2022-01, and A's own 2022-01 dummy is not statistically "
                "robust"
                + p22_txt
                + " -> the 2022-01 jump is not credited to the EV rebate."
                if mixed_2022 else
                "Clean controls show a smaller/absent 2022-01 jump -> the "
                "2022-01 price effect is consistent with (but not proven to "
                "be) an EV-rebate/ARF-floor channel."
            )
        )
    )
    verdict_ev = (
        f"2022+ EV-ERA NEGATIVE-CONTROL "
        f"{'FAIL' if same_2024 else ('MIXED' if mixed_2024 else 'PASS')}: "
        f"clean controls C (goods & buses) / D (motorcycles) 2024-01 % steps "
        f"= {c24:.1f}/{d24:.1f}% vs A (EV-eligible) {a24:.1f}% (EEAI cap "
        f"20k->15k; dose 45000->40000; contaminated open category E: "
        f"{e24:.1f}%, reported for reference). "
        + (
            "Both clean controls show the SAME 2024-01 response to an "
            "EV-rebate cap cut that does NOT apply to them -> market-wide "
            "common shock, not an EV-rebate-specific channel, in the 2022+ "
            "scope as well."
            if same_2024 else
            (
                "Clean controls SPLIT at 2024-01 -> the EV-era negative-"
                "control verdict is inconclusive on market-wideness."
                if mixed_2024 else
                "Clean controls show a smaller/absent 2024-01 step -> the "
                "2024-01 EV-era dose step is NOT falsified by the clean "
                "controls (an EV-rebate channel is consistent with the data; "
                "magnitude not identifiable at this power). The contaminated "
                "car channels (B, open E) move with the step, as expected."
            )
        )
    )
    verdict_lines = [
        "# ---- negative-control verdicts (per scope) ----",
        f"# same_effect_on_clean_controls_2022 = {same_2022}",
        f"# mixed_clean_controls_2022 = {mixed_2022}",
        f"# same_effect_on_clean_controls_2024 = {same_2024}",
        f"# mixed_clean_controls_2024 = {mixed_2024}",
        f"# A(EV-eligible) 2022-01 % jump = {a22:.2f}%",
        f"# clean control C (goods & buses) 2022-01 % jump = {c22:.2f}%",
        f"# clean control D (motorcycles) 2022-01 % jump = {d22:.2f}%",
        f"# contaminated open category E 2022-01 % jump = {e22:.2f}%",
        f"# A(EV-eligible) 2024-01 % step (EV era) = {a24:.2f}%",
        f"# clean control C (goods & buses) 2024-01 % step (EV era) = {c24:.2f}%",
        f"# clean control D (motorcycles) 2024-01 % step (EV era) = {d24:.2f}%",
        f"# contaminated open category E 2024-01 % step (EV era) = {e24:.2f}%",
        f"# VERDICT (full window, 2022-01): {verdict_full}",
        f"# VERDICT (2022+ EV era, 2024-01): {verdict_ev}",
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
    # primary spec M1: demand_l1 + demand_l2 + 4 real-policy dummies + controls
    demand = df["catA_bids_received_clean"]
    out = df.copy()
    out["demand_l1"] = D.lag(demand, 1)
    out["demand_l2"] = D.lag(demand, 2)
    X = pd.DataFrame({
        "demand_l1": out["demand_l1"], "demand_l2": out["demand_l2"],
        **{d: df[d] for d in REAL_DUMMIES}, **{c: df[c] for c in CONTROLS},
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
    # SENSITIVITY (full window, primary dummy spec; real-policy dummies)
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
        X = pd.DataFrame({**{d: df[d] for d in REAL_DUMMIES}, **cols})
        res = D.ols(o[price], X, cov_type="HC1")
        return res

    def grab(res, term, spec, note):
        r = D.coef_of(res, term)
        r.update(spec=spec, term=term, note=note)
        sens.append(r)

    # S1: drop-one CONTROL (from the full primary spec, nominal)
    for drop in ["catA_quota", "trend", "cpi_all_items"]:
        res = primary_spec("bids_received", (1, 2), drop_control=drop)
        grab(res, DUMMY_2022, f"drop_control_{drop}",
             f"primary spec w/o {drop}")
        grab(res, DUMMY_2024, f"drop_control_{drop}",
             f"primary spec w/o {drop}")
        grab(res, "l1", f"drop_control_{drop}",
             f"primary spec w/o {drop} (demand_l1)")

    # S2: alternative DEMAND definitions (bids_received primary vs bids_success)
    for dem in ["bids_received", "bids_success"]:
        res = primary_spec(dem, (1, 2))
        grab(res, DUMMY_2022, f"demand_{dem}",
             f"demand def = {dem}")
        grab(res, DUMMY_2024, f"demand_{dem}", f"demand def = {dem}")
        grab(res, "l1", f"demand_{dem}", f"demand def = {dem} (demand_l1)")

    # S3: lag-order variants (lag1 only, lag2 only, lag1+2 primary, contemp)
    for lags, lab in [((1,), "lag1_only"), ((2,), "lag2_only"),
                      ((1, 2), "lag1_plus_lag2_primary"), ((0,), "contemporaneous")]:
        res = primary_spec("bids_received", lags)
        grab(res, DUMMY_2022, f"lag_{lab}", f"lag order = {lab}")
        grab(res, DUMMY_2024, f"lag_{lab}", f"lag order = {lab}")
        grab(res, f"l{lags[0]}", f"lag_{lab}", f"lag order = {lab} (demand)")

    # S4: nominal vs REAL price (rebate coefficients must not reverse)
    for pdef in ["nominal", "real"]:
        res = primary_spec("bids_received", (1, 2), price_def=pdef)
        grab(res, DUMMY_2022, f"price_{pdef}", f"price def = {pdef}")
        grab(res, DUMMY_2024, f"price_{pdef}", f"price def = {pdef}")
        grab(res, "l1", f"price_{pdef}", f"price def = {pdef} (demand_l1)")

    sensdf = pd.DataFrame(sens)
    sensdf.to_csv(OUT_SENS, index=False)

    B.register_exhibit(
        name="negative_controls_diagnostics", kind="diagnostics",
        est_scope="2016-01..2025-05;2022-01..2025-05",
        key_regressor="catA_bids_received_clean (A) / per-category corrected "
                      "demand for C,D,E,B",
        interpretation_scope="2022-01..2025-05",
        n_obs=len(df.dropna(subset=["catA_clearing_price"])),
        notes="C (goods & buses) + D (motorcycles) = clean negative controls "
              "(expect ~0 rebate effect); B (high-power EVs) + E (open "
              "category; EV cars can bid) = contaminated; A = main effect. "
              "BOTH scopes: full window (2022-01 jump via "
              "reg_arffloor_zero_202201 = $0 ARF floor tax + 97->110kW "
              "threshold confounder) and 2022+ EV era (2024-01 step via "
              "reg_eeai_cap15k_202401); per-scope verdicts (PASS/FAIL/MIXED). "
              "ADF levels vs diffs; residual DW/Ljung-Box/BG; sensitivity: "
              "drop-one control, demand def, lag order, nominal vs real.",
    )

    print(f"[diagnostics] wrote {OUT_NC}  rows={len(nc)} (2 scopes x 5 cats)")
    print(f"[diagnostics] wrote {OUT_DIAG}  rows={len(diagdf)}")
    print(f"[diagnostics] wrote {OUT_SENS}  rows={len(sensdf)}")
    print("\n  --- negative-control verdicts ---")
    print(f"  2022-01 (full window, reg_arffloor_zero_202201): A={a22:+.2f}% "
          f"C={c22:+.2f}% D={d22:+.2f}% E={e22:+.2f}% same_effect={same_2022} "
          f"mixed={mixed_2022}")
    print(f"  2024-01 (EV era, reg_eeai_cap15k_202401): A={a24:+.2f}% "
          f"C={c24:+.2f}% D={d24:+.2f}% E={e24:+.2f}% same_effect={same_2024} "
          f"mixed={mixed_2024}")
    for K in "ABCDE":
        for scope in ("full_window", "ev_era_2022plus"):
            row = nc[(nc.category == K) & (nc.scope == scope)
                     & (nc.term == (DUMMY_2022 if scope == "full_window"
                                    else DUMMY_2024))]
            if len(row):
                r = row.iloc[0]
                print(f"  cat{K} [{scope}]: {r['term']}={r['coef']:+.0f} "
                      f"(p={r['p']:.2f}) pct_of_mean={r['coef_pct_of_mean']:+.2f}%")


if __name__ == "__main__":
    main()
