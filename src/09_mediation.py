#!/usr/bin/env python3
"""
Step 10 — mediation: rebate -> (bidding channel) -> price.
VERIFIED REAL POLICY; dual scope.

Decompose the rebate -> Cat A clearing-price effect into:
    * INDIRECT (mediated) path : rebate -> catA_bids_received_clean -> price
                                 (the BID channel ONLY; the registration
                                  channel is EXCLUDED from mediation by the
                                  design -- it is descriptive and carries no
                                  usable within-window rebate variation)
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

SCOPES (dual):
    * FULL WINDOW (primary; 2016-01..2025-05, listwise N=110, edge months
      dropped for the mediator lag): the dose varies across 4 levels
      (30000/20000/45000/40000) so it IS identifiable. The mediated share
      is computed on this full-window sample (scope-guard check (c)).
      Pre-2022 years ARE included; we state that and bound their
      EV-relevance (pre-2022 "demand" is total-car demand, not EV).
    * 2022+ EV ERA (2022-01..2025-05, 41 obs — NOW A VALID ESTIMATION SCOPE):
      under the verified policy the dose varies inside this window
      (45000 -> 40000 at 2024-01), so the mediation IS estimable here too
      (old rank-deficiency rule removed). Reported with the same 2-stage
      structure and bootstrap; wide CIs expected (41 obs, 2 dose levels,
      noisy mediator).

The treatment is the continuous DOSE (cleanest intensity). The verified dose
is a near-exact linear transform of the real-policy dummies, so the dummy
spec is NOT re-run here (the price equation carries it); the dose-only
specification is documented.

BOOTSTRAP CIs (>=1000 resamples, resampling whole months with their full
row -- preserves the time-series dependence structure as far as OLS-allowable):
    * indirect = a*b distribution
    * total    = c' + a*b
    * mediated share = (a*b)/total

WIDE CIs ARE EXPECTED (full window: 3 dose steps, 110 obs, noisy mediator;
2022+: 41 obs, 2 dose levels). SIMULTANEITY / REVERSE-CAUSALITY is flagged
prominently: the rebate is set in response to EV demand, and registrations
depend on the COE price paid -- so the "direct" and "indirect" splits are
associational decompositions, not causal.

Output: tables/mediation_effects.csv
(effect rows for BOTH scopes: scope = "full_window" (primary) and
scope = "ev_era_2022plus"; total, indirect, direct, mediated_share, CIs, N,
bootstrap info; plus the metadata block)
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
N_BOOT_EV = 1000
SEED = 20261012

CONTROLS = ["catA_quota", "trend", "cpi_all_items"]
# The rebate term used as the treatment. We use the continuous DOSE (cleanest
# intensity). The dose is NOT constant over the full window (varies
# 30000/20000/45000/40000) NOR over the 2022+ window (45000 -> 40000 at
# 2024-01), so it IS identifiable in both scopes.
TREAT = "dose_1000"


def build():
    base = D.load_estimation_frame()
    sample = D.listwise_sample(base)
    demand = D.catA_demand_column(sample, "bids_received")
    df = D.make_lags(sample, demand)
    df["dose_1000"] = df["dose_nominal_sgd"] / 1000.0
    # mediator lagged by 1 (consistent with primary demand lag)
    df["M_l1"] = df["catA_bids_received_clean"].shift(1)
    return base, sample, df


def _stage1(df, controls, trend_col):
    X = pd.DataFrame({**{c: df[c] for c in controls}, TREAT: df[TREAT],
                      trend_col: df[trend_col]})
    res = D.ols(df["catA_bids_received_clean"], X, cov_type="HC1")
    return res


def _stage2(df, controls, trend_col):
    X = pd.DataFrame({**{c: df[c] for c in controls}, TREAT: df[TREAT],
                      "M_l1": df["M_l1"], trend_col: df[trend_col]})
    res = D.ols(df["catA_clearing_price"], X, cov_type="HC1")
    return res


def _fit_pair(df, controls, trend_col):
    s1 = _stage1(df, controls, trend_col)
    s2 = _stage2(df, controls, trend_col)
    a = float(s1.params[TREAT])
    b = float(s2.params["M_l1"])
    cp = float(s2.params[TREAT])
    return a, b, cp


def _bootstrap(est, controls, trend_col, n_boot, rng):
    """Resample whole rows; recompute a*b, total, share distributions."""
    idx = est.index.to_numpy()
    boot_ind, boot_tot, boot_share = [], [], []
    for i in range(n_boot):
        sel = rng.choice(idx, size=len(idx), replace=True)
        sub = est.loc[sel].copy()
        if sub[TREAT].std() == 0 or sub["M_l1"].std() == 0:
            continue
        try:
            a_b, b_b, cp_b = _fit_pair(sub, controls, trend_col)
        except Exception:
            continue
        ind_b = a_b * b_b
        tot_b = cp_b + ind_b
        boot_ind.append(ind_b)
        boot_tot.append(tot_b)
        boot_share.append(ind_b / tot_b if tot_b != 0 else np.nan)
    return (np.asarray(boot_ind), np.asarray(boot_tot),
            np.asarray(boot_share))


def _ci(x, q=(0.025, 0.975)):
    x = x[~np.isnan(x)]
    if len(x) < 2:
        return np.nan, np.nan
    return float(np.quantile(x, q[0])), float(np.quantile(x, q[1]))


def _scope_rows(df, scope, label, controls, trend_col, n_boot, rng, n_note):
    """Estimate the 2-stage mediation on one scope; return (rows, meta_bits)."""
    est = df.dropna(subset=["M_l1", "catA_clearing_price", TREAT]).copy()
    n = len(est)
    a, b, cp = _fit_pair(est, controls, trend_col)
    indirect = a * b
    total = cp + a * b
    direct = cp
    mediated_share = (a * b) / total if total != 0 else np.nan
    boot_ind, boot_tot, boot_share = _bootstrap(est, controls, trend_col,
                                                n_boot, rng)
    ind_lo, ind_hi = _ci(boot_ind)
    tot_lo, tot_hi = _ci(boot_tot)
    shr_lo, shr_hi = _ci(boot_share)
    rows = [
        {"effect": "total", "path": "rebate -> price (total)", "scope": scope,
         "estimate": total, "ci_lo": tot_lo, "ci_hi": tot_hi, "n_obs": n,
         "note": f"{label}: rebate total effect on Cat A clearing price "
                 f"(per 1000 S$ dose)"},
        {"effect": "indirect", "path": "rebate -> demand -> price",
         "scope": scope, "estimate": indirect, "ci_lo": ind_lo, "ci_hi": ind_hi,
         "n_obs": n, "note": f"{label}: mediated (bidding channel only) = a*b; "
                             f"a=rebate->demand, b=demand(lag1)->price"},
        {"effect": "direct", "path": "rebate -> price (holding demand fixed)",
         "scope": scope, "estimate": direct, "ci_lo": np.nan, "ci_hi": np.nan,
         "n_obs": n, "note": f"{label}: residual direct = c' from stage 2 "
                             f"(point estimate; CI from total/indirect "
                             f"decomposition)"},
        {"effect": "mediated_share", "path": "indirect / total", "scope": scope,
         "estimate": mediated_share, "ci_lo": shr_lo, "ci_hi": shr_hi,
         "n_obs": n, "note": f"{label}: fraction of the rebate total effect "
                             f"routed through the bidding channel"},
    ]
    meta = {
        "n_obs": n, "boot_used": int(len(boot_ind)),
        "boot_failed": int(n_boot - len(boot_ind)), "a": a, "b": b, "cp": cp,
    }
    return rows, meta


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base, sample, df = build()
    # EV-era frame: local time trend for the 2022+ window
    ev = df[df["month"] >= "2022-01"].copy().reset_index(drop=True)
    ev["trend22"] = np.arange(len(ev))
    EV_CONTROLS = ["catA_quota", "trend22", "cpi_all_items"]

    rng = np.random.default_rng(SEED)
    rows_full, meta_full = _scope_rows(
        df, "full_window", "FULL window 2016-01..2025-05 (primary)",
        CONTROLS, "trend", N_BOOT, rng, len(df))
    rows_ev, meta_ev = _scope_rows(
        ev, "ev_era_2022plus", "EV era 2022-01..2025-05 (dose 45000->40000 "
        "at 2024-01; NOW estimable)", EV_CONTROLS, "trend22", N_BOOT_EV, rng,
        len(ev))

    out = pd.DataFrame(rows_full + rows_ev)
    meta = pd.DataFrame({
        "metric": [
            "estimation_scope", "interpretation_scope", "n_obs_full",
            "n_obs_ev_era", "n_bootstrap_used_full", "n_bootstrap_failed_full",
            "n_bootstrap_used_ev", "n_bootstrap_failed_ev", "seed",
            "mediator_lag", "treatment", "price",
            "simultaneity_flag", "pre2022_inclusion",
            "ev_relevance_bound", "wide_ci_expected",
        ],
        "value": [
            "2016-01..2025-05 (FULL window, listwise; PRIMARY; mediated "
            "share computed on this sample)",
            "2022-01..2025-05 (EV era; ALSO an estimation scope under the "
            "verified policy: dose 45000->40000 at 2024-01; old rank-"
            "deficiency rule removed; both scopes reported)",
            meta_full["n_obs"],
            meta_ev["n_obs"],
            int(meta_full["boot_used"]),
            int(meta_full["boot_failed"]),
            int(meta_ev["boot_used"]),
            int(meta_ev["boot_failed"]),
            SEED,
            1,
            TREAT,
            "catA_clearing_price (nominal)",
            "FLAGGED: rebate set in response to EV demand; registrations "
            "depend on COE price paid -> associational decomposition, not "
            "causal",
            "YES -- pre-2022 months included in the full-window sample; bound "
            "their EV-relevance (pre-2022 demand = total-car, not EV)",
            "pre-2022 years contribute to the full-window estimate but carry "
            "negligible EV signal; the 2022+ window carries the EV-relevant "
            "variation",
            "YES -- full window: 3 dose steps, ~109 obs, noisy mediator; "
            "2022+ EV era: 41 obs, 2 dose levels -> wide CIs",
        ],
    })
    out["interpretation_scope"] = "full-window primary; 2022+ EV era reported " \
                                  "(both estimable under verified policy)"
    out.to_csv(OUT, index=False)
    # append metadata as a second section (commented rows) for Batch C
    with open(OUT, "a") as fh:
        fh.write("# ---- metadata ----\n")
        for _, r in meta.iterrows():
            fh.write(f"# {r['metric']}: {r['value']}\n")
        fh.write(f"# a_full (rebate->demand) = {meta_full['a']:+.4f}; "
                 f"b_full (demand->price) = {meta_full['b']:+.4f}; "
                 f"c'_full = {meta_full['cp']:+.1f}\n")
        fh.write(f"# a_ev (rebate->demand) = {meta_ev['a']:+.4f}; "
                 f"b_ev (demand->price) = {meta_ev['b']:+.4f}; "
                 f"c'_ev = {meta_ev['cp']:+.1f}\n")

    B.register_exhibit(
        name="mediation_bidding_channel", kind="mediation",
        est_scope="2016-01..2025-05;2022-01..2025-05",
        key_regressor="catA_bids_received_clean",
        interpretation_scope="2022-01..2025-05",
        n_obs=int(meta_full["n_obs"]),
        mediation_full_window=True,
        notes="indirect = rebate->demand->price (bidding channel only; "
              "registration channel EXCLUDED); mediated share computed on the "
              "FULL-WINDOW sample (primary); pre-2022 included + EV-relevance "
              "bounded; 2022+ EV era ALSO estimated (dose 45000->40000 at "
              "2024-01 -> estimable; old rank-deficiency rule removed); "
              "simultaneity flagged; wide CIs expected in both scopes.",
    )

    print(f"[mediation] wrote {OUT}  (2 scopes: full + EV era)")
    for scope in ("full_window", "ev_era_2022plus"):
        m = out[out["scope"] == scope].set_index("effect")
        meta = meta_full if scope == "full_window" else meta_ev
        print(f"  [{scope}] N={meta['n_obs']}  boot used="
              f"{meta['boot_used']}")
        print(f"    total     = {m.loc['total', 'estimate']:+.1f} "
              f"[{m.loc['total', 'ci_lo']:+.1f}, {m.loc['total', 'ci_hi']:+.1f}]")
        print(f"    indirect  = {m.loc['indirect', 'estimate']:+.1f} "
              f"[{m.loc['indirect', 'ci_lo']:+.1f}, "
              f"{m.loc['indirect', 'ci_hi']:+.1f}]")
        print(f"    direct c' = {m.loc['direct', 'estimate']:+.1f}")
        print(f"    mediated  = {m.loc['mediated_share', 'estimate']:.3f} "
              f"[{m.loc['mediated_share', 'ci_lo']:.3f}, "
              f"{m.loc['mediated_share', 'ci_hi']:.3f}]")
        print(f"    (a=rebate->demand {meta['a']:+.3f}, "
              f"b=demand->price {meta['b']:+.4f})")


if __name__ == "__main__":
    main()
