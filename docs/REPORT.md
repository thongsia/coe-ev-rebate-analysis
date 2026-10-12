# Do EV rebates make COE bidders bid more? — Final report

**Case:** Singapore COE / EV-rebate bidding analysis, joint window **2016-01 .. 2025-05** (113 months; 110 with COE exercises — 2020-04/05/06 suspended). All numbers below are copied verbatim from `tables/*.csv`; none are recomputed in this document. Figure-traceability: 69/69 report figures verified against their source tables (see `tables/report_figures_checklist.csv` and `tables/verification_report.csv`).

---
## 1. Executive summary

### Bottom line (honest)

> **The EV rebate offer does NOT detectably cause bidders to bid more, or raise Cat A COE clearing prices, through an EV-specific channel.** Grade (from `tables/evidence_grading.csv`, link = *rebate->price (HEADLINE core question)*): **not detectable**. The full-window price equation does show a positive 2022-01 coefficient (5,880 S$, p=0.034 HC1; CI95 [444, 11,317]) — **but the negative-control check FAILS**: clean control categories C/D/E, to which **no EV rebate applies at all**, show the **same or larger** 2022-01 price jump (C 13.7%, D 41.8%, E 36.4% vs A 10.1%). The 2022-01 increase is therefore a **market-wide common shock** (co-timed with the 97→110kW Cat A threshold change), not an EV-rebate-specific effect. All estimates are **associational at best** given endogeneity (the rebate is set in response to EV demand) and low statistical power (4 effective treatment changes, 110 monthly observations).

### Graded evidence per link (from `tables/evidence_grading.csv`)

| Causal link | Full-window estimate | Grade | Interpretation scope |
|---|---|---|---|
| **rebate → price (HEADLINE)** | reg_eeai_202201 coef = **+5,880 S$** (dose/1000 = +2,349 S$/1000 S$); nominal↔real non-reversing | **not detectable** | 2022-01..2025-05 (EV-relevant interpretation of full-window est.) |
| rebate → demand (bidding) | reg_eeai coef = -278 bids (HC1 p=0.04; HAC p=0.12 → **not robust**); dose/1000 = -25.1 bids (p=0.422) → **null** | **not detectable** | 2022-01..2025-05 (EV-relevant); full-window estimate |
| rebate → demand (registration) | descriptive only (no coefficient; EEAI flat 2022-01..2025-05; no within-window variation) | **not detectable** | 2022-07..2025-05 (observed BEV window) |
| demand → price | demand_l1 coef = -1.039 S$/bid (CI95 [-2.719, +0.640]), p=0.225 → **not significant** | **not detectable** | full window (mechanism link; no EV-specificity claim) |
| rebate → demand → price (mediation) | indirect = -43.4 S$/1000 S$ (CI95 [-399.4, +253.1]); mediated share = -0.015 (CI spans 0) | **not detectable** | 2022-01..2025-05 (headline = 2022+ reading of full-window est.) |

**Read:** the only nominally 'significant' headline coefficient fails the negative control, the bidding-channel coefficient is not robust to HAC standard errors and the dose version is null, the demand→price mechanism is insignificant, and the mediated path is null. Every link grades *not detectable*. The answer to 'does the rebate cause bidders to bid more?' is: **no detectable effect; the evidence is associational at best.**

---
## 2. Data

### 2.1 Data dictionary (three stores, from `data/raw/` → `data/processed/`)

| Store | Raw rows (stated total) | Contents | Processed artifact(s) |
|---|---|---|---|
| **COE results** | 1,985 (d_69b3380a…) | one row per (month, bidding_no, vehicle_class); fields `month, bidding_no, vehicle_class, quota, bids_success, bids_received, premium, _id`; categories A (low-power cars), B (high-power cars), C (goods), D (large goods), E (motorcycles); 2010-01..2026-10 | `coe_monthly.csv` (995 rows = 199 months × 5 cats, mean clearing price, summed quota/bids, exercise-count audit); `coe_extension_2025_06_2026_10.csv` (85 rows, COE-only extension) |
| **Registrations** | 51,669 (d_d3f4d708…) | one row per (month, make, importer_type, fuel_type, vehicle_type, number); `number` null on ~57% of rows, rising over time ⇒ counts are LOWER BOUNDS; `Electric` (BEV) label first appears **2022-07** | `ev_registrations.csv` (113 rows; `ev_reg`, `ev_share`, `coverage_rate`, `nonnull_total`, `rows_total`) |
| **CPI All Items** | 207 series (d_bdaff844…) | wide-format monthly CPI, 2024 base, 2016-01..2026-08 | `cpi_deflated.csv` (113 rows; real Cat A price = nominal ÷ (CPI/100)) |

Joint panel: `panel_joint.csv`, **113 rows** (one per month, 2016-01..2025-05): per-category COE columns (A–E: clearing_price, quota, bids_received, bids_success, exercises) + EV columns + 4 regime step dummies + continuous `dose_nominal_sgd` + `in_interpretation_window`.

### 2.2 Regime timeline (from `tables/rebate_timeline.csv`, incl. verified-policy discrepancies)

| Effective month | Programme (as encoded by plan) | Size | In joint window | In extension | Verification against cited sources |
|---|---|---|---|---|---|
| 2016-11 | CEVS uplift (plan) | nominal +2000 (case-study construct; magnitude not verifiable) | Yes | No | NOT corroborated as a discrete Nov 2016 step; LTA shows a revised CEVS in force 1 Jul 2015 .. 31 Dec 2017 with no Nov 2016 step. |
| 2018-01 | CEVS lapse (plan) | nominal -4000 (case-study construct; magnitude not verifiable) | Yes | No | CORROBORATED: CEVS applied to cars/taxis registered through 31 Dec 2017, so it lapsed 1 Jan 2018 (VES replaced it). |
| 2018-09 | VES revival (plan) | nominal +1000 (case-study construct; magnitude not verifiable) | Yes | No | PARTIALLY corroborated: VES came into effect 1 Jan 2018 (NEA), not Sep 2018; the 'revival' framing is not corroborated. |
| 2022-01 | EEAI introduction incl. 45% ARF rebate capped at $7,500 (plan) | $7,500 (verified policy figure; used as dose anchor) | Yes | No | DISCREPANCY (documented): real EEAI introduced 1 Jan 2021 at 45%-of-ARF capped at $20,000 (2021-23) -> $15,000 (2024-25) -> $7,500 (2026-27). The $7,500 is the 2026 cap, not a Jan 2022 introduction. The actual Jan 2022 change was the $0 ARF floor for EVs. |
| 2026-01 | EEAI cap cut to $7,500 (real policy) | $15,000 -> $7,500 (verified) | No | Yes (2025-06..2026-10, COE-only) | CORROBORATED: 'From 1 Jan 2026 to 31 Dec 2026, the rebate will be capped at $7,500' (LTA). Outside the joint window; lives in the COE-only extension. |
| 2013-01 | CEVS introduction (plan says 2012) | — | No (before 2016-01) | No | CORROBORATED at 1 Jan 2013 (NCCS), not 2012. OUTSIDE the 2016-01 window -> contributes nothing to identification. |

**Discrepancies (documented, cited):** the plan's 4-event schedule is a stylized case-study design. Verified LTA/NEA/NCCS policy differs: real EEAI introduced 1 Jan 2021 (45% of ARF, capped $20,000 → $15,000 (2024) → **$7,500 (Jan 2026)**); VES in force from 1 Jan 2018; CEVS ran through 31 Dec 2017 (introduced 1 Jan 2013, not 2012); the actual Jan 2022 EV change was the $0 ARF floor. **Only the $7,500 dose anchor is a verified policy figure**; pre-2022 levels are nominal constructs (directions per plan, magnitudes not verifiable).

### 2.3 Collapsing rules

- **COE:** mean of `premium` (clearing price) per (month, category); SUM of quota/bids per (month, category); `exercise_count` audit — per-category exercise-count sums equal raw row counts exactly (verified: 220 per category in the 2016-01..2025-05 window, `tables/verification_report.csv` check (b)).
- **Registrations:** per month, `ev_reg` = SUM of `number` over `fuel_type == 'Electric'` rows; `rows_total` = all raw rows that month; `coverage_rate = rows_nonnull / rows_total`. Hybrids (`Petrol-Electric*`) are never folded in. 2016-01..2022-06 = NA by construction (no BEV label).
- **Joint window / COE-only extension:** the panel is 2016-01..2025-05. From 2025-06 to 2026-10 COE data continues but registrations stop ⇒ the extension is **COE-only, descriptive only** (85 rows); the Jan-2026 EEAI cap cut ($15k→$7.5k) lives there and is NOT estimated.
- **Null-coverage caveat:** `number` is null on a rising share of registration rows (coverage 18%→33% across the BEV window), so `ev_reg` is a **lower bound that decays in reliability over time**.
- **Pandemic months:** 2020-04/05/06 — no COE exercises held (documented in `tables/data_audit.csv`: `coe_exercise_gap = 2020-04; 2020-05; 2020-06`). Listwise dropped (not imputed); estimation sample N=110.

### 2.4 Estimable-scope rule (full-window estimation; 2022+ interpretation)

Every rebate-intensity exhibit is **estimated on the full window 2016-01..2025-05**. The dose is **FLAT from 2022-01 to window end** (`dose_constant_2022_01_to_2025_05 = TRUE`, `tables/dose_summary.csv`), so a 2022+-only estimation would be **rank-deficient** — the 2022+ robustness table literally contains the NA row: *"RANK-DEFICIENT: dose + reg_eeai_202201 are constant on 2022-01..2025-05 (dose flat at 7500; dummy flat at 1). A rebate coefficient is NOT estimable on a 2022+-only sample by the scope rule. Left as NA by design -- not a missing number."* (nobs=41). **2022+ is the INTERPRETATION scope only** (where the EEAI-era level is in force and the EV signal is material); it is never an estimation scope for rebate-intensity exhibits. This is audited by `src/05_scope_guard.py` (`tables/scope_audit.csv`, check (a)) and re-verified by `src/14_verify.py` (check (f)).

### 2.5 The `catA_bids_received` correction (data-integrity fix)

Batch A's panel contains a silent corruption: the raw datastore stores bid counts as strings with thousands separators (`'1,039'`) from mid-2023 on; Batch A's numeric coercion failed on those strings, and the monthly collapse summed NaNs to **0** — so `panel_joint.catA_bids_received` is literally 0 for **19 months (2023-10..2025-05)**, i.e. the entire EV-rebate era looks like zero demand. `src/00_data.py` reconstructs the monthly sums from `data/raw/coe_results_raw.csv` with comma-tolerant parsing → `catA_bids_received_clean`, **non-zero for all 110 COE months**. **Every model in this pipeline uses the corrected series**, never the corrupted panel column, never `ev_reg` as a price/bidding regressor (verified by `src/14_verify.py` check (g) and `tables/scope_audit.csv` check (b)).

---
## 3. Results

Every causal exhibit below shows (i) the **full-window estimable estimate** and (ii) its bounded **2022+ interpretation**, together with the negative-control verdict where it applies. All coefficients: HC1 robust SEs unless noted; HAC (Newey-West lag-3) reported where autocorrelation matters (DW 0.79 — see §3.8).

### 3.1 Price equation (rebate → price) — `tables/price_equation.csv`

Primary spec M1 (lag-1 + lag-2 corrected Cat A demand, 4 regime dummies, quota, linear trend, CPI): full window, listwise N=110 (3 pandemic months dropped), nobs=108.

| Term | Nominal coef (S$) | CI95 | p (HC1) | p (HAC) | Real coef (S$) | p (real, HC1) |
|---|---|---|---|---|---|---|
| **reg_eeai_202201** (headline) | +5,880.4 | [+443.6, +11,317.1] | 0.034 | 0.104 | +7,532.5 | 0.0122 |
| reg_cevs_uplift_201611 | -8,565.4 | [-12,995.1, -4,135.7] | 0.000151 | 0.00249 | -10,066.9 | 0.000138 |
| reg_cevs_lapse_201801 | -15,722.0 | [-20,021.6, -11,422.4] | 7.67e-13 | 8.54e-07 | -18,582.7 | 4.74e-13 |
| reg_ves_revival_201809 | -7,638.6 | [-11,986.1, -3,291.0] | 0.000574 | 0.00703 | -8,900.5 | 0.000388 |
| demand_l1 (S$/bid) | -1.0 | [-2.7, +0.6] | 0.225 | 0.226 | -1.2 | 0.219 |
| demand_l2 (S$/bid) | +0.3 | [-0.8, +1.5] | 0.565 | 0.569 | +0.4 | 0.561 |
| catA_quota (S$) | -6.1 | [-8.8, -3.3] | 1.71e-05 | 3.3e-05 | -7.3 | 2.2e-06 |
| trend (S$/month) | -81.0 | [-312.8, +150.9] | 0.494 | 0.602 | -66.8 | 0.589 |
| cpi_all_items (S$/index-pt) | +3,995.2 | [+2,849.9, +5,140.5] | 8.09e-12 | 5.19e-07 | +3,385.6 | 2.58e-08 |

Dose spec M3 (continuous, per 1000 S$): **nominal +2,349 S$/1000 S$ (CI95 [1,577, 3,121], p=2.45e-09); real +2,824 S$/1000 S$ (p=2.66e-10); HAC p=3.88e-05** — significant under all variants. **No nominal↔real reversal.**

**Honest read:** the 2022-01 jump (5,880 S$ ≈ +10.1% of the Cat A mean) looks positive and significant (HC1), but the HAC p-value is 0.104 and — decisively — the **negative-control check FAILS** (§3.6): clean categories with no EV rebate show the same or larger jump. This is a **market-wide common shock co-timed with the 97→110kW threshold change**, not an EV-rebate-specific price effect.

### 3.2 Bidding channel (rebate → Cat A bidding demand) — `tables/demand_bidding_channel.csv`, `tables/crosslag_check.csv`

| Spec | Term | Coef (bids) | CI95 | p (HC1) | p (HAC) | Verdict |
|---|---|---|---|---|---|---|
| dummy (4 regime steps) | **reg_eeai_202201** | -277.7 | [-542.8, -12.6] | 0.04 | **0.12** | significant HC1 only → **NOT robust** |
| dose (per 1000 S$) | dose_1000 | -25.1 | [-86.3, +36.1] | 0.422 | — | **null** |
| cross-lag | dose shifted −1 / 0 / +1 month | -37.8 / — / — | — | 0.226 / 0.422 / 0.226 | — | no timing pattern |

**Honest read:** the predicted direction for 'bidders bid more' is coefficient > 0; the estimated 2022-01 effect is −278 bids and only significant under HC1, while the continuous dose is null and the cross-lag shows no pattern. The sign is even the *wrong* direction for the hypothesised bidding channel. **This does NOT support 'the rebate causes bidders to bid more'.** Grade: not detectable. (Context: total Cat A demand is dominated by non-EV cars; the EV signal is material only from ~2022, so the 2022+ interpretation window is 2022-01..2025-05.)

### 3.3 Registration channel (rebate → EV registrations) — `tables/ev_registrations_descriptive.csv` (DESCRIPTIVE ONLY)

Observed BEV window 2022-07..2025-05 (35 months): mean 854 registrations/month (median 635, min 241, max 2,014); mean EV share 25.8% (max 43.0%); cumulative 29,899; coverage decays 18%→33%. **No within-window rebate variation** (EEAI constant ⇒ flat dose), so **no coefficient is estimable** on this channel — descriptive / correlational only, and `ev_reg` is a lower bound. Grade: not detectable.

### 3.4 Mediation (rebate → bidding demand → price) — `tables/mediation_effects.csv`

| Path | Estimate (S$/1000 S$ dose) | CI95 | n_obs |
|---|---|---|---|
| total (rebate → price) | +2897.4 | [+1890.1, +4150.7] | 109 |
| **indirect (rebate → demand → price)** | -43.4 | [-399.4, +253.1] | 109 |
| direct (holding demand fixed, point est.) | +2940.8 | — | 109 |
| **mediated share (indirect / total)** | -0.015 | [-0.158, +0.083] | 109 |

**Honest read:** the mediated share is **-0.015** with a CI that spans 0 (-0.158, +0.083) — the price effect is **NOT routed through Cat A bidding demand**. The indirect path is null (−43 S$/1000 S$, CI spans 0). 2-stage bootstrap (N=2000), full-window estimation with 2022+ interpretation; simultaneity flagged (rebate set in response to EV demand). Grade: not detectable. → **charts/06_mediation_diagram.png**

### 3.5 Event study — `tables/event_study_coefficients.csv`, `tables/event_study_prechecks.csv`

- **Episode 2 (2022-01, EEAI rebate + 97→110kW threshold — BOUNDED, combined):** onset +22,683 S$ [CI95 13,995, 31,370], p=3.1e-07; lag 1-6 +33,132 S$ (p=5.19e-06), lag 7-17 +48,411 S$ (p=1.14e-05); lead −1 +22,884 S$ (p=2.03e-07). Pre-trend check: **CONTAMINATED** (joint leads Wald p=6.16e-11; `pre_trend_clean=False`) — a secular COE trend is present, so the onset is a **bound** relative to a moving pre-trend, co-timed with the threshold change. "CONTAMINATED pre-trend: leads not ~0 (a pre-existing secular trend is present); onset effect is a BOUND relative to a moving pre-trend, not a clean causal jump. Reported honestly."
- **Episode 1 (2016-11, total/low-emission demand — NEVER EV-specific):** onset +3,485 S$ [CI95 1,478, 5,491], p=0.000664; pre-trend also contaminated (joint leads Wald p=1.05e-50). "CONTAMINATED pre-trend: leads not ~0 (a pre-existing secular trend is present); onset effect is a BOUND relative to a moving pre-trend, not a clean causal jump. Reported honestly."
- **Jan 2026 EEAI cap cut ($15k→$7.5k): DESCRIPTIVE ONLY** — lives in the COE-only extension 2025-06..2026-10; bounded by the 2026 PARF cut + supply trough; does NOT enter the joint-window event study (`tables/event_study_prechecks.csv`, row `2026-01_capcut_DESCRIPTIVE_ONLY`).

→ **charts/05_event_study.png**

### 3.6 Negative controls (the decisive test) — `tables/negative_controls.csv`

| Category | Role | reg_eeai_202201 coef (S$) | CI95 | p | 2022-01 % jump (coef/mean) |
|---|---|---|---|---|---|
| A | MAIN (low-power cars; EV-eligible) | +5,880 | [+444, +11,317] | 0.034 | **+10.11%** |
| B | CONTAMINATED upper bound (high-power EVs fall here) | +9,925 | [-359, +20,208] | 0.0586 | **+14.15%** |
| C | **CLEAN negative control** (goods; no EV rebate) | +6,704 | [-1,133, +14,542] | 0.0936 | **+13.74%** |
| D | **CLEAN negative control** (large goods; no EV rebate) | +3,195 | [+1,669, +4,721] | 4.07e-05 | **+41.76%** |
| E | **CLEAN negative control** (motorcycles; no EV rebate) | +25,992 | [+13,353, +38,631] | 5.56e-05 | **+36.42%** |

> **# VERDICT: NEGATIVE-CONTROL FAIL: clean controls C/D/E 2022-01 % jumps = 13.7/41.8/36.4% vs A (EV-eligible) 10.1%. Clean controls show the SAME 2022-01 price jump despite NO EV rebate applying to them -> the apparent 'rebate -> price' effect is a MARKET-WIDE COMMON SHOCK (co-timed 97->110kW threshold + COE market dynamics)**

Clean controls C/D/E have **no EV rebate at all** yet show the same or a larger 2022-01 jump (13.7% / 41.8% / 36.4% vs A's 10.1%). Verdict: **NEGATIVE-CONTROL FAIL** — the 2022-01 price increase is a market-wide common shock, and the headline 'rebate → price' coefficient cannot be credited to the EV rebate. → **charts/01_price_regime.png** (bottom panel)

### 3.7 2022+ robustness (demand → price only) — `tables/price_equation_2022plus_robustness.csv`

2022-01..2025-05 subsample (nobs=41; trend + CPI + quota; demand lags; nominal and real): demand_l1 -2.71 (p=0.508), demand_l2 +1.67 (p=0.535), quota -22.62 (p=0.0036), trend +954 (p=0.0308) — the price equation in the EV era is **dominated by trend + regime terms**, and demand is not significant. The rebate-intensity row is left NA by design (rank-deficient on the flat tail — see §2.4). This 2022+ subsample is **interpretation/robustness only**, never the estimation scope for rebate exhibits.

### 3.8 Diagnostics — `tables/diagnostics_stationarity_autocorr.csv`

- Stationarity: Cat A price (nominal) level ADF p=0.966 (**I(1)**); 1st-diff ADF p=4.86e-17 (stationary). Demand (corrected) level ADF p=0.2 (I(1)). CPI level ADF p=0.767 (I(1)-ish).
- Residual autocorrelation: **Durbin-Watson = 0.7910** (primary price equation); Ljung-Box Q(1) = 37.1 (p=1.14e-09, significant); Breusch-Godfrey (nlags=3): F=18.7646. ⇒ **HAC (Newey-West) SEs used throughout**; headline significance is HC1-only.
- **Power:** 4 effective treatment changes, 110 monthly obs — low power; wide CIs are expected. Precise magnitude claims are forbidden; all estimates are bounds, not precise causal magnitudes.

### 3.9 Sensitivity — `tables/sensitivity_analysis.csv`

| Variant (reg_eeai_202201) | Coef (S$) | CI95 | p | nobs |
|---|---|---|---|---|
| primary w/o catA_quota | +8,978 | [+2,743, +15,212] | 0.00477 | 108 |
| primary w/o trend | +6,950 | [+2,672, +11,228] | 0.00145 | 108 |
| primary w/o CPI | +24,867 | [+18,848, +30,885] | 5.58e-16 | 108 |
| demand def = bids_received (primary) | +5,880 | [+444, +11,317] | 0.034 | 108 |
| demand def = bids_success | +4,106 | [-1,429, +9,641] | 0.146 | 108 |
| lag order = lag-1 only | +6,037 | [+783, +11,291] | 0.0243 | 109 |
| lag order = lag-2 only | +6,021 | [+594, +11,447] | 0.0297 | 108 |
| contemporaneous demand | +7,189 | [+1,729, +12,648] | 0.00986 | 110 |
| price def = nominal (primary) | +5,880 | [+444, +11,317] | 0.034 | 108 |
| price def = real | +7,532 | [+1,644, +13,421] | 0.0122 | 108 |

The 2022-01 coefficient survives every control/variant in magnitude (positive, +5,900..+24,900 S$; only the bids_success demand definition loses significance, p=0.146) — **but significance is not the question**: the negative-control failure (§3.6) is invariant to all of these, because the common shock hits every category. Robustness of magnitude ≠ identification of cause.

---
## 4. Confounder discussion

- **Jan 2022 97→110kW Cat A threshold change (dominant confounder).** Co-timed with the encoded EEAI introduction; raises the eligible class mix and shifts clearing prices market-wide. The negative-control failure is its signature: every category, including rebate-free goods/motorcycle categories, jumps in the same month. The threshold dummy (M1b) reproduces the headline coefficient exactly, i.e. the two cannot be separated with this data.
- **Secular COE price trend.** Prices are I(1) and trending; the event-study leads are significant and non-zero (contaminated pre-trends), so event onsets are bounds, not clean jumps. The price equation absorbs a linear trend, but a trend cannot fully proxy a regime shift.
- **2026 PARF cut + 2026 supply trough.** The Jan-2026 EEAI cap cut sits in the COE-only extension alongside the 2026 PARF reform and a COE supply trough; any 2026 price movement there is descriptively confounded and is deliberately NOT estimated.
- **Category-merge windows.** Historical category reclassifications (e.g. the B/E and goods category restructuring) mean pre-2022 and post-2022 category definitions are not fully comparable; this limits cross-period comparisons of per-category levels (within-category time series remain valid).
- **CPI deflation.** Nominal vs real: the headline coefficient is +5,880 S$ (nominal) vs +7,532 S$ (real) — same sign, same interpretation; no real-terms reversal that would rescue an EV-specific reading.
- **Endogeneity / simultaneity.** The rebate was set *in response to* EV demand growth; registration data and rebate timing are mutually determined. Every coefficient is therefore associational at best absent an exogenous rebate shift.

---
## 5. Honest limitations

1. **Aggregate-only; no bid-level data.** Bids are counts, not bid distributions: 'bidders bid more' (bid amounts) is not directly observable; we test total bid *counts* and clearing prices.
2. **Total vs EV demand.** Cat A bid counts mix EV and non-EV bidders; total Cat A demand is dominated by non-EV cars, so any EV-specific bidding effect is diluted and likely unidentifiable at this aggregation.
3. **Endogeneity / simultaneity** (see §4): rebate policy responds to EV demand; no exogenous variance in the rebate level within 2022-01..2025-05 (flat $7,500 tail).
4. **Low power.** 4 effective treatment changes, 110 monthly observations; the headline p is HC1-only (HAC p≈0.104); wide CIs are expected.
5. **Event-window confounding.** Both event-study episodes have contaminated pre-trends; onsets are bounds; the 2022-01 episode is the rebate AND the threshold combined (bounded by design).
6. **Pre-2022 near-zero EV content.** Before 2022-07 there are no observed BEV registrations; pre-2022 months contribute to the full-window estimate but carry essentially no EV signal (required by the flat-tail identification design).
7. **Flat rebate level 2022-01..2025-05.** The dose never varies in the EV-relevant era, so the rebate coefficient is identified only from pre-2022 dose variation — the weakest part of the design.
8. **Null-coverage decay.** Registration counts are null on a rising share of rows (coverage 18%→33% of rows observed); `ev_reg` is a lower bound whose reliability decays over time.
9. **EV-label onset 2022-07.** The BEV label first appears 2022-07; the registration channel is right-truncated at the joint window end (2025-05).
10. **COE-only months after 2025-05.** 2025-06..2026-10 has COE but no registrations; used descriptively only (Jan-2026 cap cut).
11. **Plan's stylized rebate schedule vs verified real policy.** The 4-event dose path is a case-study construct; only the $7,500 anchor is a verified policy figure; real policy (EEAI 2021→2024→2026 caps, VES from 2018-01, CEVS 2013–2017, $0 ARF floor Jan 2022) differs — fully cited in `tables/rebate_timeline.csv`.
12. **Pandemic NA months.** 2020-04/05/06 (no COE exercises) are listwise-dropped, not imputed; N=110.
13. **Data-integrity correction.** The panel's `catA_bids_received` was corrupted to 0 for 19 months; all models use the corrected raw-reconstructed series (§2.5).

---
## 6. Charts (paths relative to the workspace root)

| Chart | File | Data table | What it shows |
|---|---|---|---|
| 1 | `charts/01_price_regime.png` | `tables/chart01_price_regime.csv` | nominal + real Cat A price with regime step markers, the Jan-2022 confounder marker, and the negative-control C/D/E vs A comparison (market-wide shock) |
| 2 | `charts/02_ev_demand.png` | `tables/chart02_ev_demand.csv` | EV registrations + EV share 2022-07..2025-05, with the coverage-rate lower-bound decay note |
| 3 | `charts/03_price_demand_dual.png` | `tables/chart03_price_demand_dual.csv` | dual-axis Cat A price vs CORRECTED Cat A bids received, 2022+ interpretation window shaded |
| 4 | `charts/04_scatter_fit_ci.png` | `tables/chart04_scatter_fit_ci.csv` | price-vs-demand scatter with bivariate fitted line + 95% CI band (association only) |
| 5 | `charts/05_event_study.png` | `tables/chart05_event_study.csv` | event-study coefficients with CIs for both episodes; pre-trend contamination annotated |
| 6 | `charts/06_mediation_diagram.png` | `tables/chart06_mediation_effects.csv` | mediation path (rebate → demand → price) with effect sizes; null mediation verdict |

---
## 7. Verification

`src/14_verify.py` re-confirmed from disk (see `tables/verification_report.csv`): fetched row counts == stated totals (a); analysis months map to real exercises + real registration rows, with the 3 pandemic NA months documented (b); every rebate step date carries a cited policy source (c); **69/69 report figures trace to saved tables** (d, `tables/report_figures_checklist.csv`); dose state = 4 changes, values [2000; 3000; 4000; 6000; 7500], flat 7500 from 2022-01 (e); no rebate-intensity exhibit estimated on a 2022+-only sample (f); price-equation demand regressor = corrected catA_bids_received, never ev_reg (g); mediated share on the full-window sample with 2022+ interpretation (h); data-flow/layering contract held (i).

*Generated by `src/15_report.py`. Every numeric claim above was read from a saved `tables/*.csv` at generation time; if any value is missing, the generator fails rather than fabricate.*