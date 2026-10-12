#!/usr/bin/env python3
"""
Step 9 — EV registration channel (DESCRIPTIVE only).

From data/processed/ev_registrations.csv (a Batch A artifact; read-only), report
the monthly EV registrations + EV share + coverage rate (lower bound) for the
observed window 2022-07..2025-05 (BEV registrations first appear 2022-07; before
that ev_reg / ev_share are NA by construction).

CHANNEL STATUS (stated explicitly):
  * There is NO within-window rebate variation in the OBSERVED window
    2022-07..2025-05 that this short series can use — the verified combined
    dose is flat at 45000 from 2022-01..2023-12 and 40000 from 2024-01
    (the 2024-01 step arrives 8 months after the series starts and the
    series is right-truncated at 2025-05), and the EV registration series
    only begins 2022-07. A rebate-coefficient cannot be identified from
    this channel alone (short, right-truncated series; the dose step is
    too close to the window end).
  * It is therefore DESCRIPTIVE / CORRELATIONAL ONLY and FEEDS NO coefficient
    exhibit (it is excluded from the price equation, bidding channel, and
    mediation by the scope rule -- see 05_scope_guard assertion (d)).
  * ev_reg is a LOWER BOUND: the registrations store leaves the count null on
    a large and rising fraction of rows, so `coverage_rate` decays from ~0.33
    to ~0.20 over the window.

Output: tables/ev_registrations_descriptive.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bootstrap as B  # noqa: E402

D = B.D
OUT_DIR = D.ROOT / "tables"
OUT = OUT_DIR / "ev_registrations_descriptive.csv"

NOTE = (
    "DESCRIPTIVE / correlational only. NO within-window rebate variation in "
    "the OBSERVED window 2022-07..2025-05 (combined dose is flat 45000 until "
    "2024-01, then 40000; the EV series begins 2022-07, right-truncated, "
    "right-censored). ev_reg is a LOWER BOUND (count null on a rising "
    "fraction of rows; coverage_rate decays ~0.33 -> ~0.20). FEEDS NO "
    "coefficient exhibit (excluded from price/bidding/mediation models)."
)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ev = pd.read_csv(D.EVREG)
    obs = ev[ev["ev_reg"].notna()].copy().reset_index(drop=True)
    obs["month"] = obs["month"]
    # monthly descriptive stats
    rows = obs[["month", "ev_reg", "ev_share", "coverage_rate",
                "nonnull_total", "rows_total", "rows_nonnull",
                "is_bev_observed"]].copy()
    rows["interpretation_scope"] = "2022-07..2025-05 (observed BEV window)"

    # summary block (appended as extra metric rows)
    summary = pd.DataFrame({
        "month": ["SUMMARY_observed_months",
                  "SUMMARY_min_ev_reg",
                  "SUMMARY_mean_ev_reg",
                  "SUMMARY_median_ev_reg",
                  "SUMMARY_max_ev_reg",
                  "SUMMARY_min_ev_share",
                  "SUMMARY_mean_ev_share",
                  "SUMMARY_max_ev_share",
                  "SUMMARY_min_coverage",
                  "SUMMARY_mean_coverage",
                  "SUMMARY_max_coverage",
                  "SUMMARY_cumulative_ev_reg"],
        "ev_reg": [
            len(obs),
            obs["ev_reg"].min(), obs["ev_reg"].mean(), obs["ev_reg"].median(),
            obs["ev_reg"].max(),
            obs["ev_share"].min(), obs["ev_share"].mean(), obs["ev_share"].max(),
            obs["coverage_rate"].min(), obs["coverage_rate"].mean(),
            obs["coverage_rate"].max(),
            obs["ev_reg"].sum(),
        ],
        "interpretation_scope": "2022-07..2025-05",
        "note": [NOTE] * 12,
    })
    out = pd.concat([rows, summary[rows.columns.intersection(summary.columns).tolist()
                                   + [c for c in summary.columns
                                      if c not in rows.columns]]],
                    ignore_index=True)
    # tidy column order
    cols = ["month", "ev_reg", "ev_share", "coverage_rate",
            "nonnull_total", "rows_total", "rows_nonnull", "is_bev_observed",
            "interpretation_scope", "note"]
    out = out[[c for c in cols if c in out.columns]]
    out.to_csv(OUT, index=False)

    B.register_exhibit(
        name="ev_registration_channel", kind="registration_descriptive",
        est_scope="2022-07..2025-05",
        key_regressor="ev_reg (descriptive only, NOT a rebate-coefficient "
                      "regressor)",
        interpretation_scope="2022-07..2025-05",
        n_obs=len(obs),
        notes="descriptive/correlational only; no within-window rebate "
              "variation; lower-bound EV registrations; feeds no coefficient "
              "exhibit.",
    )

    print(f"[ev_registration] wrote {OUT}  rows={len(out)} "
          f"(observed months={len(obs)}, cumulative EV regs={int(obs['ev_reg'].sum())})")
    print(f"  ev_share mean={obs['ev_share'].mean():.3f} "
          f"coverage mean={obs['coverage_rate'].mean():.3f}")


if __name__ == "__main__":
    main()
