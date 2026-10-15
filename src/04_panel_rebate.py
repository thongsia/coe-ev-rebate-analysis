#!/usr/bin/env python3
"""
Step 5 — Joint panel + rebate encoding (verified real Singapore policy).

Reads:
  data/processed/coe_monthly.csv        (Step 3)
  data/processed/ev_registrations.csv   (Step 4)
  data/raw/cpi_raw.csv                  (Step 2, verbatim CPI All Items wide table)
  data/raw/provenance.csv               (Step 2)

Writes:
  data/processed/panel_joint.csv                 (2016-01..2025-05, 113 rows, one per month)
  data/processed/coe_extension_2025_06_2026_10.csv (COE-only descriptive extension)
  data/processed/cpi_deflated.csv                (Category A clearing price, real terms)
  tables/rebate_timeline.csv                     (verified real Singapore policy; every row
                                                  source_url + verification note; incl.
                                                  out-of-window rows)
  tables/dose_summary.csv                        (distinct doses, 2022+ estimable note,
                                                  estimation windows)
  tables/data_audit.csv                          (rows fetched, totals, reconciliation, panel size,
                                                  exercises-per-month, distinct doses, adaptations)

DUAL-SCOPE RULE (verified policy)
---------------------------------
The rebate dose is encoded from the VERIFIED REAL SINGAPORE POLICY TIMELINE:

  * CEVS (revised) in force 1 Jul 2015 .. 31 Dec 2017 (original CEVS 2013-2015).
  * CEVS LAPSES 1 Jan 2018; VES (Vehicular Emissions Scheme) begins 1 Jan 2018
    (NEA). VES Band A1 rebate $25,000 off ARF, with a $5,000 minimum-ARF floor
    until 31 Dec 2021.
  * EEAI (EV Early Adoption Incentive) from 1 Jan 2021: 45% off ARF, capped
    $20,000 (2021-23) -> $15,000 (2024-25) -> $7,500 (2026); ceases 1 Jan 2027.
  * ARF FLOOR (tax provision, NOT a rebate): $5,000 min ARF for all cars
    2021 and earlier; LOWERED TO $0 FOR ELECTRIC CARS 1 Jan 2022 .. 31 Dec 2023
    (extended through 31 Dec 2027, LTA circular VRL/16/2025 of 8 Sep 2025).
  * VES 2024: A1 $25,000; 2026: $22,500; 2027: $20,000 (extension window only).
  * 97 -> 110 kW Category A power-threshold change: 1 Jan 2022 (confounder).

The dose is FLAT 2016-01..2017-12 (CEVS), flat 2018-01..2020-12 (VES A1),
flat 2021-01..2023-12 (stacked 45000), and flat 2024-01..2025-05 (stacked
40000). Two distinct dose values exist inside 2022-01..2025-05 (45000,
40000), so the 2022+ window is ALSO A VALID ESTIMATION scope (41 obs).
Both scopes are estimated for the headline exhibits; the full window
(2016-01..2025-05) remains primary, and the 2022+ scope is asserted by
``n_distinct_doses_2022plus == 2``.

REBATE ENCODING
---------------
``dose_nominal_sgd`` = "combined max EV rebate available that month (S$,
nominal)" = VES A1 rebate + EEAI cap when both in force, CEVS dose otherwise:
  2016-01..2017-12 : 20000   (CEVS ESTIMATE — direction certain, magnitude
                                          approximate; pre-VES baseline)
  2018-01..2020-12 : 25000   (VES A1, verified)
  2021-01..2021-12 : 45000   (VES A1 25000 + EEAI cap 20000; $5,000 ARF floor
                             in force -> part of the nominal cap unusable)
  2022-01..2023-12 : 45000   (same caps; zero ARF floor -> full caps usable)
  2024-01..2025-05 : 40000   (VES A1 25000 + EEAI cap 15000)
Distinct in-window dose values: 20000, 25000, 45000, 40000 (4 values).
Out-of-window: 2025-06..2025-12 extension = 40000 (annotated in the
COE-only extension); 2026-01..2026-10 = 27500 (VES 22500 + EEAI 7500).

DUMMIES
-------
Verified-policy dummies (the key regime columns for the headline exhibits):
  reg_real_ves_201801      = 1 from 2018-01 (VES onset, CEVS lapse)
  reg_real_evstack_202101  = 1 from 2021-01 (enhanced VES + EEAI introduction)
  reg_arffloor_zero_202201 = 1 from 2022-01 (zero ARF floor for EVs — TAX
                             provision, separate from rebates)
  reg_eeai_cap15k_202401   = 1 from 2024-01 (EEAI cap 20k -> 15k; dose 45000 -> 40000)
  ves_program (0/1)        = 1 from 2018-01 (VES/Enhanced-VES era vs CEVS era)
  eeai_active (0/1)        = 1 from 2021-01
COLLINEARITY NOTE (carried into downstream exhibits):
  dose ≈ 20000 + 5000*reg_real_ves_201801 + 20000*reg_real_evstack_202101
           - 5000*reg_eeai_cap15k_202401
so dose and the real-policy dummies are near-exact linear transforms of one
another. Exhibits must NOT put dose + all 4 real dummies + trend + intercept
in one regression; each exhibit chooses a DOSE-ONLY spec OR a DUMMY-ONLY spec
(documented per exhibit).

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

# ---------------------------------------------------------------------------
# VERIFIED-POLICY dose schedule (see module docstring for sources)
# (effective_month, regime_label, dose_nominal_sgd, verified?)
# ---------------------------------------------------------------------------
REGIMES = [
    ("2016-01", 0, 20000, False),  # CEVS estimate (revised CEVS in force; magnitude approximate)
    ("2018-01", 1, 25000, True),   # VES A1 (verified)
    ("2021-01", 2, 45000, True),   # VES A1 25000 + EEAI cap 20000 (verified; ARF floor 5000)
    ("2024-01", 3, 40000, True),   # VES A1 25000 + EEAI cap 15000 (verified)
]
# Verified-policy dummies: (effective_month, column_name)
REAL_DUMMY_NAMES = {
    "2018-01": "reg_real_ves_201801",
    "2021-01": "reg_real_evstack_202101",
    "2022-01": "reg_arffloor_zero_202201",
    "2024-01": "reg_eeai_cap15k_202401",
}
# Era dummies
ERA_DUMMY_NAMES = {
    "2018-01": "ves_program",
    "2021-01": "eeai_active",
}
# Out-of-window (extension) dose: EEAI cap 2026 = 7500, VES 2026 A1 = 22500
EXT_DOSE_2025 = 40000   # 2025-06..2025-12 (VES 25000 + EEAI 15000)
EXT_DOSE_2026 = 27500   # 2026-01..2026-10 (VES 22500 + EEAI 7500)


def regime_of(month: str):
    """Return (regime_label, dose) for a month string under the verified schedule."""
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

    # ---------------- rebate encodings (full grid, verified policy) ----------------
    enc = {}
    for mth in month_grid(WINDOW_START, WINDOW_END):
        label, dose = regime_of(mth)
        row = {"month": mth, "rebate_regime": label, "dose_nominal_sgd": dose}
        for eff, name in REAL_DUMMY_NAMES.items():
            row[name] = 1 if mth >= eff else 0
        for eff, name in ERA_DUMMY_NAMES.items():
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

    # interpretation-window flag (2022+ = EV era; also an estimation scope)
    enc_df["in_interpretation_window"] = (enc_df["month"] >= INTERP_START).astype(int)
    enc_df = enc_df.sort_values("month").reset_index(drop=True)

    assert len(enc_df) == 113, f"panel must be 113 months, got {len(enc_df)}"
    assert enc_df["month"].min() == WINDOW_START and enc_df["month"].max() == WINDOW_END

    # ---- DUAL-SCOPE DOSE ASSERTIONS (verified policy) ----
    full_doses = sorted(enc_df["dose_nominal_sgd"].unique().astype(int).tolist())
    assert full_doses == [20000, 25000, 40000, 45000], (
        f"HARD-FAIL: expected 4 distinct in-window doses "
        f"[20000, 25000, 40000, 45000], got {full_doses}")
    tail = enc_df[enc_df["month"] >= INTERP_START]["dose_nominal_sgd"]
    assert tail.nunique() == 2, (
        f"HARD-FAIL: expected 2 distinct doses in 2022-01..2025-05 "
        f"(40000, 45000), got {sorted(tail.unique())} — the 2022+ estimation "
        f"scope depends on this")
    # dose steps must occur exactly at the verified effective months
    step_months = enc_df.loc[enc_df["dose_nominal_sgd"].ne(
        enc_df["dose_nominal_sgd"].shift(1)) & (enc_df["month"] != WINDOW_START),
        "month"].tolist()
    assert step_months == ["2018-01", "2021-01", "2024-01"], (
        f"HARD-FAIL: dose step months {step_months} != expected "
        f"['2018-01','2021-01','2024-01']")
    print(f"[panel] dose verified-policy: {full_doses} (4 distinct; "
          f"2022+ window: {sorted(tail.unique().astype(int).tolist())})  [OK]")

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
    # annotate the verified-policy changes that live in the extension window
    ext["note"] = ""
    ext.loc[ext["month"] == "2026-01", "note"] = (
        "Jan 2026: real-policy EEAI ARF-rebate cap cut to $7,500 and VES A1 "
        "reduced to $22,500 take effect (combined dose 27500; COE-only "
        "extension; OUTSIDE the 2016-01..2025-05 joint window). EEAI ceases "
        "1 Jan 2027; zero-ARF-floor-for-EVs extended through 31 Dec 2027 "
        "(LTA circular VRL/16/2025).")
    # annotate the combined-dose level in force over the extension (annotated,
    # descriptive only — the extension carries no rebate dummies)
    ext["dose_nominal_sgd_annotated"] = ext["month"].map(
        lambda m: EXT_DOSE_2026 if m >= "2026-01" else EXT_DOSE_2025)
    ext.to_csv(PP / f"coe_extension_{EXT_START.replace('-', '_')}_{EXT_END.replace('-', '_')}.csv",
               index=False)
    print(f"[panel] coe_extension rows={len(ext)} ({EXT_START}..{EXT_END}, COE-only, descriptive; "
          f"dose annotated 2025={EXT_DOSE_2025}/2026={EXT_DOSE_2026})")

    # ---------------- rebate timeline (VERIFIED real Singapore policy) ----------------
    LTA_EM = "https://onemotoring.lta.gov.sg/content/onemotoring/home/buying/upfront-vehicle-costs/emissions-charges.html"
    MOTORIST = "https://www.motorist.sg/ask-motorists/591"
    NEA_VES = "https://www.nea.gov.sg/media/news/news/index/increased-rebates-for-cleaner-vehicles-under-enhanced-vehicular-emissions-scheme"
    LTA_EV = "https://www.lta.gov.sg/content/ltagov/en/industry_innovations/technologies/electric_vehicles/transitioning_to_evs.html"
    COEWATCH = "https://coewatch.sg/glossary/ev-early-adoption-incentive"
    NCCS = "https://www.nccs.gov.sg/media/new-carbon-emissions-based-vehicle-scheme-cevs-from-1-january-2013"
    ST_BUDGET = "https://www.straitstimes.com/singapore/budget-2021"
    LTA_CIRC = "LTA circular VRL/16/2025 (8 Sep 2025), as cited in coewatch.sg minimum-ARF column"
    timeline = [
        # ---- in-window verified-policy steps (these drive the dose) ----
        {"effective_month": "2018-01", "programme": "CEVS lapse; VES (Band A1 $25,000 off ARF) in force",
         "direction": "up", "size": "dose 20000 (CEVS est.) -> 25000 (VES A1, verified)",
         "in_joint_window": "Yes", "in_extension": "No",
         "source_url": LTA_EM + " | " + NEA_VES,
         "verification": "VERIFIED: revised CEVS in force 1 Jul 2015 .. 31 Dec 2017, so CEVS lapsed 1 Jan 2018; VES came into effect 1 Jan 2018 (NEA joint release 12 Nov 2020 confirms). $5,000 minimum-ARF floor in force for EVs until 31 Dec 2021."},
        {"effective_month": "2021-01", "programme": "Enhanced VES (A1 $25,000 maintained) + EEAI introduction (45% off ARF, capped $20,000)",
         "direction": "up", "size": "dose 25000 -> 45000 (verified stack; $5,000 ARF floor -> part of nominal cap unusable)",
         "in_joint_window": "Yes", "in_extension": "No",
         "source_url": NEA_VES + " | " + COEWATCH,
         "verification": "VERIFIED: NEA/LTA joint release 12 Nov 2020 ('increased rebates under enhanced VES') confirms 1 Jan 2021 levels incl. A1 $25,000 and VES in effect from 1 Jan 2018; EEAI rate set read from LTA circulars via coewatch.sg."},
        {"effective_month": "2022-01", "programme": "ARF floor lowered to $0 for electric cars (TAX PROVISION, not a rebate) + 97->110 kW Category A threshold change (confounder)",
         "direction": "n/a (no rebate step)", "size": "dose stays 45000 (caps unchanged); full caps now usable; confounder marker kept",
         "in_joint_window": "Yes", "in_extension": "No",
         "source_url": ST_BUDGET + " | " + LTA_EV,
         "verification": "VERIFIED: Straits Times Budget 2021 + coewatch minimum-ARF column: $0 ARF floor for EVs from 1 Jan 2022 (extended through 31 Dec 2027, LTA circular VRL/16/2025 of 8 Sep 2025). The 97->110 kW Cat A threshold change is an existing confounder, controlled by the threshold dummy in the price/bidding exhibits."},
        {"effective_month": "2024-01", "programme": "EEAI cap cut $20,000 -> $15,000 (VES A1 $25,000 maintained per IEA statement)",
         "direction": "down", "size": "dose 45000 -> 40000 (verified stack)",
         "in_joint_window": "Yes", "in_extension": "No",
         "source_url": COEWATCH + " | " + NEA_VES,
         "verification": "VERIFIED: EEAI cap $15,000 for 2024-01-01..2025-12-31 (coewatch.sg rate sets read from LTA circulars); VES rebates 'shall remain at S$25,000 for Band A1 cars' (IEA). This step is what makes the 2022+ window estimable (2 distinct doses inside it)."},
        # ---- out-of-window notes (required by the plan) ----
        {"effective_month": "2026-01", "programme": "EEAI cap cut to $7,500 + VES A1 cut to $22,500 (real policy)",
         "direction": "down", "size": "dose 40000 -> 27500 (verified)",
         "in_joint_window": "No", "in_extension": "Yes (2025-06..2026-10, COE-only)",
         "source_url": LTA_EV,
         "verification": "CORROBORATED: 'From 1 Jan 2026 to 31 Dec 2026, the rebate will be capped at $7,500' (LTA); VES 2026 A1 $22,500 (LTA); 2027: $20,000 (LTA, extension window only). Outside the joint window; lives in the COE-only extension."},
        {"effective_month": "2027-01", "programme": "EEAI cessation (real policy)",
         "direction": "down", "size": "EEAI rebate ceases; dose reverts to VES A1 $20,000 (2027, extension window)",
         "in_joint_window": "No", "in_extension": "No (beyond extension end 2026-10)",
         "source_url": COEWATCH + " | " + LTA_EV,
         "verification": "CORROBORATED: EEAI ceases 1 Jan 2027 (coewatch.sg glossary; LTA transitioning-to-EVs page). Documented for completeness; no data beyond 2026-10 in this pipeline."},
        {"effective_month": "2013-01", "programme": "CEVS introduction (original scheme; revised CEVS from 1 Jul 2015)",
         "direction": "baseline", "size": "original CEVS 2013-2015 Band A ~$20,000; revised CEVS 2015-2017 Band A1 (0-95 g/km, incl. electric) ~$30,000",
         "in_joint_window": "No (before 2016-01)", "in_extension": "No",
         "source_url": NCCS + " | " + LTA_EM + " | " + MOTORIST,
         "verification": "CORROBORATED: CEVS in force from 1 Jan 2013 (NCCS); revised CEVS 1 Jul 2015 .. 31 Dec 2017 (LTA emissions-charges page; motorist.sg ask-motorists/591). OUTSIDE the 2016-01 window -> contributes nothing to identification; the in-window CEVS dose (20000) is a CONSERVATIVE ESTIMATE."},
    ]
    pd.DataFrame(timeline).to_csv(TT / "rebate_timeline.csv", index=False)
    n_inwin = sum(1 for r in timeline if r["in_joint_window"].startswith("Yes"))
    n_oow = sum(1 for r in timeline if r["in_joint_window"] == "No")
    print(f"[panel] rebate_timeline rows={len(timeline)} "
          f"({n_inwin} in-window verified steps + {n_oow} out-of-window notes)")

    # ---------------- dose summary ----------------
    in_win = enc_df
    distinct_doses = sorted(in_win["dose_nominal_sgd"].unique().astype(int).tolist())
    tail_doses = sorted(in_win[in_win["month"] >= INTERP_START]["dose_nominal_sgd"]
                        .unique().astype(int).tolist())
    dose_rows = [
        {"item": "effective_in_window_changes", "value": 3,
         "note": "3 verified-policy dose steps (2018-01, 2021-01, 2024-01); "
                 "plus the 2022-01 ARF-floor-zero tax provision (no dose step) "
                 "and the 2022-01 97->110kW threshold confounder"},
        {"item": "distinct_dose_values",
         "value": "; ".join(str(d) for d in distinct_doses),
         "note": "nominal S$ combined max EV rebate; 2016-01..2017-12 = 20000 is a "
                 "CEVS ESTIMATE (direction certain, magnitude approximate); "
                 "2018-01 onward all verified"},
        {"item": "n_distinct_dose_values", "value": len(distinct_doses), "note": ""},
        {"item": "n_distinct_dose_values_2022plus",
         "value": len(tail_doses),
         "note": "ASSERTED: 2022-01..2025-05 has 2 distinct doses (45000, 40000) "
                 "-> the 2022+ window is a VALID ESTIMATION scope (41 obs). "
                 "Estimable because the dose varies within the window (2024-01 "
                 "cap cut)."},
        {"item": "estimation_windows",
         "value": f"FULL {WINDOW_START}..{WINDOW_END} (primary); "
                  f"2022+ {INTERP_START}..{WINDOW_END} (also valid for headline "
                  f"exhibits)",
         "note": "full window = CEVS->VES transition + overall level effects; "
                 "2022+ = EV era (45000 -> 40000 step at 2024-01). Both scopes "
                 "reported for the rebate->price and rebate->demand exhibits."},
        {"item": "dose_2022plus_values",
         "value": "; ".join(str(d) for d in tail_doses),
         "note": "45000 (2022-01..2023-12) -> 40000 (2024-01..2025-05)"},
    ]
    pd.DataFrame(dose_rows).to_csv(TT / "dose_summary.csv", index=False)
    print(f"[panel] dose_summary: {len(distinct_doses)} distinct doses {distinct_doses}; "
          f"2022+ window: {tail_doses} (ESTIMABLE)")

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
                  "note": "nominal S$ combined max EV rebate (verified policy; "
                          "2016-01..2017-12 CEVS dose is an estimate)"})
    audit.append({"metric": "adaptation", "value": "coverage_rate defined as rows_nonnull/rows_total",
                  "note": "fraction of raw rows with an observed (non-null) count; decays 1.0->0.23 over the window. A literal nonnull_total/(total rows) mixes count-sum/row-count and is not a rate; ev_reg remains a lower bound under either definition."})
    audit.append({"metric": "adaptation", "value": "category parse: last token of vehicle_class",
                  "note": "'Category A' must be parsed by its trailing letter; a substring match on 'A' would mis-assign every row to Category A (caught by reconciliation)."})
    audit.append({"metric": "adaptation", "value": "rebate dose encoded from verified real Singapore policy",
                  "note": "The dose is encoded from the VERIFIED policy timeline: CEVS revised in force 2015-07..2017-12 (dose 20000 = ESTIMATE); CEVS lapse + VES A1 $25,000 from 2018-01; enhanced VES + EEAI (45% ARF, cap $20,000) from 2021-01 (dose 45000); $0 ARF floor for EVs from 2022-01 (TAX provision, not a rebate — full caps usable); EEAI cap $15,000 from 2024-01 (dose 40000); EEAI cap $7,500 + VES A1 $22,500 from 2026-01; EEAI ceases 2027-01. See tables/rebate_timeline.csv (source_url + verification per row)."})
    audit.append({"metric": "adaptation", "value": "CEVS dose 2016-01..2017-12 is an ESTIMATE",
                  "note": "Conservative dose of 20000 for the pre-VES window: direction certain (CEVS in force, rebate for the cleanest band), magnitude approximate (revised CEVS Band A1 ~$30,000 vs original ~$20,000; 20000 chosen as the conservative baseline). Flagged as an estimate in every deliverable; all 2018+ dose levels are verified."})
    audit.append({"metric": "adaptation", "value": "combined-dose stacking assumption",
                  "note": "dose = VES A1 rebate + EEAI cap where both are in force (max available, not expected realized rebate). 2021: part of the EEAI cap was unusable under the $5,000 minimum-ARF floor (until 2021-12); from 2022-01 the zero floor makes the full cap usable. Dose is a CAP, not a realized average."})
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
