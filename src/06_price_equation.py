#!/usr/bin/env python3
"""
Step 7 — price equation (Cat A clearing price ~ demand + rebate intensity).

PRIMARY (full window 2016-01..2025-05, listwise N=110 after dropping the 3
pandemic NA months 2020-04/05/06):

    catA_clearing_price_{nominal,real}
        ~ demand_l1 + demand_l2           (PRIMARY: lagged Cat A demand)
        + [rebate intensity]              (reported SEPARATELY below)
        + catA_quota + trend + cpi_all_items
        + threshold_dummy (Jan-2022 97->110kW Cat A threshold change)

The DEMAND regressor is ``catA_bids_received_clean`` (corrected for the Batch A
comma bug; see 00_data.py). It is NEVER ev_reg (ev_reg is descriptive only and
is NA before 2022-07, which would shrink the sample via listwise deletion).

Rebate intensity is reported in TWO separate specifications (not combined in
one model, to keep each coefficient interpretable):
    * DUMMY spec  : the 4 regime step dummies (2016-11 up, 2018-01 down,
                    2018-09 up, 2022-01 up).
    * DOSE  spec  : the continuous nominal dose (dose_nominal_sgd), reported
                    per 1000 S$.
A contemporaneous-demand model is ALSO reported (reported, not primary).

Outputs:
    tables/price_equation.csv                       (full-window primary)
    tables/price_equation_2022plus_robustness.csv   (2022+ subsample: demand
                                                     -> price ONLY; the rebate
                                                     regressors are constant
                                                     there and are NOT
                                                     estimated -> documented
                                                     rank-deficient per the
                                                     scope rule)

The 2022+ subsample is a bounded robustness / interpretation check for the
DEMAND->price link (where the rebate level is actually in force). Headline
effects are read as the 2022+ interpretation of the full-window estimate.

Confounder notes:
    * 2026 PARF cuts + the 2026 supply trough live in the COE-only extension
      (2025-06..2026-10) and do NOT enter the joint-window models.
    * The Jan-2022 Cat A 97->110kW threshold change is co-timed with the EEAI
      regime switch -> controlled by threshold_dummy so the 2022-01 regime
      effect is not pure threshold effect.
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

REGIME_DUMMIES = [
    "reg_cevs_uplift_201611",
    "reg_cevs_lapse_201801",
    "reg_ves_revival_201809",
    "reg_eeai_202201",
]


def build_frame():
    base = D.load_estimation_frame()
    sample = D.listwise_sample(base)
    demand = D.catA_demand_column(sample, "bids_received")
    df = D.make_lags(sample, demand)
    df["threshold"] = D.threshold_dummy(df)
    return base, sample, df, demand


def fit_specs(df, price_col, label):
    """Return a list of (spec_name, OLSResults, index_names, note).

    Rank note: ``threshold_dummy`` (Jan-2022 97->110kW Cat A) is NUMERICALLY
    IDENTICAL to ``reg_eeai_202201`` (both switch on at 2022-01), so they must
    NOT appear in the same design matrix (perfect collinearity). The PRIMARY
    spec carries the 4 regime dummies; a SEPARATE spec carries the threshold
    dummy WITHOUT the EEAI dummy so the 2022-01 effect can be read either as
    the (rebate) regime or the (threshold) confounder.
    """
    controls = ["catA_quota", "trend", "cpi_all_items"]
    specs = []

    # M1 PRIMARY: lagged demand + 4 regime dummies
    X = pd.DataFrame({
        "demand_l1": df["demand_l1"], "demand_l2": df["demand_l2"],
        **{d: df[d] for d in REGIME_DUMMIES},
        **{c: df[c] for c in controls},
    })
    res = D.ols(df[price_col], X, cov_type="HC1")
    specs.append(("M1_primary_lagged_dum", res,
                  ["demand_l1", "demand_l2", *REGIME_DUMMIES, *controls],
                  "PRIMARY: lag-1+lag-2 demand + 4 regime dummies "
                  "(2022-01 captured by reg_eeai_202201)"))
    res_hac = D.ols(df[price_col], X, cov_type="HAC", maxlags=3)
    specs.append(("M1_primary_lagged_dum_HAC", res_hac,
                  ["demand_l1", "demand_l2", *REGIME_DUMMIES, *controls],
                  "same as M1, Newey-West lag-3 SEs"))

    # M1b: PRIMARY + explicit threshold dummy IN PLACE OF reg_eeai_202201
    # (bounds the 2022-01 effect as the co-timed 97->110kW threshold change)
    X = pd.DataFrame({
        "demand_l1": df["demand_l1"], "demand_l2": df["demand_l2"],
        "reg_cevs_uplift_201611": df["reg_cevs_uplift_201611"],
        "reg_cevs_lapse_201801": df["reg_cevs_lapse_201801"],
        "reg_ves_revival_201809": df["reg_ves_revival_201809"],
        "threshold": df["threshold"],
        **{c: df[c] for c in controls},
    })
    res = D.ols(df[price_col], X, cov_type="HC1")
    specs.append(("M1b_lagged_threshold", res,
                  ["demand_l1", "demand_l2", "reg_cevs_uplift_201611",
                   "reg_cevs_lapse_201801", "reg_ves_revival_201809",
                   "threshold", *controls],
                  "lagged demand + 3 pre-2022 dummies + threshold_dummy "
                  "(2022-01 read as the 97->110kW threshold confounder)"))

    # M2: contemporaneous demand (reported, not primary) + regime dummies
    X = pd.DataFrame({
        "demand_t0": df["demand_t0"],
        **{d: df[d] for d in REGIME_DUMMIES},
        **{c: df[c] for c in controls},
    })
    res = D.ols(df[price_col], X, cov_type="HC1")
    specs.append(("M2_contemporaneous_dum", res,
                  ["demand_t0", *REGIME_DUMMIES, *controls],
                  "contemporaneous demand (reported); regime dummies"))

    # M3: lagged demand + continuous DOSE (separate from dummies)
    X = pd.DataFrame({
        "demand_l1": df["demand_l1"], "demand_l2": df["demand_l2"],
        "dose_1000": df["dose_nominal_sgd"] / 1000.0,
        **{c: df[c] for c in controls},
    })
    res = D.ols(df[price_col], X, cov_type="HC1")
    specs.append(("M3_lagged_dose", res,
                  ["demand_l1", "demand_l2", "dose_1000", *controls],
                  "lagged demand + continuous dose (per 1000 S$); dose spec"))
    res_hac = D.ols(df[price_col], X, cov_type="HAC", maxlags=3)
    specs.append(("M3_lagged_dose_HAC", res_hac,
                  ["demand_l1", "demand_l2", "dose_1000", *controls],
                  "same as M3, Newey-West lag-3 SEs"))

    # M4: lagged demand ONLY (no rebate) -- demand->price baseline
    X = pd.DataFrame({"demand_l1": df["demand_l1"], "demand_l2": df["demand_l2"],
                      **{c: df[c] for c in controls}})
    res = D.ols(df[price_col], X, cov_type="HC1")
    specs.append(("M4_lagged_demand_only", res,
                  ["demand_l1", "demand_l2", *controls],
                  "lagged demand only (demand->price baseline, no rebate term)"))
    return specs


def flatten(specs, price_label):
    rows = []
    for name, res, idx, note in specs:
        for r in D.coef_rows(res, idx, extra={"note": note}):
            r["price_def"] = price_label
            r["spec"] = name
            rows.append(r)
    return rows


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base, sample, df, demand = build_frame()
    n_full = len(df.dropna(subset=["demand_l1", "demand_l2"]))

    allrows = []
    # nominal
    allrows += flatten(fit_specs(df, "catA_clearing_price", "nominal"), "nominal")
    # real (CPI-deflated)
    allrows += flatten(fit_specs(df, "catA_clearing_price_real", "real"), "real")
    full = pd.DataFrame(allrows)
    full["sample"] = f"2016-01..2025-05 (listwise N=110, 3 pandemic NA dropped)"
    full["n_effective"] = full["nobs"]
    full.to_csv(OUT, index=False)

    # ---- 2022+ subsample (bounded robustness / interpretation) ----
    # The rebate dose + the 2022-01 regime dummy are CONSTANT on 2022-01..
    # 2025-05 -> a rebate coefficient there is rank-deficient and CANNOT be
    # identified. We therefore estimate ONLY the demand->price link on the
    # subsample and DOCUMENT the rank-deficient rebate coefficient.
    sub = df[df["month"] >= "2022-01"].copy()
    sub_rows = []
    for price_col, plabel in [("catA_clearing_price", "nominal"),
                              ("catA_clearing_price_real", "real")]:
        X = pd.DataFrame({
            "demand_l1": sub["demand_l1"], "demand_l2": sub["demand_l2"],
            "catA_quota": sub["catA_quota"], "trend": sub["trend"],
            "cpi_all_items": sub["cpi_all_items"],
        })
        res = D.ols(sub[price_col], X, cov_type="HC1")
        for r in D.coef_rows(res,
                             ["demand_l1", "demand_l2", "catA_quota",
                              "trend", "cpi_all_items"],
                             extra={"note": "2022+ subsample; demand->price only"}):
            r["price_def"] = plabel
            r["spec"] = "robustness_demand_to_price_2022plus"
            r["sample"] = "2022-01..2025-05"
            sub_rows.append(r)
    sub_rows.append({
        "price_def": "nominal", "spec": "rebate_intensity_2022plus",
        "term": "rebate (dummies OR dose)", "coef": np.nan, "se": np.nan,
        "t": np.nan, "p": np.nan, "ci_lo": np.nan, "ci_hi": np.nan,
        "nobs": len(sub), "r2": np.nan, "cov_type": "HC1",
        "note": "RANK-DEFICIENT: dose + reg_eeai_202201 are constant on "
                "2022-01..2025-05 (dose flat at 7500; dummy flat at 1). "
                "A rebate coefficient is NOT estimable on a 2022+-only sample "
                "by the scope rule. Left as NA by design -- not a missing number.",
        "sample": "2022-01..2025-05",
    })
    sub = pd.DataFrame(sub_rows)
    sub.to_csv(OUT_2022, index=False)

    # register the exhibit(s) with the scope guard
    B.register_exhibit(
        name="price_equation", kind="price_equation",
        est_scope="2016-01..2025-05",
        key_regressor="catA_bids_received_clean",
        interpretation_scope="2022-01..2025-05",
        n_obs=n_full,
        notes="demand regressor = corrected catA_bids_received (lag 1+2 primary, "
              "contemporaneous reported); rebate via separate dummy & dose specs; "
              "threshold_dummy controls the co-timed 2022 Cat A 97->110kW change; "
              "nominal & real reported; core finding must not reverse.",
    )

    print(f"[price_equation] wrote {OUT}  rows={len(full)}")
    print(f"[price_equation] wrote {OUT_2022}  rows={len(sub)}")
    # headline: primary demand + rebate terms, nominal vs real, reversal check
    rebate_terms = ["reg_cevs_uplift_201611", "reg_cevs_lapse_201801",
                    "reg_ves_revival_201809", "reg_eeai_202201", "dose_1000"]
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
    for spec, t, pl in [("M1_primary_lagged_dum", "demand_l1", "nominal"),
                        ("M3_lagged_dose", "dose_1000", "nominal")]:
        r = full[(full.spec == spec) & (full.term == t) & (full.price_def == pl)]
        if len(r):
            r = r.iloc[0]
            print(f"  {spec} {t} ({pl}): coef={r['coef']:.2f} "
                  f"[{r['ci_lo']:.2f}, {r['ci_hi']:.2f}] p={r['p']:.3f}")


if __name__ == "__main__":
    main()
