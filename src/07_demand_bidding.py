#!/usr/bin/env python3
"""
Step 8 — demand / bidding channel: does the rebate move Cat A bidding demand?

PRIMARY (full window 2016-01..2025-05, listwise N=110):

    catA_bids_received_clean
        ~ [rebate intensity]              (dummy spec AND dose spec, separate)
        + trend + catA_quota
        + threshold_dummy (Jan-2022 97->110kW Cat A, co-timed with EEAI)

The dependent variable is the CORRECTED Cat A demand (catA_bids_received_clean;
see 00_data.py for the Batch A comma-bug fix). Robust (HC1) and HAC
(Newey-West lag-3) SEs are reported.

IMPORTANT CONTEXT (stated in the output table notes): this is TOTAL Cat A
demand, dominated by non-EV cars. EV-relevance is NEGIGLIBLE pre-2022 and only
MATERIAL from ~2022 (the first observed BEV registrations are 2022-07; the
interpretation window is 2022-01+). The EV signal is therefore concentrated in
the 2022+ interpretation window; pre-2022 "demand" movements read as
total-car demand, not EV demand.

Rebate timing is kept CONSISTENT with the price equation's primary lag: the
rebate regime dummy switches in the same month it affects the clearing price
(a bid submitted under a rebate regime is contemporaneous with the clearing
event). We also report a CROSS-LAG check (lag +/-1) to see whether the rebate
leads, coincides with, or lags the demand response.

Outputs:
    tables/demand_bidding_channel.csv       (full-window primary, dummy + dose
                                             specs, HC1 + HAC, with the context
                                             note)
    tables/demand_2022plus_interpretation.csv (2022+ subsample DESCRIPTION of
                                             demand levels -- NOT re-estimated
                                             rebate coefficients, which are
                                             rank-deficient there)
    tables/crosslag_check.csv               (lag -1 / 0 / +1 rebate timing)
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
OUT = OUT_DIR / "demand_bidding_channel.csv"
OUT_2022 = OUT_DIR / "demand_2022plus_interpretation.csv"
OUT_XLAG = OUT_DIR / "crosslag_check.csv"

REGIME_DUMMIES = [
    "reg_cevs_uplift_201611",
    "reg_cevs_lapse_201801",
    "reg_ves_revival_201809",
    "reg_eeai_202201",
]

CTX_NOTE = (
    "TOTAL Cat A demand dominated by non-EV cars. EV-relevance negligible "
    "pre-2022, material only from ~2022 (first BEV registrations 2022-07). "
    "EV signal concentrated in the 2022+ interpretation window. Headline read "
    "= 2022+ interpretation of the full-window estimate."
)


def build():
    base = D.load_estimation_frame()
    sample = D.listwise_sample(base)
    demand = D.catA_demand_column(sample, "bids_received")
    df = D.make_lags(sample, demand)
    df["threshold"] = D.threshold_dummy(df)
    return base, sample, df, demand


def fit_rebate_specs(df, label):
    """Rebate -> demand. Dummy spec (4 step dummies) and dose spec (continuous),
    reported separately. threshold_dummy is identical to reg_eeai_202201 so it
    is NOT combined with the full dummy set (rank)."""
    specs = []
    X = pd.DataFrame({**{d: df[d] for d in REGIME_DUMMIES},
                      "trend": df["trend"], "catA_quota": df["catA_quota"]})
    res = D.ols(df["catA_bids_received_clean"], X, cov_type="HC1")
    specs.append(("dummy", res, REGIME_DUMMIES + ["trend", "catA_quota"],
                  "4 regime step dummies + trend + quota (dummy spec)"))
    res_h = D.ols(df["catA_bids_received_clean"], X, cov_type="HAC", maxlags=3)
    specs.append(("dummy_HAC", res_h, REGIME_DUMMIES + ["trend", "catA_quota"],
                  "same as dummy, Newey-West lag-3 SEs"))

    Xd = pd.DataFrame({"dose_1000": df["dose_nominal_sgd"] / 1000.0,
                       "trend": df["trend"], "catA_quota": df["catA_quota"]})
    res = D.ols(df["catA_bids_received_clean"], Xd, cov_type="HC1")
    specs.append(("dose", res, ["dose_1000", "trend", "catA_quota"],
                  "continuous dose (per 1000 S$) + trend + quota (dose spec)"))
    res_h = D.ols(df["catA_bids_received_clean"], Xd, cov_type="HAC", maxlags=3)
    specs.append(("dose_HAC", res_h, ["dose_1000", "trend", "catA_quota"],
                  "same as dose, Newey-West lag-3 SEs"))

    # threshold dummy in place of the EEAI dummy (bounds 2022 effect as
    # threshold confounder)
    Xt = pd.DataFrame({
        "reg_cevs_uplift_201611": df["reg_cevs_uplift_201611"],
        "reg_cevs_lapse_201801": df["reg_cevs_lapse_201801"],
        "reg_ves_revival_201809": df["reg_ves_revival_201809"],
        "threshold": df["threshold"],
        "trend": df["trend"], "catA_quota": df["catA_quota"],
    })
    res = D.ols(df["catA_bids_received_clean"], Xt, cov_type="HC1")
    specs.append(("threshold", res,
                  ["reg_cevs_uplift_201611", "reg_cevs_lapse_201801",
                   "reg_ves_revival_201809", "threshold", "trend",
                   "catA_quota"],
                  "3 pre-2022 dummies + threshold_dummy + trend + quota "
                  "(2022 read as 97->110kW threshold confounder)"))
    return specs


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base, sample, df, demand = build()
    rows = []
    for name, res, idx, note in fit_rebate_specs(df, "full"):
        for r in D.coef_rows(res, idx, extra={"note": note + " | " + CTX_NOTE}):
            r["spec"] = name
            r["sample"] = "2016-01..2025-05 (listwise N=110)"
            rows.append(r)
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)

    # ---- cross-lag check: rebate timing vs demand (lag -1 / 0 / +1) ----
    # Build the rebate intensity (continuous dose, the cleanest intensity
    # measure) shifted by +/-1 month RELATIVE to the demand response month.
    # lag 0 = same-month (baseline); lag -1 = rebate leading demand by 1;
    # lag +1 = rebate lagging demand by 1.
    xl = []
    for lag in (-1, 0, +1):
        name = f"dose_{lag:+d}_month"
        if lag == 0:
            dose_lag = df["dose_nominal_sgd"] / 1000.0
        elif lag > 0:
            dose_lag = (df["dose_nominal_sgd"].shift(lag)) / 1000.0  # rebate lagging
        else:
            dose_lag = (df["dose_nominal_sgd"].shift(-lag)) / 1000.0  # rebate leading
        X = pd.DataFrame({name: dose_lag, "trend": df["trend"],
                          "catA_quota": df["catA_quota"]})
        res = D.ols(df["catA_bids_received_clean"], X, cov_type="HC1")
        for r in D.coef_rows(res, [name, "trend", "catA_quota"],
                             extra={"note": f"dose shifted {lag:+d} month vs demand"}):
            r["lag"] = lag
            r["spec"] = f"crosslag_dose_{lag:+d}"
            r["sample"] = "full window (listwise N=110, lags drop edge months)"
            xl.append(r)
    xldf = pd.DataFrame(xl)
    xldf.to_csv(OUT_XLAG, index=False)

    # ---- 2022+ interpretation (DESCRIPTION, not re-estimated rebate coefs) ----
    sub = df[df["month"] >= "2022-01"]
    desc = pd.DataFrame({
        "metric": [
            "n_months",
            "mean_demand_catA",
            "mean_demand_catA_pre2022",
            "median_demand_catA",
            "min_demand_catA",
            "max_demand_catA",
            "mean_dose_sgd",
            "mean_dose_sgd_pre2022",
        ],
        "value": [
            len(sub),
            sub["catA_bids_received_clean"].mean(),
            df[df["month"] < "2022-01"]["catA_bids_received_clean"].mean(),
            sub["catA_bids_received_clean"].median(),
            sub["catA_bids_received_clean"].min(),
            sub["catA_bids_received_clean"].max(),
            sub["dose_nominal_sgd"].mean(),
            df[df["month"] < "2022-01"]["dose_nominal_sgd"].mean(),
        ],
        "interpretation_scope": "2022-01..2025-05",
        "note": [CTX_NOTE] * 8,
    })
    desc.to_csv(OUT_2022, index=False)

    B.register_exhibit(
        name="demand_bidding_channel", kind="demand_bidding",
        est_scope="2016-01..2025-05",
        key_regressor="catA_bids_received_clean",
        interpretation_scope="2022-01..2025-05",
        n_obs=len(df.dropna(subset=["demand_l1"])),
        notes="dependent var = corrected Cat A demand (bids_received); rebate via "
              "separate dummy & dose specs; TOTAL demand dominated by non-EV; EV "
              "signal material only 2022+; cross-lag check reported.",
    )

    print(f"[demand_bidding] wrote {OUT}  rows={len(out)}")
    print(f"[demand_bidding] wrote {OUT_XLAG}  rows={len(xldf)}")
    print(f"[demand_bidding] wrote {OUT_2022}  rows={len(desc)}")
    for spec in ["dummy", "dose"]:
        for t in (["reg_eeai_202201"] if spec == "dummy" else ["dose_1000"]):
            r = out[(out.spec == spec) & (out.term == t)].iloc[0]
            print(f"  {spec} {t}: coef={r['coef']:+.2f} p={r['p']:.4f} "
                  f"[{r['ci_lo']:+.2f}, {r['ci_hi']:+.2f}]")


if __name__ == "__main__":
    main()
