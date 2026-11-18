-- Load one staged batch (:batch) into the warehouse.
-- Order: data-quality rules → new dimension members (lookup + insert) → fact → monthly fact.
-- Used by both the initial load and the incremental load. Psql-style :batch is replaced by etl_batch.py.

-- 1. Data-quality rules on the staged batch: reject rows that cannot become a valid fact
DROP TABLE IF EXISTS rejected;
CREATE TEMP TABLE rejected AS
SELECT * FROM stg.wq_results
WHERE load_batch_id = :batch
  AND (result_id IS NULL OR site_id IS NULL OR sample_date IS NULL OR result_value IS NULL
       OR characteristic NOT IN (SELECT characteristic_name FROM dw.dim_characteristic)
       OR sample_date NOT BETWEEN DATE '2024-01-01' AND DATE '2025-12-31');
DELETE FROM stg.wq_results s USING rejected r WHERE s.load_batch_id = :batch AND s.result_id = r.result_id;

-- 2a. New monitoring locations (existing sites are found by their natural key and kept)
INSERT INTO dw.dim_monitoring_location (site_id, state, region, latitude, longitude, water_type, state_match, first_load_batch)
SELECT site_id, max(state), max(region), avg(latitude), avg(longitude),
       coalesce(mode() WITHIN GROUP (ORDER BY water_type) FILTER (WHERE water_type <> 'Not Reported'), 'Not Reported'),
       max(state_match), :batch
FROM stg.wq_results WHERE load_batch_id = :batch
GROUP BY site_id
ON CONFLICT (site_id) DO NOTHING;

-- 2b. New organization/method combinations
INSERT INTO dw.dim_organization_method (organization, provider, sample_type_group, equipment_group, result_status, value_type, first_load_batch)
SELECT DISTINCT organization, provider, sample_type_group, equipment_group, result_status, value_type, :batch
FROM stg.wq_results WHERE load_batch_id = :batch
ON CONFLICT DO NOTHING;

-- 2c. Fresh statistics on the dimensions just extended, so the fact load uses fast hash joins
ANALYZE dw.dim_monitoring_location;
ANALYZE dw.dim_organization_method;
ANALYZE dw.fact_water_quality_result;

-- 3a. Safe re-runs: drop staged rows whose result is already in the warehouse (uses the unique result_id index)
DELETE FROM stg.wq_results s USING dw.fact_water_quality_result f
WHERE s.load_batch_id = :batch AND f.result_id = s.result_id;

-- 3b. Fact load: look up every surrogate key
INSERT INTO dw.fact_water_quality_result
       (result_id, date_key, time_key, location_key, characteristic_key, org_method_key, result_value, result_count,
        exceedance_flag, high_risk_flag, result_band, is_extreme_outlier, is_provisional, load_batch_id)
SELECT s.result_id, to_char(s.sample_date, 'YYYYMMDD')::INT, coalesce(s.sample_hour, -1), l.location_key, c.characteristic_key,
       o.org_method_key, s.result_value, 1, s.exceedance_flag, s.high_risk_flag, s.result_band, s.is_extreme_outlier,
       s.is_provisional, :batch
FROM stg.wq_results s
JOIN dw.dim_monitoring_location l ON l.site_id = s.site_id
JOIN dw.dim_characteristic c ON c.characteristic_name = s.characteristic
JOIN dw.dim_organization_method o
  ON o.organization = s.organization AND o.provider = s.provider
 AND o.sample_type_group = s.sample_type_group AND o.equipment_group = s.equipment_group
 AND o.result_status = s.result_status AND o.value_type = s.value_type   -- blanks were set to 'Not Reported' in staging, so plain = (fast hash join) is safe
WHERE s.load_batch_id = :batch;

-- 4. Monthly fact: rebuild only the months touched by this batch (built FROM the detail fact)
DELETE FROM dw.fact_site_monthly_water_quality
WHERE month_date_key IN (SELECT DISTINCT to_char(date_trunc('month', sample_date), 'YYYYMMDD')::INT
                         FROM stg.wq_results WHERE load_batch_id = :batch);
INSERT INTO dw.fact_site_monthly_water_quality
SELECT f.location_key, f.characteristic_key, to_char(date_trunc('month', d.full_date), 'YYYYMMDD')::INT,
       count(*), avg(f.result_value), percentile_cont(0.5) WITHIN GROUP (ORDER BY f.result_value),
       max(f.result_value), min(f.result_value), sum(f.exceedance_flag), sum(f.high_risk_flag)
FROM dw.fact_water_quality_result f JOIN dw.dim_date d ON d.date_key = f.date_key
WHERE to_char(date_trunc('month', d.full_date), 'YYYYMMDD')::INT IN
      (SELECT DISTINCT to_char(date_trunc('month', sample_date), 'YYYYMMDD')::INT FROM stg.wq_results WHERE load_batch_id = :batch)
GROUP BY 1, 2, 3;
