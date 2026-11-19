-- =====================================================================
-- Step 9: views for Power BI (schema bi)
--
-- Why views: Power BI imports these instead of the raw dw tables, so
--   * column names are friendly (they become field names in Power BI)
--   * audit / ETL-only columns are hidden
--   * the 4 dashboard pages get small, pre-aggregated helper views that load fast
-- The views hold no data of their own: they always show the current dw tables,
-- so after an incremental load a Power BI "Refresh" is enough.
--
-- Run:  python 08_olap_dashboard/olap_runner.py --views
--   or: psql -h 127.0.0.1 -p 5433 -U wq -d wq_dw -f 08_olap_dashboard/sql/02_powerbi_views.sql
--
-- DERIVED fields (computed by the project, NOT in the WQP source):
--   exceedance_flag, high_risk_flag, result_band, season, time_band, region, parameter_group, thresholds
-- No semicolons inside comments (the runner splits on them).
-- =====================================================================
DROP SCHEMA IF EXISTS bi CASCADE;
CREATE SCHEMA bi;

-- ---------------------------------------------------------------- star model (import these 7)

-- Fact: one row per measured result (3.77M rows). Keys + measures only.
CREATE VIEW bi.fact_result AS
SELECT f.result_key, f.result_id,
       f.date_key, f.time_key, f.location_key, f.characteristic_key, f.org_method_key,
       f.result_value, f.result_count,
       f.exceedance_flag,                      -- DERIVED: 1 if value breaks the exceedance rule
       f.high_risk_flag,                       -- DERIVED: 1 if value breaks the high-risk rule
       f.result_band,                          -- DERIVED: Very Low ... Very High
       f.is_provisional, f.is_extreme_outlier
FROM dw.fact_water_quality_result f;

-- Fact: site x characteristic x month snapshot (fast for trends and coverage).
CREATE VIEW bi.fact_site_month AS
SELECT m.location_key, m.characteristic_key,
       m.month_date_key AS date_key,           -- role-playing date: first day of the month
       m.sample_count, m.average_result, m.median_result, m.maximum_result, m.minimum_result,
       m.exceedance_count, m.high_risk_count
FROM dw.fact_site_monthly_water_quality m;

CREATE VIEW bi.dim_date AS
SELECT date_key, full_date, year, quarter, 'Q' || quarter AS quarter_label,
       year || '-Q' || quarter AS year_quarter,
       month, month_name, left(month_name, 3) AS month_short, year_month,
       day_of_month, day_name, day_of_week, is_weekend, week_of_year,
       season,                                 -- DERIVED from month (meteorological seasons)
       CASE season WHEN 'Winter' THEN 1 WHEN 'Spring' THEN 2 WHEN 'Summer' THEN 3 ELSE 4 END AS season_order
FROM dw.dim_date;

CREATE VIEW bi.dim_time AS
SELECT time_key, hour, time_band,
       CASE time_band WHEN 'Night' THEN 1 WHEN 'Morning' THEN 2 WHEN 'Afternoon' THEN 3
                      WHEN 'Evening' THEN 4 ELSE 5 END AS time_band_order
FROM dw.dim_time;

CREATE VIEW bi.dim_location AS
SELECT location_key, site_id, state,
       region,                                 -- DERIVED: US Census region from state
       latitude, longitude,
       water_type,                             -- location-type proxy
       coalesce(region, 'Unknown') || ' / ' || coalesce(state, 'Unknown') AS region_state
FROM dw.dim_monitoring_location;

CREATE VIEW bi.dim_characteristic AS
SELECT characteristic_key, characteristic_name, short_name, parameter_group, standard_unit,
       exceedance_rule, high_risk_rule, threshold_source,
       short_name || ' (' || standard_unit || ')' AS parameter_label
FROM dw.dim_characteristic;

CREATE VIEW bi.dim_org_method AS
SELECT org_method_key, organization, provider, sample_type_group, equipment_group, result_status, value_type
FROM dw.dim_organization_method;

-- ---------------------------------------------------------------- helper views (one per dashboard page)

-- Page 1 Executive: one-row KPI table (handy for cards and for checking the DAX measures).
CREATE VIEW bi.v_exec_kpis AS
SELECT count(*)                                    AS results,
       count(DISTINCT f.location_key)              AS sites,
       count(DISTINCT f.characteristic_key)        AS parameters,
       sum(f.exceedance_flag)                      AS exceedances,
       sum(f.high_risk_flag)                       AS high_risk_results,
       count(DISTINCT o.organization)              AS organizations,
       round(100.0 * avg(f.exceedance_flag), 2)    AS exceedance_pct,
       round(100.0 * avg(f.high_risk_flag), 2)     AS high_risk_pct,
       min(d.full_date)                            AS first_date,
       max(d.full_date)                            AS last_date
FROM dw.fact_water_quality_result f
JOIN dw.dim_organization_method o USING (org_method_key)
JOIN dw.dim_date d USING (date_key);

-- Page 2 Site & Geography: one row per site x parameter (map, site comparison, coverage).
CREATE VIEW bi.v_site_summary AS
SELECT l.location_key, l.site_id, l.state, l.region, l.water_type, l.latitude, l.longitude,
       c.short_name, c.parameter_group,
       sum(m.sample_count)                                             AS results,
       count(*)                                                        AS months_sampled,
       min(m.month_date_key)                                           AS first_month_key,
       max(m.month_date_key)                                           AS last_month_key,
       sum(m.exceedance_count)                                         AS exceedances,
       sum(m.high_risk_count)                                          AS high_risk_results,
       round(100.0 * sum(m.exceedance_count) / sum(m.sample_count), 2) AS exceedance_pct,
       round(sum(m.average_result * m.sample_count)::numeric / sum(m.sample_count), 3) AS mean_value
FROM dw.fact_site_monthly_water_quality m
JOIN dw.dim_monitoring_location l USING (location_key)
JOIN dw.dim_characteristic c USING (characteristic_key)
GROUP BY l.location_key, l.site_id, l.state, l.region, l.water_type, l.latitude, l.longitude, c.short_name, c.parameter_group;

-- Page 3 Temporal: region x parameter x month (trend, seasonality, sampling frequency).
CREATE VIEW bi.v_region_param_month AS
SELECT d.date_key AS month_date_key, d.year_month, d.year, d.quarter, d.month, d.season,
       l.region, c.short_name, c.parameter_group,
       sum(m.sample_count)                                             AS results,
       count(DISTINCT m.location_key)                                  AS sites,
       sum(m.exceedance_count)                                         AS exceedances,
       sum(m.high_risk_count)                                          AS high_risk_results,
       round(100.0 * sum(m.exceedance_count) / sum(m.sample_count), 2) AS exceedance_pct
FROM dw.fact_site_monthly_water_quality m
JOIN dw.dim_date d ON d.date_key = m.month_date_key
JOIN dw.dim_monitoring_location l USING (location_key)
JOIN dw.dim_characteristic c USING (characteristic_key)
GROUP BY d.date_key, d.year_month, d.year, d.quarter, d.month, d.season, l.region, c.short_name, c.parameter_group;

-- Page 3 Temporal: site x month heat map for the 30 most-sampled sites (a heat map of 49k sites is unreadable).
CREATE VIEW bi.v_site_month_heat AS
WITH top_sites AS (
    SELECT location_key FROM dw.fact_site_monthly_water_quality
    GROUP BY location_key ORDER BY sum(sample_count) DESC LIMIT 30
)
SELECT l.site_id, l.state, l.region, d.year_month,
       sum(m.sample_count)                                             AS results,
       round(100.0 * sum(m.exceedance_count) / sum(m.sample_count), 2) AS exceedance_pct
FROM dw.fact_site_monthly_water_quality m
JOIN top_sites t USING (location_key)
JOIN dw.dim_monitoring_location l USING (location_key)
JOIN dw.dim_date d ON d.date_key = m.month_date_key
GROUP BY l.site_id, l.state, l.region, d.year_month;

-- Page 4 Parameter analytics: distribution per parameter x month (box-plot style percentiles).
CREATE VIEW bi.v_parameter_distribution AS
SELECT c.short_name, c.standard_unit, d.year_month, d.season,
       count(*)                                                                          AS results,
       round(percentile_cont(0.10) WITHIN GROUP (ORDER BY f.result_value)::numeric, 3)  AS p10,
       round(percentile_cont(0.25) WITHIN GROUP (ORDER BY f.result_value)::numeric, 3)  AS p25,
       round(percentile_cont(0.50) WITHIN GROUP (ORDER BY f.result_value)::numeric, 3)  AS median_value,
       round(percentile_cont(0.75) WITHIN GROUP (ORDER BY f.result_value)::numeric, 3)  AS p75,
       round(percentile_cont(0.90) WITHIN GROUP (ORDER BY f.result_value)::numeric, 3)  AS p90,
       round(100.0 * avg(f.exceedance_flag), 2)                                          AS exceedance_pct
FROM dw.fact_water_quality_result f
JOIN dw.dim_characteristic c USING (characteristic_key)
JOIN dw.dim_date d USING (date_key)
GROUP BY c.short_name, c.standard_unit, d.year_month, d.season;

-- Page 4 Parameter analytics: cross-parameter view, one row per site x month with each
-- parameter's monthly median side by side (scatter DO vs temperature, conductivity vs pH ...).
-- A cell is empty when that parameter was not measured at that site in that month.
CREATE VIEW bi.v_cross_parameter AS
SELECT l.site_id, l.state, l.region, l.water_type, d.year_month, d.season,
       max(m.median_result) FILTER (WHERE c.short_name = 'Temperature')      AS temperature_c,
       max(m.median_result) FILTER (WHERE c.short_name = 'Dissolved oxygen') AS dissolved_oxygen_mgl,
       max(m.median_result) FILTER (WHERE c.short_name = 'pH')               AS ph,
       max(m.median_result) FILTER (WHERE c.short_name = 'Turbidity')        AS turbidity_ntu,
       max(m.median_result) FILTER (WHERE c.short_name = 'Conductivity')     AS conductivity_uscm,
       max(m.median_result) FILTER (WHERE c.short_name = 'Nitrate')          AS nitrate_mgl,
       count(*)                                                              AS parameters_measured
FROM dw.fact_site_monthly_water_quality m
JOIN dw.dim_monitoring_location l USING (location_key)
JOIN dw.dim_characteristic c USING (characteristic_key)
JOIN dw.dim_date d ON d.date_key = m.month_date_key
GROUP BY l.site_id, l.state, l.region, l.water_type, d.year_month, d.season
HAVING count(*) >= 2;
