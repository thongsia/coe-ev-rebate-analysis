#!/usr/bin/env python3
"""
Step 5 — Joint panel + rebate encoding (final assembly of Batch A).

Reads:
  data/processed/coe_monthly.csv        (Step 3)
  data/processed/ev_registrations.csv   (Step 4)
  data/raw/cpi_raw.csv                  (Step 2, verbatim CPI All Items wide table)
  data/raw/provenance.csv               (Step 2)

Writes:
  data/processed/panel_joint.csv                 (2016-01..2025-05, 113 rows, one per month)
  data/processed/coe_extension_2025_06_2026_10.csv (COE-only descriptive extension)
  data/processed/cpi_deflated.csv                (Category A clearing price, real terms)
  tables/rebate_timeline.csv                     (4 within-window regime changes + out-of-window notes)
  tables/dose_summary.csv                        (count of changes + distinct dose values + flat check)
  tables/data_audit.csv                          (rows fetched, totals, reconciliation, panel size,
                                                  exercises-per-month, distinct doses, adaptations)

FULL-WINDOW ESTIMATION / 2022+ INTERPRETATION RULE
--------------------------------------------------
Every rebate-intensity exhibit is ESTIMATED on the full window 2016-01..2025-05
(the joint panel below). The rebate dose is FLAT from 2022-01 to the window
end, so estimation restricted to 2022+ would be rank-deficient (a dose that
never varies within the sample cannot be identified). 2022+ is the
INTERPRETATION scope only (where the EEAI-era rebate level is actually in
force); it is NOT an estimation scope. This rule is asserted below
(`assert dose constant 2022-01..2025-05`).

REBATE ENCODING (as specified by the analysis plan — a stylized case-study
design)
--------------------------------------------
The plan specifies FOUR within-window rebate-level changes and requires the
dose to be constant from 2022-01 to the window end. We encode:
  (a) 4 discrete regime step dummies, each switching on (0 -> 1) at its
      effective month; and
  (b) a continuous nominal dose = maximum total EV rebate available that month
      (current-dollar, not deflated).

REGIME SCHEDULE (effective month -> regime level, nominal S$):
  2016-01 .. 2016-10   dose 4000   regime 0   (CEVS-era baseline)
  2016-11 .. 2017-12   dose 6000   regime 1   (plan: 'Nov 2016 CEVS uplift', up)
  2018-01 .. 2018-08   dose 2000   regime 2   (plan: 'Jan 2018 CEVS lapse', down)
  2018-09 .. 2021-12   dose 3000   regime 3   (plan: 'Sep 2018 VES revival', up)
  2022-01 .. 2025-05   dose 7500   regime 4   (plan: 'Jan 2022 EEAI', up; $7,500 anchor)

TRANSPARENCY — plan schedule vs. verified real Singapore policy
---------------------------------------------------------------
The 4-event schedule above is the analysis plan's self-consistent CASE-STUDY
construct. It is used as the identification design because the plan's
full-window / 2022+ rule depends on the dose being flat 2022-01 -> window end.
Verified LTA/MOT/NEA sources (see tables/rebate_timeline.csv, `real_policy_note`
and `source_url` columns) show real Singapore policy differs:
  - CEVS ran 1 Jan 2013 .. 31 Dec 2017 (a revised version 1 Jul 2015 ..
    31 Dec 2017); there is NO discrete 'Nov 2016 uplift' on the LTA page.
    The plan's 'Jan 2018 CEVS lapse' IS corroborated (CEVS expired 31 Dec 2017).
  - VES came into effect 1 Jan 2018 (NEA), not 'Sep 2018'; the 'revival'
    framing is not corroborated.
  - EEAI (EV Early Adoption Incentive) was introduced 1 Jan 2021 at a 45%-of-ARF
    rebate capped at $20,000 (2021-2023), then $15,000 (2024-2025), then $7,500
    (2026-2027). The $7,500 figure is real but is the 2026 cap, not a Jan 2022
    introduction. The actual Jan 2022 policy change was the $0 ARF floor for EVs.
Accordingly, ONLY the final-regime dose level ($7,500) is a verified policy
figure; the pre-2022 dose levels (4000/6000/2000/3000) are NOMINAL CASE-STUDY
CONSTRUCTS (directions per plan, magnitudes not verifiable) and are flagged as
such in every deliverable. This does not affect the 4 regime step dummies,
which carry the identification.

OUT-OF-WINDOW NOTES (required by the plan)
  - The Jan 2026 EEAI cap cut (-> $7,500) lives in the COE-ONLY extension
    (2025-06..2026-10), outside the joint panel window (which ends 2025-05).
  - The CEVS introduction (plan: 2012; verified: 1 Jan 2013) is OUTSIDE the
    2016-01 window and therefore contributes nothing to identification.

Layering contract: reads only data/raw/ and earlier data/processed/ files;
writes only data/processed/ and tables/. Run: python3 src/04_panel_rebate.py
"""

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
COE = ROOT / "data" / "processed" / "coe_monthly.csv"
EVREG = ROOT / "data" / "processed" / "ev_registrations.csv"
CPI = ROOT / "data" / "raw" / "cpi_raw.csv"
PROV = ROOT / "data" / "raw" / "provenance.csv"
PP = ROOT / "data" / "processed"
TT = ROOT / "tables"
PP.mkdir(parents=True, exist_ok=True)
TT.mkdir(parents=True, exist_ok=True)

WINDOW_START, WINDOW_END = "2016-01", "2025-05"
INTERP_START = "2022-01"
EXT_START, EXT_END = "2025-06", "2026-10"

CATS = ["A", "B", "C", "D", "E"]

# ---- regime schedule (plan-specified case-study design) ----
# (effective_month, regime_label, dose_nominal_sgd, verified?)
REGIMES = [
    ("2016-01", 0, 4000, False),
    ("2016-11", 1, 6000, False),
    ("2018-01", 2, 2000, False),
    ("2018-09", 3, 3000, False),
    ("2022-01", 4, 7500, True),   # $7,500 is the one verified policy figure
]
DUMMY_NAMES = {
    "2016-11": "reg_cevs_uplift_201611",
    "2018-01": "reg_cevs_lapse_201801",
    "2018-09": "reg_ves_revival_201809",
    "2022-01": "reg_eeai_202201",
}


def regime_of(month: str):
    """Return (regime_label, dose) for a month string under the plan schedule."""
    label, dose = REGIMES[0][1], REGIMES[0][2]
    for eff, lab, d, _ in REGIMES:
        if month >= eff:
            label, dose = lab, d
    return label, dose


def month_grid(a: str, b: str):
    y0, m0 = int(a[:4]), int(a[5:7])
    y1, m1 = int(b[:4]), int(b[5:7])
    out = []
    y, m = y0, m0
    while (y, m) <= (y1, m1):
        out.append(f"{y}-{m:02d}")
        m += 1
        if m == 13:
            m, y = 1, y + 1
    return out


def load_cpi_all_items() -> pd.DataFrame:
    """Melt the 'All Items' row of the wide CPI table to month -> index."""
    cpi = pd.read_csv(CPI, dtype=str)
    allrow = cpi[cpi["DataSeries"].str.strip() == "All Items"]
    if len(allrow) != 1:
        raise SystemExit(f"HARD-FAIL: expected 1 'All Items' CPI row, got {len(allrow)}")
    allrow = allrow.iloc[0]
    mon = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
           "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
    rows = []
    for col, val in allrow.items():
        m = re.match(r"^(20\d{2})(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)$", str(col))
        if not m or pd.isna(val):
            continue
        month = f"{m.group(1)}-{mon[m.group(2)]:02d}"
        rows.append({"month": month, "cpi_all_items": float(val)})
    c = pd.DataFrame(rows).sort_values("month").reset_index(drop=True)
    return c


def main():
    coe = pd.read_csv(COE, dtype={"month": str})
    ev = pd.read_csv(EVREG, dtype={"month": str})
    cpi = load_cpi_all_items()

    # ---------------- rebate encodings (full grid) ----------------
    enc = {}
    for mth in month_grid(WINDOW_START, WINDOW_END):
        label, dose = regime_of(mth)
        row = {"month": mth, "rebate_regime": label, "dose_nominal_sgd": dose}
        for eff, name in DUMMY_NAMES.items():
            row[name] = 1 if mth >= eff else 0
        enc[mth] = row
    enc_df = pd.DataFrame(list(enc.values()))

    # ---------------- wide-format COE per category ----------------
    coe_w = coe.set_index("month")
    for cat in CATS:
        sub = coe_w[coe_w["category"] == cat]
        for src, dst in [("clearing_price", f"cat{cat}_clearing_price"),
                         ("quota_total", f"cat{cat}_quota"),
                         ("bids_received_total", f"cat{cat}_bids_received"),
                         ("bids_successful_total", f"cat{cat}_bids_success"),
                         ("exercise_count", f"cat{cat}_exercises")]:
            enc_df = enc_df.merge(sub[[src]].rename(columns={src: dst}),
                                  on="month", how="left")

    # ---------------- EV registration columns ----------------
    ev_cols = ev[["month", "ev_reg", "ev_share", "coverage_rate",
                  "nonnull_total", "rows_total"]].rename(
        columns={"rows_total": "ev_rows_total"})
    enc_df = enc_df.merge(ev_cols, on="month", how="left")

    # interpretation-window flag (Batch B: 2022+ is interpretation scope only)
    enc_df["in_interpretation_window"] = (enc_df["month"] >= INTERP_START).astype(int)
    enc_df = enc_df.sort_values("month").reset_index(drop=True)

    assert len(enc_df) == 113, f"panel must be 113 months, got {len(enc_df)}"
    assert enc_df["month"].min() == WINDOW_START and enc_df["month"].max() == WINDOW_END

    # ---- FLAT-DOSE ASSERTION (the rank-deficiency rule it underpins) ----
    flat = enc_df[enc_df["month"] >= INTERP_START]["dose_nominal_sgd"]
    if flat.nunique() != 1:
        raise SystemExit(
            f"HARD-FAIL: dose not constant from {INTERP_START} to {WINDOW_END}; "
            f"values={sorted(flat.unique())}. Full-window estimation would be "
            f"rank-deficient only if 2022+ were the estimation scope.")
    print(f"[panel] dose constant {INTERP_START}..{WINDOW_END} = {int(flat.iloc[0])}  [OK]")

    # ---------------- CPI deflation (Category A, real terms) ----------------
    # real = nominal * 100 / CPI_index. Monthly CPI is available, so an annual
    # (e.g. calendar-yr or rolling) deflator was CONSIDERED AND REJECTED:
    # monthly CPI All Items covers the whole window and avoids averaging away
    # intra-year price moves that matter for a monthly COE clearing-price series.
    a = enc_df[["month", "catA_clearing_price"]].merge(cpi, on="month", how="left")
    if a["cpi_all_items"].isna().any():
        bad = a[a["cpi_all_items"].isna()]["month"].tolist()
        raise SystemExit(f"HARD-FAIL: CPI missing for months {bad}")
    a["catA_clearing_price_real"] = (a["catA_clearing_price"] * 100.0 / a["cpi_all_items"]).round(2)
    a = a[["month", "catA_clearing_price", "cpi_all_items", "catA_clearing_price_real"]]
    a["deflator_note"] = "monthly CPI All Items (2024 base); annual fallback rejected (monthly available)"
    a.to_csv(PP / "cpi_deflated.csv", index=False)
    print(f"[panel] cpi_deflated rows={len(a)} (Cat A real terms)")

    # ---------------- joint panel ----------------
    enc_df.to_csv(PP / "panel_joint.csv", index=False)
    print(f"[panel] panel_joint rows={len(enc_df)} ({WINDOW_START}..{WINDOW_END})")

    # ---------------- COE-only descriptive extension ----------------
    ext_months = month_grid(EXT_START, EXT_END)
    ext = coe[coe["month"].isin(ext_months)].copy()
    ext = ext.sort_values(["month", "category"]).reset_index(drop=True)
    # annotate the Jan 2026 real-policy cap cut (lives here, out of joint window)
    note = ""
    ext["note"] = ""
    ext.loc[ext["month"] == "2026-01", "note"] = (
        "Jan 2026: real-policy EEAI ARF-rebate cap cut to $7,500 takes effect "
        "(COE-only extension; OUTSIDE the 2016-01..2025-05 joint window)")
    ext.to_csv(PP / f"coe_extension_{EXT_START.replace('-', '_')}_{EXT_END.replace('-', '_')}.csv",
               index=False)
    print(f"[panel] coe_extension rows={len(ext)} ({EXT_START}..{EXT_END}, COE-only, descriptive)")

    # ---------------- rebate timeline ----------------
    LTA_EM = "https://onemotoring.lta.gov.sg/content/onemotoring/home/buying/upfront-vehicle-costs/emissions-charges.html"
    NEA_VES = "https://www.nea.gov.sg/media/news/news/index/increased-rebates-for-cleaner-vehicles-under-enhanced-vehicular-emissions-scheme"
    LTA_EV = "https://www.lta.gov.sg/content/ltagov/en/industry_innovations/technologies/electric_vehicles/transitioning_to_evs.html"
    COEWATCH = "https://coewatch.sg/glossary/ev-early-adoption-incentive"
    timeline = [
        {"effective_month": "2016-11", "programme": "CEVS uplift (plan)",
         "direction": "up", "size": "nominal +2000 (case-study construct; magnitude not verifiable)",
         "in_joint_window": "Yes", "in_extension": "No",
         "source_url": LTA_EM,
         "verification": "NOT corroborated as a discrete Nov 2016 step; LTA shows a revised CEVS in force 1 Jul 2015 .. 31 Dec 2017 with no Nov 2016 step."},
        {"effective_month": "2018-01", "programme": "CEVS lapse (plan)",
         "direction": "down", "size": "nominal -4000 (case-study construct; magnitude not verifiable)",
         "in_joint_window": "Yes", "in_extension": "No",
         "source_url": LTA_EM,
         "verification": "CORROBORATED: CEVS applied to cars/taxis registered through 31 Dec 2017, so it lapsed 1 Jan 2018 (VES replaced it)."},
        {"effective_month": "2018-09", "programme": "VES revival (plan)",
         "direction": "up", "size": "nominal +1000 (case-study construct; magnitude not verifiable)",
         "in_joint_window": "Yes", "in_extension": "No",
         "source_url": NEA_VES,
         "verification": "PARTIALLY corroborated: VES came into effect 1 Jan 2018 (NEA), not Sep 2018; the 'revival' framing is not corroborated."},
        {"effective_month": "2022-01", "programme": "EEAI introduction incl. 45% ARF rebate capped at $7,500 (plan)",
         "direction": "up", "size": "$7,500 (verified policy figure; used as dose anchor)",
         "in_joint_window": "Yes", "in_extension": "No",
         "source_url": LTA_EV + " | " + COEWATCH,
         "verification": "DISCREPANCY (documented): real EEAI introduced 1 Jan 2021 at 45%-of-ARF capped at $20,000 (2021-23) -> $15,000 (2024-25) -> $7,500 (2026-27). The $7,500 is the 2026 cap, not a Jan 2022 introduction. The actual Jan 2022 change was the $0 ARF floor for EVs."},
        # --- out-of-window notes required by the plan ---
        {"effective_month": "2026-01", "programme": "EEAI cap cut to $7,500 (real policy)",
         "direction": "down", "size": "$15,000 -> $7,500 (verified)",
         "in_joint_window": "No", "in_extension": "Yes (2025-06..2026-10, COE-only)",
         "source_url": LTA_EV,
         "verification": "CORROBORATED: 'From 1 Jan 2026 to 31 Dec 2026, the rebate will be capped at $7,500' (LTA). Outside the joint window; lives in the COE-only extension."},
        {"effective_month": "2013-01", "programme": "CEVS introduction (plan says 2012)",
         "direction": "baseline", "size": "n/a",
         "in_joint_window": "No (before 2016-01)", "in_extension": "No",
         "source_url": "https://www.nccs.gov.sg/media/new-carbon-emissions-based-vehicle-scheme-cevs-from-1-january-2013",
         "verification": "CORROBORATED at 1 Jan 2013 (NCCS), not 2012. OUTSIDE the 2016-01 window -> contributes nothing to identification."},
    ]
    pd.DataFrame(timeline).to_csv(TT / "rebate_timeline.csv", index=False)
    print(f"[panel] rebate_timeline rows={len(timeline)} (4 in-window + 2 out-of-window notes)")

    # ---------------- dose summary ----------------
    in_win = enc_df
    distinct_doses = sorted(in_win["dose_nominal_sgd"].unique().astype(int).tolist())
    flat_tail = in_win[in_win["month"] >= INTERP_START]["dose_nominal_sgd"].nunique() == 1
    dose_rows = [
        {"item": "effective_in_window_changes", "value": len(DUMMY_NAMES),
         "note": "4 regime step dummies, each switching on at its effective month"},
        {"item": "distinct_dose_values",
         "value": "; ".join(str(d) for d in distinct_doses),
         "note": "nominal S$; only $7,500 (2022-01..) is a verified policy figure; pre-2022 levels are nominal case-study constructs (directions per plan, magnitudes not verifiable)"},
        {"item": "n_distinct_dose_values", "value": len(distinct_doses), "note": ""},
        {"item": "dose_constant_2022_01_to_2025_05",
         "value": "TRUE" if flat_tail else "FALSE",
         "note": "ASSERTED — underpins the full-window estimation / 2022+ interpretation rule (2022+-only estimation is rank-deficient)"},
        {"item": "flat_tail_value", "value": int(flat.iloc[0]), "note": "dose level in force 2022-01..2025-05"},
        {"item": "estimation_window", "value": f"{WINDOW_START}..{WINDOW_END}",
         "note": "every rebate-intensity exhibit estimated here; 2022+ is interpretation scope ONLY"},
    ]
    pd.DataFrame(dose_rows).to_csv(TT / "dose_summary.csv", index=False)
    print(f"[panel] dose_summary: {len(distinct_doses)} distinct doses {distinct_doses}, flat tail={flat_tail}")

    # ---------------- data audit ----------------
    prov = pd.read_csv(PROV, dtype={"stated_source_total": str, "fetched_count": str,
                                    "unique_id_count": str})
    audit = []
    for _, r in prov.iterrows():
        audit.append({"metric": f"fetched_rows_{r['key']}", "value": r["fetched_count"],
                      "note": f"stated_source_total={r['stated_source_total']}"})
        audit.append({"metric": f"stated_total_{r['key']}", "value": r["stated_source_total"],
                      "note": f"resource_id={r['resource_id']}"})
        audit.append({"metric": f"reconciliation_{r['key']}", "value": r["match"],
                      "note": "OK = fetched_count == stated_source_total"})
    audit.append({"metric": "panel_row_count", "value": len(enc_df),
                  "note": "expected 113 (2016-01..2025-05)"})
    # exercises per month (across all 5 categories), over the panel window
    per_month_ex = enc_df[[f"cat{c}_exercises" for c in CATS]].sum(axis=1)
    audit.append({"metric": "exercises_per_month_min", "value": int(per_month_ex.min()),
                  "note": "sum across 5 categories, 2016-01..2025-05"})
    audit.append({"metric": "exercises_per_month_mean", "value": round(float(per_month_ex.mean()), 3),
                  "note": ""})
    audit.append({"metric": "exercises_per_month_max", "value": int(per_month_ex.max()),
                  "note": ""})
    # per (month, category) exercise-count distribution (1 or 2 exercises)
    per_mc = (enc_df[[f"cat{c}_exercises" for c in CATS]].stack())
    audit.append({"metric": "exercises_per_month_category_min", "value": int(per_mc.min()),
                  "note": "per (month,category): 1 or 2 exercises"})
    audit.append({"metric": "exercises_per_month_category_max", "value": int(per_mc.max()),
                  "note": ""})
    audit.append({"metric": "distinct_dose_values",
                  "value": "; ".join(str(d) for d in distinct_doses),
                  "note": "nominal S$ (only $7,500 verified)"})
    audit.append({"metric": "adaptation", "value": "coverage_rate defined as rows_nonnull/rows_total",
                  "note": "fraction of raw rows with an observed (non-null) count; decays 1.0->0.23 over the window. The plan's literal nonnull_total/(total rows) mixes count-sum/row-count and is not a rate; ev_reg remains a lower bound under either definition."})
    audit.append({"metric": "adaptation", "value": "category parse: last token of vehicle_class",
                  "note": "'Category A' must be parsed by its trailing letter; a substring match on 'A' would mis-assign every row to Category A (caught by reconciliation)."})
    audit.append({"metric": "adaptation", "value": "plan vs real rebate policy discrepancy",
                  "note": "The 4-event schedule is a stylized case-study design (plan). Verified LTA/NEA policy differs: EEAI from 1 Jan 2021 at $20k cap -> $15k (2024) -> $7.5k (2026); VES from 1 Jan 2018; CEVS ran through 31 Dec 2017; $0 ARF floor from 1 Jan 2022. Only the $7,500 dose anchor is a verified figure; pre-2022 dose levels are nominal constructs. See tables/rebate_timeline.csv."})
    audit.append({"metric": "adaptation", "value": "registrations fetched via 20k pagination",
                  "note": "datastore limit=100000 returns HTTP 413 on the 51,669-row store; paged at limit=20000. All _id unique (51,669)."})
    # genuine data gap: LTA suspended COE exercises Apr-Jun 2020 (pandemic)
    gap = sorted(set(month_grid(WINDOW_START, WINDOW_END)) - set(coe["month"]))
    audit.append({"metric": "coe_exercise_gap", "value": "; ".join(gap),
                  "note": "NO COE exercises held 2020-04/05/06 (LTA pandemic suspension) -> these 3 months have NA COE clearing prices / quota / bids in panel_joint.csv and cpi_deflated.csv. Not an error; the panel keeps the month rows (month-keyed) with missing COE values. 199 of 202 months in 2010-01..2026-10 have >=1 exercise."})
    pd.DataFrame(audit).to_csv(TT / "data_audit.csv", index=False)
    print(f"[panel] data_audit rows={len(audit)}")
    print("[panel] DONE")


if __name__ == "__main__":
    main()
