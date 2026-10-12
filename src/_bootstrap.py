#!/usr/bin/env python3
"""
Shared bootstrap for the Batch-B estimation modules (05-12).

Each estimation module is named ``0X_*.py`` (leading digit), so it cannot be
imported by name with a plain ``import``. This bootstrap:
  * loads the data layer ``00_data.py`` by path (once, cached) and exposes it
    as ``D``;
  * provides ``register_exhibit(...)`` for modules to declare their scope so
    the scope guard (05) can audit them;
  * provides ``import_all_estimation_modules()`` used by the scope guard to
    re-import (and re-register) every module.

Usage in an estimation module::

    import _bootstrap as B
    D = B.D                      # data layer
    B.register_exhibit(...)      # declare scope (called once at import time)
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent

# ---------------------------------------------------------------------------
# Data layer (loaded once by path, cached in sys.modules)
# ---------------------------------------------------------------------------
_DATA_MOD = None


def _load_data():
    global _DATA_MOD
    if _DATA_MOD is None:
        spec = importlib.util.spec_from_file_location(
            "_data_layer", SRC / "00_data.py"
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules["_data_layer"] = mod
        spec.loader.exec_module(mod)
        _DATA_MOD = mod
    return _DATA_MOD


D = _load_data()

WINDOW_LO = D.WINDOW_LO
WINDOW_HI = D.WINDOW_HI

# ---------------------------------------------------------------------------
# Exhibit registry (read by the scope guard)
# ---------------------------------------------------------------------------
EXHIBITS: list[dict] = []


def register_exhibit(
    name: str,
    kind: str,
    est_scope: str,
    key_regressor: str,
    interpretation_scope: str,
    n_obs: int | None = None,
    notes: str = "",
    mediation_full_window: bool | None = None,
    event_spans_pre_post: bool | None = None,
):
    """Declare an exhibit's scope so the scope guard can verify it.

    est_scope must be the FULL window ``2016-01..2025-05`` for every
    rebate-intensity exhibit (a 2022+-only scope is forbidden).
    """
    EXHIBITS.append(
        dict(
            name=name, kind=kind, est_scope=est_scope,
            key_regressor=key_regressor,
            interpretation_scope=interpretation_scope,
            n_obs=n_obs, notes=notes,
            mediation_full_window=mediation_full_window,
            event_spans_pre_post=event_spans_pre_post,
        )
    )


# The Batch-B ESTIMATION modules (steps 6-13). Batch A (01-04) and the shared
# data/bootstrap modules are NOT exhibits and are excluded everywhere.
EST_MODULES = [
    "05_scope_guard.py", "06_price_equation.py", "07_demand_bidding.py",
    "08_demand_registration.py", "09_mediation.py", "10_event_study.py",
    "11_diagnostics.py", "12_grading.py",
]


def import_all_estimation_modules(include_guard=False, run_main=True):
    """Import (fresh) every Batch-B ESTIMATION module in numeric order (06-12).

    Each module both (a) writes its tables and (b) registers its exhibit(s) as
    a side effect of running its ``main()``. With ``run_main=True`` (default)
    this runs the FULL pipeline, so the scope guard is a single entrypoint:
    ``python3 src/05_scope_guard.py`` executes 06-12 in order, then audits the
    freshly-registered exhibits. Modules are executed in numeric order so that
    downstream readers (e.g. 12_grading, which consumes 06-11's tables) run
    after their inputs exist.
    """
    for mod in EST_MODULES:
        if mod == "05_scope_guard.py" and not include_guard:
            continue
        path = SRC / mod
        if not path.exists():
            continue
        mname = mod[:-3]
        spec = importlib.util.spec_from_file_location(mname, path)
        m = importlib.util.module_from_spec(spec)
        sys.modules[mname] = m
        spec.loader.exec_module(m)
        if run_main and hasattr(m, "main"):
            m.main()
