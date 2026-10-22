#!/usr/bin/env python3
"""
Step 6 — scope guard (programmatic assertion layer; verified policy).

SCOPE RULE (dual-scope)
-----------------------
The verified real dose is NOT flat over the 2022+ window: it steps
45000 -> 40000 at 2024-01 (EEAI cap cut), so the 2022-01..2025-05 window has
TWO distinct dose values (41 obs) and is ALSO A VALID ESTIMATION scope.

  (a) full-window (2016-01..2025-05) estimation remains PRIMARY for the
      CEVS->VES transition and overall level effects;
  (b) the 2022-01..2025-05 window is ALSO ESTIMATED for the headline
      exhibits (price equation, bidding channel, mediation): a '2022+ (EV
      era)' spec with the dose step (45000->40000 at 2024-01) + trend +
      ARF-floor/stacking dummies as appropriate;
  (c) a rebate-intensity exhibit may NEVER be estimated on a 2022+-only
      sample: every coefficient exhibit must contain the full window in its
      estimation scope (headline exhibits are dual-scope: full + 2022+).

Assertions enforced:
  (a) no rebate-intensity exhibit estimated on a 2022+-only sample; headline
      exhibits (price_equation, demand_bidding, mediation) must ALSO carry the
      2022+ estimation scope (dual scope) since the dose varies within it;
  (b) the price-equation demand regressor is catA_bids_received (corrected),
      never ev_reg;
  (c) the mediated (indirect/total) share is computed on the full-window
      sample with the 2022+ interpretation stated;
  (d) ev_reg / ev_share enter NO rebate-coefficient model;
  (e) event-study samples span pre- AND post-treatment months;
  (f) data-flow / layering contract: no forward reads (a module may not read a
      file written by a LATER module);
  (g) dose state: 4 distinct in-window doses {20000,30000,45000,40000} and 2
      distinct doses in 2022-01..2025-05 {45000,40000} -> the 2022+ window
      is a valid estimation scope.

A SEPARATE data-integrity assertion is also logged: the panel's
catA_bids_received is corrupted (0) for the last 19 months, and this batch
uses the corrected raw-reconstructed column instead.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bootstrap as B  # noqa: E402

D = B.D
ROOT = D.ROOT
SRC = D.ROOT / "src"
TABLES = D.ROOT / "tables"
AUDIT = TABLES / "scope_audit.csv"

WINDOW_LO = D.WINDOW_LO
WINDOW_HI = D.WINDOW_HI
NATURAL_MONTHS = D.NATURAL_MONTHS

FULL_SCOPE = f"{WINDOW_LO}..{WINDOW_HI}"
PLUS22_SCOPE = f"{WINDOW_LO}..{WINDOW_HI};2022-01..{WINDOW_HI}"

# The ONLY demand-regressor column names a rebate-intensity exhibit may key on.
ALLOWED_DEMAND = {
    "catA_bids_received_clean",   # PRIMARY (design)
    "catA_bids_success_clean",    # sensitivity alternative
}
# Columns that must NEVER be a rebate-coefficient regressor (descriptive only).
FORBIDDEN_IN_REBATE_MODEL = {"ev_reg", "ev_share", "coverage_rate"}
# The corrupted panel columns (must not be used as demand regressors).
CORRUPTED_PANEL_DEMAND = {
    "catA_bids_received", "catA_bids_success",
    "catB_bids_received", "catB_bids_success",
}

# Permitted file reads for ESTIMATION modules (Batch B src/05..12).
ALLOWED_READS = {
    "data/raw/coe_results_raw.csv",
    "data/raw/registrations_raw.csv",
    "data/raw/cpi_raw.csv",
    "data/raw/provenance.csv",
    "data/processed/panel_joint.csv",
    "data/processed/coe_monthly.csv",
    "data/processed/coe_extension_2025_06_2026_10.csv",
    "data/processed/cpi_deflated.csv",
    "data/processed/ev_registrations.csv",
    "tables/rebate_timeline.csv",
    "tables/dose_summary.csv",
    "tables/data_audit.csv",
    "tables/scope_audit.csv",
}

# The Batch-B estimation modules subject to the guard's static scans (06-12).
# The guard itself (05) is excluded (it is the auditor); Batch A (01-04) and the
# shared data/bootstrap modules are upstream data-prep, not exhibits.
MODULE_ORDER = [m for m in B.EST_MODULES
                if m not in ("00_data.py", "_bootstrap.py", "05_scope_guard.py")]


# ---------------------------------------------------------------------------
# Static scans
# ---------------------------------------------------------------------------
def _scan_corrupted_demand_usage() -> list[tuple[str, int, str]]:
    """Find any Batch-B estimation module that USES the corrupted panel
    bid-count columns as a data input (referencing the bare column name in
    CODE, not inside a string literal / docstring / comment)."""
    hits = []
    for mod in MODULE_ORDER:
        if mod == Path(__file__).name:
            continue
        text = (SRC / mod).read_text()
        for i, line in enumerate(text.splitlines(), start=1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            # strip string literals so a bare name inside a quoted note/doc is
            # not mistaken for a code reference
            code_part = re.sub(r'"[^"]*"', " ", line)
            code_part = re.sub(r"'[^']*'", " ", code_part)
            if stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            for bad in CORRUPTED_PANEL_DEMAND:
                if re.search(rf"\b{bad}\b", code_part) and f"{bad}_clean" not in code_part:
                    hits.append((mod, i, line.strip()))
                    break
    return hits


def _scan_evreg_in_rebate_model() -> list[tuple[str, int, str]]:
    """Flag any src module (except the descriptive registration module 08) that
    uses ev_reg / ev_share / coverage_rate as a REBATE-COEFFICIENT regressor
    (i.e. on the same line as an OLS fit, or inside a regressor frame built for
    a model). Merely reporting these columns descriptively (e.g. the grading
    module reading a descriptive table) is NOT flagged -- we require the
    column to appear in a model-input context (an ``ols`` call line or a
    regressor DataFrame/concat line).
    """
    hits = []
    for mod in MODULE_ORDER:
        if mod in (Path(__file__).name, "08_demand_registration.py"):
            continue
        text = (SRC / mod).read_text()
        for i, line in enumerate(text.splitlines(), start=1):
            s = line.strip()
            if s.startswith("#") or s.startswith('"""') or s.startswith("'''"):
                continue
            is_model_line = ("ols(" in s or "ols " in s or
                             ("DataFrame({" in s and "demand" in s.lower()) or
                             "reindex" in s and "ols" in s)
            for bad in FORBIDDEN_IN_REBATE_MODEL:
                if re.search(rf"\b{bad}\b", line) and is_model_line:
                    hits.append((mod, i, s))
                    break
    return hits


# The set of every known pipeline file: Batch A artifacts (ALLOWED_READS) plus
# every file a Batch-B module writes. Used to (i) resolve bare table-name reads
# to tables/<name>, and (ii) decide whether a read targets a real pipeline file.
ALL_KNOWN_FILES = set(ALLOWED_READS)
for _files in D.FILES_WRITTEN.values():
    ALL_KNOWN_FILES.update(_files)


def _strip_docstrings(text: str) -> str:
    """Remove triple-quoted docstrings/comments so the file-read collector only
    sees executable code (a documented input in a docstring is not a read)."""
    out = []
    i = 0
    n = len(text)
    in_str = None
    while i < n:
        ch = text[i]
        if in_str is None:
            if ch in "\"'" and text[i:i + 3] in ('"""', "'''"):
                in_str = text[i:i + 3]
                i += 3
                continue
            if ch == "#":
                while i < n and text[i] != "\n":
                    i += 1
                continue
            out.append(ch)
            i += 1
        else:
            if text[i:i + 3] == in_str:
                in_str = None
                i += 3
            else:
                i += 1
    return "".join(out)


def _collect_file_reads() -> dict[str, set[str]]:
    """For each src module, the set of data file paths it reads (from the
    EXECUTABLE code only -- docstrings and comments are stripped)."""
    reads: dict[str, set[str]] = {}
    const_map = {
        "RAW_COE": "data/raw/coe_results_raw.csv",
        "PANEL": "data/processed/panel_joint.csv",
        "CPI": "data/processed/cpi_deflated.csv",
        "EVREG": "data/processed/ev_registrations.csv",
        "AUDIT": "tables/scope_audit.csv",
    }
    # Collect reads only from the modules that consume other modules' outputs.
    # 00_data.py is the shared base layer (reads only Batch-A artifacts, and its
    # FILES_WRITTEN dict declares outputs rather than reading them) -- skipping
    # it avoids false forward-read flags from its output-declaration lines.
    read_modules = ["05_scope_guard.py"] + MODULE_ORDER
    for mod in read_modules:
        if not (SRC / mod).exists():
            continue
        text = _strip_docstrings((SRC / mod).read_text())
        found: set[str] = set()
        for m in re.finditer(r'read_csv\(\s*(?:[A-Za-z_]+\s*/\s*)?["\']([^"\']+)[\'"]', text):
            name = m.group(1)
            # a bare table name read via OUT_DIR/"name.csv" -> canonical tables/name
            if name.endswith(".csv") and "/" not in name and f"tables/{name}" in ALL_KNOWN_FILES:
                found.add(f"tables/{name}")
            else:
                found.add(name)
        for cname, fpath in const_map.items():
            if re.search(rf"\bD\.{cname}\b", text):
                found.add(fpath)
        for m in re.finditer(
            r'["\'](tables/[^"\']+\.csv|data/raw/[^"\']+\.csv|data/processed/[^"\']+\.csv)[\'"]',
            text,
        ):
            found.add(m.group(1))
        # bare table file names (read relative to OUT_DIR), e.g.
        #   pd.read_csv(OUT_DIR / "price_equation.csv")
        for m in re.finditer(r'["\']([a-z0-9_]+\.csv)[\'"]', text):
            name = m.group(1)
            if f"tables/{name}" in ALL_KNOWN_FILES:
                found.add(f"tables/{name}")
        reads[mod] = found
    return reads


def _forward_read_violations(reads: dict[str, set[str]]) -> list[tuple[str, str, str]]:
    """A module may only read files written by EARLIER modules (or the shared
    data layer / Batch A). Flag reads of files written by a LATER module.

    The ordering is by numeric filename prefix (00_data/_bootstrap = base
    layer, index 0; 05 < 06 < ... < 12). A read of the guard's own output or
    the shared data layer is not a forward read.
    """
    writer_of: dict[str, str] = {}
    for mod, files in D.FILES_WRITTEN.items():
        for f in files:
            writer_of[f] = mod
    # complete numeric ordering over every module that appears anywhere
    all_mods = set(reads) | set(D.FILES_WRITTEN) | {"00_data.py", "_bootstrap.py"}
    def key(m):
        try:
            return int(m[:2])
        except ValueError:
            return 999
    order_idx = {m: i for i, m in enumerate(sorted(all_mods, key=key))}
    viol = []
    for mod, files in reads.items():
        for f in files:
            w = writer_of.get(f)
            if w and w != mod and order_idx.get(w, 999) > order_idx.get(mod, 999):
                viol.append((mod, f, w))
    return viol


# ---------------------------------------------------------------------------
# Main audit
# ---------------------------------------------------------------------------
def run_audit() -> pd.DataFrame:
    rows = []

    def add(check, status, detail=""):
        rows.append({"check": check, "status": status, "detail": detail})

    exhibits = B.EXHIBITS  # populated when modules are imported

    # Kinds that are true REBATE-INTENSITY (coefficient) exhibits and must be
    # estimated on the full window. Descriptive exhibits (the EV registration
    # channel) are exempt from (a) because they carry no within-window rebate
    # variation and feed no coefficient.
    REBATE_KINDS = {"price_equation", "demand_bidding", "mediation",
                    "event_study", "demand_registration"}
    # Headline exhibits that, under the verified-policy dual-scope rule, must
    # ALSO be estimated on the 2022+ EV-era window (estimable: the dose
    # varies inside it, 45000 -> 40000 at 2024-01).
    DUAL_SCOPE_KINDS = {"price_equation", "demand_bidding", "mediation"}

    # ---- data-integrity: panel corruption detected + correction in use ----
    frame = D.load_estimation_frame()
    corrupted = int(frame["panel_catA_br_corrupted"].sum())
    clean_nonzero = int((frame["catA_bids_received_clean"] > 0).sum())
    add(
        "DATA-INTEGRITY: panel catA_bids_received corruption detected & corrected",
        "PASS" if (corrupted == 19 and clean_nonzero >= NATURAL_MONTHS - 3) else "FAIL",
        f"panel==0 but raw>0 in {corrupted} months (2023-10..2025-05); "
        f"corrected col nonzero for {clean_nonzero}/110 COE months. "
        f"All Batch-B models use catA_bids_received_clean.",
    )

    # ---- (a) no 2022+-only estimation scope; headline exhibits dual-scope ----
    coeff_exhibits = [e for e in exhibits if e["kind"] in REBATE_KINDS]
    full_ok = bool(coeff_exhibits) and all(
        e["est_scope"].replace(" ", "").startswith(FULL_SCOPE)
        for e in coeff_exhibits
    )
    dual_exhibits = [e for e in exhibits if e["kind"] in DUAL_SCOPE_KINDS]
    dual_ok = bool(dual_exhibits) and all(
        f"2022-01..{WINDOW_HI}" in e["est_scope"].replace(" ", "")
        for e in dual_exhibits
    )
    add(
        "(a) no rebate-intensity exhibit estimated on a 2022+-only sample; "
        "headline exhibits carry the dual scope (full window + 2022+ EV era)",
        "PASS" if (full_ok and dual_ok) else "FAIL",
        f"{len(coeff_exhibits)} coefficient exhibits registered "
        f"(descriptive exhibits exempt); est_scope="
        f"{sorted(set(e['est_scope'] for e in coeff_exhibits))}. "
        f"Verified dose varies in 2022-01..{WINDOW_HI} (45000->40000 at "
        f"2024-01) so 2022+ is ALSO an estimation scope; full window remains "
        f"primary. Dual-scope kinds: "
        f"{[e['name'] for e in dual_exhibits]}.",
    )

    # ---- (b) price-equation demand regressor ----
    pe = [e for e in exhibits if e["kind"] == "price_equation"]
    ok_b = bool(pe) and all(e["key_regressor"] in ALLOWED_DEMAND for e in pe)
    bad_b = _scan_corrupted_demand_usage()
    # filter hits that are only in the two "allowed" documentation modules
    bad_b = [h for h in bad_b if h[0] not in ("00_data.py", "_bootstrap.py")]
    add(
        "(b) price-equation demand regressor = catA_bids_received (corrected), never ev_reg",
        "PASS" if (ok_b and not bad_b) else "FAIL",
        f"price_equation key_regressor={[e['key_regressor'] for e in pe]}; "
        f"static scan for corrupted-panel demand usage (code): "
        f"{bad_b if bad_b else 'clean'}",
    )

    # ---- (c) mediated share on full-window sample ----
    med = [e for e in exhibits if e["kind"] == "mediation"]
    ok_c = bool(med) and all(e.get("mediation_full_window") for e in med) \
        and all("2022" in e["interpretation_scope"] for e in med)
    add(
        "(c) mediated share computed on full-window sample; 2022+ interpretation stated",
        "PASS" if ok_c else "FAIL",
        f"mediation exhibits={len(med)}; full-window={[e.get('mediation_full_window') for e in med]}; "
        f"interpretation={[e['interpretation_scope'] for e in med]}",
    )

    # ---- (d) ev_reg / ev_share in no rebate-coefficient model ----
    bad_d = _scan_evreg_in_rebate_model()
    add(
        "(d) ev_reg / ev_share enter NO rebate-coefficient model",
        "PASS" if not bad_d else "FAIL",
        f"static scan (excluding descriptive module 08): {bad_d if bad_d else 'clean'}",
    )

    # ---- (e) event-study samples span pre- and post-treatment ----
    ev = [e for e in exhibits if e["kind"] == "event_study"]
    ok_e = bool(ev) and all(e.get("event_spans_pre_post") for e in ev)
    add(
        "(e) event-study samples span pre- AND post-treatment months",
        "PASS" if ok_e else "FAIL",
        f"event_study exhibits={len(ev)}; spans_pre_post={ [e.get('event_spans_pre_post') for e in ev]}",
    )

    # ---- (f) layering contract: no forward reads ----
    reads = _collect_file_reads()
    fwd = _forward_read_violations(reads)
    # A read is DISALLOWED only if it targets a file that (i) is a forward read
    # of a later module, OR (ii) is not a known pipeline file at all (not a
    # Batch A artifact and not written by any Batch B module). Reading an
    # EARLIER module's output is legitimate pipeline flow and is allowed.
    all_written = set()
    for files in D.FILES_WRITTEN.values():
        all_written.update(files)
    known_files = ALLOWED_READS | all_written
    disallowed = [
        (m, f) for m, fs in reads.items()
        if m != Path(__file__).name
        for f in fs
        if f not in known_files
    ]
    add(
        "(f) data-flow layering contract: no forward reads / no disallowed inputs",
        "PASS" if (not fwd and not disallowed) else "FAIL",
        f"forward_reads={fwd if fwd else 'none'}; "
        f"disallowed_inputs={disallowed if disallowed else 'none'}",
    )

    # ---- (g) dose state under the verified policy (replaces the old
    # dose-state assertion (verified policy; 2 distinct doses inside 2022+) ----
    panel = pd.read_csv(D.PANEL)
    full_doses = sorted(panel["dose_nominal_sgd"].unique().astype(int).tolist())
    tail = panel[panel["month"] >= "2022-01"]["dose_nominal_sgd"]
    tail_doses = sorted(tail.unique().astype(int).tolist())
    ok_g = (full_doses == [20000, 30000, 40000, 45000]
            and tail_doses == [40000, 45000]
            and len(tail) == 41)
    add(
        "(g) dose state (verified policy): 4 distinct in-window doses "
        "{20000,30000,40000,45000} (all levels verified from LTA/NEA tables); "
        "2022+ window has 2 distinct doses {40000,45000} over 41 obs -> "
        "2022+ IS a valid estimation scope",
        "PASS" if ok_g else "FAIL",
        f"full-window distinct={full_doses}; 2022-01..2025-05 distinct="
        f"{tail_doses} (n={len(tail)}). The dose varies within the 2022+ "
        f"window (45000 -> 40000 at 2024-01), so it is estimable.",
    )

    add(
        "SCOPE-FACT: effective verified-policy dose steps = 3 "
        "(2018-01: 30000->20000 CEVS->VES; 2021-01: 20000->45000 enhanced "
        "VES + EEAI; 2024-01: 45000->40000 cap cut) + 2022-01 ARF-floor-zero "
        "(tax) + 2022-05 97->110kW threshold (confounder, separate dummy)",
        "PASS",
        "5 in-window policy events (3 dose steps + 2022-01 ARF floor + "
        "2022-05 threshold); low-power caveat: full window 110 monthly "
        "obs (113 months, 3 pandemic NA); 2022+ scope 41 obs. Grades bounded "
        "accordingly (step 12).",
    )

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.Timestamp.now("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
    return df


def main():
    TABLES.mkdir(parents=True, exist_ok=True)
    B.EXHIBITS.clear()
    B.import_all_estimation_modules()
    df = run_audit()
    df.to_csv(AUDIT, index=False)
    n_pass = int((df["status"] == "PASS").sum())
    n_fail = int((df["status"] == "FAIL").sum())
    print(f"[scope_guard] wrote {AUDIT}  checks={len(df)} PASS={n_pass} FAIL={n_fail}")
    for _, r in df.iterrows():
        mark = "ok " if r["status"] == "PASS" else "FAIL"
        print(f"  [{mark}] {r['check']}\n         {r['detail']}")
    if n_fail:
        raise SystemExit(f"HARD-FAIL: {n_fail} scope-guard assertion(s) failed")


if __name__ == "__main__":
    main()
