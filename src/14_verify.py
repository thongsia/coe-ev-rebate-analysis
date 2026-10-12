#!/usr/bin/env python3
"""
Step 15 (Batch C) — Independent verification pass.

Re-confirms, from the files on disk (never from memory), that the pipeline's
claims hold, and builds the report-figures checklist that Step 16's report
script must use so every number in REPORT.md traces to a saved table.

Checks:
  (a) fetched row counts == stated totals (re-read data/raw/provenance.csv and
      count the raw CSVs on disk)
  (b) every analysis month maps to real exercises (per-category audit-column
      sums == raw rows in window; the 3 pandemic NA months documented) and real
      registration rows (per-month rows_total == raw rows; EV totals reconcile)
  (c) every rebate step date has a cited policy source in rebate_timeline.csv
  (d) every report figure traces to a saved table (checklist below; written to
      tables/report_figures_checklist.csv)
  (e) dose state: count of effective changes + distinct dose values (+ flat tail)
  (f) no rebate-intensity exhibit estimated on a 2022+-only sample
  (g) price-equation demand regressor = corrected catA_bids_received (not ev_reg)
  (h) mediated share computed on the full-window sample, 2022+ interpretation
  (i) data-flow / layering contract held for the Batch-C modules

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
# (c) every rebate step date matches a cited policy source
# ---------------------------------------------------------------------------
def check_c() -> None:
    panel = pd.read_csv(PROC / "panel_joint.csv")
    rt = pd.read_csv(TABLES / "rebate_timeline.csv")
    step_cols = [
        "reg_cevs_uplift_201611", "reg_cevs_lapse_201801",
        "reg_ves_revival_201809", "reg_eeai_202201",
    ]
    ok_all, details = True, []
    for c in step_cols:
        # effective month = first month where the dummy switches 0 -> 1
        switch = panel.loc[(panel[c] == 1), "month"].iloc[0]
        row = rt[rt["effective_month"] == switch]
        has_cite = (
            len(row) == 1
            and pd.notna(row["source_url"].iloc[0])
            and str(row["source_url"].iloc[0]).startswith("http")
            and pd.notna(row["verification"].iloc[0])
            and len(str(row["verification"].iloc[0])) > 10
        )
        ok_all &= has_cite
        inw = str(row["in_joint_window"].iloc[0]) if len(row) else "ABSENT"
        details.append(f"{c}@{switch}: cited={has_cite} in_joint_window={inw}")
    add("c", "every rebate step date has a cited policy source (rebate_timeline.csv)",
        ok_all, "; ".join(details))


# ---------------------------------------------------------------------------
# (d) report-figures checklist: every figure the report quotes traces to a table
# ---------------------------------------------------------------------------
# Each entry: (fig_id, label, table, filter {col: value}, value_col, expected)
# Filter comparison is exact on str(stripped) unless the value is numeric.
CHECKLIST: list[tuple] = [
    # --- headline price equation (price_equation.csv) ---
    ("pe_headline_coef", "headline reg_eeai_202201 coef (nominal, M1 primary, HC1)",
     "price_equation.csv",
     {"term": "reg_eeai_202201", "spec": "M1_primary_lagged_dum", "price_def": "nominal", "cov_type": "HC1"},
     "coef", 5880.369135737933),
    ("pe_headline_ci_lo", "headline CI lo", "price_equation.csv",
     {"term": "reg_eeai_202201", "spec": "M1_primary_lagged_dum", "price_def": "nominal", "cov_type": "HC1"},
     "ci_lo", 443.59300908121895),
    ("pe_headline_ci_hi", "headline CI hi", "price_equation.csv",
     {"term": "reg_eeai_202201", "spec": "M1_primary_lagged_dum", "price_def": "nominal", "cov_type": "HC1"},
     "ci_hi", 11317.145262394646),
    ("pe_headline_p", "headline p (HC1)", "price_equation.csv",
     {"term": "reg_eeai_202201", "spec": "M1_primary_lagged_dum", "price_def": "nominal", "cov_type": "HC1"},
     "p", 0.034016185897268764),
    ("pe_headline_hac_p", "headline p (HAC)", "price_equation.csv",
     {"term": "reg_eeai_202201", "spec": "M1_primary_lagged_dum_HAC", "price_def": "nominal", "cov_type": "HAC"},
     "p", 0.1039786),
    ("pe_dose_coef", "dose/1000 coef (nominal, M3, HC1)", "price_equation.csv",
     {"term": "dose_1000", "spec": "M3_lagged_dose", "price_def": "nominal", "cov_type": "HC1"},
     "coef", 2348.817485021629),
    ("pe_dose_p", "dose/1000 p (nominal, M3, HC1)", "price_equation.csv",
     {"term": "dose_1000", "spec": "M3_lagged_dose", "price_def": "nominal", "cov_type": "HC1"},
     "p", 2.451135e-09),
    ("pe_dose_real", "dose/1000 coef (real, M3, HC1)", "price_equation.csv",
     {"term": "dose_1000", "spec": "M3_lagged_dose", "price_def": "real", "cov_type": "HC1"},
     "coef", 2824.408603),
    ("pe_real_headline", "reg_eeai coef (real, M1 primary, HC1)", "price_equation.csv",
     {"term": "reg_eeai_202201", "spec": "M1_primary_lagged_dum", "price_def": "real", "cov_type": "HC1"},
     "coef", 7532.475897),
    ("pe_real_headline_p", "reg_eeai p (real, M1 primary, HC1)", "price_equation.csv",
     {"term": "reg_eeai_202201", "spec": "M1_primary_lagged_dum", "price_def": "real", "cov_type": "HC1"},
     "p", 0.01216553),
    ("pe_demand_l1", "demand_l1 coef (nominal, M1 primary, HC1)", "price_equation.csv",
     {"term": "demand_l1", "spec": "M1_primary_lagged_dum", "price_def": "nominal", "cov_type": "HC1"},
     "coef", -1.0393435388757877),
    ("pe_demand_l1_p", "demand_l1 p", "price_equation.csv",
     {"term": "demand_l1", "spec": "M1_primary_lagged_dum", "price_def": "nominal", "cov_type": "HC1"},
     "p", 0.22512912876566982),
    # --- bidding channel (demand_bidding_channel.csv) ---
    ("bd_dummy_hc1", "rebate->demand reg_eeai coef (dummy, HC1)", "demand_bidding_channel.csv",
     {"term": "reg_eeai_202201", "spec": "dummy", "cov_type": "HC1"}, "coef", -277.714269),
    ("bd_dummy_hc1_p", "rebate->demand p (dummy, HC1)", "demand_bidding_channel.csv",
     {"term": "reg_eeai_202201", "spec": "dummy", "cov_type": "HC1"}, "p", 0.0400384050611151),
    ("bd_dummy_hc1_ci", "rebate->demand CI (dummy, HC1)", "demand_bidding_channel.csv",
     {"term": "reg_eeai_202201", "spec": "dummy", "cov_type": "HC1"}, "ci_lo", -542.797821),
    ("bd_dummy_hac_p", "rebate->demand p (dummy, HAC)", "demand_bidding_channel.csv",
     {"term": "reg_eeai_202201", "spec": "dummy_HAC", "cov_type": "HAC"}, "p", 0.1201031),
    ("bd_dose", "rebate->demand dose/1000 coef (dose spec)", "demand_bidding_channel.csv",
     {"term": "dose_1000", "spec": "dose", "cov_type": "HC1"}, "coef", -25.071184),
    ("bd_dose_p", "rebate->demand dose/1000 p", "demand_bidding_channel.csv",
     {"term": "dose_1000", "spec": "dose", "cov_type": "HC1"}, "p", 0.4220217),
    # --- cross-lag (crosslag_check.csv) ---
    ("xl_minus1_p", "cross-lag dose(-1) p", "crosslag_check.csv",
     {"term": "dose_-1_month", "cov_type": "HC1"}, "p", 0.22625199299422727),
    ("xl_plus0_p", "cross-lag dose(0) p", "crosslag_check.csv",
     {"term": "dose_+0_month", "cov_type": "HC1"}, "p", 0.4220217),
    ("xl_plus1_p", "cross-lag dose(+1) p", "crosslag_check.csv",
     {"term": "dose_+1_month", "cov_type": "HC1"}, "p", 0.22625199299422727),
    # --- mediation (mediation_effects.csv) ---
    ("med_total", "mediation total effect", "mediation_effects.csv",
     {"effect": "total"}, "estimate", 2897.443875855129),
    ("med_total_ci", "mediation total CI lo", "mediation_effects.csv",
     {"effect": "total"}, "ci_lo", 1890.1208899496748),
    ("med_indirect", "mediation indirect effect", "mediation_effects.csv",
     {"effect": "indirect"}, "estimate", -43.38119107461191),
    ("med_indirect_ci_lo", "mediation indirect CI lo", "mediation_effects.csv",
     {"effect": "indirect"}, "ci_lo", -399.35084222623016),
    ("med_indirect_ci_hi", "mediation indirect CI hi", "mediation_effects.csv",
     {"effect": "indirect"}, "ci_hi", 253.0904792259348),
    ("med_direct", "mediation direct effect", "mediation_effects.csv",
     {"effect": "direct"}, "estimate", 2940.825066929741),
    ("med_share", "mediated share", "mediation_effects.csv",
     {"effect": "mediated_share"}, "estimate", -0.014972228258194897),
    ("med_share_ci_lo", "mediated share CI lo", "mediation_effects.csv",
     {"effect": "mediated_share"}, "ci_lo", -0.157899),
    ("med_nobs", "mediation n_obs", "mediation_effects.csv",
     {"effect": "mediated_share"}, "n_obs", 109),
    # --- event study (event_study_coefficients.csv) ---
    ("es_onset22", "2022-01 episode onset coef (bounded)", "event_study_coefficients.csv",
     {"episode": "2022-01_eeai_rebate_PLUS_threshold_bounded", "term": "onset_0"},
     "coef", 22682.693696),
    ("es_onset22_ci_lo", "2022-01 onset CI lo", "event_study_coefficients.csv",
     {"episode": "2022-01_eeai_rebate_PLUS_threshold_bounded", "term": "onset_0"},
     "ci_lo", 13995.266283),
    ("es_onset22_p", "2022-01 onset p", "event_study_coefficients.csv",
     {"episode": "2022-01_eeai_rebate_PLUS_threshold_bounded", "term": "onset_0"},
     "p", 3.097343e-07),
    ("es_onset16", "2016-11 episode onset coef (total/low-emission, NOT EV-specific)",
     "event_study_coefficients.csv",
     {"episode": "2016-2018_episode_total_low_emission", "term": "onset_0"},
     "coef", 3484.904917),
    # --- negative controls (negative_controls.csv) ---
    ("nc_A_pct", "2022-01 jump Cat A (EV-eligible) %", "negative_controls.csv",
     {"term": "reg_eeai_202201", "category": "A"}, "coef_pct_of_mean", 10.110609579766617),
    ("nc_C_pct", "2022-01 jump Cat C (clean control) %", "negative_controls.csv",
     {"term": "reg_eeai_202201", "category": "C"}, "coef_pct_of_mean", 13.736183),
    ("nc_D_pct", "2022-01 jump Cat D (clean control) %", "negative_controls.csv",
     {"term": "reg_eeai_202201", "category": "D"}, "coef_pct_of_mean", 41.762959),
    ("nc_E_pct", "2022-01 jump Cat E (clean control) %", "negative_controls.csv",
     {"term": "reg_eeai_202201", "category": "E"}, "coef_pct_of_mean", 36.415949),
    # --- diagnostics (diagnostics_stationarity_autocorr.csv) ---
    ("diag_adf_price_level", "ADF price level p (I(1) evidence)", "diagnostics_stationarity_autocorr.csv",
     {"variable": "catA_clearing_price (nominal)", "form": "level"}, "adf_p", 0.9664896298423258),
    ("diag_adf_price_diff", "ADF price 1st-diff p", "diagnostics_stationarity_autocorr.csv",
     {"variable": "catA_clearing_price (nominal)", "form": "1st diff"}, "adf_p", 4.864086e-17),
    ("diag_dw", "Durbin-Watson of primary residuals (0.7910 row)", "diagnostics_stationarity_autocorr.csv",
     {"variable": "primary price eq. residuals", "form": "residual",
      "note": "Durbin-Watson = 0.7910"}, "variable", "primary price eq. residuals"),
    # --- sensitivity (sensitivity_analysis.csv) ---
    ("sens_noquota", "reg_eeai without catA_quota", "sensitivity_analysis.csv",
     {"spec": "drop_control_catA_quota", "term": "reg_eeai_202201"}, "coef", 8977.563358452839),
    ("sens_notrend", "reg_eeai without trend", "sensitivity_analysis.csv",
     {"spec": "drop_control_trend", "term": "reg_eeai_202201"}, "coef", 6950.021369),
    ("sens_nocpi", "reg_eeai without cpi", "sensitivity_analysis.csv",
     {"spec": "drop_control_cpi_all_items", "term": "reg_eeai_202201"}, "coef", 24866.859723),
    ("sens_bidssucc", "reg_eeai demand=bids_success", "sensitivity_analysis.csv",
     {"spec": "demand_bids_success", "term": "reg_eeai_202201"}, "p", 0.1459261),
    ("sens_lag1", "reg_eeai lag1_only", "sensitivity_analysis.csv",
     {"spec": "lag_lag1_only", "term": "reg_eeai_202201"}, "coef", 6036.897255),
    ("sens_contemp", "reg_eeai contemporaneous", "sensitivity_analysis.csv",
     {"spec": "lag_contemporaneous", "term": "reg_eeai_202201"}, "coef", 7188.714026),
    ("sens_real", "reg_eeai real price def", "sensitivity_analysis.csv",
     {"spec": "price_real", "term": "reg_eeai_202201"}, "coef", 7532.475897),
    # --- 2022+ robustness (price_equation_2022plus_robustness.csv) ---
    ("rob22_d1_p", "2022+ demand_l1 p (nominal)", "price_equation_2022plus_robustness.csv",
     {"term": "demand_l1", "price_def": "nominal"}, "p", 0.507752),
    ("rob22_quota", "2022+ catA_quota coef (nominal)", "price_equation_2022plus_robustness.csv",
     {"term": "catA_quota", "price_def": "nominal"}, "coef", -22.6175),
    ("rob22_rankdef", "2022+ rebate-intensity row is the RANK-DEFICIENT NA row (nobs=41)",
     "price_equation_2022plus_robustness.csv",
     {"term": "rebate (dummies OR dose)"}, "nobs", 41),
    # --- evidence grading (evidence_grading.csv) ---
    ("grade_headline", "headline grade", "evidence_grading.csv",
     {"link": "rebate->price (HEADLINE core question)"}, "grade", "not detectable"),
    ("grade_bidding", "bidding-channel grade", "evidence_grading.csv",
     {"link": "rebate->demand (bidding channel)"}, "grade", "not detectable"),
    ("grade_reg", "registration-channel grade", "evidence_grading.csv",
     {"link": "rebate->demand (registration channel)"}, "grade", "not detectable"),
    ("grade_demand_price", "demand->price grade", "evidence_grading.csv",
     {"link": "demand->price"}, "grade", "not detectable"),
    ("grade_med", "mediation grade", "evidence_grading.csv",
     {"link": "total indirect effect (rebate->demand->price)"}, "grade", "not detectable"),
    # --- EV descriptive (ev_registrations_descriptive.csv) ---
    ("ev_n_months", "observed BEV months", "ev_registrations_descriptive.csv",
     {"month": "SUMMARY_observed_months"}, "ev_reg", 35),
    ("ev_mean", "mean EV registrations", "ev_registrations_descriptive.csv",
     {"month": "SUMMARY_mean_ev_reg"}, "ev_reg", 854.257143),
    ("ev_max", "max EV registrations", "ev_registrations_descriptive.csv",
     {"month": "SUMMARY_max_ev_reg"}, "ev_reg", 2014),
    ("ev_share_mean", "mean EV share", "ev_registrations_descriptive.csv",
     {"month": "SUMMARY_mean_ev_share"}, "ev_reg", 0.258154),
    ("ev_cum", "cumulative EV registrations", "ev_registrations_descriptive.csv",
     {"month": "SUMMARY_cumulative_ev_reg"}, "ev_reg", 29899),
    ("ev_cov_min", "min coverage (lower-bound decay)", "ev_registrations_descriptive.csv",
     {"month": "SUMMARY_min_coverage"}, "ev_reg", 0.181713),
    # --- dose / scope (dose_summary.csv, scope_audit.csv, data_audit.csv) ---
    ("dose_changes", "effective in-window changes", "dose_summary.csv",
     {"item": "effective_in_window_changes"}, "value", 4),
    ("dose_flat", "dose constant 2022-01..2025-05", "dose_summary.csv",
     {"item": "dose_constant_2022_01_to_2025_05"}, "value", "TRUE"),
    ("scope_a", "scope audit (a) no 2022+-only rebate exhibit", "scope_audit.csv",
     {"detail_prefix": "(a)"}, "status", "PASS"),
    ("scope_b", "scope audit (b) demand regressor = clean", "scope_audit.csv",
     {"detail_prefix": "(b)"}, "status", "PASS"),
    ("scope_c", "scope audit (c) mediated share full-window", "scope_audit.csv",
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
# (e) dose state: count of effective changes + distinct dose values
# ---------------------------------------------------------------------------
def check_e() -> None:
    panel = pd.read_csv(PROC / "panel_joint.csv")
    doses = sorted(panel["dose_nominal_sgd"].dropna().unique().tolist())
    ds = pd.read_csv(TABLES / "dose_summary.csv").set_index("item")
    distinct = int(ds.loc["n_distinct_dose_values", "value"])
    changes = int(ds.loc["effective_in_window_changes", "value"])
    flat_tail = int(ds.loc["flat_tail_value", "value"])
    sub = panel[panel["month"] >= "2022-01"]
    flat_ok = (sub["dose_nominal_sgd"].nunique() == 1
               and int(sub["dose_nominal_sgd"].iloc[0]) == flat_tail == 7500)
    ok = (
        distinct == len(doses) == 5
        and changes == 4
        and doses == [2000, 3000, 4000, 6000, 7500]
        and flat_ok
    )
    add("e", "dose state: 4 effective changes; distinct doses [2000,3000,4000,6000,7500]; flat 7500 from 2022-01",
        ok, f"panel distinct={doses} (n={len(doses)}); dose_summary: distinct={distinct}, "
            f"changes={changes}, flat_tail={flat_tail}; 2022-01..2025-05 flat={flat_ok}")


# ---------------------------------------------------------------------------
# (f) no rebate-intensity exhibit estimated on a 2022+-only sample
# ---------------------------------------------------------------------------
def check_f() -> None:
    pe = pd.read_csv(TABLES / "price_equation.csv")
    # every row carrying a rebate term must have a full-window sample
    rebate_rows = pe[pe["term"].isin(["reg_eeai_202201", "dose_1000", "threshold"])]
    full = rebate_rows["sample"].astype(str).str.startswith("2016-01..2025-05")
    bd = pd.read_csv(TABLES / "demand_bidding_channel.csv")
    bd_full = bd[bd["term"].isin(["reg_eeai_202201", "dose_1000", "threshold"])]
    bd_full = bd_full["sample"].astype(str).str.startswith("2016-01..2025-05").all()
    med = pd.read_csv(TABLES / "mediation_effects.csv")
    med_scope = any(
        str(r["effect"]).startswith("# estimation_scope: 2016-01..2025-05")
        for _, r in med.iterrows()
    )
    scope_a = (
        pd.read_csv(TABLES / "scope_audit.csv")
        .query("check.str.startswith('(a)')")["status"] == "PASS"
    ).all()
    rob = pd.read_csv(TABLES / "price_equation_2022plus_robustness.csv")
    rankdef = (
        rob[rob["term"].astype(str).str.startswith("rebate (dummies OR dose)")]
        ["note"].astype(str).str.startswith("RANK-DEFICIENT").all()
        and len(
            rob[rob["term"].astype(str).str.startswith("rebate (dummies OR dose)")]
        ) > 0
    )
    ok = full.all() and bd_full and med_scope and scope_a and rankdef
    add("f", "no rebate-intensity exhibit estimated on a 2022+-only sample",
        ok,
        f"price_equation rebate-term rows full-window={full.all()} (n={len(rebate_rows)}) | "
        f"bidding-channel full-window={bd_full} | mediation est-scope full-window={med_scope} | "
        f"scope_audit(a) PASS={scope_a} | 2022+ robustness rebate row RANK-DEFICIENT={rankdef}")


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
# (h) mediated share on full-window sample, 2022+ interpretation
# ---------------------------------------------------------------------------
def check_h() -> None:
    med = pd.read_csv(TABLES / "mediation_effects.csv")
    est = [r["effect"] for _, r in med.iterrows()
           if str(r["effect"]).startswith("# estimation_scope")]
    interp = [r["effect"] for _, r in med.iterrows()
              if str(r["effect"]).startswith("# interpretation_scope")]
    scope_c = (
        pd.read_csv(TABLES / "scope_audit.csv")
        .query("check.str.startswith('(c)')")["status"] == "PASS"
    ).all()
    ok = (
        len(est) == 1 and "2016-01..2025-05" in est[0]
        and len(interp) == 1 and "2022-01..2025-05" in interp[0]
        and scope_c
    )
    add("h", "mediated share computed on full-window sample with 2022+ interpretation",
        ok, f"estimation_scope={est} interpretation_scope={interp} scope_audit(c) PASS={scope_c}")


# ---------------------------------------------------------------------------
# (i) data-flow / layering contract for the Batch-C modules
# ---------------------------------------------------------------------------
def check_i() -> None:
    modules = ["13_charts.py", "14_verify.py", "15_report.py"]
    allowed_read_prefixes = ("data/raw/", "data/processed/", "tables/", "src/")
    allowed_write = ("tables/", "charts/")
    root_writes = {"REPORT.md", "STATS_SUMMARY.md"}
    ok_all, details = True, []
    for mod in modules:
        p = SRC / mod
        if not p.exists():
            ok_all = False
            details.append(f"{mod}: MISSING")
            continue
        txt = p.read_text()
        # every quoted workspace-relative path must live in an allowed location
        paths = set(re.findall(r'["\']((?:data|tables|charts|src)/[^"\'\s]*)["\']', txt))
        paths |= set(re.findall(r'["\']((?:REPORT\.md|STATS_SUMMARY\.md))["\']', txt))
        # bare directory-prefix tokens ("data/", "tables/", ...) are the
        # verifier's own startswith() checks, not file reads
        bare = {"data/", "tables/", "charts/", "src/", "data", "tables", "charts", "src"}
        bad_reads = [
            q for q in paths
            if q not in bare
            and not q.startswith(allowed_read_prefixes) and q not in root_writes
        ]
        # writes: open(..., "w"/"a") and to_csv(<path>) must target tables/ or charts/ or (15) root reports
        writes = re.findall(r'open\(\s*(?:f?["\'])([^"\']+)', txt)
        writes += re.findall(r'to_csv\(\s*(?:f?["\'])([^"\']+)', txt)
        bad_writes = []
        for w in writes:
            w = w.strip()
            if w.startswith("tables/") or w.startswith("charts/"):
                continue
            if mod == "15_report.py" and w in root_writes:
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
    add("i", "data-flow/layering contract held (Batch-C modules)", ok_all,
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
