#!/usr/bin/env python3
"""
Step 3 — COE monthly collapsing.

Reads:   data/raw/coe_results_raw.csv
Writes:  data/processed/coe_monthly.csv   (2010-01 .. 2026-10, one row per category per month)

Collapsing rule (documented):
  For each (month, category):
    clearing_price          = MEAN of premium across that month's 1-2 exercises
    quota_total             = SUM of quota
    bids_received_total     = SUM of bids_received
    bids_successful_total   = SUM of bids_success
    exercise_count          = number of raw exercise rows that month-category (audit)
    bidding_nos             = comma-joined bidding_no of the exercises (audit)

The raw `month` field is already 'YYYY-MM' (e.g. '2010-01'); `vehicle_class`
is of the form 'Category A' .. 'Category E'. We parse the category letter.

Reconciliation (HARD-FAIL on mismatch):
  per category, sum(exercise_count) over the monthly table must equal the raw
  row count for that category. (Equivalent to: every raw row is assigned to
  exactly one monthly row.)

Layering contract: reads only data/raw/; writes only data/processed/.
Run: python3 src/02_coe_panel.py
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "coe_results_raw.csv"
OUT = ROOT / "data" / "processed" / "coe_monthly.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)


def cat_letter(vehicle_class: str) -> str:
    # 'Category A' -> 'A'  (take the LAST char; substring search would match the
    # 'A' inside 'Category' and mis-assign every row to category A.)
    s = str(vehicle_class).strip().split()[-1].upper()
    if s not in ("A", "B", "C", "D", "E"):
        raise SystemExit(f"HARD-FAIL: unrecognised vehicle_class: {vehicle_class!r}")
    return s


def main():
    raw = pd.read_csv(RAW, dtype=str)
    # coerce numerics (premium / quota / bids may be strings)
    for c in ("premium", "quota", "bids_success", "bids_received"):
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    raw["category"] = raw["vehicle_class"].map(cat_letter)

    # sanity: month format
    bad = raw[~raw["month"].str.match(r"^\d{4}-\d{2}$", na=False)]
    if len(bad):
        raise SystemExit(f"HARD-FAIL: {len(bad)} rows with non-YYYY-MM month")

    # raw row count per category (for reconciliation)
    raw_counts = raw.groupby("category").size().to_dict()

    g = (
        raw.groupby(["month", "category"])
        .agg(
            clearing_price=("premium", "mean"),
            quota_total=("quota", "sum"),
            bids_received_total=("bids_received", "sum"),
            bids_successful_total=("bids_success", "sum"),
            exercise_count=("bidding_no", "count"),
            bidding_nos=("bidding_no", lambda s: ",".join(sorted(map(str, s)))),
        )
        .reset_index()
    )
    g = g.sort_values(["month", "category"]).reset_index(drop=True)

    # ---- reconciliation: per-category sum(exercise_count) == raw row count ----
    collapsed_counts = g.groupby("category")["exercise_count"].sum().to_dict()
    cats = set(raw_counts) | set(collapsed_counts)
    if cats != {"A", "B", "C", "D", "E"}:
        raise SystemExit(
            f"HARD-FAIL: expected categories A-E, got {sorted(cats)} "
            f"(category parse bug?)"
        )
    for cat in sorted(cats):
        a, b = raw_counts.get(cat, 0), collapsed_counts.get(cat, 0)
        if a != b:
            raise SystemExit(
                f"HARD-FAIL reconciliation: category {cat} raw={a} collapsed={b}"
            )

    # keep a tidy column order
    cols = ["month", "category", "clearing_price", "quota_total",
            "bids_received_total", "bids_successful_total",
            "exercise_count", "bidding_nos"]
    g = g[cols]

    # rounding: clearing price to 2 dp (mean of 1-2 ints), totals are ints
    g["clearing_price"] = g["clearing_price"].round(2)
    for c in ("quota_total", "bids_received_total", "bids_successful_total"):
        g[c] = g[c].astype("int64")

    n_months = g["month"].nunique()
    lo, hi = g["month"].min(), g["month"].max()
    g.to_csv(OUT, index=False)
    print(f"[coe] wrote {OUT}  rows={len(g)}  months={n_months} ({lo}..{hi})")
    print(f"[coe] per-category raw==collapsed: "
          + ", ".join(f"{c}:{collapsed_counts[c]}" for c in "ABCDE")
          + "  [reconciliation OK, all 5 categories present]")


if __name__ == "__main__":
    main()
