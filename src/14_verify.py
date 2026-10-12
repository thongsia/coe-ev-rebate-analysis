#!/usr/bin/env python3
"""
Step 15 (Batch C) — Independent verification pass. VERIFIED-POLICY RE-RUN.

Re-confirms, from the files on disk (never from memory), that the pipeline's
claims hold, and builds the report-figures checklist that Step 16's report
script must use so every number in REPORT.md traces to a saved table.

Checks:
  (a) fetched row counts == stated totals (re-read data/raw/provenance.csv and
      count the raw CSVs on disk)
  (b) every analysis month maps to real exercises (per-category audit-column
      sums == raw rows in window; the 3 pandemic NA months documented) and real
      registration rows (per-month rows_total == raw rows; EV totals reconcile)
  (c) every VERIFIED rebate-step date has a cited policy source in
      rebate_timeline.csv (2018-01, 2021-01, 2022-01, 2024-01; out-of-window
      rows 2013-01 / 2026-01 / 2027-01 present and cited; deprecated plan rows
      marked)
  (d) every report figure traces to a saved table (checklist below; written to
      tables/report_figures_checklist.csv)
  (e) dose state: 3 effective verified-policy changes + distinct dose values
      {20000, 25000, 40000, 45000}; NEW: 2022-01..2025-05 has >=2 (exactly 2)
      distinct dose values -> 2022+ IS a valid estimation scope (old flat-tail
      assertion REMOVED)
  (f) rebate exhibits are estimated on the full window AND the headline
      exhibits (price + bidding demand + mediation) are ALSO estimated on the
      2022+ EV-era window (dual-scope, both scopes present in the tables; no
      rank-deficient NA rows — the 2022+ window is estimable under the
      verified dose)
  (g) price-equation demand regressor = corrected catA_bids_received (not ev_reg)
  (h) mediated share computed on the full-window sample (primary) with the
      2022+ EV-era scope reported alongside
  (i) data-flow / layering contract held for the Batch-C modules (15_report
      writes docs/REPORT.md + docs/STATS_SUMMARY.md)

Writes tables/verification_report.csv (with an OVERALL PASS/FAIL row) and
tables/report_figures_checklist.csv. Writes nothing to data/ and modifies no
earlier batch's file.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
TABLES = ROOT / "tables"
CHARTS = ROOT / "charts"

RESULTS: list[dict] = []


def add(check_id: str, name: str, ok: bool, detail: str) -> None:
    RESULTS.append(
        {"check": check_id, "name": name, "status": "PASS" if ok else "FAIL", "detail": detail}
    )


def _close(a, b, tol=1e-6) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))
    except (TypeError, ValueError):
        return str(a).strip() == str(b).strip()


# ---------------------------------------------------------------------------
# (a) fetched row counts == stated totals (provenance re-read)
# ---------------------------------------------------------------------------
def check_a() -> None:
    prov = pd.read_csv(RAW / "provenance.csv")
    ok_all, details = True, []
    for _, r in prov.iterrows():
        key = str(r["key"])
        raw_file = ROOT / r["raw_file"]
        ondisk = len(pd.read_csv(raw_file))
        match = (
            int(r["fetched_count"]) == int(r["stated_source_total"]) == ondisk
        )
        ok_all &= match
        details.append(
            f"{key}: fetched={r['fetched_count']} stated={r['stated_source_total']} "
            f"on_disk={ondisk} match={r['match']} -> {'OK' if match else 'MISMATCH'}"
        )
    add("a", "fetched row counts == stated totals (provenance re-read)", ok_all,
        "; ".join(details))


# ---------------------------------------------------------------------------
# (b) analysis months map to real exercises + real registration rows
# ---------------------------------------------------------------------------
def check_b() -> None:
    raw = pd.read_csv(RAW / "coe_results_raw.csv", dtype=str)
    win = raw[(raw["month"] >= "2016-01") & (raw["month"] <= "2025-05")]
    cm = pd.read_csv(PROC / "coe_monthly.csv", dtype=str)
    cmw = cm[(cm["month"] >= "2016-01") & (cm["month"] <= "2025-05")].copy()
    cmw["ec"] = pd.to_numeric(cmw["exercise_count"], errors="coerce")

    ok_per_cat, cat_detail = True, []
    for K in "ABCDE":
        raw_n = int((win["vehicle_class"] == f"Category {K}").sum())
        audit_n = int(cmw.loc[cmw["category"] == K, "ec"].sum())
        ok_per_cat &= raw_n == audit_n
        cat_detail.append(f"cat{K} raw={raw_n} audit_sum={audit_n}")

    panel = pd.read_csv(PROC / "panel_joint.csv")
    months_panel = set(panel["month"])
    months_raw = set(win["month"])
    na_months = sorted(months_panel - months_raw)
    audit_gap = (
        pd.read_csv(TABLES / "data_audit.csv")
        .set_index("metric")["value"]
    )
    gap_ok = (
        na_months == ["2020-04", "2020-05", "2020-06"]
        and set(str(audit_gap.get("coe_exercise_gap", "")).split("; "))
        == set(na_months)
    )

    # registration rows reconcile per month
    reg = pd.read_csv(RAW / "registrations_raw.csv", dtype=str)
    regw = reg[(reg["month"] >= "2016-01") & (reg["month"] <= "2025-05")]
    ev = pd.read_csv(PROC / "ev_registrations.csv")
    per_month_ok = True
    per_month_detail = []
    for _, r in ev.iterrows():
        raw_n = int((regw["month"] == r["month"]).sum())
        if raw_n != int(r["rows_total"]):
            per_month_ok = False
            per_month_detail.append(f"{r['month']} raw={raw_n} rows_total={r['rows_total']}")
    ev_sum_proc = float(ev["ev_reg"].sum())
    ev_sum_raw = float(
        pd.to_numeric(regw.loc[regw["fuel_type"] == "Electric", "number"],
                      errors="coerce").sum()
    )
    ev_ok = _close(ev_sum_proc, ev_sum_raw)
    ev_descriptive = pd.read_csv(TABLES / "ev_registrations_descriptive.csv")
    cum = float(
        ev_descriptive.loc[ev_descriptive["month"] == "SUMMARY_cumulative_ev_reg",
                           "ev_reg"].iloc[0]
    )
    ok = ok_per_cat and gap_ok and per_month_ok and ev_ok and _close(cum, ev_sum_raw)
    add(
        "b",
        "analysis months map to real exercises + real registration rows",
        ok,
        "per-category " + ", ".join(cat_detail)
        + f" | panel months={len(months_panel)} raw months in window={len(months_raw)} "
        f"pandemic NA months (documented)={na_months} (data_audit coe_exercise_gap match={gap_ok})"
        + f" | per-month registration rows_total==raw: {per_month_ok}"
        + (f" mismatches={per_month_detail[:3]}" if per_month_detail else "")
        + f" | EV registrations reconcile: processed_sum={ev_sum_proc:.0f} raw_sum={ev_sum_raw:.0f} "
        f"descriptive_cumulative={cum:.0f} ok={ev_ok and _close(cum, ev_sum_raw)}",
    )


# ---------------------------------------------------------------------------
# (c) every VERIFIED rebate step date has a cited policy source
# ---------------------------------------------------------------------------
REAL_STEP_MONTHS = ["2018-01", "2021-01", "2022-01", "2024-01"]
OUT_OF_WINDOW_MONTHS = ["2013-01", "2026-01", "2027-01"]


def check_c() -> None:
    rt_all = pd.read_csv(TABLES / "rebate_timeline.csv")
    dep = rt_all[rt_all["programme"].astype(str).str.startswith("DEPRECATED")]
    rt = rt_all[~rt_all["programme"].astype(str).str.startswith("DEPRECATED")]
    ok_all, details = True, []
    for m in REAL_STEP_MONTHS:
        row = rt[rt["effective_month"] == m]
        has_cite = (
            len(row) >= 1
            and all(str(u).startswith("http") for u in row["source_url"])
            and all(len(str(v)) > 10 for v in row["verification"])
            and all(str(v).startswith(("VERIFIED", "CORROBORATED")) for v in row["verification"])
        )
        inw = all(str(x).lower().startswith("yes") for x in row["in_joint_window"]) if len(row) else False
        ok_all &= has_cite and inw
        details.append(f"{m}: rows={len(row)} cited={has_cite} in_joint_window={inw}")
    # out-of-window rows must be present and cited
    oow_ok, oow_detail = True, []
    for m in OUT_OF_WINDOW_MONTHS:
        row = rt[rt["effective_month"] == m]
        ok = len(row) >= 1 and all(str(u).startswith("http") for u in row["source_url"])
        oow_ok &= ok
        oow_detail.append(f"{m}: rows={len(row)} cited={ok}")
    # deprecated plan rows must be marked deprecated (captured from rt_all above)
    dep_ok = len(dep) >= 2
    ok_all &= oow_ok and dep_ok
    add("c", "every verified rebate-step date has a cited policy source (rebate_timeline.csv)",
        ok_all, "; ".join(details) + " | out-of-window: " + "; ".join(oow_detail)
        + f" | deprecated plan rows marked={dep_ok} (n={len(dep)})")


# ---------------------------------------------------------------------------
# (d) report-figures checklist: every figure the report quotes traces to a table
# ---------------------------------------------------------------------------
# Each entry: (fig_id, label, table, filter {col: value}, value_col, expected)
# Filter comparison is exact on str(stripped) unless the value is numeric.
CHECKLIST: list[tuple] = [
    # --- headline price equation, FULL WINDOW (price_equation.csv) ---
    # dummy spec (M1 primary), nominal
    ("pe_ves_coef", "VES-onset dummy coef (nominal, M1, HC1)", "price_equation.csv",
     {"term": "reg_real_ves_201801", "spec": "M1_primary_lagged_dum", "price_def": "nominal", "cov_type": "HC1"},
     "coef", -16580.9344981381),
    ("pe_ves_p", "VES-onset dummy p", "price_equation.csv",
     {"term": "reg_real_ves_201801", "spec": "M1_primary_lagged_dum", "price_def": "nominal", "cov_type": "HC1"},
     "p", 2.7713660077025012e-09),
    ("pe_evstack_coef", "EV-stack dummy coef (2021-01; dose 25000->45000)", "price_equation.csv",
     {"term": "reg_real_evstack_202101", "spec": "M1_primary_lagged_dum", "price_def": "nominal", "cov_type": "HC1"},
     "coef", 7666.11416137701),
    ("pe_arffloor_coef", "2022-01 ARF-floor dummy coef (nominal, M1, HC1)", "price_equation.csv",
     {"term": "reg_arffloor_zero_202201", "spec": "M1_primary_lagged_dum", "price_def": "nominal", "cov_type": "HC1"},
     "coef", 3825.641620640139),
    ("pe_arffloor_ci_lo", "ARF-floor CI lo", "price_equation.csv",
     {"term": "reg_arffloor_zero_202201", "spec": "M1_primary_lagged_dum", "price_def": "nominal", "cov_type": "HC1"},
     "ci_lo", -227.7881545829769),
    ("pe_arffloor_ci_hi", "ARF-floor CI hi", "price_equation.csv",
     {"term": "reg_arffloor_zero_202201", "spec": "M1_primary_lagged_dum", "price_def": "nominal", "cov_type": "HC1"},
     "ci_hi", 7879.071395863255),
    ("pe_arffloor_p", "ARF-floor p (HC1)", "price_equation.csv",
     {"term": "reg_arffloor_zero_202201", "spec": "M1_primary_lagged_dum", "price_def": "nominal", "cov_type": "HC1"},
     "p", 0.0643393433430473),
    ("pe_cap15k_coef", "2024-01 EEAI cap-cut dummy coef (nominal, M1, HC1)", "price_equation.csv",
     {"term": "reg_eeai_cap15k_202401", "spec": "M1_primary_lagged_dum", "price_def": "nominal", "cov_type": "HC1"},
     "coef", -11972.24558703884),
    ("pe_cap15k_ci_lo", "cap-15k CI lo", "price_equation.csv",
     {"term": "reg_eeai_cap15k_202401", "spec": "M1_primary_lagged_dum", "price_def": "nominal", "cov_type": "HC1"},
     "ci_lo", -21799.53670790389),
    ("pe_cap15k_ci_hi", "cap-15k CI hi", "price_equation.csv",
     {"term": "reg_eeai_cap15k_202401", "spec": "M1_primary_lagged_dum", "price_def": "nominal", "cov_type": "HC1"},
     "ci_hi", -2144.954466173791),
    ("pe_cap15k_p", "cap-15k p (HC1)", "price_equation.csv",
     {"term": "reg_eeai_cap15k_202401", "spec": "M1_primary_lagged_dum", "price_def": "nominal", "cov_type": "HC1"},
     "p", 0.016951606989936),
    ("pe_cap15k_hac_p", "cap-15k p (HAC)", "price_equation.csv",
     {"term": "reg_eeai_cap15k_202401", "spec": "M1_primary_lagged_dum_HAC", "price_def": "nominal", "cov_type": "HAC"},
     "p", 0.0086006381527052),
    ("pe_arffloor_real", "ARF-floor dummy coef (real, M1, HC1)", "price_equation.csv",
     {"term": "reg_arffloor_zero_202201", "spec": "M1_primary_lagged_dum", "price_def": "real", "cov_type": "HC1"},
     "coef", 5327.575749996559),
    ("pe_arffloor_real_p", "ARF-floor p (real, HC1)", "price_equation.csv",
     {"term": "reg_arffloor_zero_202201", "spec": "M1_primary_lagged_dum", "price_def": "real", "cov_type": "HC1"},
     "p", 0.0172442191432382),
    # dose spec (M3), nominal + real
    ("pe_dose_coef", "dose/1000 coef (nominal, M3, HC1)", "price_equation.csv",
     {"term": "dose_1000", "spec": "M3_lagged_dose", "price_def": "nominal", "cov_type": "HC1"},
     "coef", 598.9007731443369),
    ("pe_dose_ci_lo", "dose CI lo", "price_equation.csv",
     {"term": "dose_1000", "spec": "M3_lagged_dose", "price_def": "nominal", "cov_type": "HC1"},
     "ci_lo", 361.1328798455544),
    ("pe_dose_ci_hi", "dose CI hi", "price_equation.csv",
     {"term": "dose_1000", "spec": "M3_lagged_dose", "price_def": "nominal", "cov_type": "HC1"},
     "ci_hi", 836.6686664431193),
    ("pe_dose_p", "dose p (nominal, M3, HC1)", "price_equation.csv",
     {"term": "dose_1000", "spec": "M3_lagged_dose", "price_def": "nominal", "cov_type": "HC1"},
     "p", 7.939530691797492e-07),
    ("pe_dose_real", "dose/1000 coef (real, M3, HC1)", "price_equation.csv",
     {"term": "dose_1000", "spec": "M3_lagged_dose", "price_def": "real", "cov_type": "HC1"},
     "coef", 730.3653635860281),
    ("pe_dose_real_p", "dose p (real, M3, HC1)", "price_equation.csv",
     {"term": "dose_1000", "spec": "M3_lagged_dose", "price_def": "real", "cov_type": "HC1"},
     "p", 1.2364720924608172e-07),
    # demand terms
    ("pe_demand_l1", "demand_l1 coef (nominal, M1, HC1)", "price_equation.csv",
     {"term": "demand_l1", "spec": "M1_primary_lagged_dum", "price_def": "nominal", "cov_type": "HC1"},
     "coef", -0.0267153705197591),
    ("pe_demand_l1_p", "demand_l1 p", "price_equation.csv",
     {"term": "demand_l1", "spec": "M1_primary_lagged_dum", "price_def": "nominal", "cov_type": "HC1"},
     "p", 0.9764302141164208),
    ("pe_demand_l2", "demand_l2 coef (nominal, M1, HC1)", "price_equation.csv",
     {"term": "demand_l2", "spec": "M1_primary_lagged_dum", "price_def": "nominal", "cov_type": "HC1"},
     "coef", 1.7183636673102),
    # --- 2022+ EV-era price specs (price_equation_2022plus_robustness.csv) ---
    ("pe22_dose_coef", "2022+ EV-era dose/1000 coef (E1, nominal, HC1)", "price_equation_2022plus_robustness.csv",
     {"term": "dose_1000", "spec": "E1_ev_era_lagged_dose", "price_def": "nominal", "cov_type": "HC1"},
     "coef", 4112.724774819341),
    ("pe22_dose_ci_lo", "2022+ dose CI lo", "price_equation_2022plus_robustness.csv",
     {"term": "dose_1000", "spec": "E1_ev_era_lagged_dose", "price_def": "nominal", "cov_type": "HC1"},
     "ci_lo", 2136.680206),
    ("pe22_dose_ci_hi", "2022+ dose CI hi", "price_equation_2022plus_robustness.csv",
     {"term": "dose_1000", "spec": "E1_ev_era_lagged_dose", "price_def": "nominal", "cov_type": "HC1"},
     "ci_hi", 6088.769344),
    ("pe22_dose_p", "2022+ dose p", "price_equation_2022plus_robustness.csv",
     {"term": "dose_1000", "spec": "E1_ev_era_lagged_dose", "price_def": "nominal", "cov_type": "HC1"},
     "p", 4.517998676710449e-05),
    ("pe22_step_coef", "2022+ step dummy (45000->40000) coef (E2, nominal, HC1)", "price_equation_2022plus_robustness.csv",
     {"term": "reg_eeai_cap15k_202401", "spec": "E2_ev_era_lagged_dum", "price_def": "nominal", "cov_type": "HC1"},
     "coef", -20563.623874097702),
    ("pe22_step_ci_lo", "2022+ step CI lo", "price_equation_2022plus_robustness.csv",
     {"term": "reg_eeai_cap15k_202401", "spec": "E2_ev_era_lagged_dum", "price_def": "nominal", "cov_type": "HC1"},
     "ci_lo", -30443.846721),
    ("pe22_step_ci_hi", "2022+ step CI hi", "price_equation_2022plus_robustness.csv",
     {"term": "reg_eeai_cap15k_202401", "spec": "E2_ev_era_lagged_dum", "price_def": "nominal", "cov_type": "HC1"},
     "ci_hi", -10683.401028),
    ("pe22_step_p", "2022+ step p", "price_equation_2022plus_robustness.csv",
     {"term": "reg_eeai_cap15k_202401", "spec": "E2_ev_era_lagged_dum", "price_def": "nominal", "cov_type": "HC1"},
     "p", 4.517998676718005e-05),
    ("pe22_d1", "2022+ demand_l1 coef (E3, nominal, HC1)", "price_equation_2022plus_robustness.csv",
     {"term": "demand_l1", "spec": "E3_ev_era_demand_only", "price_def": "nominal", "cov_type": "HC1"},
     "coef", -2.7097565522551883),
    ("pe22_d1_p", "2022+ demand_l1 p", "price_equation_2022plus_robustness.csv",
     {"term": "demand_l1", "spec": "E3_ev_era_demand_only", "price_def": "nominal", "cov_type": "HC1"},
     "p", 0.5077517510098639),
    # --- bidding channel (demand_bidding_channel.csv), BOTH scopes ---
    ("bd_dummy_hc1", "full-window rebate->demand step-dummy coef", "demand_bidding_channel.csv",
     {"term": "reg_eeai_cap15k_202401", "spec": "dummy", "cov_type": "HC1"}, "coef", 679.7145230653476),
    ("bd_dummy_hc1_p", "full-window rebate->demand step-dummy p", "demand_bidding_channel.csv",
     {"term": "reg_eeai_cap15k_202401", "spec": "dummy", "cov_type": "HC1"}, "p", 0.0042858228001889),
    ("bd_dummy_hc1_ci", "full-window rebate->demand CI lo", "demand_bidding_channel.csv",
     {"term": "reg_eeai_cap15k_202401", "spec": "dummy", "cov_type": "HC1"}, "ci_lo", 213.304682),
    ("bd_dummy_hac_p", "full-window rebate->demand p (HAC)", "demand_bidding_channel.csv",
     {"term": "reg_eeai_cap15k_202401", "spec": "dummy_HAC", "cov_type": "HAC"}, "p", 0.0215274420582814),
    ("bd_dose", "full-window rebate->demand dose/1000 coef", "demand_bidding_channel.csv",
     {"term": "dose_1000", "spec": "dose", "cov_type": "HC1"}, "coef", -11.689939449901448),
    ("bd_dose_p", "full-window rebate->demand dose/1000 p", "demand_bidding_channel.csv",
     {"term": "dose_1000", "spec": "dose", "cov_type": "HC1"}, "p", 0.2853636939003477),
    ("bd_dose_hac_p", "full-window rebate->demand dose p (HAC)", "demand_bidding_channel.csv",
     {"term": "dose_1000", "spec": "dose_HAC", "cov_type": "HAC"}, "p", 0.3865637516577126),
    ("bd22_dose_coef", "2022+ EV-era rebate->demand dose/1000 coef (E1)", "demand_bidding_channel.csv",
     {"term": "dose_1000", "spec": "E1_ev_era_dose", "cov_type": "HC1"}, "coef", -111.450569),
    ("bd22_dose_p", "2022+ EV-era rebate->demand dose/1000 p", "demand_bidding_channel.csv",
     {"term": "dose_1000", "spec": "E1_ev_era_dose", "cov_type": "HC1"}, "p", 0.005408543324145),
    ("bd22_dum_coef", "2022+ EV-era rebate->demand step-dummy coef (E2)", "demand_bidding_channel.csv",
     {"term": "reg_eeai_cap15k_202401", "spec": "E2_ev_era_dum", "cov_type": "HC1"}, "coef", 557.252844),
    ("bd22_dum_p", "2022+ EV-era rebate->demand step-dummy p", "demand_bidding_channel.csv",
     {"term": "reg_eeai_cap15k_202401", "spec": "E2_ev_era_dum", "cov_type": "HC1"}, "p", 0.005408543324145),
    # --- cross-lag (crosslag_check.csv) ---
    ("xl_minus1_p", "cross-lag dose(-1) p", "crosslag_check.csv",
     {"term": "dose_-1_month", "cov_type": "HC1"}, "p", 0.4792305715369578),
    ("xl_plus0_p", "cross-lag dose(0) p", "crosslag_check.csv",
     {"term": "dose_+0_month", "cov_type": "HC1"}, "p", 0.2853636939003477),
    ("xl_plus1_p", "cross-lag dose(+1) p", "crosslag_check.csv",
     {"term": "dose_+1_month", "cov_type": "HC1"}, "p", 0.4792305715369578),
    # --- mediation, BOTH scopes (mediation_effects.csv) ---
    ("med_full_total", "mediation total (full window)", "mediation_effects.csv",
     {"effect": "total", "scope": "full_window"}, "estimate", 569.1309324065705),
    ("med_full_total_ci", "mediation total CI lo (full window)", "mediation_effects.csv",
     {"effect": "total", "scope": "full_window"}, "ci_lo", 339.742883),
    ("med_full_indirect", "mediation indirect (full window)", "mediation_effects.csv",
     {"effect": "indirect", "scope": "full_window"}, "estimate", -9.037756311691187),
    ("med_full_indirect_ci_lo", "mediation indirect CI lo (full)", "mediation_effects.csv",
     {"effect": "indirect", "scope": "full_window"}, "ci_lo", -52.768221),
    ("med_full_indirect_ci_hi", "mediation indirect CI hi (full)", "mediation_effects.csv",
     {"effect": "indirect", "scope": "full_window"}, "ci_hi", 28.562778),
    ("med_full_share", "mediated share (full window)", "mediation_effects.csv",
     {"effect": "mediated_share", "scope": "full_window"}, "estimate", -0.01587992463083148),
    ("med_full_share_ci_lo", "mediated share CI lo (full)", "mediation_effects.csv",
     {"effect": "mediated_share", "scope": "full_window"}, "ci_lo", -0.09895),
    ("med_full_share_ci_hi", "mediated share CI hi (full)", "mediation_effects.csv",
     {"effect": "mediated_share", "scope": "full_window"}, "ci_hi", 0.05914),
    ("med_full_nobs", "mediation n_obs (full window)", "mediation_effects.csv",
     {"effect": "mediated_share", "scope": "full_window"}, "n_obs", 109),
    ("med_ev_total", "mediation total (2022+ EV era)", "mediation_effects.csv",
     {"effect": "total", "scope": "ev_era_2022plus"}, "estimate", 2881.970547296436),
    ("med_ev_total_ci", "mediation total CI lo (EV era)", "mediation_effects.csv",
     {"effect": "total", "scope": "ev_era_2022plus"}, "ci_lo", 1048.459944),
    ("med_ev_indirect", "mediation indirect (2022+ EV era)", "mediation_effects.csv",
     {"effect": "indirect", "scope": "ev_era_2022plus"}, "estimate", -331.774532761807),
    ("med_ev_share", "mediated share (2022+ EV era)", "mediation_effects.csv",
     {"effect": "mediated_share", "scope": "ev_era_2022plus"}, "estimate", -0.11512072289324513),
    ("med_ev_nobs", "mediation n_obs (2022+ EV era)", "mediation_effects.csv",
     {"effect": "mediated_share", "scope": "ev_era_2022plus"}, "n_obs", 41),
    # --- event study (event_study_coefficients.csv): 4 verified-policy events ---
    ("es_onset2018", "2018-01 CEVS-lapse/VES-onset onset coef (bounded)", "event_study_coefficients.csv",
     {"episode": "2018-01_cevs_lapse_VES_onset", "term": "onset_0"}, "coef", -17067.519848),
    ("es_onset2021", "2021-01 enhanced-VES+EEAI-stack onset coef (bounded)", "event_study_coefficients.csv",
     {"episode": "2021-01_enhanced_VES_EEAI_stack", "term": "onset_0"}, "coef", 11144.888604),
    ("es_onset2022", "2022-01 ARF-floor+threshold onset coef (bounded)", "event_study_coefficients.csv",
     {"episode": "2022-01_ARF_floor_zero_PLUS_threshold_bounded", "term": "onset_0"}, "coef", 26921.664905),
    ("es_onset2022_ci_lo", "2022-01 onset CI lo", "event_study_coefficients.csv",
     {"episode": "2022-01_ARF_floor_zero_PLUS_threshold_bounded", "term": "onset_0"}, "ci_lo", 18997.057351),
    ("es_onset2022_ci_hi", "2022-01 onset CI hi", "event_study_coefficients.csv",
     {"episode": "2022-01_ARF_floor_zero_PLUS_threshold_bounded", "term": "onset_0"}, "ci_hi", 34846.272458),
    ("es_onset2024", "2024-01 EEAI cap-cut onset coef (bounded)", "event_study_coefficients.csv",
     {"episode": "2024-01_eeai_cap15k_step", "term": "onset_0"}, "coef", -39016.970906),
    ("es_onset2024_ci_lo", "2024-01 onset CI lo", "event_study_coefficients.csv",
     {"episode": "2024-01_eeai_cap15k_step", "term": "onset_0"}, "ci_lo", -43177.765211),
    ("es_onset2024_ci_hi", "2024-01 onset CI hi", "event_study_coefficients.csv",
     {"episode": "2024-01_eeai_cap15k_step", "term": "onset_0"}, "ci_hi", -34856.1766),
    # --- negative controls (negative_controls.csv), per scope ---
    ("nc_A_22", "2022-01 jump Cat A (EV-eligible) % (full window)", "negative_controls.csv",
     {"term": "reg_arffloor_zero_202201", "category": "A", "scope": "full_window", "spec": "dummy"}, "coef_pct_of_mean", 6.577745023407299),
    ("nc_C_22", "2022-01 jump Cat C (clean) % (full window)", "negative_controls.csv",
     {"term": "reg_arffloor_zero_202201", "category": "C", "scope": "full_window", "spec": "dummy"}, "coef_pct_of_mean", -10.156085029502531),
    ("nc_D_22", "2022-01 jump Cat D (clean) % (full window)", "negative_controls.csv",
     {"term": "reg_arffloor_zero_202201", "category": "D", "scope": "full_window", "spec": "dummy"}, "coef_pct_of_mean", 16.299740518763812),
    ("nc_E_22", "2022-01 jump Cat E (clean) % (full window)", "negative_controls.csv",
     {"term": "reg_arffloor_zero_202201", "category": "E", "scope": "full_window", "spec": "dummy"}, "coef_pct_of_mean", 10.260839861583907),
    ("nc_A_24", "2024-01 step Cat A (EV-eligible) % (2022+ EV era)", "negative_controls.csv",
     {"term": "reg_eeai_cap15k_202401", "category": "A", "scope": "ev_era_2022plus", "spec": "dummy"}, "coef_pct_of_mean", -22.9613772533957),
    ("nc_C_24", "2024-01 step Cat C (clean) % (2022+ EV era)", "negative_controls.csv",
     {"term": "reg_eeai_cap15k_202401", "category": "C", "scope": "ev_era_2022plus", "spec": "dummy"}, "coef_pct_of_mean", -7.927621288328092),
    ("nc_D_24", "2024-01 step Cat D (clean) % (2022+ EV era)", "negative_controls.csv",
     {"term": "reg_eeai_cap15k_202401", "category": "D", "scope": "ev_era_2022plus", "spec": "dummy"}, "coef_pct_of_mean", -7.419567375389774),
    ("nc_E_24", "2024-01 step Cat E (clean) % (2022+ EV era)", "negative_controls.csv",
     {"term": "reg_eeai_cap15k_202401", "category": "E", "scope": "ev_era_2022plus", "spec": "dummy"}, "coef_pct_of_mean", -36.06956635773724),
    # --- diagnostics (diagnostics_stationarity_autocorr.csv) ---
    ("diag_adf_price_level", "ADF price level p (I(1) evidence)", "diagnostics_stationarity_autocorr.csv",
     {"variable": "catA_clearing_price (nominal)", "form": "level"}, "adf_p", 9.664896e-01),
    ("diag_adf_price_diff", "ADF price 1st-diff p", "diagnostics_stationarity_autocorr.csv",
     {"variable": "catA_clearing_price (nominal)", "form": "1st diff"}, "adf_p", 4.864086e-17),
    ("diag_dw", "Durbin-Watson of primary residuals", "diagnostics_stationarity_autocorr.csv",
     {"variable": "primary price eq. residuals", "form": "residual",
      "note": "Durbin-Watson = 0.7886"}, "variable", "primary price eq. residuals"),
    # --- sensitivity (sensitivity_analysis.csv) ---
    ("sens_noquota", "cap-15k dummy without catA_quota", "sensitivity_analysis.csv",
     {"spec": "drop_control_catA_quota", "term": "reg_eeai_cap15k_202401"}, "coef", -14030.377783669786),
    ("sens_notrend", "cap-15k dummy without trend", "sensitivity_analysis.csv",
     {"spec": "drop_control_trend", "term": "reg_eeai_cap15k_202401"}, "coef", -14549.356670812736),
    ("sens_nocpi", "cap-15k dummy without cpi", "sensitivity_analysis.csv",
     {"spec": "drop_control_cpi_all_items", "term": "reg_eeai_cap15k_202401"}, "coef", -10806.20715940096),
    ("sens_bidssucc", "cap-15k dummy demand=bids_success", "sensitivity_analysis.csv",
     {"spec": "demand_bids_success", "term": "reg_eeai_cap15k_202401"}, "coef", -9363.578852614495),
    ("sens_lag1", "cap-15k dummy lag1_only", "sensitivity_analysis.csv",
     {"spec": "lag_lag1_only", "term": "reg_eeai_cap15k_202401"}, "coef", -10732.656038205449),
    ("sens_contemp", "cap-15k dummy contemporaneous", "sensitivity_analysis.csv",
     {"spec": "lag_contemporaneous", "term": "reg_eeai_cap15k_202401"}, "coef", -10684.334121278349),
    ("sens_real", "cap-15k dummy real price def", "sensitivity_analysis.csv",
     {"spec": "price_real", "term": "reg_eeai_cap15k_202401"}, "coef", -12056.228497768652),
    # --- 2022+ EV-era price robustness sanity ---
    ("rob22_nobs", "2022+ EV-era price spec nobs (estimable, not rank-deficient)",
     "price_equation_2022plus_robustness.csv",
     {"term": "dose_1000", "spec": "E1_ev_era_lagged_dose"}, "nobs", 41),
    # --- evidence grading (evidence_grading.csv), per scope ---
    ("grade_headline_full", "headline grade (full window)", "evidence_grading.csv",
     {"link": "rebate->price (HEADLINE core question)", "scope": "full_window"}, "grade", "not detectable"),
    ("grade_headline_ev", "headline grade (2022+ EV era)", "evidence_grading.csv",
     {"link": "rebate->price (HEADLINE core question)", "scope": "ev_era_2022plus"}, "grade", "supported"),
    ("grade_bidding_full", "bidding-channel grade (full window)", "evidence_grading.csv",
     {"link": "rebate->demand (bidding channel)", "scope": "full_window"}, "grade", "directionally consistent"),
    ("grade_bidding_ev", "bidding-channel grade (2022+ EV era)", "evidence_grading.csv",
     {"link": "rebate->demand (bidding channel)", "scope": "ev_era_2022plus"}, "grade", "not detectable"),
    ("grade_reg", "registration-channel grade (descriptive)", "evidence_grading.csv",
     {"link": "rebate->demand (registration channel)", "scope": "descriptive"}, "grade", "not detectable"),
    ("grade_demand_price_full", "demand->price grade (full window)", "evidence_grading.csv",
     {"link": "demand->price", "scope": "full_window"}, "grade", "not detectable"),
    ("grade_med_full", "mediation grade (full window)", "evidence_grading.csv",
     {"link": "total indirect effect (rebate->demand->price)", "scope": "full_window"}, "grade", "not detectable"),
    ("grade_med_ev", "mediation grade (2022+ EV era)", "evidence_grading.csv",
     {"link": "total indirect effect (rebate->demand->price)", "scope": "ev_era_2022plus"}, "grade", "not detectable"),
    # --- EV descriptive (ev_registrations_descriptive.csv) ---
    ("ev_n_months", "observed BEV months", "ev_registrations_descriptive.csv",
     {"month": "SUMMARY_observed_months"}, "ev_reg", 35),
    ("ev_mean", "mean EV registrations", "ev_registrations_descriptive.csv",
     {"month": "SUMMARY_mean_ev_reg"}, "ev_reg", 854.2571428571429),
    ("ev_max", "max EV registrations", "ev_registrations_descriptive.csv",
     {"month": "SUMMARY_max_ev_reg"}, "ev_reg", 2014),
    ("ev_share_mean", "mean EV share", "ev_registrations_descriptive.csv",
     {"month": "SUMMARY_mean_ev_share"}, "ev_reg", 0.2581540692967779),
    ("ev_cum", "cumulative EV registrations", "ev_registrations_descriptive.csv",
     {"month": "SUMMARY_cumulative_ev_reg"}, "ev_reg", 29899),
    ("ev_cov_min", "min coverage (lower-bound decay)", "ev_registrations_descriptive.csv",
     {"month": "SUMMARY_min_coverage"}, "ev_reg", 0.1817129629629629),
    # --- dose / scope (dose_summary.csv, scope_audit.csv, data_audit.csv) ---
    ("dose_changes", "effective in-window verified-policy changes", "dose_summary.csv",
     {"item": "effective_in_window_changes"}, "value", 3),
    ("dose_distinct", "distinct dose values", "dose_summary.csv",
     {"item": "n_distinct_dose_values"}, "value", 4),
    ("dose_distinct_vals", "distinct dose value list", "dose_summary.csv",
     {"item": "distinct_dose_values"}, "value", "20000; 25000; 40000; 45000"),
    ("dose_2022plus_n", "2022+ distinct dose count (>=2 -> estimable)", "dose_summary.csv",
     {"item": "n_distinct_dose_values_2022plus"}, "value", 2),
    ("dose_2022plus_vals", "2022+ distinct dose values", "dose_summary.csv",
     {"item": "dose_2022plus_values"}, "value", "40000; 45000"),
    ("scope_a", "scope audit (a) dual-scope rule", "scope_audit.csv",
     {"detail_prefix": "(a)"}, "status", "PASS"),
    ("scope_b", "scope audit (b) demand regressor = clean", "scope_audit.csv",
     {"detail_prefix": "(b)"}, "status", "PASS"),
    ("scope_c", "scope audit (c) mediated share dual-scope", "scope_audit.csv",
     {"detail_prefix": "(c)"}, "status", "PASS"),
    ("scope_f", "scope audit (f) layering contract", "scope_audit.csv",
     {"detail_prefix": "(f)"}, "status", "PASS"),
    ("audit_panel_rows", "panel row count", "data_audit.csv",
     {"metric": "panel_row_count"}, "value", 113),
]


def check_d() -> None:
    rows = []
    ok_all, bad = True, []
    for fig_id, label, table, flt, col, expected in CHECKLIST:
        df = pd.read_csv(TABLES / table)
        m = df
        for k, v in flt.items():
            if k == "detail_prefix":
                m = m[m["check"].astype(str).str.startswith(str(v))]
            elif k == "note_prefix":
                m = m[m["note"].astype(str).str.startswith(str(v))]
            elif k == "note":
                m = m[m["note"].astype(str).str.strip() == str(v)]
            elif isinstance(v, float) and abs(v) < 1 and abs(v) >= 1e-30:
                m = m[_close(m[k], v) | (m[k].astype(str).str.strip() == str(v))]
            else:
                m = m[m[k].astype(str).str.strip() == str(v)]
        if len(m) == 0:
            ok_all = False
            bad.append(f"{fig_id}: NO ROW for {table} {flt}")
            got = None
        else:
            got = m[col].iloc[0]
            if not _close(got, expected, tol=1e-5) and str(got) != str(expected):
                ok_all = False
                bad.append(f"{fig_id}: table={table} got={got!r} expected={expected!r}")
        rows.append(
            {"fig_id": fig_id, "label": label, "source_table": table,
             "filter": str(flt), "value_col": col,
             "value_in_table": ("" if len(m) == 0 else str(m[col].iloc[0])),
             "value_quoted_in_report": str(expected),
             "match": "OK" if (len(m) and (_close(got, expected, tol=1e-5) or str(got) == str(expected))) else "MISMATCH"}
        )
    pd.DataFrame(rows).to_csv(TABLES / "report_figures_checklist.csv", index=False)
    add("d", f"report figures trace to saved tables ({len(CHECKLIST)} figures checked)",
        ok_all, ("all figures match their source tables" if ok_all else "; ".join(bad[:6]))
        + f" | checklist written to tables/report_figures_checklist.csv")


# ---------------------------------------------------------------------------
# (e) dose state: verified-policy changes + distinct doses; 2022+ has >=2
# ---------------------------------------------------------------------------
def check_e() -> None:
    panel = pd.read_csv(PROC / "panel_joint.csv")
    doses = sorted(panel["dose_nominal_sgd"].dropna().unique().tolist())
    ds = pd.read_csv(TABLES / "dose_summary.csv").set_index("item")
    distinct = int(ds.loc["n_distinct_dose_values", "value"])
    changes = int(ds.loc["effective_in_window_changes", "value"])
    tail = panel[panel["month"] >= "2022-01"]
    tail_doses = sorted(tail["dose_nominal_sgd"].unique().tolist())
    # NEW: 2022+ must have >=2 distinct doses (old flat-tail assertion REMOVED)
    tail_estimable = len(tail_doses) >= 2
    ok = (
        distinct == len(doses) == 4
        and doses == [20000, 25000, 40000, 45000]
        and changes == 3
        and tail_doses == [40000, 45000]
        and tail_estimable
        and len(tail) == 41
    )
    add("e", "dose state (verified policy): 4 distinct doses {20000,25000,40000,45000}; "
             "3 effective changes (2018-01, 2021-01, 2024-01); 2022+ window has 2 distinct "
             "doses {40000,45000} over 41 obs -> 2022+ IS a valid estimation scope "
             "(old flat-tail rule REMOVED)",
        ok, f"panel distinct={doses} (n={len(doses)}); dose_summary: distinct={distinct}, "
            f"changes={changes}; 2022-01..2025-05 distinct={tail_doses} (n_obs={len(tail)}) "
            f"estimable={tail_estimable}")


# ---------------------------------------------------------------------------
# (f) headline exhibits estimated on full window AND 2022+ EV era (dual-scope)
# ---------------------------------------------------------------------------
def check_f() -> None:
    pe = pd.read_csv(TABLES / "price_equation.csv")
    # every full-window price row must carry the full-window sample
    full_ok = pe["sample"].astype(str).str.startswith("2016-01..2025-05").all()
    # 2022+ EV-era price specs present and ESTIMABLE (nobs=41, no rank-deficient
    # NA rows — the verified dose varies within the window)
    rob = pd.read_csv(TABLES / "price_equation_2022plus_robustness.csv")
    ev_specs = {"E1_ev_era_lagged_dose", "E2_ev_era_lagged_dum", "E3_ev_era_demand_only"}
    ev_present = ev_specs.issubset(set(rob["spec"]))
    ev_nobs = (rob[rob["spec"].isin(ev_specs)]["nobs"] == 41).all()
    ev_no_nan = not rob[rob["spec"].isin(ev_specs)]["coef"].isna().any()
    # bidding channel: both scopes present
    bd = pd.read_csv(TABLES / "demand_bidding_channel.csv")
    bd_full = bd[bd["term"].isin(["dose_1000", "reg_eeai_cap15k_202401"])
                 & bd["spec"].isin(["dummy", "dose"])]["sample"].astype(str).str.startswith("2016-01..2025-05").all()
    bd_ev = bd[bd["spec"].isin(["E1_ev_era_dose", "E2_ev_era_dum"])]["sample"].astype(str).str.startswith("2022-01..2025-05").all()
    bd_ev_n = len(bd[bd["spec"].isin(["E1_ev_era_dose", "E2_ev_era_dum"])]) >= 2
    # mediation: both scopes present
    med = pd.read_csv(TABLES / "mediation_effects.csv")
    med_scopes = set(med["scope"].dropna().unique())
    med_both = {"full_window", "ev_era_2022plus"}.issubset(med_scopes)
    # scope-guard audit
    scope_a = (
        pd.read_csv(TABLES / "scope_audit.csv")
        .query("check.str.startswith('(a)')")["status"] == "PASS"
    ).all()
    ok = full_ok and ev_present and ev_nobs and ev_no_nan and bd_full and bd_ev and bd_ev_n and med_both and scope_a
    add("f", "headline exhibits estimated on full window AND 2022+ EV era (dual-scope; "
             "2022+ estimable under the verified dose)",
        ok,
        f"price_equation full-window sample={full_ok} (n={len(pe)}) | 2022+ EV-era price specs present={ev_present} "
        f"nobs=41={ev_nobs} no rank-deficient NaN={ev_no_nan} | bidding dual-scope={bd_full and bd_ev and bd_ev_n} | "
        f"mediation both scopes={med_both} (scopes={sorted(med_scopes)}) | scope_audit(a) PASS={scope_a}")


# ---------------------------------------------------------------------------
# (g) price-equation demand regressor = corrected catA_bids_received (not ev_reg)
# ---------------------------------------------------------------------------
def check_g() -> None:
    scope = pd.read_csv(TABLES / "scope_audit.csv")
    row_b = scope[scope["check"].astype(str).str.startswith("(b)")]
    scope_ok = len(row_b) == 1 and row_b["status"].iloc[0] == "PASS"
    src = (SRC / "06_price_equation.py").read_text()
    uses_clean = "catA_bids_received_clean" in src or "catA_demand_column" in src
    uses_ev = re.search(r"ols\([^)]*ev_reg", src) is not None
    # prove the correction matters: panel column is corrupted 0 in months where raw > 0
    raw = pd.read_csv(RAW / "coe_results_raw.csv", dtype=str)
    win = raw[(raw["month"] >= "2016-01") & (raw["month"] <= "2025-05")
              & (raw["vehicle_class"] == "Category A")].copy()
    win["br"] = pd.to_numeric(
        win["bids_received"].astype(str).str.replace(",", "", regex=False), errors="coerce"
    )
    corr = win.groupby("month")["br"].sum()
    panel = pd.read_csv(PROC / "panel_joint.csv")
    panel_br = pd.to_numeric(panel["catA_bids_received"], errors="coerce")
    bad = panel[(panel_br == 0) & (panel["month"].map(lambda m: corr.get(m, 0) > 0))]
    corrected_nz = int((corr > 0).sum())
    ok = scope_ok and uses_clean and (not uses_ev) and len(bad) >= 1
    add("g", "price-equation demand regressor = corrected catA_bids_received (not ev_reg)",
        ok,
        f"scope_audit(b) PASS={scope_ok} | 06_price_equation.py uses corrected series={uses_clean} "
        f"uses ev_reg as regressor={uses_ev} | panel column corrupted (0 where raw>0) in "
        f"{len(bad)} months (2023-10..2025-05) -> correction required; corrected series "
        f"nonzero in {corrected_nz}/{len(corr)} COE months (reconstructed from raw)")


# ---------------------------------------------------------------------------
# (h) mediated share on full-window sample (primary), 2022+ EV era reported
# ---------------------------------------------------------------------------
def check_h() -> None:
    med = pd.read_csv(TABLES / "mediation_effects.csv")
    est = [r["effect"] for _, r in med.iterrows()
           if str(r["effect"]).startswith("# estimation_scope")]
    interp = [r["effect"] for _, r in med.iterrows()
              if str(r["effect"]).startswith("# interpretation_scope")]
    # the full-window rows must exist (primary sample) AND the EV-era rows
    full_row = len(med[(med["scope"] == "full_window")]) >= 4
    ev_row = len(med[(med["scope"] == "ev_era_2022plus")]) >= 4
    scope_c = (
        pd.read_csv(TABLES / "scope_audit.csv")
        .query("check.str.startswith('(c)')")["status"] == "PASS"
    ).all()
    ok = (
        len(est) == 1 and "2016-01..2025-05" in est[0]
        and len(interp) == 1 and "2022-01..2025-05" in interp[0]
        and full_row and ev_row
        and scope_c
    )
    add("h", "mediated share computed on the full-window sample (primary) with the "
             "2022+ EV-era scope reported alongside",
        ok, f"estimation_scope={est} interpretation_scope={interp} | full-window rows={full_row} "
            f"EV-era rows={ev_row} | scope_audit(c) PASS={scope_c}")


# ---------------------------------------------------------------------------
# (i) data-flow / layering contract for the Batch-C modules
# ---------------------------------------------------------------------------
def check_i() -> None:
    modules = ["13_charts.py", "14_verify.py", "15_report.py"]
    allowed_read_prefixes = ("data/raw/", "data/processed/", "tables/", "src/")
    allowed_write_prefixes = ("tables/", "charts/", "docs/")
    ok_all, details = True, []
    for mod in modules:
        p = SRC / mod
        if not p.exists():
            ok_all = False
            details.append(f"{mod}: MISSING")
            continue
        txt = p.read_text()
        # every quoted workspace-relative path must live in an allowed location
        paths = set(re.findall(r'["\']((?:data|tables|charts|src|docs)/[^"\'\s]*)["\']', txt))
        # bare directory-prefix tokens are the verifier's own startswith() checks,
        # not file reads
        bare = {"data/", "tables/", "charts/", "src/", "docs/",
                "data", "tables", "charts", "src", "docs"}
        bad_reads = [
            q for q in paths
            if q not in bare
            and not q.startswith(allowed_read_prefixes)
        ]
        # writes: open(..., "w"/"a") and to_csv(<path>) must target tables/, charts/ or docs/
        writes = re.findall(r'open\(\s*(?:f?["\'])([^"\']+)', txt)
        writes += re.findall(r'to_csv\(\s*(?:f?["\'])([^"\']+)', txt)
        bad_writes = []
        for w in writes:
            w = w.strip()
            if w.startswith(allowed_write_prefixes):
                continue
            bad_writes.append(w)
        # no writes into data/
        into_data = any(w.startswith("data/") for w in writes)
        ok = (not bad_reads) and (not bad_writes) and (not into_data)
        ok_all &= ok
        details.append(
            f"{mod}: reads-allowed={not bad_reads}{(' ' + str(bad_reads)) if bad_reads else ''} "
            f"writes-allowed={not bad_writes}{(' ' + str(bad_writes)) if bad_writes else ''} "
            f"no-data-write={not into_data}"
        )
    scope_f = (
        pd.read_csv(TABLES / "scope_audit.csv")
        .query("check.str.startswith('(f)')")["status"] == "PASS"
    ).all()
    ok_all &= scope_f
    add("i", "data-flow/layering contract held (Batch-C modules; 15_report writes docs/)", ok_all,
        " | ".join(details) + f" | scope_audit(f) PASS={scope_f}")


# ---------------------------------------------------------------------------
def main() -> None:
    check_a()
    check_b()
    check_c()
    check_d()
    check_e()
    check_f()
    check_g()
    check_h()
    check_i()

    overall = all(r["status"] == "PASS" for r in RESULTS)
    out = pd.DataFrame(RESULTS)
    out.loc[len(out)] = [
        "OVERALL", "verification pass", "PASS" if overall else "FAIL",
        f"{sum(r['status'] == 'PASS' for r in RESULTS)}/{len(RESULTS)} checks PASS"
        + ("" if overall else "; failing: "
           + ", ".join(r["check"] for r in RESULTS if r["status"] == "FAIL")),
    ]
    out.to_csv(TABLES / "verification_report.csv", index=False)

    print(f"{'=' * 78}\nVERIFICATION PASS — {out.iloc[-1]['detail']}\n{'=' * 78}")
    for r in RESULTS:
        print(f"  [{r['status']}] ({r['check']}) {r['name']}")
        print(f"         {r['detail'][:300]}")
    print(f"\nWROTE {TABLES / 'verification_report.csv'}")
    print(f"WROTE {TABLES / 'report_figures_checklist.csv'}")
    print(f"OVERALL: {'PASS' if overall else 'FAIL'}")
    if not overall:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
