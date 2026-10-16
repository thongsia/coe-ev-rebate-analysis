# STATS SUMMARY — one page (verified real policy)

**Question:** does the EV-rebate offer cause COE bidders to bid more?  
**Answer (honest, dual-scope):** full window (primary) = **not detectable** as a robust EV-specific
effect (the 2022-01 ARF-floor effect is not robust, p=0.064, and is a tax/threshold confounder; the
2022-01 negative-control test is MIXED — clean controls C/D split — and the effect is not credited to the rebate). 2022+ EV
era (estimable, 41 obs, dose 45000→40000) = **supported** for rebate→price (2024-01 dose step
significant; 2024-01 negative control not falsified) — but LOW POWER and associational, not a causal
magnitude. All other links: rebate→demand (bidding) not detectable / directionally consistent;
demand→price not detectable; mediation not detectable (both scopes).

**Scopes.** Primary estimation = **full window 2016-01..2025-05** (listwise N=110; 3 pandemic
months dropped; nobs≈108). **2022+ EV era 2022-01..2025-05 (41 obs, 2 dose levels) is ALSO a
valid estimation scope** for the headline price + bidding + mediation exhibits — the verified
dose varies 45000→40000 at 2024-01, so the window is estimable.

| Quantity | Value | Source |
|---|---|---|
| Dose (verified) | 4 distinct: 20000; 25000; 40000; 45000; 2022+ = 40000; 45000 | dose_summary.csv |
| FULL-WINDOW rebate→price (2022-01 ARF-floor dummy, nominal, HC1) | 3,826 S$ [-228, 7,879], p=0.0643 → **not detectable** | price_equation.csv |
| FULL-WINDOW rebate→price (2024-01 cap-cut dummy) | -11,972 S$ p=0.017 | price_equation.csv |
| FULL-WINDOW dose/1000 (nominal / real, M3, HC1) | +599 p=7.94e-07 / +730 p=1.24e-07 | price_equation.csv |
| **2022+ EV-ERA rebate→price (dose/1000, E1, nominal, HC1)** | **+4,113 S$/1000 S$ p=4.52e-05** (step dummy -20,564 S$ p=4.52e-05) → **supported** (LOW POWER, 41 obs) | price_equation_2022plus_robustness.csv |
| rebate→bidding (2024-01 step / dose, full-window, HC1) | +680 bids (p=0.00429; HAC p=0.0215) / -11.7 (p=0.285 → not detectable | demand_bidding_channel.csv |
| 2022+ EV-ERA rebate→bidding (dose/1000) | -111.5 bids (p=0.00541) → **opposite sign** | demand_bidding_channel.csv |
| demand→price (lag-1, nominal, full / EV) | -0.027 (p=0.976) / -2.710 (p=0.508) → n.s. both | price_equation*.csv |
| mediation (mediated share, full / EV) | -0.016 / -0.115 (both CI span 0) → NOT routed through bidding | mediation_effects.csv |
| event-study onsets (bounded; pre-trend contaminated) | 2018 -17,068 / 2021 +11,145 / 2022 +26,922 / 2024 -39,017 S$ | event_study_coefficients.csv |
| **NEGATIVE CONTROL 2022-01 % (full window)** | A +6.6% (EV-eligible) vs C -10.2% / D +16.3% / E +10.3% (no EV rebate) → **not falsified** (tax/threshold confounder) | negative_controls.csv |
| **NEGATIVE CONTROL 2024-01 % (2022+ EV era)** | A -23.0% (EV-eligible) vs C -7.9% / D -7.4% / E -36.1% → **not falsified** | negative_controls.csv |
| diagnostics | prices/demand I(1); DW 0.7886; LB Q(1) p=5.35e-10 → HAC SEs; low power (110 obs full / 41 obs EV) | diagnostics_stationarity_autocorr.csv |

**Grades (`evidence_grading.csv`), per scope:** rebate→price HEADLINE = full **not detectable** / 2022+ **supported**; rebate→demand (bidding) = full **directionally consistent** / 2022+ **not detectable**; rebate→demand (registration) = **not detectable** (descriptive); demand→price = full **not detectable** / 2022+ **not detectable**; mediation = full **not detectable** / 2022+ **not detectable**.

**Caveats:** CEVS dose (2016-17) is an ESTIMATE; dose is a stacked CAP not a realized average;
2022+ scope is 41 obs / 2 dose levels (low power); $0 ARF floor is a tax provision, not a rebate;
all estimates are bounds (precise magnitude claims forbidden).

*All values copied from `tables/*.csv`; see REPORT.md for the full derivation and
`tables/verification_report.csv` for the verification pass.*