-- Historical analytical queries on the batch warehouse.
-- Each block starts with "-- name: <id> | <question>" so etl_batch.py can run and time them.

-- name: Q1_monthly_trend | Q1: results, sites and exceedance rate per month
SELECT d.year_month, count(*) AS results, count(DISTINCT f.location_key) AS sites,
       round(100.0 * avg(f.exceedance_flag), 2) AS exceedance_pct
FROM dw.fact_water_quality_result f JOIN dw.dim_date d USING (date_key)
GROUP BY d.year_month ORDER BY d.year_month;

-- name: Q2_site_comparison | Q2: median value per parameter for sites with >= 30 results (spread across sites)
SELECT c.short_name, count(*) AS sites,
       round(percentile_cont(0.1) WITHIN GROUP (ORDER BY med)::numeric, 2) AS p10_site_median,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY med)::numeric, 2) AS median_site_median,
       round(percentile_cont(0.9) WITHIN GROUP (ORDER BY med)::numeric, 2) AS p90_site_median
FROM (SELECT location_key, characteristic_key, percentile_cont(0.5) WITHIN GROUP (ORDER BY result_value) AS med
      FROM dw.fact_water_quality_result GROUP BY 1, 2 HAVING count(*) >= 30) s
JOIN dw.dim_characteristic c USING (characteristic_key)
GROUP BY c.short_name ORDER BY c.short_name;

-- name: Q3_worst_sites | Q3: sites with the highest DO exceedance rate (>= 30 results)
SELECT l.site_id, l.state, count(*) AS results, round(100.0 * avg(f.exceedance_flag), 1) AS exceedance_pct,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY f.result_value)::numeric, 2) AS median_do
FROM dw.fact_water_quality_result f
JOIN dw.dim_monitoring_location l USING (location_key)
JOIN dw.dim_characteristic c USING (characteristic_key)
WHERE c.short_name = 'Dissolved oxygen'
GROUP BY l.site_id, l.state HAVING count(*) >= 30
ORDER BY exceedance_pct DESC, results DESC LIMIT 10;

-- name: Q4_seasonal | Q4: seasonal median and exceedance rate per parameter
SELECT c.short_name, d.season, count(*) AS results,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY f.result_value)::numeric, 2) AS median_value,
       round(100.0 * avg(f.exceedance_flag), 2) AS exceedance_pct
FROM dw.fact_water_quality_result f JOIN dw.dim_date d USING (date_key) JOIN dw.dim_characteristic c USING (characteristic_key)
GROUP BY c.short_name, d.season ORDER BY c.short_name, d.season;

-- name: Q6_exceedance_by_region | Q6: exceedances and high-risk results by region and parameter
SELECT l.region, c.short_name, count(*) AS results, sum(f.exceedance_flag) AS exceedances,
       round(100.0 * avg(f.exceedance_flag), 2) AS exceedance_pct, sum(f.high_risk_flag) AS high_risk
FROM dw.fact_water_quality_result f
JOIN dw.dim_monitoring_location l USING (location_key) JOIN dw.dim_characteristic c USING (characteristic_key)
GROUP BY l.region, c.short_name ORDER BY exceedance_pct DESC;

-- name: Q7_org_coverage | Q7: organization coverage (sites, parameters, months)
SELECT o.organization, count(*) AS results, count(DISTINCT f.location_key) AS sites,
       count(DISTINCT f.characteristic_key) AS parameters, count(DISTINCT d.year_month) AS months
FROM dw.fact_water_quality_result f
JOIN dw.dim_organization_method o USING (org_method_key) JOIN dw.dim_date d USING (date_key)
GROUP BY o.organization ORDER BY results DESC LIMIT 15;

-- name: Q8_water_type | Q8: median value by location (water) type and parameter
SELECT l.water_type, c.short_name, count(*) AS results,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY f.result_value)::numeric, 2) AS median_value
FROM dw.fact_water_quality_result f
JOIN dw.dim_monitoring_location l USING (location_key) JOIN dw.dim_characteristic c USING (characteristic_key)
WHERE l.water_type IN ('Surface Water', 'Groundwater', 'Ocean Water')
GROUP BY l.water_type, c.short_name ORDER BY c.short_name, l.water_type;

-- name: M1_monthly_fact_trend | Same monthly trend answered from the aggregate fact (constellation benefit)
SELECT d.year_month, sum(m.sample_count) AS results,
       round(100.0 * sum(m.exceedance_count) / sum(m.sample_count), 2) AS exceedance_pct
FROM dw.fact_site_monthly_water_quality m JOIN dw.dim_date d ON d.date_key = m.month_date_key
GROUP BY d.year_month ORDER BY d.year_month;
