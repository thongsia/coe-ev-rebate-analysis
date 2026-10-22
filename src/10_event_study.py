#!/usr/bin/env python3
"""
Step 11 — event study (5 in-window verified-policy events).

EVENTS (all five are real, cited policy changes):
  * 2018-01 : CEVS lapse + VES onset (dose 30000 revised-CEVS A1 -> 20000
    VES A1; both verified). TOTAL / low-emission + early-clean demand era —
    NOT yet EV-specific at scale.
  * 2021-01 : Enhanced VES (A1 raised 20000 -> 25000) + EEAI introduction
    (dose 20000 -> 45000; verified stack). EV-relevant from here on.
  * 2022-01 : $0 ARF floor for EVs (TAX provision, dose UNCHANGED).
  * 2022-05 : 97->110 kW Category A threshold for electric cars (CONFOUNDER,
    dose UNCHANGED; effective from the May 2022 bidding exercise, LTA
    announcement 14 Apr 2022). This is the confounder the price/bidding
    exhibits control with reg_threshold_110kw_202205; estimated here so its
    own price effect is visible and netted out of the 2024-01 reading.
  * 2024-01 : EEAI cap cut 20k -> 15k (dose 45000 -> 40000; verified). The
    EV-era step that makes the 2022+ window estimable.

Each event-study regression is estimated on a window that SPANS pre- AND
post-treatment months (so LEADS are defined):
    * pre-base   : months strictly before the lead window (reference period)
    * leads      : L monthly dummies immediately before onset (pre-trend test)
    * onset      : the treatment month
    * lags       : bucketed post-onset dummies
plus controls (Cat A quota, CPI — no linear trend: the pre-base reference
group carries the pre-onset level and a separate trend is near-collinear with
the event-time dummies once the pandemic gap breaks lead contiguity). The
dependent variable is the Cat A clearing price (nominal), consistent with the
price equation.

Pre-trend verification: the lead coefficients are reported individually (with
CIs) and JOINTLY (Wald test H0: all lead betas = 0). We report HONESTLY when a
pre-existing trend contaminates the episode (a non-zero lead or a failed joint
test is flagged, not papered over).

The Jan-2026 cap cut ($7,500 EEAI + $22,500 VES A1) and the 2027 EEAI cessation
live in / beyond the COE-only extension (2025-06..2026-10) and are
DESCRIPTIVE ONLY; they do NOT enter the joint-window event study.

Outputs:
    tables/event_study_coefficients.csv   (per-event event-time dummies, CIs)
    tables/event_study_prechecks.csv      (pre-trend test results per event)
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

# The 4 in-window verified-policy events (onset, lead months, lag buckets,
# label, interpretation)
EVENTS = [
    ("2018-01", 6,
     [("lag_1_6", 1, 6), ("lag_7_12", 7, 12), ("lag_13_plus", 13, -1)],
     "2018-01_cevs_lapse_VES_onset",
     "VES onset (CEVS lapse): dose 30000 (revised CEVS A1, verified) -> "
     "20000 (VES A1, verified); total/low-emission era — not yet EV-specific "
     "at scale"),
    ("2021-01", 6,
     [("lag_1_6", 1, 6), ("lag_7_12", 7, 12), ("lag_13_plus", 13, -1)],
     "2021-01_enhanced_VES_EEAI_stack",
     "Enhanced VES (A1 20000->25000) + EEAI (45% ARF, cap $20k): dose "
     "20000 -> 45000 (verified stack); EV-relevant from here on"),
    ("2022-01", 6,
     [("lag_1_6", 1, 6), ("lag_7_12", 7, 12), ("lag_13_plus", 13, -1)],
     "2022-01_ARF_floor_zero",
     "$0 ARF floor for EVs (TAX, dose UNCHANGED); any 2022-01 price move is "
     "the ARF-floor / market dynamics, NOT a rebate step (bounded)"),
    ("2022-05", 6,
     [("lag_1_6", 1, 6), ("lag_7_12", 7, 12), ("lag_13_plus", 13, -1)],
     "2022-05_threshold_110kw_catA",
     "97->110 kW Category A threshold for electric cars (CONFOUNDER, dose "
     "UNCHANGED; effective from the May 2022 bidding exercise, LTA 14 Apr "
     "2022); controlled by reg_threshold_110kw_202205 in the headline "
     "exhibits"),
    ("2024-01", 6,
     [("lag_1_6", 1, 6), ("lag_7_plus", 7, -1)],
     "2024-01_eeai_cap15k_step",
     "EEAI cap cut 20k -> 15k: dose 45000 -> 40000 (verified); the EV-era "
     "step that makes the 2022+ window estimable"),
]


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


def event_study(df, onset_month, lead_months, lag_buckets, label, interp):
    """Estimate an event-study with onset_month as the treatment start.

    lag_buckets: list of (name, first_offset, last_offset) in months relative
    to onset (offset 0 = onset month itself handled separately).
    Returns (coef_df, precheck_dict).
    """
    onset_mi = df.loc[df["month"] == onset_month, "mi"].iloc[0]
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
        "interpretation": interp,
    }
    return pd.DataFrame(rows), precheck


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base, df = build()

    coef_rows = []
    pre_rows = []
    for onset, lead, buckets, label, interp in EVENTS:
        c, p = event_study(df, onset_month=onset, lead_months=lead,
                           lag_buckets=buckets, label=label, interp=interp)
        coef_rows.append(c)
        pre_rows.append(p)

    coef = pd.concat(coef_rows, ignore_index=True)
    coef = coef.drop_duplicates(subset=["episode", "term"], keep="last")
    coef = coef.sort_values(["episode", "role", "term"]).reset_index(drop=True)
    coef.to_csv(OUT_COEF, index=False)

    pre = pd.DataFrame(pre_rows)
    # Jan-2026 / 2027 descriptive notes (COE-only extension; do not enter the model)
    pre_note = pd.DataFrame([
        {
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
            "interpretation": "Jan-2026 EEAI cap cut ($15k->$7.5k) + VES A1 "
                              "$22,500 (combined dose 27500) live in the "
                              "COE-only extension 2025-06..2026-10; descriptive "
                              "only, bounded by the 2026 PARF cut + supply "
                              "trough. Does NOT enter the joint-window event "
                              "study.",
        },
        {
            "episode": "2027-01_EEAI_cessation_DESCRIPTIVE_ONLY",
            "onset_month": "2027-01",
            "lead_months": None,
            "pre_base_months": None,
            "n_obs": None,
            "joint_leads_wald_F": None,
            "joint_leads_wald_p": None,
            "constraint_rank": None,
            "constraint_rank_ok": None,
            "any_lead_p_lt_010": None,
            "pre_trend_clean": "NOT ESTIMATED (beyond extension end 2026-10)",
            "pre_trend_interpretation": "n/a",
            "interpretation": "EEAI ceases 1 Jan 2027 (dose reverts to VES A1 "
                              "$20,000, 2027 extension window). Beyond the data; "
                              "documented for completeness only.",
        },
    ])
    pre = pd.concat([pre, pre_note], ignore_index=True)
    pre.to_csv(OUT_PRE, index=False)

    B.register_exhibit(
        name="event_study", kind="event_study",
        est_scope="2016-01..2025-05",
        key_regressor="catA_clearing_price (event-time dummies on the 5 "
                      "verified-policy events)",
        interpretation_scope="2021-01..2025-05 (EV-relevant events); 2022-01 "
                             "=$0 ARF floor (tax); 2022-05 = 97->110kW "
                             "threshold confounder",
        n_obs=int(df["catA_clearing_price"].notna().sum()),
        event_spans_pre_post=True,
        notes="5 verified-policy in-window events (2018-01, 2021-01, 2022-01, "
              "2022-05, 2024-01); 2022-01 = $0 ARF floor (tax), 2022-05 = "
              "97->110kW threshold confounder (separate events, both "
              "non-dose); windows span pre+post so leads defined; pre-trends "
              "tested jointly + individually; 2026 cap cut + 2027 EEAI "
              "cessation descriptive only.",
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
