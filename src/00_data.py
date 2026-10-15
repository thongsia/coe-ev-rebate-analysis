#!/usr/bin/env python3
"""
Step 0 (shared data layer, Batch B) — clean estimation frame.

WHY THIS MODULE EXISTS (documented data-integrity fix)
------------------------------------------------------
Batch A's ``data/processed/panel_joint.csv`` (and ``coe_monthly.csv`` /
``coe_extension_*.csv``) contain a SILENT CORRUPTION in the bid-count columns:

  * The raw datastore (``data/raw/coe_results_raw.csv``) stores the
    ``bids_received`` and ``bids_success`` fields as STRINGS. From
    2023-05/2024-08 onward the source uses THOUSANDS SEPARATORS, e.g.
    ``'1,039'``, ``'2,240'`` (109 raw rows carry a comma in bids_received,
    41 in bids_success).
  * Batch A's ``src/02_coe_panel.py`` coerces with
    ``pd.to_numeric(col, errors="coerce")``. A string like ``'1,039'`` does
    not parse -> NaN.
  * The monthly collapse then uses ``groupby(...).sum()``. A month-category
    where BOTH exercises' values are NaN sums to 0 (pandas ``sum`` skips
    NaN; an all-NaN group returns 0).
  * Result: in ``panel_joint.csv`` ``catA_bids_received`` is literally ``0``
    for 19 months (2023-10 .. 2025-05), ``catA_bids_success`` is ``0`` for
    9 months, ``catB_bids_received`` is ``0`` for 14 months, and
    ``catD_bids_received`` for 1 month -- all INSIDE the 2022+ EV
    interpretation window, where quota and clearing_price are fully
    populated (you cannot have 0 bids received with 1,570 bids succeeding).

This is a hidden gap masquerading as a zero. Any model that uses the panel's
``catA_bids_received`` as the "demand" regressor would silently treat the
entire EV-rebate era as having zero Cat A demand -- a spurious, non-physical
drop that is exactly the window the analysis cares about.

FIX (within the layering contract): read the Batch A raw artifact
``data/raw/coe_results_raw.csv`` (allowed: the contract says read from
``data/raw`` and ``data/processed``), strip the thousands separators, and
recompute the monthly sums. The corrected bid counts are NON-ZERO for all 110
COE months in 2016-01..2025-05. This module exposes the corrected
``*_bids_received_clean`` / ``*_bids_success_clean`` columns. Every downstream
module (05-12) uses these; none uses the corrupted panel columns.

Everything else in the panel (clearing_price, quota, the rebate dummies, dose,
EV columns, in_interpretation_window) is CLEAN -- ``premium`` and ``quota``
carry no comma-formatted rows -- so those are taken verbatim from the panel.

Layering contract: reads data/raw/coe_results_raw.csv and
data/processed/{panel_joint,cpi_deflated,ev_registrations}.csv. Writes NOTHING
to disk (pure in-memory frame provider + file-dependency registry for the
scope guard's forward-read check).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_COE = ROOT / "data" / "raw" / "coe_results_raw.csv"
PANEL = ROOT / "data" / "processed" / "panel_joint.csv"
CPI = ROOT / "data" / "processed" / "cpi_deflated.csv"
EVREG = ROOT / "data" / "processed" / "ev_registrations.csv"

WINDOW_LO = "2016-01"
WINDOW_HI = "2025-05"
NATURAL_MONTHS = 113  # 2016-01 .. 2025-05 inclusive
CATS = ["A", "B", "C", "D", "E"]

# Files this module READS (used by the scope guard to verify the layering
# contract has no forward reads). Values are relative to ROOT.
FILE_DEPENDENCIES: dict[str, list[str]] = {
    # shared data layer
    "00_data.py": [
        "data/raw/coe_results_raw.csv",
        "data/processed/panel_joint.csv",
        "data/processed/cpi_deflated.csv",
        "data/processed/ev_registrations.csv",
    ],
}

# Files written by each module (for the forward-read / layering audit).
FILES_WRITTEN: dict[str, list[str]] = {
    "05_scope_guard.py": ["tables/scope_audit.csv"],
    "06_price_equation.py": [
        "tables/price_equation.csv",
        "tables/price_equation_2022plus_robustness.csv",
    ],
    "07_demand_bidding.py": [
        "tables/demand_bidding_channel.csv",
        "tables/demand_2022plus_interpretation.csv",
        "tables/crosslag_check.csv",
    ],
    "08_demand_registration.py": ["tables/ev_registrations_descriptive.csv"],
    "09_mediation.py": ["tables/mediation_effects.csv"],
    "10_event_study.py": [
        "tables/event_study_coefficients.csv",
        "tables/event_study_prechecks.csv",
    ],
    "11_diagnostics.py": [
        "tables/negative_controls.csv",
        "tables/diagnostics_stationarity_autocorr.csv",
        "tables/sensitivity_analysis.csv",
    ],
    "12_grading.py": ["tables/evidence_grading.csv"],
}


def _to_num_strip(s: pd.Series) -> pd.Series:
    """Numeric parse that tolerates thousands separators and blank strings.

    This is the correction for the Batch A comma bug: ``'1,039'`` -> 1039.
    Empty/missing -> NaN (never silently 0).
    """
    s = s.astype(str).str.strip()
    s = s.replace({"": None, "nan": None, "None": None})
    return pd.to_numeric(s.str.replace(",", "", regex=False), errors="coerce")


def _cat_letter(vehicle_class: str) -> str:
    s = str(vehicle_class).strip().split()[-1].upper()
    if s not in CATS:
        raise SystemExit(f"HARD-FAIL: unrecognised vehicle_class {vehicle_class!r}")
    return s


def build_corrected_bid_counts() -> pd.DataFrame:
    """Monthly SUM of bids_received / bids_success per category, corrected for
    the Batch A comma bug. Long format: month, cat, br, bs."""
    raw = pd.read_csv(RAW_COE, dtype=str)
    raw["cat"] = raw["vehicle_class"].map(_cat_letter)
    raw["br"] = _to_num_strip(raw["bids_received"])
    raw["bs"] = _to_num_strip(raw["bids_success"])
    g = (
        raw.groupby(["month", "cat"])
        .agg(br=("br", "sum"), bs=("bs", "sum"))
        .reset_index()
    )
    return g


def load_estimation_frame() -> pd.DataFrame:
    """Assemble the clean monthly estimation frame (2016-01..2025-05).

    Columns (all per-category *_clearing_price / *_quota taken from the panel
    -- clean; *_bids_received_clean / *_bids_success_clean reconstructed from
    raw -- corrected):
      month, <rebate dummies: 4 real-policy dummies
      (reg_real_ves_201801, reg_real_evstack_202101, reg_arffloor_zero_202201,
      reg_eeai_cap15k_202401) + era dummies (ves_program, eeai_active)>,
      dose_nominal_sgd, in_interpretation_window,
      cpi_all_items, catA_clearing_price, catA_clearing_price_real,
      catA_quota, catA_bids_received_clean, catA_bids_success_clean,
      cat{B,C,D,E}_{clearing_price,quota,bids_received_clean,bids_success_clean},
      ev_reg, ev_share, coverage_rate,
      n_obs (1 if month has COE data else 0),
      panel_bids_received_bad (1 if panel's raw value is the corrupted 0)
    """
    panel = pd.read_csv(PANEL)
    panel = panel[
        (panel["month"] >= WINDOW_LO) & (panel["month"] <= WINDOW_HI)
    ].copy().reset_index(drop=True)
    assert len(panel) == NATURAL_MONTHS, (
        f"panel must have {NATURAL_MONTHS} rows in window, got {len(panel)}"
    )

    cpi = pd.read_csv(CPI)
    ev = pd.read_csv(EVREG)
    corr = build_corrected_bid_counts()

    frame = panel[["month"]].copy()

    # --- rebate encoding (verbatim from panel; clean) ---
    frame["dose_nominal_sgd"] = panel["dose_nominal_sgd"].to_numpy()
    # --- verified-policy dummies (the key regime columns) ---
    frame["reg_real_ves_201801"] = panel["reg_real_ves_201801"].to_numpy()
    frame["reg_real_evstack_202101"] = panel["reg_real_evstack_202101"].to_numpy()
    frame["reg_arffloor_zero_202201"] = panel["reg_arffloor_zero_202201"].to_numpy()
    frame["reg_eeai_cap15k_202401"] = panel["reg_eeai_cap15k_202401"].to_numpy()
    frame["ves_program"] = panel["ves_program"].to_numpy()
    frame["eeai_active"] = panel["eeai_active"].to_numpy()
    frame["rebate_regime"] = panel["rebate_regime"].to_numpy()
    frame["in_interpretation_window"] = panel["in_interpretation_window"].to_numpy()

    # --- EV / coverage (verbatim from ev_registrations; clean) ---
    for c in ("ev_reg", "ev_share", "coverage_rate"):
        frame[c] = ev.set_index("month").reindex(frame["month"])[c].to_numpy()

    # --- CPI deflator (clean) ---
    cpi_idx = cpi.set_index("month")
    frame["cpi_all_items"] = cpi_idx.reindex(frame["month"])["cpi_all_items"].to_numpy()
    frame["catA_clearing_price_real"] = cpi_idx.reindex(frame["month"])[
        "catA_clearing_price_real"
    ].to_numpy()

    # --- per-category COE: clearing_price + quota from PANEL (clean) ---
    for K in CATS:
        frame[f"cat{K}_clearing_price"] = panel[f"cat{K}_clearing_price"].to_numpy()
        frame[f"cat{K}_quota"] = panel[f"cat{K}_quota"].to_numpy()

    # --- per-category bid counts: CORRECTED from raw (the fix) ---
    for K in CATS:
        sub = corr[corr["cat"] == K].set_index("month")
        frame[f"cat{K}_bids_received_clean"] = sub.reindex(frame["month"])["br"].to_numpy()
        frame[f"cat{K}_bids_success_clean"] = sub.reindex(frame["month"])["bs"].to_numpy()
        # audit flag: is the PANEL's original bid-count a corrupted 0?
        panel_br = pd.to_numeric(panel[f"cat{K}_bids_received"], errors="coerce")
        corr_br = frame[f"cat{K}_bids_received_clean"]
        frame[f"panel_cat{K}_br_corrupted"] = (
            (panel_br == 0) & (corr_br > 0)
        ).astype(int).to_numpy()

    # COE-availability flag (1 if clearing_price present)
    frame["n_obs"] = (~panel["catA_clearing_price"].isna()).astype(int).to_numpy()

    return frame


def listwise_sample(frame: pd.DataFrame) -> pd.DataFrame:
    """The common 110-month sample: drop the 3 pandemic NA months (2020-04/05/06)
    where COE exercises were not held (clearing_price/quota/bids all NA).

    Listwise deletion (NOT imputation), per the Batch A note. N = 110.
    """
    sub = frame[frame["n_obs"] == 1].copy().reset_index(drop=True)
    return sub


def catA_demand_column(frame: pd.DataFrame, definition: str = "bids_received") -> pd.Series:
    """Demand regressor for the price/bidding exhibits.

    PRIMARY (per design): catA_bids_received (corrected).
    ALTERNATIVE (sensitivity): catA_bids_success (corrected).
    Both are reconstructed from raw, so they are defined (nonzero) for all 110
    COE months -- unlike the corrupted panel column.
    """
    if definition == "bids_received":
        return frame["catA_bids_received_clean"]
    if definition == "bids_success":
        return frame["catA_bids_success_clean"]
    raise ValueError(f"unknown demand definition {definition!r}")


def lag(series: pd.Series, k: int) -> pd.Series:
    return series.shift(k)


# ----------------------------------------------------------------------------
# Shared estimation helpers (used by modules 05-12 so SE/CIs are computed the
# same way everywhere).
# ----------------------------------------------------------------------------
def ols(y, X, cov_type="HC1", maxlags=3, name="model"):
    """OLS with robust (HC1) or HAC (Newey-West) SEs.

    X : pd.DataFrame of regressors (NO intercept column -- added here).
    y : pd.Series / np.ndarray (aligned with X.index).
    Returns a statsmodels OLSResults (fit on the rows where y and X are
    all non-NaN, i.e. listwise deletion).
    """
    import statsmodels.api as sm

    d = pd.DataFrame({"__y__": y.to_numpy() if hasattr(y, "to_numpy") else np.asarray(y)})
    d = pd.concat([d, X.reset_index(drop=True)], axis=1)
    d = d.dropna()
    yv = d.pop("__y__")
    # keep column names so params/bse are named (add_constant on a DataFrame)
    xv = sm.add_constant(d.astype(float))
    xv = xv.rename(columns={0: "const"}) if 0 in xv.columns else xv
    if cov_type in ("HAC", "NeweyWest"):
        res = sm.OLS(yv, xv).fit(cov_type="HAC", cov_kwds={"maxlags": maxlags})
    elif cov_type == "HC1":
        res = sm.OLS(yv, xv).fit(cov_type="HC1")
    else:
        res = sm.OLS(yv, xv).fit()
    return res


def coef_rows(res, index_names, extra=None):
    """Flatten an OLSResults into standardized coefficient rows (dicts).

    index_names: list of regressor names matching the columns of X (in order);
    res.params[0] is the constant ('const').
    Uses NAME-based access (statsmodels 0.15 params is a named Series).
    """
    names = ["const"] + list(index_names)
    ci = res.conf_int()
    rows = []
    for nm in names:
        if nm not in res.params.index:
            continue
        rows.append(
            {
                "term": nm,
                "coef": float(res.params[nm]),
                "se": float(res.bse[nm]),
                "t": float(res.tvalues[nm]),
                "p": float(res.pvalues[nm]),
                "ci_lo": float(ci.loc[nm, 0]),
                "ci_hi": float(ci.loc[nm, 1]),
                "nobs": int(res.nobs),
                "r2": float(res.rsquared),
                "cov_type": res.cov_type,
                **(extra if extra is not None else {"note": ""}),
            }
        )
    return rows


def name_of(res):
    return getattr(res, "_model_name", "OLS")


def coef_of(res, term, extra=None):
    """Return a single named coefficient row from an OLSResults (term is the
    regressor name, NOT 'const'). Uses name-based access."""
    ci = res.conf_int()
    row = {
        "term": term,
        "coef": float(res.params[term]),
        "se": float(res.bse[term]),
        "t": float(res.tvalues[term]),
        "p": float(res.pvalues[term]),
        "ci_lo": float(ci.loc[term, 0]),
        "ci_hi": float(ci.loc[term, 1]),
        "nobs": int(res.nobs),
        "r2": float(res.rsquared),
        "cov_type": res.cov_type,
        **(extra if extra is not None else {"note": ""}),
    }
    return row


def make_lags(df: pd.DataFrame, demand: pd.Series) -> pd.DataFrame:
    """Add L1/L2 (and contemporaneous) demand columns + a linear time trend.

    The first `max_lag` rows have NaN in the lagged demand; callers do
    listwise deletion on top of the already-listwise 110-month sample.
    """
    out = df.copy()
    out["demand_l1"] = lag(demand, 1)
    out["demand_l2"] = lag(demand, 2)
    out["demand_t0"] = demand
    out["trend"] = np.arange(len(out))  # linear time trend (0-based month index)
    return out


def threshold_dummy(df: pd.DataFrame) -> pd.Series:
    """Jan-2022 97->110kW Cat A threshold change: on from 2022-01."""
    return (df["month"] >= "2022-01").astype(int)


def load_data():
    """Self-loader: other modules (named 0X_*.py, leading digit -> not
    importable normally) load THIS module by path via this helper.

    Usage in a module:  ``D = importlib.util...`` is cumbersome, so each
    module does:
        from importlib import import_module
        D = import_module("_data_layer")   # after adding src/ to sys.path
    Simpler: use ``load_data()`` below which execs the file once.
    """
    import importlib.util

    _spec = importlib.util.spec_from_file_location(
        "_data_layer", Path(__file__).resolve()
    )
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    return _mod


if __name__ == "__main__":
    fr = load_estimation_frame()
    samp = listwise_sample(fr)
    print(f"[data] frame rows={len(fr)} (2016-01..2025-05)")
    print(f"[data] listwise sample N={len(samp)} "
          f"(dropped {len(fr)-len(samp)} pandemic NA months: "
          f"{fr.loc[fr.n_obs==0,'month'].tolist()})")
    bad = fr[fr["panel_catA_br_corrupted"] == 1]
    print(f"[data] CORRUPTION audit: panel catA_bids_received==0 but raw>0 in "
          f"{len(bad)} months: {bad['month'].tolist()}")
    for K in CATS:
        z = samp[f"cat{K}_bids_received_clean"]
        print(f"[data] cat{K}_bids_received_clean: "
              f"min={z.min():.0f} max={z.max():.0f} "
              f"na={int(z.isna().sum())} zero={int((z==0).sum())}")
