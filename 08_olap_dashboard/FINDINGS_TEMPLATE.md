# 10 Business Findings (Step 9, brief §14)

Format for every finding: **Question → Analysis → Evidence → Interpretation → Recommendation.**

**How to complete this file:** run `python 08_olap_dashboard/olap_runner.py`, then replace every `[CONFIRM: …]` with the real number from the named CSV / Power BI visual. Numbers marked *EDA* come from Step 3 (`02_eda/`) and must still be re-checked against the warehouse (the warehouse holds the 3.77 M analysis-ready results, the EDA percentages were computed on the curated set, so small differences are expected; report the warehouse value).

> **Derived-field note:** "exceedance" and "high-risk" are **derived** by this project by comparing each result with a documented threshold (`dim_characteristic.exceedance_rule`, `high_risk_rule`, `threshold_source`). They are not regulatory violations and not fields in the WQP source. Several thresholds are project choices (marked "Project threshold"), so findings compare *relative* risk, not legal compliance.

---

### F1. Dissolved oxygen is the parameter that fails most often
- **Question:** Which parameter breaks its threshold most often?
- **Analysis:** Roll-up of all results to the characteristic level (ROLLUP over Parameter group → Characteristic).
- **Evidence:** `O16_rollup_parameter_hierarchy` (`tables/O16…csv`, `figures/O16…png`); Power BI page 1 bar chart. Measure: Exceedance Rate %. Dimension: Characteristic. Filters: none. EDA: DO 18.2 %, turbidity 10.5 %, pH 8.7 %, conductivity 6.1 %, temperature 3.4 %, nitrate 3.3 %. Warehouse: DO **[CONFIRM: % from O16]**, turbidity **[CONFIRM]**, nitrate **[CONFIRM]**.
- **Interpretation:** Low oxygen (< 5 mg/L) is the dominant water-quality problem in the data, roughly [CONFIRM: ratio] times the rate of the next parameter. Low DO harms fish and signals organic pollution or nutrient enrichment.
- **Recommendation:** Prioritise DO in monitoring and alerting (the real-time DW alert rules should treat DO < 2 mg/L as the top alert); investigate the causes at the worst sites (F4).

### F2. Dissolved-oxygen exceedances triple in summer
- **Question:** Does the DO problem depend on the season?
- **Analysis:** Slice on Characteristic = Dissolved oxygen, then Region × Season; Pivot of Parameter × Season.
- **Evidence:** `O05_slice_parameter`, `O09_pivot_parameter_season` (column `seasonal_range_pts`); Power BI page 3 seasonal chart. Measure: Exceedance Rate %. Dimensions: Season, Region. EDA: summer 25.9 % vs winter 7.7 %. Warehouse: summer **[CONFIRM]**, winter **[CONFIRM]**, range **[CONFIRM] points**.
- **Interpretation:** Warm water holds less oxygen and biological activity is higher in summer, so DO failures are strongly seasonal. DO is expected to have the largest seasonal range of all parameters [CONFIRM from O09].
- **Recommendation:** Increase DO sampling frequency (or continuous sensors) from June to August; schedule interventions (aeration, discharge limits) before summer.

### F3. The South has the highest overall exceedance rate
- **Question:** Which region has the worst water quality?
- **Analysis:** Roll-up Site → State → Region; Pivot Region × Parameter.
- **Evidence:** `O01_rollup_geography`, `O10_pivot_region_parameter`; Power BI page 2 regional chart. Measure: Exceedance Rate %. Dimension: Region. EDA: South 16.4 %. Warehouse: South **[CONFIRM]**, best region **[CONFIRM: name, %]**.
- **Interpretation:** The South's higher rate is driven mainly by [CONFIRM from O10: which parameter column is highest for South, expected DO]. Warmer climate links this to F2.
- **Recommendation:** Allocate more follow-up monitoring and remediation budget to Southern states; compare with the per-parameter pivot before deciding which parameter to target.

### F4. A small number of sites account for a large share of exceedances
- **Question:** Inside the worst state, are exceedances spread out or concentrated?
- **Analysis:** Drill-down Region → State → Site for the state with the highest rate (≥ 10,000 results).
- **Evidence:** `O04_drilldown_geography`; Power BI page 2 "Exceedances by site" table. Measures: Exceedances, Exceedance Rate %. Filter: sites with ≥ 30 results. Worst state: **[CONFIRM: state]**. Top 15 sites hold **[CONFIRM: sum of exceedances in O04 ÷ state total]** % of the state's exceedances.
- **Interpretation:** If a few sites dominate, the problem is local (point sources) rather than state-wide.
- **Recommendation:** Field inspection of the top sites listed in O04; treat them as "hot spots" in the real-time dashboard.

### F5. Summer and winter behave differently for chemical parameters in the South and West
- **Question:** In the two largest-risk regions, how different are summer and winter for chemical parameters (DO, pH)?
- **Analysis:** Dice: Region ∈ {South, West}, Season ∈ {Summer, Winter}, Parameter group = Chemical.
- **Evidence:** `O07_dice_region_season`. Measures: Exceedance Rate %, Median Value. South DO summer **[CONFIRM]** vs winter **[CONFIRM]**; West DO summer **[CONFIRM]** vs winter **[CONFIRM]**; pH change **[CONFIRM]**.
- **Interpretation:** [CONFIRM: does pH stay stable while DO swings? If yes:] pH is a chemistry property of the water body, while DO is driven by temperature, so seasonal policy should focus on DO.
- **Recommendation:** Use season-specific alert thresholds or reporting for DO only; keep pH monitoring at its current frequency.

### F6. Turbidity is the main physical problem, especially at surface-water sites
- **Question:** Which physical parameter fails most, and where?
- **Analysis:** Slice Year = 2025 by parameter; Dice Physical × Surface Water × Summer 2025 by state.
- **Evidence:** `O06_slice_time`, `O08_dice_physical_surface`; Power BI page 4 turbidity chart. EDA: turbidity 10.5 %. Warehouse 2025: **[CONFIRM]**. Top states: **[CONFIRM: names and %]**.
- **Interpretation:** High turbidity follows storms, erosion and run-off, so it concentrates in surface water.
- **Recommendation:** Pair turbidity monitoring with rainfall data; target erosion control in the listed states.

### F7. Nitrate exceedances are rare but concentrated
- **Question:** Is nitrate (the nutrient) a widespread problem?
- **Analysis:** Roll-up by Parameter group; Pivot Region × Parameter (nitrate column).
- **Evidence:** `O16_rollup_parameter_hierarchy` (Nutrient subtotal), `O10_pivot_region_parameter` (`nitrate_pct`); Power BI page 4 nutrients chart. EDA: nitrate 3.3 %. Warehouse **[CONFIRM]**; highest region **[CONFIRM]**.
- **Interpretation:** The 10 mg/L threshold is the drinking-water limit, so even a low rate matters where people drink groundwater. Check whether the highest rates are in groundwater sites [CONFIRM in Power BI: filter water_type].
- **Recommendation:** Focus nitrate testing on agricultural regions and groundwater wells rather than raising frequency everywhere.

### F8. The overall exceedance rate is stable between years but moves with the seasons
- **Question:** Is water quality getting better or worse over 2024–2025?
- **Analysis:** ROLLUP Year → Quarter → Month; Roll-up Month → Quarter.
- **Evidence:** `O15_rollup_time_hierarchy`, `O02_rollup_time`; Power BI page 3 monthly trend. 2024 total **[CONFIRM]** %, 2025 total **[CONFIRM]** %; highest quarter **[CONFIRM]**.
- **Interpretation:** [CONFIRM: if the yearly difference is under ~1 point:] Two years are too short to claim a trend; the within-year (seasonal) swing is larger than the year-to-year change. Note that December 2025 was loaded incrementally and has fewer results.
- **Recommendation:** Report seasonally-adjusted comparisons (same quarter year-on-year) rather than raw month-to-month changes.

### F9. Exceedance rates differ by data provider and sampling method
- **Question:** Does where/how the data was collected change the exceedance rate?
- **Analysis:** GROUPING SETS on Provider, Sample type and Equipment (one query, three summaries).
- **Evidence:** `O14_grouping_sets_org_method`. Measures: Results, Organizations, Exceedance Rate %. Provider rates: **[CONFIRM: NWIS %, STORET %]**; largest equipment-group gap **[CONFIRM]**.
- **Interpretation:** Differences can come from *where* each provider samples (site selection), not from data quality. This is a caution for comparisons across organisations.
- **Recommendation:** When comparing regions, also check that the provider mix is similar; keep provider as a slicer on the dashboard.

### F10. High-risk results are rare and concentrated in specific season–group cells
- **Question:** Where are the most severe (high-risk) results?
- **Analysis:** CUBE on Season × Parameter group (with all subtotals); CUBE Month × Region × Parameter group.
- **Evidence:** `O12_cube_season_group`, `O11_cube_month_region_group`; Power BI page 1 High-Risk card. Overall high-risk rate **[CONFIRM]** % (**[CONFIRM]** results); highest cell **[CONFIRM: season, group, %]**.
- **Interpretation:** High-risk results are a small fraction of exceedances, so most exceedances are moderate. The CUBE shows that [CONFIRM: e.g. Chemical in Summer] holds most of them.
- **Recommendation:** Use the high-risk flag (not the plain exceedance flag) to trigger urgent alerts, so that staff are not flooded with moderate cases.

---

## Summary table (fill after the run)

| # | Finding (one line) | Key number | Query / visual |
|---|---|---|---|
| F1 | DO fails most often | [CONFIRM] % | O16 / page 1 |
| F2 | DO summer ≫ winter | [CONFIRM] vs [CONFIRM] % | O05, O09 / page 3 |
| F3 | South is worst region | [CONFIRM] % | O01, O10 / page 2 |
| F4 | Few sites dominate the worst state | [CONFIRM] % share | O04 / page 2 |
| F5 | Chemical: DO seasonal, pH stable | [CONFIRM] | O07 |
| F6 | Turbidity: surface-water problem | [CONFIRM] % | O06, O08 / page 4 |
| F7 | Nitrate rare but concentrated | [CONFIRM] % | O10, O16 / page 4 |
| F8 | No clear year trend; seasonal swing | [CONFIRM] vs [CONFIRM] % | O15 / page 3 |
| F9 | Provider / method differences | [CONFIRM] | O14 |
| F10 | High-risk results rare, concentrated | [CONFIRM] % | O11, O12 / page 1 |
