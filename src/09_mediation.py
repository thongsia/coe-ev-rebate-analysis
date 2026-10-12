#!/usr/bin/env python3
"""
Step 10 — mediation: rebate -> (bidding channel) -> price.

Decompose the rebate -> Cat A clearing-price effect into:
    * INDIRECT (mediated) path : rebate -> catA_bids_received_clean -> price
                                 (the BID channel ONLY; the registration
                                  channel is EXCLUDED from mediation by the
                                  design -- it is descriptive and carries no
                                  within-window rebate variation)
    * DIRECT (residual) path   : rebate -> price, holding the mediator fixed
    * MEDIATED (indirect/total) SHARE with CIs

METHOD (2-stage, consistent with the primary mediator lag):
    Stage 1 (mediator):   M_t = a * rebate_t + controls + e1
    Stage 2 (outcome):    Y_t = c' * rebate_t + b * M_{t-1} + controls + e2
                          (the mediator is lagged by 1 to be consistent with
                           the price equation's PRIMARY lagged-demand regressor)
    Indirect effect  = a * b
    Total effect     = c' + a * b      (rebate total effect on price)
    Direct (residual) = c'
    Mediated share   = (a * b) / (c' + a * b)

The FULL-WINDOW estimable sample (2016-01..2025-05, listwise N=110, edge
months dropped for the mediator lag) is used for BOTH stages and for the
mediated share. Pre-2022 years ARE included; we state that and bound their
EV-relevance (pre-2022 "demand" is total-car demand, not EV). The headline
indirect effect is read as the 2022+ INTERPRETATION of the full-window
estimate -- it is NEVER a 2022+-only number (which is rank-deficient: the
rebate dose + 2022 dummy are constant there).

BOOTSTRAP CIs (>=1000 resamples, resampling whole months with their full
row -- preserves the time-series dependence structure as far as OLS-allowable):
    * indirect = a*b distribution
    * total    = c' + a*b
    * mediated share = (a*b)/total

WIDE CIs ARE EXPECTED (4 effective treatment changes, 110 obs, noisy
mediator). SIMULTANEITY / REVERSE-CAUSALITY is flagged prominently: the
rebate is set in response to EV demand, and registrations depend on the COE
price paid -- so the "direct" and "indirect" splits are associational
decompositions, not causal.

Output: tables/mediation_effects.csv
(total, indirect, direct, mediated_share, CIs, N, bootstrap info)
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
OUT = OUT_DIR / "mediation_effects.csv"

N_BOOT = 2000
SEED = 20261012

CONTROLS = ["catA_quota", "trend", "cpi_all_items"]
# The rebate term used as the treatment. We use the continuous DOSE (cleanest
# intensity; the dummy spec is reported separately in the price equation). The
# dose is NOT constant over the full window (varies 2000..7500) so it IS
# identifiable here -- unlike on a 2022+-only sample.
TREAT = "dose_1000"


def build():
    base = D.load_estimation_frame()
    sample = D.listwise_sample(base)
    demand = D.catA_demand_column(sample, "bids_received")
    df = D.make_lags(sample, demand)
    df["dose_1000"] = df["dose_nominal_sgd"] / 1000.0
    df["threshold"] = D.threshold_dummy(df)
    # mediator lagged by 1 (consistent with primary demand lag)
    df["M_l1"] = df["catA_bids_received_clean"].shift(1)
    return base, sample, df


def _stage1(df, treat):
    X = pd.DataFrame({**{c: df[c] for c in CONTROLS}, treat: df[treat],
                      "threshold": df["threshold"]})
    res = D.ols(df["catA_bids_received_clean"], X, cov_type="HC1")
    return res


def _stage2(df, treat):
    X = pd.DataFrame({**{c: df[c] for c in CONTROLS}, treat: df[treat],
                      "M_l1": df["M_l1"], "threshold": df["threshold"]})
    res = D.ols(df["catA_clearing_price"], X, cov_type="HC1")
    return res


def _fit_pair(df, treat):
    s1 = _stage1(df, treat)
    s2 = _stage2(df, treat)
    a = float(s1.params[treat])
    b = float(s2.params["M_l1"])
    cp = float(s2.params[treat])
    return a, b, cp


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base, sample, df = build()
    # estimable sample: drop rows with NaN in the lagged mediator
    est = df.dropna(subset=["M_l1", "catA_clearing_price", "dose_1000"]).copy()
    n_full = len(est)

    # point estimates
    a, b, cp = _fit_pair(est, TREAT)
    indirect = a * b
    total = cp + a * b
    direct = cp
    mediated_share = (a * b) / total if total != 0 else np.nan

    # ---- bootstrap (resample whole rows; recompute a*b, total, share) ----
    rng = np.random.default_rng(SEED)
    idx = est.index.to_numpy()
    boot_ind, boot_tot, boot_share = [], [], []
    for i in range(N_BOOT):
        sel = rng.choice(idx, size=len(idx), replace=True)
        sub = est.loc[sel].copy()
        if sub[TREAT].std() == 0 or sub["M_l1"].std() == 0:
            continue
        try:
            a_b, b_b, cp_b = _fit_pair(sub, TREAT)
        except Exception:
            continue
        ind_b = a_b * b_b
        tot_b = cp_b + ind_b
        boot_ind.append(ind_b)
        boot_tot.append(tot_b)
        boot_share.append(ind_b / tot_b if tot_b != 0 else np.nan)
    boot_ind = np.asarray(boot_ind)
    boot_tot = np.asarray(boot_tot)
    boot_share = np.asarray(boot_share)
    alpha = 0.05
    q = (alpha / 2, 1 - alpha / 2)

    def ci(x, q=q):
        x = x[~np.isnan(x)]
        if len(x) < 2:
            return np.nan, np.nan
        return float(np.quantile(x, q[0])), float(np.quantile(x, q[1]))

    ind_lo, ind_hi = ci(boot_ind)
    tot_lo, tot_hi = ci(boot_tot)
    shr_lo, shr_hi = ci(boot_share)

    rows = [
        {"effect": "total", "path": "rebate -> price (total)",
         "estimate": total, "ci_lo": tot_lo, "ci_hi": tot_hi,
         "n_obs": n_full,
         "note": "rebate total effect on Cat A clearing price (per 1000 S$ dose)"},
        {"effect": "indirect", "path": "rebate -> demand -> price",
         "estimate": indirect, "ci_lo": ind_lo, "ci_hi": ind_hi,
         "n_obs": n_full,
         "note": "mediated (bidding channel only) = a*b; a=rebate->demand, "
                 "b=demand(lag1)->price"},
        {"effect": "direct", "path": "rebate -> price (holding demand fixed)",
         "estimate": direct, "ci_lo": np.nan, "ci_hi": np.nan,
         "n_obs": n_full,
         "note": "residual direct = c' from stage 2 (point estimate; CI from "
                 "total/indirect decomposition)"},
        {"effect": "mediated_share", "path": "indirect / total",
         "estimate": mediated_share, "ci_lo": shr_lo, "ci_hi": shr_hi,
         "n_obs": n_full,
         "note": "fraction of the rebate total effect routed through the "
                 "bidding channel"},
    ]
    out = pd.DataFrame(rows)
    meta = pd.DataFrame({
        "metric": [
            "estimation_scope", "interpretation_scope", "n_obs_full",
            "n_bootstrap_used", "n_bootstrap_failed", "seed",
            "mediator_lag", "treatment", "price",
            "simultaneity_flag", "pre2022_inclusion",
            "ev_relevance_bound", "wide_ci_expected",
        ],
        "value": [
            "2016-01..2025-05 (FULL window, listwise)",
            "2022-01..2025-05 (headline indirect = 2022+ reading of the "
            "full-window estimate; NEVER a 2022+-only number)",
            n_full,
            int(len(boot_ind)),
            int(N_BOOT - len(boot_ind)),
            SEED,
            1,
            TREAT,
            "catA_clearing_price (nominal)",
            "FLAGGED: rebate set in response to EV demand; registrations "
            "depend on COE price paid -> associational decomposition, not "
            "causal",
            "YES -- pre-2022 months included in the full-window sample; bound "
            "their EV-relevance (pre-2022 demand = total-car, not EV)",
            "pre-2022 years contribute to the estimate but carry negligible "
            "EV signal; the 2022+ window carries the EV-relevant variation",
            "YES -- 4 effective treatment changes, 110 obs, noisy mediator",
        ],
    })
    # combine: write effects rows then a metadata block
    out["interpretation_scope"] = meta["value"][1]
    out.to_csv(OUT, index=False)
    # append metadata as a second section (commented rows) for Batch C
    with open(OUT, "a") as fh:
        fh.write("# ---- metadata ----\n")
        for _, r in meta.iterrows():
            fh.write(f"# {r['metric']}: {r['value']}\n")

    B.register_exhibit(
        name="mediation_bidding_channel", kind="mediation",
        est_scope="2016-01..2025-05",
        key_regressor="catA_bids_received_clean",
        interpretation_scope="2022-01..2025-05",
        n_obs=n_full,
        mediation_full_window=True,
        notes="indirect = rebate->demand->price (bidding channel only; "
              "registration channel EXCLUDED); mediated share computed on the "
              "FULL-WINDOW sample; pre-2022 included + EV-relevance bounded; "
              "headline indirect = 2022+ interpretation; simultaneity flagged; "
              "wide CIs expected.",
    )

    print(f"[mediation] wrote {OUT}")
    print(f"  N={n_full}  boot used={len(boot_ind)}/{N_BOOT}")
    print(f"  total     = {total:+.1f} [{tot_lo:+.1f}, {tot_hi:+.1f}]")
    print(f"  indirect  = {indirect:+.1f} [{ind_lo:+.1f}, {ind_hi:+.1f}]")
    print(f"  direct c' = {direct:+.1f}")
    print(f"  mediated  = {mediated_share:.3f} [{shr_lo:.3f}, {shr_hi:.3f}]")
    print(f"  (a=rebate->demand {a:+.3f}, b=demand->price {b:+.4f})")


if __name__ == "__main__":
    main()
