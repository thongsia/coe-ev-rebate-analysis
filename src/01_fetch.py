#!/usr/bin/env python3
"""
Step 2 — Data acquisition (data.gov.sg datastore).

Downloads three resources IN FULL:
  1. COE results       d_69b3380ad7e51aff3a7dcc84eba52b8a  (stated total 1985)
  2. Registrations     d_d3f4d708e1d0a37b4365414e2fad3a07  (stated total 51669)
  3. CPI All Items     d_bdaff844e3ef89d39fceb962ff8f0791  (stated total reported by API)

Writes:
  data/raw/coe_results_raw.csv      (verbatim records)
  data/raw/registrations_raw.csv    (verbatim records)
  data/raw/cpi_raw.csv             (verbatim records)
  data/raw/provenance.csv          (one pinned record per resource)

Hard-fails (raises) if fetched count != stated total for ANY resource.
Pagination: datastore caps a single call (limit=100000 returns HTTP 413);
we page at limit=20000 which is safe for all three stores.

Layering contract: this module reads NOTHING local (source = live API) and
writes ONLY to data/raw/. It is the root of the pipeline.

Run from the workspace root:  python3 src/01_fetch.py
"""

import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://data.gov.sg/api/action/datastore_search"
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

PAGE = 20000  # safe page size (limit=100000 -> HTTP 413 on the big store)

# (key, resource_id, expected_stated_total_or_None, raw_csv)
RESOURCES = [
    ("coe",           "d_69b3380ad7e51aff3a7dcc84eba52b8a", 1985,  "coe_results_raw.csv"),
    ("registrations", "d_d3f4d708e1d0a37b4365414e2fad3a07", 51669, "registrations_raw.csv"),
    ("cpi",           "d_bdaff844e3ef89d39fceb962ff8f0791", None,  "cpi_raw.csv"),
]


def fetch_page(resource_id: str, limit: int, offset: int) -> dict:
    url = f"{BASE}?resource_id={resource_id}&limit={limit}&offset={offset}"
    with urllib.request.urlopen(url, timeout=300) as r:
        raw = r.read().decode("utf-8")
    # data.gov.sg embeds control chars in some fields -> strict=False
    return json.loads(raw, strict=False)["result"]


def fetch_full(resource_id: str):
    """Page through the whole store. Returns (stated_total, records, field_order)."""
    records = []
    total = None
    fields = None
    offset = 0
    while True:
        res = fetch_page(resource_id, PAGE, offset)
        if total is None:
            total = res.get("total")
        if fields is None:
            fields = [f["id"] for f in res.get("fields", [])]
        page = res.get("records", [])
        if not page:
            break
        records.extend(page)
        offset += PAGE
        if offset >= total:
            break
    return total, records, fields


def write_csv(path: Path, records, field_order):
    import csv
    cols = field_order
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for rec in records:
            w.writerow([rec.get(c, "") if rec.get(c) is not None else "" for c in cols])


def main():
    prov_rows = []
    for key, rid, expected, fname in RESOURCES:
        print(f"[fetch] {key}: resource_id={rid} ...", flush=True)
        stated_total, records, fields = fetch_full(rid)
        n = len(records)
        # uniqueness check (datastore _id should be unique per row)
        ids = [r.get("_id") for r in records]
        n_unique = len(set(ids))
        if n != stated_total:
            raise SystemExit(
                f"HARD-FAIL [{key}]: fetched {n} != stated total {stated_total}"
            )
        if n_unique != n:
            raise SystemExit(f"HARD-FAIL [{key}]: duplicate _id rows ({n_unique} unique of {n})")
        out = RAW / fname
        write_csv(out, records, fields)
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        prov_rows.append({
            "key": key,
            "resource_id": rid,
            "retrieval_timestamp_utc": ts,
            "stated_source_total": stated_total,
            "fetched_count": n,
            "unique_id_count": n_unique,
            "match": "OK" if n == stated_total else "MISMATCH",
            "raw_file": f"data/raw/{fname}",
            "n_fields": len(fields),
        })
        print(f"[fetch] {key}: total={stated_total} fetched={n} unique={n_unique} -> {out.name}",
              flush=True)

    # pinned provenance record
    import csv
    prov = RAW / "provenance.csv"
    cols = ["key", "resource_id", "retrieval_timestamp_utc", "stated_source_total",
            "fetched_count", "unique_id_count", "match", "raw_file", "n_fields"]
    with open(prov, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(prov_rows)
    print(f"[fetch] provenance -> {prov}")
    print("[fetch] DONE")


if __name__ == "__main__":
    main()
