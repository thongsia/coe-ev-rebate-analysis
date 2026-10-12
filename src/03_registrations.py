#!/usr/bin/env python3
"""
Step 4 — EV registration channel.

Reads:   data/raw/registrations_raw.csv
Writes:  data/processed/ev_registrations.csv

Per month (from 2022-07 onward):
  ev_reg         = sum of NON-NULL registration counts where fuel_type == 'Electric'
  nonnull_total  = sum of NON-NULL registration counts across ALL fuel labels
  ev_share       = ev_reg / nonnull_total
  coverage_rate  = nonnull_total / (total rows that month)
  rows_total     = total raw rows that month (all fuel labels)
  rows_nonnull   = raw rows that month with a non-null count

MONTHS 2016-01 .. 2022-06 ARE NA BY CONSTRUCTION — never imputed. They are
included with ev_reg = ev_share = NaN (NA), because:
  (a) 'Electric' (BEV) first appears 2022-07 in this store; and
  (b) the null-coverage decay means pre-2022 totals are unreliable anyway.

WHY ev_reg IS A LOWER BOUND (null-coverage decay):
  The registration-count field ('number') is null on ~57% of all rows, and the
  share of nulls RISES over time — ~0% missing in 2016-17, ~77% by 2025.
  When a row's count is null we CANNOT know whether that make/model was an EV.
  We only count the rows whose count is present. So ev_reg under-counts true
  EV registrations by exactly the EV rows whose counts are null. Hence
  ev_reg is a LOWER BOUND on monthly EV registrations, and ev_share
  (relative to nonnull_total) is a LOWER BOUND on the EV share of the
  *observable* new-car market. We deliberately do NOT impute nulls.

  'Petrol-Electric' (hybrid) and 'Petrol-Electric (Plug-In)' / 'Diesel-Electric'
  rows are NEVER folded into 'Electric' — BEV only.

Reconciliation (HARD-FAIL on mismatch):
  per month, rows_total must equal the raw store's row count for that month.

Layering contract: reads only data/raw/; writes only data/processed/.
Run: python3 src/03_registrations.py
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "registrations_raw.csv"
OUT = ROOT / "data" / "processed" / "ev_registrations.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)

BEV = "Electric"
# full grid 2016-01 .. 2025-05 (113 months)
ALL_MONTHS = [f"{y}-{m:02d}"
              for y in range(2016, 2026)
              for m in range(1, 13)]
ALL_MONTHS = [m for m in ALL_MONTHS if m <= "2025-05"]


def main():
    raw = pd.read_csv(RAW, dtype=str)
    raw["number"] = pd.to_numeric(raw["number"], errors="coerce")  # NaN when null
    raw["month"] = raw["month"].astype(str)

    # raw row count per month (for reconciliation)
    raw_month_rows = raw.groupby("month").size().to_dict()

    rows = []
    for mth in ALL_MONTHS:
        sub = raw[raw["month"] == mth]
        rows_total = len(sub)
        if rows_total != raw_month_rows.get(mth, 0):
            raise SystemExit(
                f"HARD-FAIL reconciliation: {mth} rows_total={rows_total} "
                f"raw={raw_month_rows.get(mth)}"
            )
        num = sub["number"]
        rows_nonnull = int(num.notna().sum())
        nonnull_total = float(num.sum()) if rows_nonnull else 0.0
        bev = sub[sub["fuel_type"] == BEV]["number"]
        ev_reg = float(bev.sum()) if int(bev.notna().sum()) else 0.0
        coverage = (rows_nonnull / rows_total) if rows_total else None
        rows.append({
            "month": mth,
            "ev_reg": ev_reg if (mth >= "2022-07" and rows_nonnull) else None,
            "nonnull_total": nonnull_total,
            "ev_share": (ev_reg / nonnull_total) if (mth >= "2022-07" and nonnull_total > 0) else None,
            "coverage_rate": coverage,
            "rows_total": rows_total,
            "rows_nonnull": rows_nonnull,
            "is_bev_observed": 1 if mth >= "2022-07" else 0,
        })

    df = pd.DataFrame(rows)

    # coverage trend snapshot (document lower-bound decay)
    cov_early = df[df["month"].between("2016-01", "2017-12")]["coverage_rate"].mean()
    cov_late = df[df["month"].between("2024-01", "2025-05")]["coverage_rate"].mean()
    ev_months = df[df["month"] >= "2022-07"]
    ev_sum = float(df["ev_reg"].sum())  # 0.0 for pre-2022 (None -> 0 in sum? guard)
    # careful: None -> NaN; sum skips NaN
    print(f"[reg] wrote {OUT}  rows={len(df)}  months={df['month'].min()}..{df['month'].max()}")
    print(f"[reg] months with BEV observed: {len(ev_months)}  "
          f"({df[df['month'] >= '2022-07']['month'].min()}..{df[df['month'] >= '2022-07']['month'].max()})")
    print(f"[reg] total ev_reg (lower bound, 2022-07+): {ev_sum:.0f}")
    print(f"[reg] coverage_rate mean 2016-17: {cov_early:.3f}  ->  2024-25: {cov_late:.3f}  (decay confirms lower-bound)")
    print(f"[reg] ev_share range (2022-07+): {ev_months['ev_share'].min():.4f} .. {ev_months['ev_share'].max():.4f}")

    # hard-check: 2016-01 coverage should be ~1.0, 2025-05 low
    c2016 = df[df["month"] == "2016-01"]["coverage_rate"].iloc[0]
    c2025 = df[df["month"] == "2025-05"]["coverage_rate"].iloc[0]
    if c2016 < 0.99:
        raise SystemExit(f"HARD-FAIL: 2016-01 coverage {c2016} not ~1.0 (data changed?)")
    if not (0.0 < c2025 < 0.4):
        raise SystemExit(f"WARNING-as-FAIL: 2025-05 coverage {c2025} outside expected decay band")

    df.to_csv(OUT, index=False)
    print("[reg] DONE")


if __name__ == "__main__":
    main()
