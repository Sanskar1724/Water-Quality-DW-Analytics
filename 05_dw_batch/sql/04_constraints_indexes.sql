-- Created AFTER the initial bulk load (standard practice: loading is much faster without them).
-- From then on every incremental load is checked by these constraints automatically.

ALTER TABLE dw.fact_water_quality_result
  ADD CONSTRAINT fk_fact_date     FOREIGN KEY (date_key)           REFERENCES dw.dim_date,
  ADD CONSTRAINT fk_fact_time     FOREIGN KEY (time_key)           REFERENCES dw.dim_time,
  ADD CONSTRAINT fk_fact_location FOREIGN KEY (location_key)       REFERENCES dw.dim_monitoring_location,
  ADD CONSTRAINT fk_fact_char     FOREIGN KEY (characteristic_key) REFERENCES dw.dim_characteristic,
  ADD CONSTRAINT fk_fact_orgm     FOREIGN KEY (org_method_key)     REFERENCES dw.dim_organization_method,
  ADD CONSTRAINT chk_flags CHECK (exceedance_flag IN (0, 1) AND high_risk_flag IN (0, 1));

CREATE UNIQUE INDEX ux_fact_result_id   ON dw.fact_water_quality_result (result_id);
CREATE INDEX ix_fact_date               ON dw.fact_water_quality_result (date_key);
CREATE INDEX ix_fact_location           ON dw.fact_water_quality_result (location_key);
CREATE INDEX ix_fact_char_date          ON dw.fact_water_quality_result (characteristic_key, date_key);
CREATE INDEX ix_fact_org                ON dw.fact_water_quality_result (org_method_key);
CREATE INDEX ix_month_char_month        ON dw.fact_site_monthly_water_quality (characteristic_key, month_date_key);
CREATE INDEX ix_stg_batch               ON stg.wq_results (load_batch_id, result_id);
ANALYZE;
