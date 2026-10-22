#!/usr/bin/env python3
"""
Step 7 — price equation (Cat A clearing price ~ demand + rebate intensity).
Verified real policy; dual scope.

FULL WINDOW (primary; 2016-01..2025-05, listwise N=110 after dropping the 3
pandemic NA months 2020-04/05/06):

    catA_clearing_price_{nominal,real}
        ~ demand_l1 + demand_l2           (PRIMARY: lagged Cat A demand)
        + [rebate intensity]              (reported SEPARATELY below)
        + catA_quota + trend + cpi_all_items

Rebate intensity is reported in TWO separate specifications (never combined —
the verified dose is an exact linear transform of the 3 dose-step dummies,
so dose + those dummies + trend + intercept would be collinear; each exhibit
picks ONE spec and documents it):
    * DUMMY spec (M1, PRIMARY)  : the 5 real-policy dummies
        (reg_real_ves_201801, reg_real_evstack_202101,
         reg_arffloor_zero_202201, reg_threshold_110kw_202205,
         reg_eeai_cap15k_202401). The 2022-05 threshold dummy is the
        confounder control for the 97->110 kW Category A change (effective
        from the May 2022 bidding exercise — NOT co-timed with the ARF
        floor).
    * DOSE  spec  (M3)          : the continuous nominal dose (per 1000 S$)
                                  + the 2022-05 threshold dummy (the threshold
                                  switches inside a flat-dose stretch, so it is
                                  not collinear with the dose).
A contemporaneous-demand model (M2) and a demand-only baseline (M4) are also
reported.

2022+ EV-ERA SCOPE (2022-01..2025-05, 41 obs — NOW A VALID ESTIMATION SCOPE):
Under the verified policy the dose varies inside this window (45000 ->
40000 at 2024-01, the EEAI cap cut), so the rebate coefficient IS identifiable
here (the old rank-deficiency rule is removed). Two real dummies vary inside
this window (the 2024-01 cap cut and the 2022-05 threshold). Estimated:
    * E1 (dose)  : price ~ demand_l1 + demand_l2 + dose_1000
                   + reg_threshold_110kw_202205 + catA_quota
                   + trend(local) + cpi_all_items
    * E2 (dummy) : price ~ demand_l1 + demand_l2 + reg_eeai_cap15k_202401
                   + reg_threshold_110kw_202205 + catA_quota
                   + trend(local) + cpi_all_items
                   (the ARF-floor / VES / evstack dummies are constant = 1
                   there and would be collinear with the intercept)
    * E3         : demand-only baseline (demand -> price in the EV era).

The DEMAND regressor is ``catA_bids_received_clean`` (corrected for the Batch A
comma bug; see 00_data.py). It is NEVER ev_reg.

Outputs:
    tables/price_equation.csv                       (full-window primary,
                                                     dual-scope rows: spec names
                                                     M* = full window)
    tables/price_equation_2022plus_robustness.csv   (2022+ EV-era estimation:
                                                     E1/E2/E3, nominal + real)

Confounder notes:
    * 2026 PARF cuts + the 2026 supply trough live in the COE-only extension
      (2025-06..2026-10) and do NOT enter the joint-window models.
    * The May-2022 Cat A 97->110kW threshold change (effective from the May
      2022 bidding exercise; LTA announcement 14 Apr 2022) is controlled by
      reg_threshold_110kw_202205 in BOTH the dummy and the dose specs. It is
      NOT co-timed with the Jan-2022 $0 ARF floor (reg_arffloor_zero_202201),
      which is a separate TAX provision; the dose does NOT step at 2022-01
      under the verified schedule.
    * The pre-2018 CEVS dose (30000) is VERIFIED from the LTA revised-CEVS
      table (Band A1 $30,000, 2015-07..2017-12); an earlier conservative
      20000 estimate gives the same headline (sensitivity note in
      tables/data_audit.csv).
    * Simultaneity / reverse causality: policy is adjusted in response to EV
      demand, and registrations depend on the COE price paid. All rebate
      coefficients are read as bounds, not precise causal magnitudes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bootstrap as B  # noqa: E402

D = B.D
OUT_DIR = D.ROOT / "tables"
OUT = OUT_DIR / "price_equation.csv"
OUT_2022 = OUT_DIR / "price_equation_2022plus_robustness.csv"

# Real-policy dummies (verified). reg_threshold_110kw_202205 is the 97->110kW
# Category A confounder control (effective May 2022; separate from the
# Jan-2022 ARF-floor tax provision).
REAL_DUMMIES = [
    "reg_real_ves_201801",
    "reg_real_evstack_202101",
    "reg_arffloor_zero_202201",
    "reg_threshold_110kw_202205",
    "reg_eeai_cap15k_202401",
]
# Dummies that vary INSIDE the 2022+ window (all others are constant = 1).
EV_ERA_DUMMIES = ["reg_threshold_110kw_202205", "reg_eeai_cap15k_202401"]
EV_ERA_DUMMY = "reg_eeai_cap15k_202401"


def build_frame():
    base = D.load_estimation_frame()
    sample = D.listwise_sample(base)
    demand = D.catA_demand_column(sample, "bids_received")
    df = D.make_lags(sample, demand)
    return base, sample, df, demand


def fit_full_specs(df, price_col, label):
    """Full-window specifications. DUMMY spec (M1, primary) and DOSE spec (M3)
    are reported SEPARATELY (documented choice — see module docstring)."""
    controls = ["catA_quota", "trend", "cpi_all_items"]
    specs = []

    # M1 PRIMARY: lagged demand + 5 real-policy dummies
    # (reg_arffloor_zero_202201 = $0 ARF floor tax; reg_threshold_110kw_202205
    #  = 97->110kW Cat A threshold confounder, effective May 2022)
    X = pd.DataFrame({
        "demand_l1": df["demand_l1"], "demand_l2": df["demand_l2"],
        **{d: df[d] for d in REAL_DUMMIES},
        **{c: df[c] for c in controls},
    })
    res = D.ols(df[price_col], X, cov_type="HC1")
    specs.append(("M1_primary_lagged_dum", res,
                  ["demand_l1", "demand_l2", *REAL_DUMMIES, *controls],
                  "PRIMARY: lag-1+lag-2 demand + 5 real-policy dummies "
                  "(2022-01 = $0 ARF floor tax; 2022-05 = 97->110kW threshold "
                  "confounder; 2024-01 = EEAI cap cut)"))
    res_hac = D.ols(df[price_col], X, cov_type="HAC", maxlags=3)
    specs.append(("M1_primary_lagged_dum_HAC", res_hac,
                  ["demand_l1", "demand_l2", *REAL_DUMMIES, *controls],
                  "same as M1, Newey-West lag-3 SEs"))

    # M2: contemporaneous demand (reported, not primary) + dose + threshold
    X = pd.DataFrame({
        "demand_t0": df["demand_t0"],
        "dose_1000": df["dose_nominal_sgd"] / 1000.0,
        "reg_threshold_110kw_202205": df["reg_threshold_110kw_202205"],
        **{c: df[c] for c in controls},
    })
    res = D.ols(df[price_col], X, cov_type="HC1")
    specs.append(("M2_contemporaneous_dose", res,
                  ["demand_t0", "dose_1000", "reg_threshold_110kw_202205", *controls],
                  "contemporaneous demand (reported); dose spec + May-2022 "
                  "threshold control"))

    # M3: lagged demand + continuous DOSE + threshold (separate from dummies)
    X = pd.DataFrame({
        "demand_l1": df["demand_l1"], "demand_l2": df["demand_l2"],
        "dose_1000": df["dose_nominal_sgd"] / 1000.0,
        "reg_threshold_110kw_202205": df["reg_threshold_110kw_202205"],
        **{c: df[c] for c in controls},
    })
    res = D.ols(df[price_col], X, cov_type="HC1")
    specs.append(("M3_lagged_dose", res,
                  ["demand_l1", "demand_l2", "dose_1000",
                   "reg_threshold_110kw_202205", *controls],
                  "lagged demand + continuous dose (per 1000 S$) + May-2022 "
                  "threshold control; dose spec. All dose levels verified "
                  "(2016-01..2017-12 = 30000 revised CEVS A1)"))
    res_hac = D.ols(df[price_col], X, cov_type="HAC", maxlags=3)
    specs.append(("M3_lagged_dose_HAC", res_hac,
                  ["demand_l1", "demand_l2", "dose_1000",
                   "reg_threshold_110kw_202205", *controls],
                  "same as M3, Newey-West lag-3 SEs"))

    # M4: lagged demand ONLY (no rebate) -- demand->price baseline
    X = pd.DataFrame({"demand_l1": df["demand_l1"], "demand_l2": df["demand_l2"],
                      **{c: df[c] for c in controls}})
    res = D.ols(df[price_col], X, cov_type="HC1")
    specs.append(("M4_lagged_demand_only", res,
                  ["demand_l1", "demand_l2", *controls],
                  "lagged demand only (demand->price baseline, no rebate term)"))
    return specs


def fit_ev_era_specs(sub, price_col, label):
    """2022+ EV-era specifications (41 obs). The dose varies inside this window
    (45000 -> 40000 at 2024-01) so the rebate coefficient is IDENTIFIABLE here
    (valid estimation scope under the verified policy)."""
    sub = sub.copy().reset_index(drop=True)
    # local time trend (0-based within the EV era)
    sub["trend22"] = np.arange(len(sub))
    controls = ["catA_quota", "trend22", "cpi_all_items"]
    specs = []

    # E1: dose-only spec (two levels: 45, 40) + May-2022 threshold control
    X = pd.DataFrame({
        "demand_l1": sub["demand_l1"], "demand_l2": sub["demand_l2"],
        "dose_1000": sub["dose_nominal_sgd"] / 1000.0,
        "reg_threshold_110kw_202205": sub["reg_threshold_110kw_202205"],
        **{c: sub[c] for c in controls},
    })
    res = D.ols(sub[price_col], X, cov_type="HC1")
    specs.append(("E1_ev_era_lagged_dose", res,
                  ["demand_l1", "demand_l2", "dose_1000",
                   "reg_threshold_110kw_202205", *controls],
                  "2022+ EV era: lagged demand + dose (45000->40000 at 2024-01) "
                  "+ May-2022 threshold control + local trend + quota + CPI "
                  "(dose-only spec)"))
    res_hac = D.ols(sub[price_col], X, cov_type="HAC", maxlags=3)
    specs.append(("E1_ev_era_lagged_dose_HAC", res_hac,
                  ["demand_l1", "demand_l2", "dose_1000",
                   "reg_threshold_110kw_202205", *controls],
                  "same as E1, Newey-West lag-3 SEs"))

    # E2: dummy spec (reg_eeai_cap15k_202401 + reg_threshold_110kw_202205 vary
    # inside the window; the other real dummies are constant 1 -> collinear
    # with intercept)
    X = pd.DataFrame({
        "demand_l1": sub["demand_l1"], "demand_l2": sub["demand_l2"],
        "reg_eeai_cap15k_202401": sub["reg_eeai_cap15k_202401"],
        "reg_threshold_110kw_202205": sub["reg_threshold_110kw_202205"],
        **{c: sub[c] for c in controls},
    })
    res = D.ols(sub[price_col], X, cov_type="HC1")
    specs.append(("E2_ev_era_lagged_dum", res,
                  ["demand_l1", "demand_l2", "reg_eeai_cap15k_202401",
                   "reg_threshold_110kw_202205", *controls],
                  "2022+ EV era: lagged demand + reg_eeai_cap15k_202401 "
                  "(45000->40000 step) + May-2022 threshold control + local "
                  "trend + quota + CPI (dummy-only spec; ARF-floor/VES/evstack "
                  "dummies constant in-window)"))

    # E3: demand-only baseline in the EV era
    X = pd.DataFrame({"demand_l1": sub["demand_l1"], "demand_l2": sub["demand_l2"],
                      **{c: sub[c] for c in controls}})
    res = D.ols(sub[price_col], X, cov_type="HC1")
    specs.append(("E3_ev_era_demand_only", res,
                  ["demand_l1", "demand_l2", *controls],
                  "2022+ EV era: lagged demand only (demand->price baseline)"))
    return specs


def flatten(specs, price_label, sample_label):
    rows = []
    for name, res, idx, note in specs:
        for r in D.coef_rows(res, idx, extra={"note": note}):
            r["price_def"] = price_label
            r["spec"] = name
            r["sample"] = sample_label
            rows.append(r)
    return rows


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base, sample, df, demand = build_frame()
    n_full = len(df.dropna(subset=["demand_l1", "demand_l2"]))

    allrows = []
    # full window: nominal + real
    allrows += flatten(fit_full_specs(df, "catA_clearing_price", "nominal"),
                       "nominal", f"2016-01..2025-05 (listwise N=110, 3 pandemic NA dropped)")
    allrows += flatten(fit_full_specs(df, "catA_clearing_price_real", "real"),
                       "real", f"2016-01..2025-05 (listwise N=110, 3 pandemic NA dropped)")
    full = pd.DataFrame(allrows)
    full["n_effective"] = full["nobs"]
    full.to_csv(OUT, index=False)

    # ---- 2022+ EV-era estimation (valid scope: dose varies 45000 -> 40000) ----
    sub = df[df["month"] >= "2022-01"].copy()
    n_ev = int(sub["catA_clearing_price"].notna().sum())
    ev_rows = []
    for price_col, plabel in [("catA_clearing_price", "nominal"),
                              ("catA_clearing_price_real", "real")]:
        ev_rows += flatten(fit_ev_era_specs(sub, price_col, plabel),
                           plabel, "2022-01..2025-05 (EV era, 41 obs; "
                                   "dose varies 45000->40000 at 2024-01 -> estimable)")
    ev = pd.DataFrame(ev_rows)
    ev.to_csv(OUT_2022, index=False)

    # register the exhibit(s) with the scope guard (dual scope)
    B.register_exhibit(
        name="price_equation", kind="price_equation",
        est_scope="2016-01..2025-05;2022-01..2025-05",
        key_regressor="catA_bids_received_clean",
        interpretation_scope="2022-01..2025-05",
        n_obs=n_full,
        notes="demand regressor = corrected catA_bids_received (lag 1+2 primary, "
              "contemporaneous reported); rebate via separate dummy & dose specs "
              "(documented choice — collinear if combined); 5 real-policy "
              "dummies incl. the May-2022 97->110kW threshold confounder "
              "(reg_threshold_110kw_202205), also added to the dose specs; "
              "2022+ EV-era scope now estimated (dose 45000->40000 at "
              "2024-01; threshold + cap dummies vary in-window); nominal & real "
              "reported; core finding must not reverse.",
    )

    print(f"[price_equation] wrote {OUT}  rows={len(full)}")
    print(f"[price_equation] wrote {OUT_2022}  rows={len(ev)} (EV era, {n_ev} obs)")
    # headline: primary demand + rebate terms, nominal vs real, reversal check
    rebate_terms = REAL_DUMMIES + ["dose_1000"]
    reversal = False
    for spec in ["M1_primary_lagged_dum", "M3_lagged_dose"]:
        for t in rebate_terms:
            n = full[(full.spec == spec) & (full.price_def == "nominal") & (full.term == t)]
            r = full[(full.spec == spec) & (full.price_def == "real") & (full.term == t)]
            if len(n) and len(r):
                same = (n.iloc[0]["coef"] * r.iloc[0]["coef"]) > 0
                reversal = reversal or (not same)
                print(f"  {spec} {t}: nominal={n.iloc[0]['coef']:+.1f} "
                      f"real={r.iloc[0]['coef']:+.1f} same_sign={same}")
    print(f"  CORE-FINDING reversal nominal<->real: {reversal} "
          f"({'REVERSED - FLAG' if reversal else 'no reversal - robust'})")
    for spec, t, pl in [("M1_primary_lagged_dum", EV_ERA_DUMMY, "nominal"),
                        ("M3_lagged_dose", "dose_1000", "nominal")]:
        r = full[(full.spec == spec) & (full.term == t) & (full.price_def == pl)]
        if len(r):
            r = r.iloc[0]
            print(f"  {spec} {t} ({pl}): coef={r['coef']:.2f} "
                  f"[{r['ci_lo']:.2f}, {r['ci_hi']:.2f}] p={r['p']:.3f}")
    for spec, t, pl in [("E1_ev_era_lagged_dose", "dose_1000", "nominal"),
                        ("E2_ev_era_lagged_dum", EV_ERA_DUMMY, "nominal")]:
        r = ev[(ev.spec == spec) & (ev.term == t) & (ev.price_def == pl)]
        if len(r):
            r = r.iloc[0]
            print(f"  {spec} {t} ({pl}): coef={r['coef']:.2f} "
                  f"[{r['ci_lo']:.2f}, {r['ci_hi']:.2f}] p={r['p']:.3f}")


if __name__ == "__main__":
    main()
