#!/usr/bin/env python3
"""
Step 11 — event study (per the episode discipline).

Episodes (per the saturated Dory spec):
  * 2016-2018 episode : the three closely-spaced changes (Nov-2016 up,
    Jan-2018 down, Sep-2018 up, spaced <15 months) are treated as ONE
    episode, anchored at its first change (2016-11). Interpreted as
    TOTAL / LOW-EMISSION demand -- NEVER EV-specific (there is no EV signal
    pre-2022).
  * Jan-2022 event    : co-occurs with the 97->110kW Cat A threshold change.
    The threshold dummy is numerically identical to a 2022-01+ step, so it
    would be perfectly collinear with the post-onset event dummies; we
    therefore BOUND interpretation -- the Jan-2022 event-study coefficients
    reflect the COMBINED rebate + threshold effect, not the rebate alone.

Each event-study regression is estimated on a window that SPANS pre- AND
post-treatment months (so LEADS are defined):
    * pre-base   : months strictly before the lead window (reference period)
    * leads      : L monthly dummies immediately before onset (pre-trend test)
    * onset      : the treatment month
    * lags       : bucketed post-onset dummies
plus controls (linear time trend, Cat A quota, CPI). The dependent variable is
the Cat A clearing price (nominal), consistent with the price equation.

Pre-trend verification: the lead coefficients are reported individually (with
CIs) and JOINTLY (Wald test H0: all lead betas = 0). We report HONESTLY when a
pre-existing trend contaminates the episode (a non-zero lead or a failed joint
test is flagged, not papered over).

The Jan-2026 cap cut lives in the COE-only extension (2025-06..2026-10) and is
DESCRIPTIVE ONLY, bounded by the 2026 PARF cut + supply trough; it does NOT
enter the joint-window event study.

Outputs:
    tables/event_study_coefficients.csv   (per-episode event-time dummies, CIs)
    tables/event_study_prechecks.csv      (pre-trend test results per episode)
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bootstrap as B  # noqa: E402

D = B.D
OUT_DIR = D.ROOT / "tables"
OUT_COEF = OUT_DIR / "event_study_coefficients.csv"
OUT_PRE = OUT_DIR / "event_study_prechecks.csv"

CONTROLS = ["catA_quota", "cpi_all_items"]
# NOTE: no linear time trend in the event study. The pre-treatment reference
# group (all months strictly before the lead window) carries the pre-onset
# level, and the lead dummies measure deviations from that reference. A
# separate linear trend is near-collinear with the event-time dummies once the
# pandemic gap (2020-04/05/06) breaks lead contiguity, which makes the joint
# pre-trend Wald constraint rank-deficient. The bucketed lag dummies absorb
# the post-onset time structure.


def _month_index(df):
    """0-based month index from the 'YYYY-MM' column (true calendar months,
    uniform spacing). Using days//30 produces ties (months are 28-31 days)
    and breaks the trend/dummy separation -> rank deficiency."""
    m = pd.to_datetime(df["month"], format="%Y-%m")
    return (m.dt.year * 12 + m.dt.month).to_numpy() - (
        m.iloc[0].year * 12 + m.iloc[0].month
    )


def build():
    base = D.load_estimation_frame()
    sample = D.listwise_sample(base)
    df = sample.copy().reset_index(drop=True)
    df["mi"] = _month_index(df)
    df["trend"] = df["mi"].astype(float)
    return base, df


def event_study(df, onset_month, lead_months, lag_buckets, label):
    """Estimate an event-study with onset_month as the treatment start.

    lag_buckets: list of (name, first_offset, last_offset) in months relative
    to onset (offset 0 = onset month itself handled separately).
    Returns (coef_df, precheck_dict).
    """
    onset_mi = df.loc[df["month"] == onset_month, "mi"].iloc[0]
    lead_start = onset_mi - lead_months

    # event-time buckets
    t = df["mi"] - onset_mi
    # pre-base: t < -lead_months (reference)
    pre_base = t < -lead_months
    # leads: -lead_months <= t <= -1  (monthly)
    lead_mask = (t >= -lead_months) & (t <= -1)
    # onset: t == 0
    onset_mask = t == 0
    # lags: t >= 1, bucketed
    lag_masks = {}
    for name, lo, hi in lag_buckets:
        m = (t >= lo) & (t <= hi) if hi != -1 else (t >= lo)
        lag_masks[name] = m

    # build design (NO linear trend; pre-base is the reference group)
    X = pd.DataFrame({c: df[c] for c in CONTROLS}, index=df.index)
    lead_terms = {}
    for k in range(-lead_months, 0):
        name = f"lead_{k}"
        X[name] = ((t == k)).astype(int)
        lead_terms[name] = (t == k)
    X["onset_0"] = onset_mask.astype(int)
    for name, m in lag_masks.items():
        X[name] = m.astype(int)
    # pre-base indicator (for reference; constant absorbs it but keep explicit
    # count for N reporting)
    pre_base_count = int(pre_base.sum())

    y = df["catA_clearing_price"]
    d = pd.concat([y.rename("__y__").reset_index(drop=True),
                   X.reset_index(drop=True)], axis=1).dropna()
    yv = d.pop("__y__")
    xv = sm.add_constant(d.astype(float))
    xv = xv.rename(columns={0: "const"}) if 0 in xv.columns else xv
    res = sm.OLS(yv, xv).fit(cov_type="HC1")

    ci = res.conf_int()
    rows = []
    for nm in ["onset_0"] + list(lag_masks) + list(lead_terms):
        rows.append({
            "episode": label, "term": nm,
            "coef": float(res.params[nm]), "se": float(res.bse[nm]),
            "p": float(res.pvalues[nm]),
            "ci_lo": float(ci.loc[nm, 0]), "ci_hi": float(ci.loc[nm, 1]),
            "n_obs": int(res.nobs),
            "role": "lead" if nm in lead_terms else
                    ("onset" if nm == "onset_0" else "lag"),
        })

    # ---- joint pre-trend Wald test (H0: all lead betas = 0) ----
    # Manual Wald (robust): F = (b_R' V_R^-1 b_R) / q on the q lead betas.
    # We report the RANK of the constraint covariance V_R; if it is < q the
    # constraint is degenerate (each lead dummy is a single month here), so we
    # fall back to a Moore-Penrose pseudo-inverse and flag it. The individual
    # lead p-values (reported separately) remain the primary pre-trend evidence.
    lead_names = list(lead_terms)
    R = np.zeros((len(lead_names), len(xv.columns)))
    cl = list(xv.columns)
    for i, nm in enumerate(lead_names):
        R[i, cl.index(nm)] = 1.0
    beta = res.params.to_numpy()
    V = res.cov_params().to_numpy()
    bR = R @ beta
    VR = R @ V @ R.T
    vr_rank = int(np.linalg.matrix_rank(VR))
    Vinv = np.linalg.pinv(VR)
    q = len(lead_names)
    wald_stat = float(bR @ Vinv @ bR) / q
    # degrees of freedom = rank(VR) (effective constraints), not q
    dof = max(vr_rank, 1)
    from scipy import stats as _sp

    wald_f = wald_stat
    wald_p = float(_sp.f.sf(wald_stat, dof, max(len(df) - len(xv.columns), 1)))
    constraint_rank_ok = (vr_rank == q)
    lead_sig = any(r["p"] < 0.10 for r in rows if r["role"] == "lead")
    pre_trend_clean = (not lead_sig) and (wald_p >= 0.10)
    if pre_trend_clean:
        interp_clean = "CLEAN pre-trend (leads ~0, joint Wald p>0.10)"
    else:
        interp_clean = (
            "CONTAMINATED pre-trend: leads not ~0 (a pre-existing secular "
            "trend is present); onset effect is a BOUND relative to a moving "
            "pre-trend, not a clean causal jump. Reported honestly."
        )
    precheck = {
        "episode": label,
        "onset_month": onset_month,
        "lead_months": lead_months,
        "pre_base_months": pre_base_count,
        "n_obs": int(res.nobs),
        "joint_leads_wald_F": wald_f,
        "joint_leads_wald_p": wald_p,
        "constraint_rank": vr_rank,
        "constraint_rank_ok": constraint_rank_ok,
        "any_lead_p_lt_010": lead_sig,
        "pre_trend_clean": pre_trend_clean,
        "pre_trend_interpretation": interp_clean,
        "interpretation": (
            "TOTAL/low-emission demand episode; never EV-specific"
            if label.startswith("2016") else
            "rebate + co-timed 97->110kW threshold COMBINED (bounded); "
            "EV-relevant from 2022-01"
        ),
    }
    return pd.DataFrame(rows), precheck


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base, df = build()

    coef_rows = []
    pre_rows = []

    # 2016-2018 episode (one episode, anchored at 2016-11)
    c, p = event_study(
        df, onset_month="2016-11", lead_months=6,
        lag_buckets=[("lag_1_9", 1, 9), ("lag_10_22", 10, 22),
                     ("lag_23_plus", 23, -1)],
        label="2016-2018_episode_total_low_emission",
    )
    coef_rows.append(c)
    pre_rows.append(p)

    # Jan-2022 event (bounded: rebate + threshold combined)
    c, p = event_study(
        df, onset_month="2022-01", lead_months=6,
        lag_buckets=[("lag_1_6", 1, 6), ("lag_7_17", 7, 17),
                     ("lag_18_plus", 18, -1)],
        label="2022-01_eeai_rebate_PLUS_threshold_bounded",
    )
    coef_rows.append(c)
    pre_rows.append(p)

    coef = pd.concat(coef_rows, ignore_index=True)
    # de-dup lead rows (we appended them twice in event_study)
    coef = coef.drop_duplicates(subset=["episode", "term"], keep="last")
    coef = coef.sort_values(["episode", "role", "term"]).reset_index(drop=True)
    coef.to_csv(OUT_COEF, index=False)

    pre = pd.DataFrame(pre_rows)
    # Jan-2026 descriptive note (COE-only extension; does not enter the model)
    pre_note = pd.DataFrame([{
        "episode": "2026-01_capcut_DESCRIPTIVE_ONLY",
        "onset_month": "2026-01",
        "lead_months": None,
        "pre_base_months": None,
        "n_obs": None,
        "joint_leads_wald_F": None,
        "joint_leads_wald_p": None,
        "constraint_rank": None,
        "constraint_rank_ok": None,
        "any_lead_p_lt_010": None,
        "pre_trend_clean": "NOT ESTIMATED (outside joint window)",
        "pre_trend_interpretation": "n/a",
        "interpretation": "Jan-2026 EEAI cap cut ($15k->$7.5k) lives in the "
                          "COE-only extension 2025-06..2026-10; descriptive "
                          "only, bounded by the 2026 PARF cut + supply trough. "
                          "Does NOT enter the joint-window event study.",
    }])
    pre = pd.concat([pre, pre_note], ignore_index=True)
    pre.to_csv(OUT_PRE, index=False)

    B.register_exhibit(
        name="event_study", kind="event_study",
        est_scope="2016-01..2025-05",
        key_regressor="catA_clearing_price (event-time dummies on dose regime)",
        interpretation_scope="2022-01..2025-05 (Jan-2022 event is the "
                             "EV-relevant one; bounded by threshold)",
        n_obs=int(df["catA_clearing_price"].notna().sum()),
        event_spans_pre_post=True,
        notes="2016-2018 = ONE episode (total/low-emission, never EV); Jan-2022 "
              "co-timed with 97->110kW threshold -> bounded interpretation; "
              "windows span pre+post so leads defined; pre-trends tested "
              "jointly + individually; 2026 cap cut descriptive only.",
    )

    print(f"[event_study] wrote {OUT_COEF}  rows={len(coef)}")
    print(f"[event_study] wrote {OUT_PRE}  rows={len(pre)}")
    for p in pre_rows:
        print(f"  {p['episode']}: onset={p['onset_month']} N={p['n_obs']} "
              f"pre_trend_clean={p['pre_trend_clean']} "
              f"(joint Wald F={p['joint_leads_wald_F']:.3f} "
              f"p={p['joint_leads_wald_p']:.3g}, "
              f"constraint_rank={p['constraint_rank']}/{p['lead_months']})")
        print(f"      {p['pre_trend_interpretation']}")
        onset = coef[(coef.episode == p['episode']) & (coef.term == 'onset_0')]
        if len(onset):
            o = onset.iloc[0]
            print(f"      onset coef={o['coef']:+.0f} [{o['ci_lo']:+.0f}, "
                  f"{o['ci_hi']:+.0f}] p={o['p']:.3f}")


if __name__ == "__main__":
    main()
