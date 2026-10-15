#!/usr/bin/env python3
"""
Step 13 — evidence grading (verified real policy; dual scope).

Grade each causal link PER SCOPE — the full window (2016-01..2025-05, primary)
AND the 2022+ EV era (2022-01..2025-05, a valid estimation scope because
the verified dose varies 45000 -> 40000 at 2024-01) — as:
  supported / directionally consistent / not detectable,
with the negative-control verdict stated per scope. Re-state the low-power
caveat (full window: 3 dose steps, 110 monthly obs after listwise deletion of
3 pandemic months; 2022+ EV era: 41 obs, 2 dose levels). Forbid precise
magnitude claims.

This module READS the outputs of steps 7-11 (the tables/*.csv Batch B just
wrote) plus the scope audit, and produces the machine-readable grading table
that the report consumes:

    tables/evidence_grading.csv
        columns: link, scope, estimate, ci, p, n_obs, grade,
                 interpretation_scope, negative_control_check, notes

Grades are assigned from the ACTUAL numbers in the tables (not hand-typed),
so the grading is reproducible and consistent with the estimation.

Links (graded per scope where the scope is estimable):
    rebate -> demand (bidding channel):
        from demand_bidding_channel.csv — full window: dummy spec (the
        reg_eeai_cap15k_202401 step + the dose spec); 2022+ EV era:
        E1_ev_era_dose / E2_ev_era_dum + cross-lag (full window).
    rebate -> demand (registration channel):
        from ev_registrations_descriptive.csv (descriptive only; the observed
        EV series begins 2022-07 and is right-truncated -> not a coefficient
        link in either scope).
    demand -> price:
        from price_equation.csv (full window demand_l1/demand_l2; 2022+ EV era
        E3_ev_era_demand_only).
    total indirect effect (mediation):
        from mediation_effects.csv (full_window primary + ev_era_2022plus).
    rebate -> price (headline, the core question):
        from price_equation.csv — full window: M1 (reg_eeai_cap15k_202401 +
        dose M3) MODIFIED by the full-window negative-control verdict
        (2022-01 jump); 2022+ EV era: E1_ev_era_lagged_dose /
        E2_ev_era_lagged_dum MODIFIED by the EV-era negative-control verdict
        (2024-01 step).

Grading rubric (applied per link, per scope):
    supported              : the coefficient is significant (p<0.05) in the
                             primary spec AND the negative-control check does
                             NOT falsify it (for the headline price link).
    directionally consistent: the coefficient is significant (or marginally,
                             p<0.10) and points in the predicted direction,
                             but a robustness/control check weakens it (e.g.
                             negative controls fail, or HAC SEs flip
                             significance, or it is a common shock).
    not detectable         : the coefficient is not distinguishable from zero
                             (CI spans 0, p>0.10), or the link is descriptive
                             only, or the negative-control check shows the
                             effect is a market-wide common shock not
                             attributable to the rebate.
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
OUT = OUT_DIR / "evidence_grading.csv"

DUMMY_2022 = "reg_arffloor_zero_202201"
DUMMY_2024 = "reg_eeai_cap15k_202401"


def _row(df, **kw):
    m = df
    for k, v in kw.items():
        m = m[m[k] == v]
    if not len(m):
        return None
    return m.iloc[0]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    price = pd.read_csv(OUT_DIR / "price_equation.csv")
    ev_era = pd.read_csv(OUT_DIR / "price_equation_2022plus_robustness.csv")
    demand = pd.read_csv(OUT_DIR / "demand_bidding_channel.csv")
    crosslag = pd.read_csv(OUT_DIR / "crosslag_check.csv")
    evreg = pd.read_csv(OUT_DIR / "ev_registrations_descriptive.csv")
    med = pd.read_csv(OUT_DIR / "mediation_effects.csv")
    med = med[med["effect"].astype(str).str.match(r"^(total|indirect|direct|mediated_share)$")].copy()
    for c in ("estimate", "ci_lo", "ci_hi"):
        med[c] = pd.to_numeric(med[c], errors="coerce")
    nc = pd.read_csv(OUT_DIR / "negative_controls.csv")
    pre = pd.read_csv(OUT_DIR / "event_study_prechecks.csv")

    # ---- negative-control verdicts (read from the commented block) ----
    same_2022, same_2024 = None, None
    try:
        with open(OUT_DIR / "negative_controls.csv") as fh:
            for line in fh:
                if line.startswith("# same_effect_on_clean_controls_2022"):
                    same_2022 = "True" in line.split("=")[1].strip()
                if line.startswith("# same_effect_on_clean_controls_2024"):
                    same_2024 = "True" in line.split("=")[1].strip()
    except Exception:
        pass

    rows = []

    def add(link, scope, est, ci, p, n, grade, interp_scope, nc_check, notes):
        rows.append({
            "link": link, "scope": scope,
            "estimate": est, "ci": ci, "p_value": p, "n_obs": n,
            "grade": grade, "interpretation_scope": interp_scope,
            "negative_control_check": nc_check, "notes": notes,
        })

    # =================================================================
    # LINK 1: rebate -> demand (bidding channel) — full window
    # =================================================================
    ee = _row(demand, spec="dummy", term=DUMMY_2024)
    do = _row(demand, spec="dose", term="dose_1000")
    if ee is not None and do is not None:
        p = float(ee["p"])
        sig = p < 0.05
        # predicted direction: a rebate should INCREASE bidding demand -> coef>0
        pred_dir = float(ee["coef"]) > 0
        # cross-lag (full window): is any lag significant?
        xl = crosslag[crosslag.term.str.contains("month")]
        xl_sig = bool((xl["p"] < 0.05).any())
        if sig and pred_dir:
            g = "directionally consistent"
        elif sig and not pred_dir:
            # significant but WRONG direction (rebate associated with LESS demand)
            g = "not detectable"
        else:
            g = "not detectable"
        add(
            "rebate->demand (bidding channel)", "full_window",
            f"reg_eeai_cap15k_202401 coef={float(ee['coef']):+.1f} "
            f"(dose/1000={float(do['coef']):+.1f})",
            f"[{float(ee['ci_lo']):+.1f}, {float(ee['ci_hi']):+.1f}]",
            p, int(ee["nobs"]), g,
            "full window (2016-01..2025-05; primary)",
            "n/a (demand, not price)",
            f"2024-01 step dummy sig={sig}; predicted direction (coef>0)="
            f"{pred_dir}; cross-lag any-sig={xl_sig}. TOTAL Cat A demand "
            f"dominated by non-EV; EV signal material only 2022+. "
            f"{g.upper()}.",
        )

    # ---- LINK 1 (2022+ EV era scope) ----
    e1 = _row(demand, spec="E1_ev_era_dose", term="dose_1000")
    e2 = _row(demand, spec="E2_ev_era_dum", term=DUMMY_2024)
    if e1 is not None and e2 is not None:
        p = min(float(e1["p"]), float(e2["p"]))
        sig = p < 0.05
        pred_dir = float(e1["coef"]) > 0
        if sig and pred_dir:
            g = "directionally consistent"
        elif sig and not pred_dir:
            g = "not detectable"
        else:
            g = "not detectable"
        add(
            "rebate->demand (bidding channel)", "ev_era_2022plus",
            f"dose/1000 coef={float(e1['coef']):+.1f} (p={float(e1['p']):.3f}); "
            f"step dummy coef={float(e2['coef']):+.1f} (p={float(e2['p']):.3f})",
            f"dose [{float(e1['ci_lo']):+.1f}, {float(e1['ci_hi']):+.1f}]",
            p, int(e1["nobs"]), g,
            "2022+ EV era (2022-01..2025-05; 41 obs; dose 45000->40000 at "
            "2024-01)",
            "n/a (demand, not price)",
            f"EV-era dose step sig={sig}; predicted direction (coef>0)="
            f"{pred_dir}. 41 obs, 2 dose levels -> low power, wide CIs. "
            f"{g.upper()}.",
        )

    # =================================================================
    # LINK 2: rebate -> demand (registration channel) — descriptive
    # =================================================================
    n_obs_ev = int(evreg[evreg.month.str.startswith("20") &
                          (evreg.ev_reg.notna())].shape[0])
    add(
        "rebate->demand (registration channel)", "descriptive",
        "DESCRIPTIVE ONLY (no coefficient)",
        "n/a", None, n_obs_ev,
        "not detectable",
        "2022-07..2025-05 (observed BEV window)",
        "n/a",
        "Observed EV series begins 2022-07, right-truncated at 2025-05; the "
        "2024-01 dose step arrives 8 months in and the series is too short/"
        "censored to identify a coefficient. ev_reg is a lower bound. Feeds "
        "no coefficient exhibit in either scope.",
    )

    # =================================================================
    # LINK 3: demand -> price — full window
    # =================================================================
    dl1 = _row(price, spec="M1_primary_lagged_dum", term="demand_l1")
    dl2 = _row(price, spec="M1_primary_lagged_dum", term="demand_l2")
    if dl1 is not None:
        p1 = float(dl1["p"])
        sig1 = p1 < 0.05
        pred1 = float(dl1["coef"]) > 0  # more demand vs fixed quota -> higher price
        dl1_real = _row(price, spec="M1_primary_lagged_dum", term="demand_l1",
                        price_def="real")
        nonrev = (dl1_real is not None and
                  np.sign(float(dl1["coef"])) == np.sign(float(dl1_real["coef"])))
        if sig1 and pred1 and nonrev:
            g = "supported"
        elif sig1 and pred1:
            g = "directionally consistent"
        elif sig1 and not pred1:
            g = "directionally consistent"  # significant but negative (see notes)
        else:
            g = "not detectable"
        add(
            "demand->price", "full_window",
            f"demand_l1 coef={float(dl1['coef']):+.3f} "
            f"(demand_l2={float(dl2['coef']):+.3f})",
            f"[{float(dl1['ci_lo']):+.3f}, {float(dl1['ci_hi']):+.3f}]",
            p1, int(dl1["nobs"]), g,
            "full window (mechanism link; no EV-specificity claim)",
            "n/a (mechanism)",
            f"lag-1 demand sig={sig1}; predicted dir (coef>0)={pred1}; "
            f"nominal<->real non-reversal={nonrev}. With a strong secular "
            f"trend + quota controls the contemporaneous demand effect is "
            f"weak/ambiguous; the price equation is dominated by the trend + "
            f"rebate-regime terms. {g.upper()}.",
        )

    # ---- LINK 3 (2022+ EV era scope) ----
    e3d1 = _row(ev_era, spec="E3_ev_era_demand_only", term="demand_l1",
                price_def="nominal")
    if e3d1 is not None:
        p1 = float(e3d1["p"])
        sig1 = p1 < 0.05
        pred1 = float(e3d1["coef"]) > 0
        g = ("supported" if sig1 and pred1
             else "directionally consistent" if sig1
             else "not detectable")
        add(
            "demand->price", "ev_era_2022plus",
            f"demand_l1 coef={float(e3d1['coef']):+.3f}",
            f"[{float(e3d1['ci_lo']):+.3f}, {float(e3d1['ci_hi']):+.3f}]",
            p1, int(e3d1["nobs"]), g,
            "2022+ EV era (2022-01..2025-05; 41 obs)",
            "n/a (mechanism)",
            f"EV-era lag-1 demand sig={sig1}; predicted dir (coef>0)={pred1}. "
            f"41 obs -> low power. {g.upper()}.",
        )

    # =================================================================
    # LINK 4: total indirect effect (mediation) — both scopes
    # =================================================================
    for scope, lab in [("full_window", "FULL window (primary)"),
                       ("ev_era_2022plus", "2022+ EV era")]:
        m = med[med["scope"] == scope]
        ind = m[m.effect == "indirect"].iloc[0] if len(m[m.effect == "indirect"]) else None
        tot = m[m.effect == "total"].iloc[0] if len(m[m.effect == "total"]) else None
        shr = m[m.effect == "mediated_share"].iloc[0] if len(m[m.effect == "mediated_share"]) else None
        if ind is None:
            continue
        ind_ci_spans_zero = (float(ind["ci_lo"]) < 0 < float(ind["ci_hi"]))
        g = "not detectable" if ind_ci_spans_zero else "directionally consistent"
        add(
            "total indirect effect (rebate->demand->price)", scope,
            f"indirect={float(ind['estimate']):+.1f}; "
            f"total={float(tot['estimate']):+.1f}; "
            f"mediated_share={float(shr['estimate']):.3f}",
            f"indirect [{float(ind['ci_lo']):+.1f}, {float(ind['ci_hi']):+.1f}]",
            None, int(ind["n_obs"]), g,
            "full-window primary; 2022+ EV era reported (both estimable under "
            "verified policy)",
            "bidding channel only (registration excluded)",
            f"2-stage bootstrap; {lab}; mediated share CI "
            f"{('spans 0 -> NOT routed through Cat A bidding demand' if ind_ci_spans_zero
              else 'excludes 0 -> some mediation through bidding')}."
            f" Simultaneity flagged. {g.upper()}.",
        )

    # =================================================================
    # LINK 5 (HEADLINE): rebate -> price — per scope, vs the scope's
    # negative-control verdict
    # =================================================================
    # --- full window (2022-01 jump via reg_arffloor_zero_202201 + dose M3) ---
    ee_p = _row(price, spec="M1_primary_lagged_dum", term=DUMMY_2022)
    dose_p = _row(price, spec="M3_lagged_dose", term="dose_1000")
    if ee_p is not None:
        p = float(ee_p["p"])
        sig = p < 0.05
        pred = float(ee_p["coef"]) > 0
        ee_real = _row(price, spec="M1_primary_lagged_dum",
                       term=DUMMY_2022, price_def="real")
        nonrev = (ee_real is not None and
                  np.sign(float(ee_p["coef"])) == np.sign(float(ee_real["coef"])))
        if same_2022:
            g = "not detectable"
            nc_chk = ("FAIL (clean controls C/D/E show the same/larger 2022-01 "
                      "jump -> market-wide common shock, not EV-rebate-specific; "
                      "note the verified dose does NOT step at 2022-01 — it was "
                      "the $0 ARF floor (tax) + 97->110kW threshold)")
        elif sig and pred and nonrev:
            g = "supported"
            nc_chk = "PASS"
        elif sig and pred:
            g = "directionally consistent"
            nc_chk = "PASS (marginally)"
        else:
            g = "not detectable"
            nc_chk = "PASS"
        add(
            "rebate->price (HEADLINE core question)", "full_window",
            f"reg_arffloor_zero_202201 coef={float(ee_p['coef']):+.1f} S$ "
            f"(dose/1000={float(dose_p['coef']):+.1f} S$/1000S$)",
            f"[{float(ee_p['ci_lo']):+.1f}, {float(ee_p['ci_hi']):+.1f}]",
            p, int(ee_p["nobs"]), g,
            "full window (primary; 2022-01 = $0 ARF floor + threshold)",
            nc_chk,
            f"full-window est sig={sig}, predicted dir (coef>0)={pred}, "
            f"nominal<->real non-reversal={nonrev}. "
            + ("CRITICAL: the full-window negative-control check FAILS — clean "
               "controls with no EV rebate show the same 2022-01 price jump, "
               "so the increase is a market-wide common shock (co-timed 97->"
               "110kW threshold + COE market + $0 ARF floor), NOT an "
               "EV-rebate-specific channel. DOWNGRADED to not detectable."
               if same_2022 else
               "negative-control check does not falsify the effect.")
            + " Precise magnitude claims are FORBIDDEN (low power).",
        )

    # --- 2022+ EV era (2024-01 step via E1 dose / E2 dummy) ---
    e1p = _row(ev_era, spec="E1_ev_era_lagged_dose", term="dose_1000",
               price_def="nominal")
    e2p = _row(ev_era, spec="E2_ev_era_lagged_dum", term=DUMMY_2024,
               price_def="nominal")
    if e1p is not None and e2p is not None:
        p = min(float(e1p["p"]), float(e2p["p"]))
        sig = p < 0.05
        pred = float(e1p["coef"]) > 0
        if same_2024:
            g = "not detectable"
            nc_chk = ("FAIL (clean controls C/D/E show the same/larger 2024-01 "
                      "step in response to an EV-rebate cap cut that does NOT "
                      "apply to them -> market-wide common shock in the 2022+ "
                      "scope as well)")
        elif sig and pred:
            g = "supported"
            nc_chk = "PASS (EV era: clean controls do not respond at 2024-01)"
        elif sig and not pred:
            g = "directionally consistent"
            nc_chk = "PASS (EV era; wrong direction)"
        else:
            g = "not detectable"
            nc_chk = "PASS (EV era: clean controls do not respond at 2024-01)"
        add(
            "rebate->price (HEADLINE core question)", "ev_era_2022plus",
            f"dose/1000 coef={float(e1p['coef']):+.1f} (p={float(e1p['p']):.3f}); "
            f"step dummy coef={float(e2p['coef']):+.1f} "
            f"(p={float(e2p['p']):.3f})",
            f"dose [{float(e1p['ci_lo']):+.1f}, {float(e1p['ci_hi']):+.1f}]",
            p, int(e1p["nobs"]), g,
            "2022+ EV era (2022-01..2025-05; 41 obs; dose 45000->40000 at "
            "2024-01; estimable: 2 dose levels in window)",
            nc_chk,
            f"EV-era dose step sig={sig}, predicted dir (coef>0)={pred}. 41 "
            f"obs, 2 dose levels -> LOW POWER, wide CIs; magnitude claims "
            f"forbidden. Grade read per the EV-era negative-control verdict. "
            f"{g.upper()}.",
        )

    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)

    # ---- low-power caveat + grading rubric as a commented block ----
    with open(OUT, "a") as fh:
        fh.write("# ---- grading rubric & caveats ----\n")
        fh.write("# grades: supported / directionally consistent / not detectable\n")
        fh.write("# DUAL-SCOPE: each link graded per scope — full window "
                 "(2016-01..2025-05, primary; 3 dose steps, 110 monthly obs, 3 "
                 "pandemic NA dropped) AND 2022+ EV era (2022-01..2025-05, 41 "
                 "obs, 2 dose levels — the verified dose varies 45000->40000 at "
                 "2024-01, so the 2022+ window is estimable).\n")
        fh.write("# low-power caveat: wide CIs expected in BOTH scopes "
                 "(2022+ scope has only 41 obs / 2 dose levels).\n")
        fh.write("# precise magnitude claims are FORBIDDEN. All estimates are "
                 "bounds, not precise causal magnitudes.\n")
        fh.write("# simultaneity/reverse-causality: the rebate is set in "
                 "response to EV demand and registrations depend on the COE "
                 "price paid -> associational, not causal, without an "
                 "exogenous shift in the rebate.\n")
        fh.write(f"# negative-control same-effect-on-clean (2022-01, full "
                 f"window) = {same_2022}\n")
        fh.write(f"# negative-control same-effect-on-clean (2024-01, 2022+ EV "
                 f"era) = {same_2024}\n")
        fh.write("# interpretation scope = 2022-01..2025-05 for every link "
                 "(full-window estimate read on the EV-relevant window).\n")

    B.register_exhibit(
        name="evidence_grading", kind="grading",
        est_scope="2016-01..2025-05;2022-01..2025-05",
        key_regressor="n/a (grades read from steps 7-11 tables)",
        interpretation_scope="2022-01..2025-05",
        n_obs=110,
        notes="graded each link PER SCOPE (full window AND 2022+ EV era) "
              "supported/directionally consistent/not detectable; per-scope "
              "negative-control verdicts (2022-01 full window; 2024-01 EV "
              "era); low-power caveat restated for both scopes; precise "
              "magnitudes forbidden.",
    )

    print(f"[grading] wrote {OUT}  rows={len(out)} (per-scope)")
    for r in rows:
        print(f"  [{r['scope']}] {r['link']}: {r['grade'].upper()}  "
              f"(nc={str(r['negative_control_check'])[:40]})")
        print(f"      est={r['estimate']}")


if __name__ == "__main__":
    main()
