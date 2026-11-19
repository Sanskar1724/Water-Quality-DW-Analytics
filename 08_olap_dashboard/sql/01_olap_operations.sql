-- =====================================================================
-- Step 9: OLAP operations on the batch warehouse (schema dw)
--
-- Hierarchies used (stored as columns in the star dimensions):
--   Time      : Year -> Quarter -> Month -> Day          (dw.dim_date)
--   Geography : Region -> State -> Site                  (dw.dim_monitoring_location)
--   Parameter : ParameterGroup -> Characteristic         (dw.dim_characteristic)
--
-- Measures:
--   results         = count of results (SUM of result_count)
--   exceedance_pct  = 100 x AVG(exceedance_flag)   -- flag is DERIVED in the ETL from project thresholds
--   high_risk_pct   = 100 x AVG(high_risk_flag)    -- flag is DERIVED in the ETL from project thresholds
--   median_value    = median of result_value (only inside ONE characteristic, units differ)
--
-- Queries on whole-site/month totals read the aggregate fact (fact_site_monthly_water_quality)
-- because it is ~100x smaller. Counts and rates are additive there (sum of counts / sum of samples).
-- Medians are NOT additive, so queries with medians read the detail fact.
--
-- Runner contract (olap_runner.py): each block starts with
--   -- name: <id> | <operation> | <business question>
-- and ends at the first semicolon. No semicolons inside comments or string literals.
-- =====================================================================


-- name: O01_rollup_geography | Roll-Up | Which regions have the highest exceedance rate when site-level results are rolled up to region level
-- Site -> State -> Region: the detail rows are summarised up to the top level of the Geography hierarchy.
SELECT l.region,
       count(DISTINCT l.state)                         AS states,
       count(DISTINCT m.location_key)                  AS sites,
       sum(m.sample_count)                             AS results,
       sum(m.exceedance_count)                         AS exceedances,
       round(100.0 * sum(m.exceedance_count) / sum(m.sample_count), 2) AS exceedance_pct,
       round(100.0 * sum(m.high_risk_count)  / sum(m.sample_count), 2) AS high_risk_pct
FROM dw.fact_site_monthly_water_quality m
JOIN dw.dim_monitoring_location l USING (location_key)
GROUP BY l.region
ORDER BY exceedance_pct DESC;


-- name: O02_rollup_time | Roll-Up | How does the exceedance rate change when monthly results are rolled up to quarters and years
-- Month -> Quarter -> Year: the monthly snapshot is summarised to Year x Quarter.
SELECT d.year,
       'Q' || d.quarter                                AS quarter,
       d.year || '-Q' || d.quarter                     AS year_quarter,
       sum(m.sample_count)                             AS results,
       count(DISTINCT m.location_key)                  AS sites,
       round(100.0 * sum(m.exceedance_count) / sum(m.sample_count), 2) AS exceedance_pct,
       round(100.0 * sum(m.high_risk_count)  / sum(m.sample_count), 2) AS high_risk_pct
FROM dw.fact_site_monthly_water_quality m
JOIN dw.dim_date d ON d.date_key = m.month_date_key
GROUP BY d.year, d.quarter
ORDER BY d.year, d.quarter;


-- name: O03_drilldown_time | Drill-Down | Within each year and quarter, which months drive the dissolved-oxygen exceedances
-- Year -> Quarter -> Month for one parameter (DO), using the detail fact so the median is exact.
SELECT d.year, d.quarter, d.month, d.year_month, d.month_name,
       count(*)                                        AS results,
       round(100.0 * avg(f.exceedance_flag), 2)        AS exceedance_pct,
       round(100.0 * avg(f.high_risk_flag), 2)         AS high_risk_pct,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY f.result_value)::numeric, 2) AS median_value
FROM dw.fact_water_quality_result f
JOIN dw.dim_date d USING (date_key)
JOIN dw.dim_characteristic c USING (characteristic_key)
WHERE c.short_name = 'Dissolved oxygen'
GROUP BY d.year, d.quarter, d.month, d.year_month, d.month_name
ORDER BY d.year, d.quarter, d.month;


-- name: O04_drilldown_geography | Drill-Down | Inside the worst state, which individual sites cause most exceedances
-- Region -> State -> Site: first find the state with the highest exceedance rate (at least 10000 results),
-- then drill down to its sites with at least 30 results.
WITH state_rate AS (
    SELECT l.region, l.state, sum(m.sample_count) AS results,
           sum(m.exceedance_count)::numeric / sum(m.sample_count) AS rate
    FROM dw.fact_site_monthly_water_quality m
    JOIN dw.dim_monitoring_location l USING (location_key)
    WHERE l.state IS NOT NULL
    GROUP BY l.region, l.state
    HAVING sum(m.sample_count) >= 10000
), worst AS (
    SELECT region, state FROM state_rate ORDER BY rate DESC LIMIT 1
)
SELECT l.region, l.state, l.site_id, l.water_type,
       sum(m.sample_count)                             AS results,
       sum(m.exceedance_count)                         AS exceedances,
       round(100.0 * sum(m.exceedance_count) / sum(m.sample_count), 2) AS exceedance_pct,
       round(100.0 * sum(m.high_risk_count)  / sum(m.sample_count), 2) AS high_risk_pct
FROM dw.fact_site_monthly_water_quality m
JOIN dw.dim_monitoring_location l USING (location_key)
JOIN worst w ON w.region = l.region AND w.state = l.state
GROUP BY l.region, l.state, l.site_id, l.water_type
HAVING sum(m.sample_count) >= 30
ORDER BY exceedances DESC, exceedance_pct DESC
LIMIT 15;


-- name: O05_slice_parameter | Slice | For dissolved oxygen only, how does the exceedance rate vary by region and season
-- Slice: one dimension is fixed to a single value (Characteristic = Dissolved oxygen), leaving a Region x Season sub-cube.
SELECT l.region, d.season,
       count(*)                                        AS results,
       round(100.0 * avg(f.exceedance_flag), 2)        AS exceedance_pct,
       round(100.0 * avg(f.high_risk_flag), 2)         AS high_risk_pct,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY f.result_value)::numeric, 2) AS median_value
FROM dw.fact_water_quality_result f
JOIN dw.dim_date d USING (date_key)
JOIN dw.dim_monitoring_location l USING (location_key)
JOIN dw.dim_characteristic c USING (characteristic_key)
WHERE c.short_name = 'Dissolved oxygen'
GROUP BY l.region, d.season
ORDER BY l.region, d.season;


-- name: O06_slice_time | Slice | In the year 2025 only, which parameters exceed their thresholds most often
-- Slice: Time is fixed to Year = 2025, leaving the Parameter dimension.
SELECT c.parameter_group, c.short_name, c.standard_unit,
       count(*)                                        AS results,
       count(DISTINCT f.location_key)                  AS sites,
       round(100.0 * avg(f.exceedance_flag), 2)        AS exceedance_pct,
       round(100.0 * avg(f.high_risk_flag), 2)         AS high_risk_pct,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY f.result_value)::numeric, 2) AS median_value
FROM dw.fact_water_quality_result f
JOIN dw.dim_date d USING (date_key)
JOIN dw.dim_characteristic c USING (characteristic_key)
WHERE d.year = 2025
GROUP BY c.parameter_group, c.short_name, c.standard_unit
ORDER BY exceedance_pct DESC;


-- name: O07_dice_region_season | Dice | In the South and West, for Chemical parameters, how different are summer and winter exceedance rates
-- Dice: several dimensions are filtered at once (Region in South/West, Season in Summer/Winter, ParameterGroup = Chemical).
SELECT l.region, d.season, c.short_name,
       count(*)                                        AS results,
       round(100.0 * avg(f.exceedance_flag), 2)        AS exceedance_pct,
       round(100.0 * avg(f.high_risk_flag), 2)         AS high_risk_pct,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY f.result_value)::numeric, 2) AS median_value
FROM dw.fact_water_quality_result f
JOIN dw.dim_date d USING (date_key)
JOIN dw.dim_monitoring_location l USING (location_key)
JOIN dw.dim_characteristic c USING (characteristic_key)
WHERE l.region IN ('South', 'West')
  AND d.season IN ('Summer', 'Winter')
  AND c.parameter_group = 'Chemical'
GROUP BY l.region, d.season, c.short_name
ORDER BY c.short_name, l.region, d.season;


-- name: O08_dice_physical_surface | Dice | For Physical parameters at surface-water sites during summer 2025, which states have the highest exceedance rate
-- Dice: ParameterGroup = Physical, water_type = Surface Water, Year = 2025, Season = Summer, states with at least 500 results.
SELECT l.region, l.state,
       count(*)                                        AS results,
       count(DISTINCT f.location_key)                  AS sites,
       round(100.0 * avg(f.exceedance_flag), 2)        AS exceedance_pct,
       round(100.0 * avg(f.high_risk_flag), 2)         AS high_risk_pct
FROM dw.fact_water_quality_result f
JOIN dw.dim_date d USING (date_key)
JOIN dw.dim_monitoring_location l USING (location_key)
JOIN dw.dim_characteristic c USING (characteristic_key)
WHERE c.parameter_group = 'Physical'
  AND l.water_type = 'Surface Water'
  AND d.year = 2025
  AND d.season = 'Summer'
GROUP BY l.region, l.state
HAVING count(*) >= 500
ORDER BY exceedance_pct DESC
LIMIT 20;


-- name: O09_pivot_parameter_season | Pivot | Shown as a parameter-by-season grid, which parameter is most seasonal
-- Pivot (rotate): seasons move from rows to columns using conditional aggregation (FILTER).
-- seasonal_range_pts = highest season rate minus lowest season rate (percentage points).
SELECT short_name, winter_pct, spring_pct, summer_pct, autumn_pct, all_seasons_pct,
       greatest(winter_pct, spring_pct, summer_pct, autumn_pct)
         - least(winter_pct, spring_pct, summer_pct, autumn_pct)                  AS seasonal_range_pts
FROM (SELECT c.short_name,
             round(100.0 * avg(f.exceedance_flag) FILTER (WHERE d.season = 'Winter'), 2) AS winter_pct,
             round(100.0 * avg(f.exceedance_flag) FILTER (WHERE d.season = 'Spring'), 2) AS spring_pct,
             round(100.0 * avg(f.exceedance_flag) FILTER (WHERE d.season = 'Summer'), 2) AS summer_pct,
             round(100.0 * avg(f.exceedance_flag) FILTER (WHERE d.season = 'Autumn'), 2) AS autumn_pct,
             round(100.0 * avg(f.exceedance_flag), 2)                                    AS all_seasons_pct
      FROM dw.fact_water_quality_result f
      JOIN dw.dim_date d USING (date_key)
      JOIN dw.dim_characteristic c USING (characteristic_key)
      GROUP BY c.short_name) p
ORDER BY seasonal_range_pts DESC;


-- name: O10_pivot_region_parameter | Pivot | Shown as a region-by-parameter grid, where is each parameter worst
-- Pivot: parameters become columns (exceedance %), regions are rows. Read from the aggregate fact.
SELECT l.region,
       round(100.0 * sum(m.exceedance_count) FILTER (WHERE c.short_name = 'Dissolved oxygen') / nullif(sum(m.sample_count) FILTER (WHERE c.short_name = 'Dissolved oxygen'), 0), 2) AS dissolved_oxygen_pct,
       round(100.0 * sum(m.exceedance_count) FILTER (WHERE c.short_name = 'Turbidity')        / nullif(sum(m.sample_count) FILTER (WHERE c.short_name = 'Turbidity'), 0), 2)        AS turbidity_pct,
       round(100.0 * sum(m.exceedance_count) FILTER (WHERE c.short_name = 'pH')               / nullif(sum(m.sample_count) FILTER (WHERE c.short_name = 'pH'), 0), 2)               AS ph_pct,
       round(100.0 * sum(m.exceedance_count) FILTER (WHERE c.short_name = 'Conductivity')     / nullif(sum(m.sample_count) FILTER (WHERE c.short_name = 'Conductivity'), 0), 2)     AS conductivity_pct,
       round(100.0 * sum(m.exceedance_count) FILTER (WHERE c.short_name = 'Temperature')      / nullif(sum(m.sample_count) FILTER (WHERE c.short_name = 'Temperature'), 0), 2)      AS temperature_pct,
       round(100.0 * sum(m.exceedance_count) FILTER (WHERE c.short_name = 'Nitrate')          / nullif(sum(m.sample_count) FILTER (WHERE c.short_name = 'Nitrate'), 0), 2)          AS nitrate_pct,
       round(100.0 * sum(m.exceedance_count) / sum(m.sample_count), 2) AS all_parameters_pct
FROM dw.fact_site_monthly_water_quality m
JOIN dw.dim_monitoring_location l USING (location_key)
JOIN dw.dim_characteristic c USING (characteristic_key)
GROUP BY l.region
ORDER BY all_parameters_pct DESC;


-- name: O11_cube_month_region_group | CUBE | Across Month x Region x ParameterGroup, what are the exceedance rates for every combination and every subtotal
-- CUBE(a, b, c) returns all 2^3 = 8 groupings in one pass: detail, every pair, every single dimension and the grand total.
-- GROUPING() returns 1 when the column is rolled up, so the label becomes 'ALL'.
SELECT CASE WHEN GROUPING(d.year_month) = 1 THEN 'ALL' ELSE d.year_month END          AS year_month,
       CASE WHEN GROUPING(l.region) = 1 THEN 'ALL' ELSE l.region END                  AS region,
       CASE WHEN GROUPING(c.parameter_group) = 1 THEN 'ALL' ELSE c.parameter_group END AS parameter_group,
       GROUPING(d.year_month, l.region, c.parameter_group)                            AS grouping_id,
       sum(m.sample_count)                                                            AS results,
       sum(m.exceedance_count)                                                        AS exceedances,
       round(100.0 * sum(m.exceedance_count) / sum(m.sample_count), 2)                AS exceedance_pct,
       round(100.0 * sum(m.high_risk_count)  / sum(m.sample_count), 2)                AS high_risk_pct
FROM dw.fact_site_monthly_water_quality m
JOIN dw.dim_date d ON d.date_key = m.month_date_key
JOIN dw.dim_monitoring_location l USING (location_key)
JOIN dw.dim_characteristic c USING (characteristic_key)
GROUP BY CUBE (d.year_month, l.region, c.parameter_group)
ORDER BY grouping_id, year_month, region, parameter_group;


-- name: O12_cube_season_group | CUBE | Across Season x ParameterGroup, including subtotals, when and where are high-risk results concentrated
-- Smaller CUBE read from the detail fact. High-risk results are rare, so the rate keeps 3 decimals.
SELECT CASE WHEN GROUPING(d.season) = 1 THEN 'ALL' ELSE d.season END                  AS season,
       CASE WHEN GROUPING(c.parameter_group) = 1 THEN 'ALL' ELSE c.parameter_group END AS parameter_group,
       GROUPING(d.season, c.parameter_group)                                          AS grouping_id,
       count(*)                                                                       AS results,
       round(100.0 * avg(f.exceedance_flag), 2)                                       AS exceedance_pct,
       round(100.0 * avg(f.high_risk_flag), 3)                                        AS high_risk_pct,
       sum(f.high_risk_flag)                                                          AS high_risk_results
FROM dw.fact_water_quality_result f
JOIN dw.dim_date d USING (date_key)
JOIN dw.dim_characteristic c USING (characteristic_key)
GROUP BY CUBE (d.season, c.parameter_group)
ORDER BY grouping_id, season, parameter_group;


-- name: O13_grouping_sets_summary | GROUPING SETS | In one scan, what are the exceedance rates by region, by parameter, by season and overall
-- GROUPING SETS lists exactly the groupings wanted (here 4), instead of all combinations as CUBE does.
SELECT CASE WHEN GROUPING(l.region) = 0 THEN 'Region'
            WHEN GROUPING(c.short_name) = 0 THEN 'Parameter'
            WHEN GROUPING(d.season) = 0 THEN 'Season'
            ELSE 'Overall' END                                        AS dimension,
       coalesce(l.region, c.short_name, d.season, 'ALL')              AS member,
       count(*)                                                       AS results,
       count(DISTINCT f.location_key)                                 AS sites,
       round(100.0 * avg(f.exceedance_flag), 2)                       AS exceedance_pct,
       round(100.0 * avg(f.high_risk_flag), 2)                        AS high_risk_pct
FROM dw.fact_water_quality_result f
JOIN dw.dim_date d USING (date_key)
JOIN dw.dim_monitoring_location l USING (location_key)
JOIN dw.dim_characteristic c USING (characteristic_key)
GROUP BY GROUPING SETS ((l.region), (c.short_name), (d.season), ())
ORDER BY dimension, exceedance_pct DESC;


-- name: O14_grouping_sets_org_method | GROUPING SETS | Does the exceedance rate depend on the data provider, the sample type or the equipment used
-- GROUPING SETS on the organisation/method (junk) dimension: three separate one-dimension summaries in one query.
SELECT CASE WHEN GROUPING(o.provider) = 0 THEN 'Provider'
            WHEN GROUPING(o.sample_type_group) = 0 THEN 'Sample type'
            ELSE 'Equipment' END                                      AS dimension,
       coalesce(o.provider, o.sample_type_group, o.equipment_group, 'Not recorded') AS member,
       count(*)                                                       AS results,
       count(DISTINCT o.organization)                                 AS organizations,
       round(100.0 * avg(f.exceedance_flag), 2)                       AS exceedance_pct,
       round(100.0 * avg(f.high_risk_flag), 2)                        AS high_risk_pct
FROM dw.fact_water_quality_result f
JOIN dw.dim_organization_method o USING (org_method_key)
GROUP BY GROUPING SETS ((o.provider), (o.sample_type_group), (o.equipment_group))
ORDER BY dimension, results DESC;


-- name: O15_rollup_time_hierarchy | ROLLUP | What are the results and exceedance rate per month, with quarter, year and grand-total subtotals
-- ROLLUP(year, quarter, month) follows the Time hierarchy: month rows, quarter subtotals, year subtotals, grand total.
SELECT CASE WHEN GROUPING(d.year) = 1 THEN 'ALL' ELSE d.year::text END        AS year,
       CASE WHEN GROUPING(d.quarter) = 1 THEN 'ALL' ELSE 'Q' || d.quarter END  AS quarter,
       CASE WHEN GROUPING(d.month) = 1 THEN 'ALL' ELSE lpad(d.month::text, 2, '0') END AS month,
       CASE WHEN GROUPING(d.year) = 1 THEN 'Grand total'
            WHEN GROUPING(d.quarter) = 1 THEN 'Year subtotal'
            WHEN GROUPING(d.month) = 1 THEN 'Quarter subtotal'
            ELSE 'Month' END                                                  AS level,
       sum(m.sample_count)                                                    AS results,
       count(DISTINCT m.location_key)                                         AS sites,
       round(100.0 * sum(m.exceedance_count) / sum(m.sample_count), 2)        AS exceedance_pct
FROM dw.fact_site_monthly_water_quality m
JOIN dw.dim_date d ON d.date_key = m.month_date_key
GROUP BY ROLLUP (d.year, d.quarter, d.month)
ORDER BY d.year NULLS LAST, d.quarter NULLS LAST, d.month NULLS LAST;


-- name: O16_rollup_parameter_hierarchy | ROLLUP | Per characteristic, with parameter-group subtotals and a grand total, how often are thresholds exceeded
-- ROLLUP(parameter_group, characteristic) follows the Parameter hierarchy.
SELECT CASE WHEN GROUPING(c.parameter_group) = 1 THEN 'ALL' ELSE c.parameter_group END AS parameter_group,
       CASE WHEN GROUPING(c.short_name) = 1 THEN 'ALL' ELSE c.short_name END          AS characteristic,
       CASE WHEN GROUPING(c.parameter_group) = 1 THEN 'Grand total'
            WHEN GROUPING(c.short_name) = 1 THEN 'Group subtotal'
            ELSE 'Characteristic' END                                                 AS level,
       sum(m.sample_count)                                                            AS results,
       count(DISTINCT m.location_key)                                                 AS sites,
       sum(m.exceedance_count)                                                        AS exceedances,
       round(100.0 * sum(m.exceedance_count) / sum(m.sample_count), 2)                AS exceedance_pct,
       round(100.0 * sum(m.high_risk_count)  / sum(m.sample_count), 2)                AS high_risk_pct
FROM dw.fact_site_monthly_water_quality m
JOIN dw.dim_characteristic c USING (characteristic_key)
GROUP BY ROLLUP (c.parameter_group, c.short_name)
ORDER BY c.parameter_group NULLS LAST, c.short_name NULLS LAST;
