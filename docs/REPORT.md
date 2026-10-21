# Do EV rebates drive more COE bidding demand? — Final report

> **Scope and policy basis.** The analysis covers 2016-01..2025-05 and uses the verified
> real Singapore rebate timeline (CEVS -> VES 2018 -> enhanced VES + EEAI 2021 -> $0 ARF floor
> 2022 -> EEAI cap cut 2024). All
> numbers below are copied verbatim from `tables/*.csv`; none are recomputed in this
> document. Figure-traceability: 112/112 report figures verified against
> their source tables (see `tables/report_figures_checklist.csv` and
> `tables/verification_report.csv`).

**Case:** Singapore COE / EV-rebate bidding analysis, joint window **2016-01 .. 2025-05** 
(113 months; 110 with COE exercises — 2020-04/05/06 suspended).

---
## 1. Executive summary

### Bottom line (honest, decided by the verified-policy evidence)

> **Full window (primary, 2016-01..2025-05):** the headline *rebate → price* link grades 
**not detectable**. The 2022-01 ARF-floor/threshold dummy is positive but not robust
(3,826 S$, p=0.0643 HC1). The 2022-01 negative-control test is **MIXED**: the two clean controls (C goods & buses, D motorcycles — the only categories with NO EV rebate) split (A +6.6% vs C -10.2%, D +16.3%; contaminated open category E +10.3% moves with the car channels) — so the jump is neither a clean market-wide signal nor a clean EV-specific one. **And** the 2022-01 effect is (i) not statistically robust (p=0.0643) and (ii) a TAX provision ($0 ARF floor) co-timed with the 97→110kW threshold change, not a rebate dose step — so it cannot be credited to the EV rebate.

> **2022+ EV era (2022-01..2025-05; NOW an estimation scope — 41 obs, dose 45000→40000 at 2024-01):**
the headline *rebate → price* link grades **supported** — the dose step
(+4,113 S$/1000 S$, p=4.52e-05; the 45000→40000 step dummy
-20,564 S$, p=4.52e-05) is statistically significant, and the
**2024-01 negative-control test does NOT falsify it** (clean controls C/D show a much smaller 2024-01
step: A -23.0% vs C -7.9%, D -7.4%; the contaminated channels B -36.8% and open E -36.1% move with the EV channels, as expected). **But** this is a 41-observation, two-dose-level estimate: it has LOW POWER,
wide CIs, is associational (not causal) given endogeneity, and the 2024-01 step coincides with
other EV-market activity. We report it as the one scope that *does* detect an EV-era
rebate→price association — with every caveat — NOT as proof of a causal magnitude.

> **Overall honest answer:** on the primary full-window scope the EV rebate does NOT produce a
> detectable, robust EV-specific price or bidding effect (the 2022-01 ARF-floor effect is not
> robust and is a tax/threshold confounder, not a rebate). On the newly-estimable 2022+ EV era, a
> rebate→price association IS detected (2024-01 dose step) and the 2024-01 negative control does
> not falsify it — but it is low-power (41 obs, 2 dose levels) and associational, not a causal
> magnitude. The answer is scope-dependent and none of it is a clean causal magnitude; all
> estimates are bounds (precise magnitude claims are forbidden at this power).

### Graded evidence per link — BOTH scopes (from `tables/evidence_grading.csv`)

| Causal link | Full-window estimate | Full-window grade | 2022+ EV-era estimate | 2022+ grade |
|---|---|---|---|---|
| **rebate → price (HEADLINE)** | 2022-01 ARF-floor dummy 3,826 S$ (p=0.0643); 2024-01 cap-cut -11,972 S$ (p=0.017); dose/1000 +599 S$/1000 S$ (p=7.94e-07) | **not detectable** | dose/1000 +4,113 S$/1000 S$ (p=4.52e-05); step -20,564 S$ (p=4.52e-05) | **supported** |
| rebate → demand (bidding) | 2024-01 step dummy +680 bids (p=0.00429; HAC p=0.0215); dose/1000 -11.7 (p=0.285) | **directionally consistent** | EV-era dose/1000 -111.5 (p=0.00541); step +557 (p=0.00541) | **not detectable** |
| rebate → demand (registration) | descriptive only (no coefficient; observed BEV window 2022-07..2025-05 is too short/censored) | **not detectable** | — | — |
| demand → price | lag-1 -0.027 S$/bid (p=0.976) | **not detectable** | lag-1 -2.710 S$/bid (p=0.508) | **not detectable** |
| rebate → demand → price (mediation) | indirect -9.0 (CI spans 0); mediated share -0.016 | **not detectable** | indirect -331.8 (CI spans 0); mediated share -0.115 | **not detectable** |

**Read:** the full-window headline 2022-01 effect is not robust (p=0.064) and is a tax/threshold
confounder, not a rebate step — the negative-control test is MIXED (clean controls split: D jumps
more, C the other way) but the effect cannot
be credited to the rebate. The bidding channel is directionally consistent at best (full window) and
null/opposite-sign (2022+); the demand→price mechanism and the mediated path are not detectable in
either scope. The 2022+ EV era is the one scope that *does* grade the headline rebate→price link as
**supported** — but at 41 observations / 2 dose levels it is low-power and associational, not a
causal magnitude.

---
## 2. Data

### 2.1 Data dictionary (three stores, from `data/raw/` → `data/processed/`)

| Store | Raw rows (stated total) | Contents | Processed artifact(s) |
|---|---|---|---|
| **COE results** | 1,985 | one row per (month, bidding_no, vehicle_class); categories A (small cars), B (large cars + high-power EVs), C (goods vehicles & buses), D (motorcycles), E (open — all vehicles except motorcycles); 2010-01..2026-10 | `coe_monthly.csv`, `coe_extension_2025_06_2026_10.csv` (COE-only) |
| **Registrations** | 51,669 | one row per (month, make, importer, fuel_type, vehicle_type, number); `number` null on a rising share ⇒ counts are LOWER BOUNDS; `Electric` (BEV) label first appears **2022-07** | `ev_registrations.csv` |
| **CPI All Items** | 207 series | monthly CPI, 2024 base, 2016-01..2026-08 | `cpi_deflated.csv` (real Cat A price = nominal ÷ (CPI/100)) |

Joint panel: `panel_joint.csv`, **113 rows** (one per month, 2016-01..2025-05): per-category COE columns (A–E) + EV columns + REAL-POLICY dummies (`reg_real_ves_201801`, `reg_real_evstack_202101`, `reg_arffloor_zero_202201`, `reg_eeai_cap15k_202401`) + era dummies (`ves_program`, `eeai_active`) + continuous `dose_nominal_sgd` + `in_interpretation_window`.

### 2.2 Verified policy timeline (from `tables/rebate_timeline.csv`)

| Effective month | Programme (verified real policy) | Size / dose | In joint window | In extension | Verification (cited) |
|---|---|---|---|---|---|
| 2018-01 | CEVS lapse; VES (Band A1 $25,000 off ARF) in force | dose 20000 (CEVS est.) -> 25000 (VES A1, verified) | Yes | No | VERIFIED: revised CEVS in force 1 Jul 2015 .. 31 Dec 2017, so CEVS lapsed 1 Jan 2018; VES came into effect 1 Jan 2018 (NEA joint release 12 Nov 2020 confirms). $5,000 minimum-ARF floor in force for EVs until 31 Dec 2021. |
| 2021-01 | Enhanced VES (A1 $25,000 maintained) + EEAI introduction (45% off ARF, capped $20,000) | dose 25000 -> 45000 (verified stack; $5,000 ARF floor -> part of nominal cap unusable) | Yes | No | VERIFIED: NEA/LTA joint release 12 Nov 2020 ('increased rebates under enhanced VES') confirms 1 Jan 2021 levels incl. A1 $25,000 and VES in effect from 1 Jan 2018; EEAI rate set read from LTA circulars via coewatch.sg. |
| 2022-01 | ARF floor lowered to $0 for electric cars (TAX PROVISION, not a rebate) + 97->110 kW Category A threshold change (confounder) | dose stays 45000 (caps unchanged); full caps now usable; confounder marker kept | Yes | No | VERIFIED: Straits Times Budget 2021 + coewatch minimum-ARF column: $0 ARF floor for EVs from 1 Jan 2022 (extended through 31 Dec 2027, LTA circular VRL/16/2025 of 8 Sep 2025). The 97->110 kW Cat A threshold change is an existing confounder, controlled by the threshold dummy in the price/bidding exhibits. |
| 2024-01 | EEAI cap cut $20,000 -> $15,000 (VES A1 $25,000 maintained per IEA statement) | dose 45000 -> 40000 (verified stack) | Yes | No | VERIFIED: EEAI cap $15,000 for 2024-01-01..2025-12-31 (coewatch.sg rate sets read from LTA circulars); VES rebates 'shall remain at S$25,000 for Band A1 cars' (IEA). This step is what makes the 2022+ window estimable (2 distinct doses inside it). |
| 2026-01 | EEAI cap cut to $7,500 + VES A1 cut to $22,500 (real policy) | dose 40000 -> 27500 (verified) | No | Yes (2025-06..2026-10, COE-only) | CORROBORATED: 'From 1 Jan 2026 to 31 Dec 2026, the rebate will be capped at $7,500' (LTA); VES 2026 A1 $22,500 (LTA); 2027: $20,000 (LTA, extension window only). Outside the joint window; lives in the COE-only extension. |
| 2027-01 | EEAI cessation (real policy) | EEAI rebate ceases; dose reverts to VES A1 $20,000 (2027, extension window) | No | No (beyond extension end 2026-10) | CORROBORATED: EEAI ceases 1 Jan 2027 (coewatch.sg glossary; LTA transitioning-to-EVs page). Documented for completeness; no data beyond 2026-10 in this pipeline. |
| 2013-01 | CEVS introduction (original scheme; revised CEVS from 1 Jul 2015) | original CEVS 2013-2015 Band A ~$20,000; revised CEVS 2015-2017 Band A1 (0-95 g/km, incl. electric) ~$30,000 | No (before 2016-01) | No | CORROBORATED: CEVS in force from 1 Jan 2013 (NCCS); revised CEVS 1 Jul 2015 .. 31 Dec 2017 (LTA emissions-charges page; motorist.sg ask-motorists/591). OUTSIDE the 2016-01 window -> contributes nothing to identification; the in-window CEVS dose (20000) is a CONSERVATIVE ESTIMATE. |

**Verified facts (all cited in the table):** CEVS in force 1 Jul 2015..31 Dec 2017 (revised Band A1 ~$30k; we use a CONSERVATIVE CEVS dose of $20,000 for 2016-01..2017-12 — an **ESTIMATE**: direction certain, magnitude approximate — as the pre-VES baseline). CEVS LAPSES 1 Jan 2018; VES (Band A1 $25,000 off ARF, $5,000 ARF floor until 31 Dec 2021) begins 1 Jan 2018. Enhanced VES 1 Jan 2021 (A1 $25,000 maintained) + EEAI (45% off ARF, capped $20,000, 2021-01..2023-12). $0 ARF floor for electric cars 1 Jan 2022..31 Dec 2023 (extended to 2027) — a **TAX PROVISION, not a rebate** (2022-01). EEAI cap cut to $15,000 2024-01, $7,500 2026-01, ceases 2027-01. The 97→110 kW Cat A threshold change 1 Jan 2022 is a kept confounder marker. 2026: VES A1 $22,500; 2027: VES A1 $20,000 (extension window only). Every row in the table carries its cited policy source.

### 2.3 The combined EV-rebate dose (column `dose_nominal_sgd`)

| Period | Dose (S$, nominal) | Composition | Status |
|---|---|---|---|
| 2016-01..2017-12 | 20,000 | CEVS (pre-VES baseline) | **ESTIMATE** (flagged) |
| 2018-01..2020-12 | 25,000 | VES Band A1 | verified |
| 2021-01..2023-12 | 45,000 | VES A1 25,000 + EEAI cap 20,000 (stacked; $5,000 ARF floor → part of the cap unusable) | verified |
| 2024-01..2025-05 | 40,000 | VES A1 25,000 + EEAI cap 15,000 (zero ARF floor → full caps usable) | verified |

**Distinct in-window dose values (4):** 20000; 25000; 40000; 45000. **Within the 2022-01..2025-05 window there are 2 values (40000; 45000) — so the 2022+ window is NOW a VALID ESTIMATION scope** (41 obs, 2 dose levels). Estimation windows: FULL 2016-01..2025-05 (primary); 2022+ 2022-01..2025-05 (also valid for headline exhibits).

### 2.4 Scope rule (full window PRIMARY + 2022+ EV era ALSO an estimation scope)

(a) The **full window 2016-01..2025-05** remains the PRIMARY estimation scope for the
CEVS→VES transition and overall level effects (110 monthly obs, 3 pandemic months dropped).
(b) The **2022+ EV era 2022-01..2025-05** is ALSO a VALID ESTIMATION scope (41 obs,
2 distinct dose levels 45000→40000 at 2024-01), because the dose varies within the window.
The headline price + bidding + mediation exhibits are estimated
on BOTH scopes and both are reported. (c) Collinearity: the continuous dose and the 4
real-policy dummies are near-exact linear transforms of one another — no spec mixes both;
each exhibit uses a dose-only OR dummy-only spec (documented per exhibit). Audited by
`src/05_scope_guard.py` (`tables/scope_audit.csv`) and re-verified by `src/14_verify.py`.

### 2.5 The `catA_bids_received` correction (data-integrity fix)

The raw datastore stores bid counts as comma-separated strings from mid-2023 on; the panel's
numeric coercion failed and summed NaNs to **0** for **19 months (2023-10..2025-05)** — the
entire EV-rebate era looked like zero demand. `src/00_data.py` reconstructs monthly sums from
`data/raw/coe_results_raw.csv` with comma-tolerant parsing → `catA_bids_received_clean`,
non-zero for all 110 COE months. **Every model uses the corrected series**, never the
corrupted panel column, never `ev_reg` (verified by `src/14_verify.py` check (g)).

### 2.6 Collapsing rules

- **COE:** mean of `premium` (clearing price) per (month, category); SUM of quota/bids per
  (month, category); `exercise_count` audit — per-category sums equal raw row counts exactly
  (220 per category in-window, `tables/verification_report.csv` check (b)).
- **Registrations:** per month, `ev_reg` = SUM of `number` over `fuel_type == 'Electric'`;
  `coverage_rate = rows_nonnull / rows_total` (decays 18%→33%) ⇒ `ev_reg` is a lower bound.
- **Pandemic months:** 2020-04/05/06 (no COE exercises) listwise-dropped, not imputed; N=110.

---
## 3. Results (BOTH scopes, per exhibit)

All coefficients: HC1 robust SEs unless noted; HAC (Newey-West lag-3) reported where
autocorrelation matters (DW 0.7886 — §3.8). Each exhibit states which
spec (dose-only or dummy-only) it uses, per the collinearity rule.

### 3.1 Price equation (rebate → price) — `tables/price_equation.csv`, `tables/price_equation_2022plus_robustness.csv`

**Full window (primary), DUMMY spec M1** (4 real-policy dummies, lag-1+lag-2 demand, quota,
trend, CPI; nominal, nobs=108):

| Term (real-policy) | Nominal coef (S$) | CI95 | p (HC1) | p (HAC) | Real coef (S$) | p (real) |
|---|---|---|---|---|---|---|
| **reg_real_ves_201801** (VES onset; 20000→25000) | -16,580.9 | [-22,047.8, -11,114.1] | 2.77e-09 | 0.000347 | — | — |
| **reg_real_evstack_202101** (enhanced VES+EEAI; 25000→45000) | +7,666.1 | [+4,200.5, +11,131.8] | 1.45e-05 | 0.00149 | — | — |
| reg_arffloor_zero_202201 ($0 ARF floor — TAX) | +3,825.6 | [-227.8, +7,879.1] | 0.0643 | 0.0692 | +5,327.6 | 0.0172 |
| **reg_eeai_cap15k_202401** (EEAI cap cut; 45000→40000) | -11,972.2 | [-21,799.5, -2,145.0] | 0.017 | 0.0086 | -12,056.2 | 0.0184 |
| demand_l1 (S$/bid) | -0.03 | [-1.80, +1.75] | 0.976 | 0.974 | — | — |
| demand_l2 (S$/bid) | +1.72 | [+0.14, +3.30] | 0.0327 | 0.0236 | — | — |

**Full window, DOSE spec M3** (continuous, per 1000 S$): **nominal +599 S$/1000 S$ (CI95 [361, 837], p=7.94e-07); HAC p=0.00065; real +730 S$/1000 S$ (p=1.24e-07).** No nominal↔real reversal.

**2022+ EV era (2022-01..2025-05, 41 obs, dose 45000→40000 at 2024-01 — estimable, 2 dose levels in window), DOSE spec E1** (dose + local trend + quota, nominal):

| Term | Coef (S$/1000 S$) | CI95 | p (HC1) | p (HAC) |
|---|---|---|---|---|
| **dose_1000 (45000→40000 step)** | +4,112.7 | [+2,136.7, +6,088.8] | **4.52e-05** | 5.14e-10 |
| reg_eeai_cap15k_202401 (step dummy, E2) | -20,563.6 | [-30,443.8, -10,683.4] | **4.52e-05** | — |
| demand_l1 (S$/bid, E3) | -2.71 | [-10.73, +5.31] | 0.508 | — |

**Honest read:** full-window, the 2022-01 ARF-floor dummy is positive but not robust (a tax/
threshold confounder, not a rebate step) and the 2024-01 cap-cut dummy is negative; the negative
control (§3.6) does not falsify the 2022-01 effect but it cannot be credited to the rebate. **On the
2022+ EV era, the dose step IS statistically
significant (+4,113 S$/1000 S$, p=4.52e-05) and survives the 2022+ negative
control — but at 41 obs / 2 dose levels it is LOW POWER, wide-CI, and associational (not a
causal magnitude). → **charts/01_price_regime.png**

### 3.2 Bidding channel (rebate → Cat A bidding demand) — `tables/demand_bidding_channel.csv`, `tables/crosslag_check.csv`

| Scope | Spec | Term | Coef (bids) | CI95 | p (HC1) | p (HAC) | Verdict |
|---|---|---|---|---|---|---|---|
| full window | dummy | 2024-01 cap-cut step | +679.7 | [+213.3, +1,146.1] | 0.00429 | 0.0215 | dir-consistent (full) |
| full window | dose | dose_1000 | -11.7 | [-33.1, +9.8] | 0.285 | 0.387 | null |
| cross-lag | dose | shifted −1/0/+1 mo | -7.7 / — / — | — | 0.479 / 0.285 / 0.479 | — | no timing pattern |
| **2022+ EV era** | dose | dose_1000 | -111.5 | [-190.0, -32.9] | 0.00541 | — | **opposite sign (negative)** |
| **2022+ EV era** | dummy | cap-cut step | +557.3 | [+164.6, +949.9] | 0.00541 | — | pos. but low power |

**Honest read:** the predicted direction for 'more bids placed' is coefficient > 0. Full-window,
the 2024-01 step is positive and HC1-significant (but the dose version is null). On the 2022+ EV
era the dose coefficient is **negative** (opposite the hypothesised direction) — the bidding
channel does NOT cleanly support 'the rebate drives more bidding demand'. Total Cat A demand is
dominated by non-EV cars; the EV signal is material only from ~2022. Grade: directionally
consistent (full) / not detectable (2022+).

### 3.3 Registration channel (rebate → EV registrations) — `tables/ev_registrations_descriptive.csv` (DESCRIPTIVE ONLY)

Observed BEV window 2022-07..2025-05 (35 months): mean 854 registrations/month (min 241, max 2,014); mean EV share 25.8% (max 43.0%); cumulative 29,899; coverage decays 18%→33%. The observed BEV window is too short and right-truncated (and `ev_reg` is a lower bound) to estimate a coefficient on this channel — **descriptive only**. Grade: not detectable.
Adoption kept rising after the Jan 2024 cap cut: mean 1,311 registrations/month in 2024-01..2025-05 vs 423 in 2022-07..2023-12 (EV share 35% vs 17%) — the first link of the chain (rebate → EV demand) does not track the rebate level.

### 3.4 Mediation (rebate → bidding demand → price) — `tables/mediation_effects.csv`

| Path | Full window (S$/1000 S$) | CI95 | 2022+ EV era | CI95 | n_obs (full / EV) |
|---|---|---|---|---|---|
| total (rebate → price) | +569.1 | [+339.7, +824.1] | +2882.0 | [+1048.5, +5335.5] | 109 / 41 |
| **indirect (rebate → demand → price)** | -9.0 | [-52.8, +28.6] | -331.8 | [-1034.7, +436.9] | 109 / 41 |
| **mediated share (indirect / total)** | -0.016 | [-0.099, +0.059] | -0.115 | [-0.374, +0.197] | 109 / 41 |

**Honest read (full window):** mediated share = **-0.016** with a CI spanning 0 (-0.099, +0.059) — the price effect is **NOT routed through Cat A bidding demand** (indirect -9.0, CI spans 0). 2-stage bootstrap (N=2000), full-window primary. **2022+ EV era:** mediated share **-0.115** (CI -0.374, +0.197), indirect -331.8 (CI spans 0) — again NOT routed through bidding; 41 obs → low power. Simultaneity flagged (rebate set in response to EV demand). Grade: not detectable (both scopes). → **charts/07_mediation_diagram.png**

### 3.5 Event study (4 verified-policy events) — `tables/event_study_coefficients.csv`, `tables/event_study_prechecks.csv`

| Event | Onset coef (S$) | CI95 | p | Pre-trend clean? | Note |
|---|---|---|---|---|---|
| 2018-01 CEVS lapse / VES onset (dose 20000 est→25000) | -17,068 | [-19,592, -14,543] | 4.43e-40 | False (joint leads Wald p=6.01e-47) | clean |
| 2021-01 enhanced VES + EEAI stack (dose 25000→45000) | +11,145 | [+8,142, +14,147] | 3.47e-13 | False (joint leads Wald p=1.03e-12) | clean |
| 2022-01 $0 ARF floor (TAX) + 97→110kW threshold (confounder) [BOUNDED] | +26,922 | [+18,997, +34,846] | 2.77e-11 | False (joint leads Wald p=3.68e-12) | clean |
| 2024-01 EEAI cap cut (dose 45000→40000; the EV-era step) | -39,017 | [-43,178, -34,856] | 1.93e-75 | False (joint leads Wald p=7.5e-87) | clean |

**Honest read:** all four onsets have **contaminated pre-trends** (significant non-zero leads —
a secular COE trend is present), so every onset is a **bound** relative to a moving pre-trend, not
a clean causal jump. The 2022-01 event is explicitly bounded (ARF floor + threshold combined,
co-timed). The 2026-01 cap cut is descriptive-only (COE-only extension). → **charts/08_event_study.png**

### 3.6 Negative controls (the decisive test) — `tables/negative_controls.csv`

**Full window, 2022-01 ARF-floor/threshold dummy** (clean controls C/D have NO EV rebate; B and E are EV-contaminated):

| Category | Role | coef (S$) | CI95 | p | 2022-01 % jump (coef/mean) |
|---|---|---|---|---|---|
| A | MAIN (low-power cars; EV-eligible) | +3,826 | [-228, +7,879] | 0.0643 | **+6.58%** |
| B | CONTAMINATED upper bound (high-power EVs fall here) | +10,926 | [+2,196, +19,656] | 0.0142 | **+15.58%** |
| C | **CLEAN negative control** (goods vehicles & buses; no EV rebate) | -4,957 | [-10,993, +1,079] | 0.107 | **-10.16%** |
| D | **CLEAN negative control** (motorcycles; no EV rebate) | +1,247 | [+201, +2,293] | 0.0195 | **+16.30%** |
| E | CONTAMINATED (open category — cars incl. EVs can bid) | +7,324 | [-1,783, +16,430] | 0.115 | **+10.26%** |

> **VERDICT (full window, 2022-01): FULL-WINDOW NEGATIVE-CONTROL MIXED: clean controls C (goods & buses) / D (motorcycles) 2022-01 % jumps = -10.2/16.3% vs A (EV-eligible) 6.6% (contaminated open category E: 10.3%, reported for reference). Clean controls SPLIT at 2022-01 (one shows a same-direction jump at least half of A's size, the other does not) -> the test is inconclusive on market-wideness, and it does NOT establish an EV-specific channel either: the 2022-01 change was the $0 ARF floor (a TAX provision) co-timed with the 97->110kW car threshold, the verified dose does NOT step at 2022-01, and A's own 2022-01 dummy is not statistically robust (p=0.064) -> the 2022-01 jump is not credited to the EV rebate.**

**2022+ EV era, 2024-01 EEAI cap-cut step** (the EV-rebate-specific variation):

| Category | 2024-01 % step (coef/mean) | coef (S$) | p |
|---|---|---|---|
| A (MAIN (EV-eligible)) | **-22.96%** | -20,204 | 6.3e-05 |
| B (CONTAMINATED (high-power EVs)) | **-36.84%** | -40,418 | 7e-07 |
| C (CLEAN (goods & buses; no EV rebate)) | **-7.93%** | -5,505 | 0.211 |
| D (CLEAN (motorcycles; no EV rebate)) | **-7.42%** | -754 | 0.117 |
| E (CONTAMINATED (open category; EVs can bid)) | **-36.07%** | -40,225 | 1.32e-07 |

> **VERDICT (2022+ EV era, 2024-01): 2022+ EV-ERA NEGATIVE-CONTROL PASS: clean controls C (goods & buses) / D (motorcycles) 2024-01 % steps = -7.9/-7.4% vs A (EV-eligible) -23.0% (EEAI cap 20k->15k; dose 45000->40000; contaminated open category E: -36.1%, reported for reference). Clean controls show a smaller/absent 2024-01 step -> the 2024-01 EV-era dose step is NOT falsified by the clean controls (an EV-rebate channel is consistent with the data; magnitude not identifiable at this power). The contaminated car channels (B, open E) move with the step, as expected.**

**Honest read (per scope, from the verdict rows):** full window — the 2022-01 ARF-floor/threshold dummy is positive in A, but the two CLEAN controls (C goods & buses, D motorcycles — the only two categories with no EV rebate) **split**: D shows a larger same-direction jump, C moves the other way (contaminated B and open E move with the car channels) — so the test is MIXED: the 2022-01 jump is neither a clean market-wide signal nor a clean EV-specific one, and (with p=0.064, not robust; a TAX provision co-timed with the threshold change) it is not credited to the rebate. 2022+ EV era — the 2024-01 step (the pure EV-rebate variation) is large across the EV-eligible car channels (A, B, open E) while the clean controls C/D move far less, so the 2024-01 EV-era step is **NOT falsified** — consistent with an EV-rebate channel (magnitude not identifiable at this power). → **charts/02_negative_control_2022.png** (2022-01, full window) and **charts/03_negative_control_2024.png** (2024-01, 2022+ EV era)

### 3.7 Diagnostics — `tables/diagnostics_stationarity_autocorr.csv`

- Stationarity: Cat A price (nominal) level ADF p=0.966 (**I(1)**); 1st-diff ADF p=4.86e-17 (stationary). Demand level ADF p=0.2 (I(1)). CPI level ADF p=0.767 (I(1)-ish).
- Residual autocorrelation: **Durbin-Watson = 0.7886** (primary price equation); Ljung-Box Q(1) = 38.5 (p=5.35e-10, significant); Breusch-Godfrey (nlags=3): F=20.0961. ⇒ **HAC (Newey-West) SEs used**; headline significance is HC1-only.
- **Power:** full window = 3 verified dose steps + 2 tax/confounder events, 110 monthly obs;
2022+ EV era = 2 dose levels, **41 obs** — LOW POWER in both scopes; wide CIs expected. Precise
magnitude claims are forbidden; all estimates are bounds, not precise causal magnitudes.

### 3.8 Sensitivity (full window, 2024-01 cap-cut dummy) — `tables/sensitivity_analysis.csv`

| Variant | Coef (S$) | CI95 | p | nobs |
|---|---|---|---|---|
| primary w/o catA_quota | -14,030 | [-23,097, -4,964] | 0.00242 | 108 |
| primary w/o trend | -14,549 | [-22,164, -6,934] | 0.000181 | 108 |
| primary w/o CPI | -10,806 | [-21,350, -262] | 0.0446 | 108 |
| demand def = bids_success | -9,364 | [-19,149, +422] | 0.0607 | 108 |
| lag order = lag-1 only | -10,733 | [-20,302, -1,163] | 0.0279 | 109 |
| contemporaneous demand | -10,684 | [-19,451, -1,918] | 0.0169 | 110 |
| price def = real | -12,056 | [-22,079, -2,034] | 0.0184 | 108 |

The 2024-01 coefficient is negative across every variant (robust in sign/magnitude) — the
negative-control verdict (§3.6) is the identification question, and it is scope-dependent:
not falsified on the 2022+ EV era, not isolating a clean EV effect on the full window.

---
## 4. Confounder discussion

- **Jan 2022 97→110kW Cat A threshold change (dominant confounder).** Co-timed with the $0 ARF
  floor; shifts clearing prices across categories (2022-01 % moves, from §3.6: A +6.6%, D +16.3%, E +10.3%, C -10.2%). It is a kept confounder marker,
  not a rebate dose; it complicates attributing the 2022-01 price move to the EV rebate alone.
- **Secular COE price trend.** Prices are I(1) and trending; event-study leads are significant
  and non-zero (contaminated pre-trends), so onsets are bounds, not clean jumps.
- **$0 ARF floor is a TAX provision, not a rebate.** While the $5,000 ARF floor applied (2021),
  part of the nominal EEAI cap was unusable; from 1 Jan 2022 the full cap is usable. Encoded as
  `reg_arffloor_zero_202201` and controlled separately from the rebate dose.
- **2026 PARF cut + 2026 supply trough.** The Jan-2026 EEAI cap cut sits in the COE-only
  extension alongside the 2026 PARF reform + a supply trough; descriptively confounded, NOT estimated.
- **CPI deflation.** Nominal vs real: no real-terms reversal that would change the interpretation.
- **Endogeneity / simultaneity.** The rebate was set *in response to* EV demand growth; every
  coefficient is associational at best absent an exogenous rebate shift.

---
## 5. Honest limitations

1. **CEVS dose is an ESTIMATE (2016-01..2017-12).** The pre-VES baseline of $20,000 is a
   conservative estimate (direction certain, magnitude approximate); the revised CEVS Band A1 was
   ~$30,000. All 2018+ dose levels are verified.
2. **Combined-dose stacking assumption.** The dose adds VES A1 + EEAI cap when both are in force
   (45000 / 40000). This is the *maximum combined rebate available*, a CAP, not a realized average
   rebate actually claimed; real per-vehicle rebates are lower.
3. **Dose is a CAP, not a realized average.** No vehicle-level redemption data; the coefficient is
   per $1,000 of *available* rebate capacity, not per $1,000 actually received.
4. **41-obs 2022+ EV-era power.** The newly-estimable 2022+ scope has only 41 observations and 2
   dose levels — LOW POWER, wide CIs; the 'supported' grade there is associational, not a causal magnitude.
5. **Aggregate-only; no bid-level data.** Bids are counts, not bid distributions; 'more bids
   placed' (bid amounts) is not directly observable.
6. **Total vs EV demand.** Cat A bid counts mix bids for EV and non-EV cars; total Cat A demand is
   dominated by non-EV cars, diluting any EV-specific bidding effect.
7. **Endogeneity / simultaneity** (§4): rebate policy responds to EV demand.
8. **Event-window confounding.** All 4 event-study episodes have contaminated pre-trends; onsets
   are bounds; 2022-01 is rebate/tax AND threshold combined (bounded).
9. **Null-coverage decay.** Registration counts are null on a rising share of rows (coverage
   18%→33%); `ev_reg` is a lower bound whose reliability decays.
10. **EV-label onset 2022-07 / right-truncation.** The registration channel is too short/censored
   for a coefficient; descriptive only.
11. **COE-only months after 2025-05.** 2025-06..2026-10 has COE but no registrations; descriptive
   only (Jan-2026 cap cut).
12. **Pandemic NA months.** 2020-04/05/06 listwise-dropped, not imputed; N=110.

*Dropped from the old limitations:* the 'plan schedule differs from real policy' limitation is no
*longer applicable — this run IS the verified policy.*

---
## 6. Charts (paths relative to the repo root)

| Chart | File | Data table | What it shows |
|---|---|---|---|
| 1 | `charts/01_price_regime.png` | `tables/chart01_price_regime.csv` | Cat A clearing price (nominal) with the verified policy markers (2018/2021/2024) + the 2022-01 tax/threshold confounder marker |
| 2 | `charts/02_negative_control_2022.png` | `tables/chart02_negative_control_2022.csv` | negative-control check: 2022-01 % price jump by category (full window) |
| 3 | `charts/03_negative_control_2024.png` | `tables/chart03_negative_control_2024.csv` | negative-control check: 2024-01 EEAI cap-cut step by category (2022+ EV era) |
| 4 | `charts/04_price_demand_dual.png` | `tables/chart04_price_demand_dual.csv` | Cat A COE price vs Cat A bids received, 2016-01..2025-05; 2022-01+ rebate era shaded, Jan 2024 cut marked |
| 5 | `charts/05_ev_demand.png` | `tables/chart05_ev_demand.csv` | EV registrations + EV share 2022-07..2025-05 (lower bound; some months have no count); Jan 2024 rebate cut marked |
| 6 | `charts/06_scatter_fit_ci.png` | `tables/chart06_scatter_fit_ci.csv` | price-vs-demand scatter with bivariate fitted line + 95% CI band (association only) |
| 7 | `charts/07_mediation_diagram.png` | `tables/chart07_mediation_effects.csv` | mediation chain (rebate → bidding demand → price) as a single diagram: per step, the prediction if the hypothesis were true vs the observed result (decade + 2022–25), and the not-via-bidding conclusion |
| 8 | `charts/08_event_study.png` | `tables/chart08_event_study.csv` | event-study coefficients with CIs for the 4 verified-policy events; pre-trend contamination annotated |

---
## 7. Verification

`src/14_verify.py` re-confirmed from disk (see `tables/verification_report.csv`): fetched row
counts == stated totals (a); analysis months map to real exercises + real registration rows, with
the 3 pandemic NA months documented (b); every VERIFIED rebate-step date (2018-01, 2021-01,
2022-01, 2024-01) + out-of-window rows (2013/2026/2027) carry a cited policy source (c);
**112/112 report figures trace to saved tables** (d,
`tables/report_figures_checklist.csv`); dose state = 3 verified changes, 4 distinct
doses [20000; 25000; 40000; 45000], and the 2022+ window has 2 distinct doses (40000; 45000) → a
valid estimation scope — the dose varies within the window (e); headline exhibits estimated on the full
window AND the 2022+ EV era (f); price-equation demand regressor = catA_bids_received,
never ev_reg (g); mediated share on the full-window sample with the 2022+ EV
era reported alongside (h); data-flow/layering contract held (i).

*Generated by `src/15_report.py`. Every numeric claim above was read from a saved
`tables/*.csv` at generation time; if any value is missing, the generator fails rather than
fabricate.*