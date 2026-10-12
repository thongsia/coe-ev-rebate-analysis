#!/usr/bin/env python3
"""
Step 8 — demand / bidding channel: does the rebate move Cat A bidding demand?
VERIFIED-POLICY RE-RUN (dual scope).

FULL WINDOW (primary; 2016-01..2025-05, listwise N=110):

    catA_bids_received_clean
        ~ [rebate intensity]              (dummy spec AND dose spec, separate)
        + trend + catA_quota

Rebate intensity in two separate specifications (documented choice — the
verified dose is a near-exact linear transform of the real-policy dummies, so
they are never combined in one model):
    * DUMMY spec : the 4 real-policy dummies (VES 2018, EV stack 2021,
                   ARF-floor-zero 2022 [= the $0 ARF floor tax provision AND
                   the 97->110kW threshold confounder, both co-timed],
                   EEAI cap15k 2024).
    * DOSE  spec : the continuous nominal dose (per 1000 S$).
Robust (HC1) and HAC (Newey-West lag-3) SEs are reported.

2022+ EV-ERA SCOPE (2022-01..2025-05, 41 obs — NOW A VALID ESTIMATION SCOPE):
the verified dose varies inside the window (45000 -> 40000 at 2024-01, the
EEAI cap cut), so the rebate coefficient is identifiable here (old
rank-deficiency rule removed):
    * E1 (dose)  : demand ~ dose_1000 + trend(local) + catA_quota
    * E2 (dummy) : demand ~ reg_eeai_cap15k_202401 + trend(local) + catA_quota
                   (only real dummy varying inside the window)
    * E3         : demand-only baseline (rebate omitted)

The dependent variable is the CORRECTED Cat A demand (catA_bids_received_clean;
see 00_data.py for the Batch A comma-bug fix). Robust (HC1) and HAC SEs.

IMPORTANT CONTEXT (stated in the output table notes): this is TOTAL Cat A
demand, dominated by non-EV cars. EV-relevance is NEGLIGIBLE pre-2022 and only
MATERIAL from ~2022 (first observed BEV registrations 2022-07). The EV signal
is therefore concentrated in the 2022+ EV-era window; pre-2022 "demand"
movements read as total-car demand, not EV demand.

Rebate timing is kept CONSISTENT with the price equation's primary lag: the
rebate dummy/dose switches in the same month it affects the clearing price.
A CROSS-LAG check (lag +/-1) is reported on the full window.

Outputs:
    tables/demand_bidding_channel.csv       (full-window primary + 2022+ EV-era
                                             specs; dummy + dose specs, HC1 + HAC,
                                             with the context note)
    tables/demand_2022plus_interpretation.csv (2022+ subsample DESCRIPTION of
                                             demand levels + the two dose levels)
    tables/crosslag_check.csv               (lag -1 / 0 / +1 rebate timing,
                                             full window)
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

# Real-policy dummies (verified). reg_arffloor_zero_202201 is the $0 ARF floor
# (tax provision) AND the 97->110kW threshold confounder (both 2022-01).
REAL_DUMMIES = [
    "reg_real_ves_201801",
    "reg_real_evstack_202101",
    "reg_arffloor_zero_202201",
    "reg_eeai_cap15k_202401",
]
# The only real dummy that varies INSIDE the 2022+ window.
EV_ERA_DUMMY = "reg_eeai_cap15k_202401"

CTX_NOTE = (
    "TOTAL Cat A demand dominated by non-EV cars. EV-relevance negligible "
    "pre-2022, material only from ~2022 (first BEV registrations 2022-07). "
    "EV signal concentrated in the 2022+ EV-era window. Full window = primary "
    "estimation scope; 2022+ = also an estimation scope (verified dose varies "
    "45000->40000 at 2024-01)."
)


def build():
    base = D.load_estimation_frame()
    sample = D.listwise_sample(base)
    demand = D.catA_demand_column(sample, "bids_received")
    df = D.make_lags(sample, demand)
    return base, sample, df, demand


def fit_full_specs(df):
    """Full-window rebate -> demand. Dummy spec (4 real-policy dummies) and
    dose spec (continuous), reported separately (documented choice)."""
    specs = []
    X = pd.DataFrame({**{d: df[d] for d in REAL_DUMMIES},
                      "trend": df["trend"], "catA_quota": df["catA_quota"]})
    res = D.ols(df["catA_bids_received_clean"], X, cov_type="HC1")
    specs.append(("dummy", res, REAL_DUMMIES + ["trend", "catA_quota"],
                  "4 real-policy dummies + trend + quota (dummy spec); "
                  "2022-01 = $0 ARF floor (tax) + 97->110kW threshold "
                  "(co-timed confounder)"))
    res_h = D.ols(df["catA_bids_received_clean"], X, cov_type="HAC", maxlags=3)
    specs.append(("dummy_HAC", res_h, REAL_DUMMIES + ["trend", "catA_quota"],
                  "same as dummy, Newey-West lag-3 SEs"))

    Xd = pd.DataFrame({"dose_1000": df["dose_nominal_sgd"] / 1000.0,
                       "trend": df["trend"], "catA_quota": df["catA_quota"]})
    res = D.ols(df["catA_bids_received_clean"], Xd, cov_type="HC1")
    specs.append(("dose", res, ["dose_1000", "trend", "catA_quota"],
                  "continuous dose (per 1000 S$) + trend + quota (dose spec); "
                  "2016-01..2017-12 dose level is the CEVS estimate (20000)"))
    res_h = D.ols(df["catA_bids_received_clean"], Xd, cov_type="HAC", maxlags=3)
    specs.append(("dose_HAC", res_h, ["dose_1000", "trend", "catA_quota"],
                  "same as dose, Newey-West lag-3 SEs"))
    return specs


def fit_ev_era_specs(sub):
    """2022+ EV-era rebate -> demand (41 obs; the verified dose varies inside
    the window, so the coefficient is estimable)."""
    sub = sub.copy().reset_index(drop=True)
    sub["trend22"] = np.arange(len(sub))
    specs = []
    X = pd.DataFrame({"dose_1000": sub["dose_nominal_sgd"] / 1000.0,
                      "trend22": sub["trend22"], "catA_quota": sub["catA_quota"]})
    res = D.ols(sub["catA_bids_received_clean"], X, cov_type="HC1")
    specs.append(("E1_ev_era_dose", res, ["dose_1000", "trend22", "catA_quota"],
                  "2022+ EV era: dose (45000->40000 at 2024-01) + local trend "
                  "+ quota (dose-only spec)"))
    Xd = pd.DataFrame({EV_ERA_DUMMY: sub[EV_ERA_DUMMY],
                       "trend22": sub["trend22"], "catA_quota": sub["catA_quota"]})
    res = D.ols(sub["catA_bids_received_clean"], Xd, cov_type="HC1")
    specs.append(("E2_ev_era_dum", res, [EV_ERA_DUMMY, "trend22", "catA_quota"],
                  "2022+ EV era: reg_eeai_cap15k_202401 (45000->40000 step) + "
                  "local trend + quota (dummy-only spec)"))
    return specs


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base, sample, df, demand = build()
    rows = []
    for name, res, idx, note in fit_full_specs(df):
        for r in D.coef_rows(res, idx, extra={"note": note + " | " + CTX_NOTE}):
            r["spec"] = name
            r["sample"] = "2016-01..2025-05 (listwise N=110)"
            rows.append(r)
    # 2022+ EV-era specs
    sub = df[df["month"] >= "2022-01"]
    for name, res, idx, note in fit_ev_era_specs(sub):
        for r in D.coef_rows(res, idx, extra={"note": note + " | " + CTX_NOTE}):
            r["spec"] = name
            r["sample"] = ("2022-01..2025-05 (EV era, 41 obs; dose varies "
                           "45000->40000 at 2024-01 -> estimable)")
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

    # ---- 2022+ description (levels + the two dose levels) ----
    s22 = df[df["month"] >= "2022-01"]
    s24 = df[df["month"] >= "2024-01"]
    desc = pd.DataFrame({
        "metric": [
            "n_months",
            "mean_demand_catA",
            "mean_demand_catA_pre2022",
            "median_demand_catA",
            "min_demand_catA",
            "max_demand_catA",
            "mean_dose_sgd",
            "mean_dose_sgd_2022_23",
            "mean_dose_sgd_2024_plus",
            "mean_demand_catA_2022_23",
            "mean_demand_catA_2024_plus",
        ],
        "value": [
            len(s22),
            s22["catA_bids_received_clean"].mean(),
            df[df["month"] < "2022-01"]["catA_bids_received_clean"].mean(),
            s22["catA_bids_received_clean"].median(),
            s22["catA_bids_received_clean"].min(),
            s22["catA_bids_received_clean"].max(),
            s22["dose_nominal_sgd"].mean(),
            df[(df["month"] >= "2022-01") & (df["month"] < "2024-01")]
              ["dose_nominal_sgd"].mean(),
            s24["dose_nominal_sgd"].mean(),
            df[(df["month"] >= "2022-01") & (df["month"] < "2024-01")]
              ["catA_bids_received_clean"].mean(),
            s24["catA_bids_received_clean"].mean(),
        ],
        "interpretation_scope": "2022-01..2025-05",
        "note": [CTX_NOTE] * 11,
    })
    desc.to_csv(OUT_2022, index=False)

    B.register_exhibit(
        name="demand_bidding_channel", kind="demand_bidding",
        est_scope="2016-01..2025-05;2022-01..2025-05",
        key_regressor="catA_bids_received_clean",
        interpretation_scope="2022-01..2025-05",
        n_obs=len(df.dropna(subset=["demand_l1"])),
        notes="dependent var = corrected Cat A demand (bids_received); rebate via "
              "separate dummy & dose specs (documented choice); real-policy dummies; "
              "TOTAL demand dominated by non-EV; EV signal material only 2022+; "
              "2022+ EV era now estimated (dose 45000->40000 at 2024-01); "
              "cross-lag check reported (full window).",
    )

    print(f"[demand_bidding] wrote {OUT}  rows={len(out)}")
    print(f"[demand_bidding] wrote {OUT_XLAG}  rows={len(xldf)}")
    print(f"[demand_bidding] wrote {OUT_2022}  rows={len(desc)}")
    for spec in ["dummy", "dose"]:
        for t in (REAL_DUMMIES if spec == "dummy" else ["dose_1000"]):
            r = out[(out.spec == spec) & (out.term == t)]
            if not len(r):
                continue
            r = r.iloc[0]
            print(f"  {spec} {t}: coef={r['coef']:+.2f} p={r['p']:.4f} "
                  f"[{r['ci_lo']:+.2f}, {r['ci_hi']:+.2f}]")
    for spec in ["E1_ev_era_dose", "E2_ev_era_dum"]:
        t = "dose_1000" if spec.endswith("dose") else EV_ERA_DUMMY
        r = out[(out.spec == spec) & (out.term == t)]
        if len(r):
            r = r.iloc[0]
            print(f"  {spec} {t}: coef={r['coef']:+.2f} p={r['p']:.4f} "
                  f"[{r['ci_lo']:+.2f}, {r['ci_hi']:+.2f}]")


if __name__ == "__main__":
    main()
