-- =====================================================================
-- Water Quality DW: schema (fact constellation with star dimensions)
-- stg = staging area (raw landing of each load batch)
-- dw  = dimensional warehouse
-- =====================================================================
DROP SCHEMA IF EXISTS dw CASCADE;
DROP SCHEMA IF EXISTS stg CASCADE;
CREATE SCHEMA stg;
CREATE SCHEMA dw;

-- ---------- Staging: one row per curated, analysis-ready result ----------
CREATE UNLOGGED TABLE stg.wq_results (
    load_batch_id      INT,
    result_id          TEXT,
    site_id            TEXT,
    state              TEXT,
    region             TEXT,
    state_match        TEXT,
    latitude           DOUBLE PRECISION,
    longitude          DOUBLE PRECISION,
    water_type         TEXT,
    characteristic     TEXT,
    result_value       DOUBLE PRECISION,
    standard_unit      TEXT,
    sample_date        DATE,
    sample_hour        INT,
    time_band          TEXT,
    organization       TEXT,
    provider           TEXT,
    sample_type_group  TEXT,
    equipment_group    TEXT,
    result_status      TEXT,
    value_type         TEXT,
    result_band        TEXT,
    exceedance_flag    SMALLINT,
    high_risk_flag     SMALLINT,
    is_extreme_outlier BOOLEAN,
    is_provisional     BOOLEAN
);

-- ---------- ETL audit ----------
CREATE TABLE dw.etl_load_log (
    load_batch_id      INT PRIMARY KEY,
    load_mode          TEXT,          -- initial / incremental
    period_start       DATE,
    period_end         DATE,
    staged_rows        BIGINT,
    rejected_rows      BIGINT,
    new_locations      INT,
    new_org_methods    INT,
    fact_rows_inserted BIGINT,
    monthly_rows       BIGINT,
    started_at         TIMESTAMP,
    finished_at        TIMESTAMP,
    seconds            NUMERIC(10, 1)
);

-- ---------- Dimensions ----------
CREATE TABLE dw.dim_date (
    date_key     INT PRIMARY KEY,           -- YYYYMMDD
    full_date    DATE NOT NULL UNIQUE,
    day_of_month SMALLINT,
    day_name     TEXT,
    day_of_week  SMALLINT,                  -- 1 = Monday … 7 = Sunday
    is_weekend   BOOLEAN,
    week_of_year SMALLINT,
    month        SMALLINT,
    month_name   TEXT,
    year_month   TEXT,                      -- e.g. 2025-05
    quarter      SMALLINT,
    year         SMALLINT,
    season       TEXT
);

CREATE TABLE dw.dim_time (
    time_key  INT PRIMARY KEY,               -- hour 0–23; -1 = Not Reported
    hour      SMALLINT,
    time_band TEXT NOT NULL
);

CREATE TABLE dw.dim_monitoring_location (
    location_key SERIAL PRIMARY KEY,
    site_id      TEXT NOT NULL UNIQUE,       -- natural key from WQP
    state        TEXT,
    region       TEXT,
    latitude     DOUBLE PRECISION,
    longitude    DOUBLE PRECISION,
    water_type   TEXT,                       -- location-type proxy
    state_match  TEXT,
    first_load_batch INT
);

CREATE TABLE dw.dim_characteristic (
    characteristic_key  SERIAL PRIMARY KEY,
    characteristic_name TEXT NOT NULL UNIQUE,
    short_name          TEXT,
    parameter_group     TEXT,
    standard_unit       TEXT,
    exceedance_rule     TEXT,
    high_risk_rule      TEXT,
    threshold_source    TEXT
);

CREATE TABLE dw.dim_organization_method (
    org_method_key    SERIAL PRIMARY KEY,
    organization      TEXT NOT NULL,
    provider          TEXT,
    sample_type_group TEXT,
    equipment_group   TEXT,
    result_status     TEXT,
    value_type        TEXT,
    first_load_batch  INT,
    UNIQUE NULLS NOT DISTINCT (organization, provider, sample_type_group, equipment_group, result_status, value_type)
);

-- ---------- Fact 1: one row per measured result ----------
CREATE TABLE dw.fact_water_quality_result (
    result_key         BIGSERIAL PRIMARY KEY,
    result_id          TEXT NOT NULL,        -- degenerate dimension (WQP ResultIdentifier)
    date_key           INT NOT NULL,
    time_key           INT NOT NULL,
    location_key       INT NOT NULL,
    characteristic_key INT NOT NULL,
    org_method_key     INT NOT NULL,
    result_value       DOUBLE PRECISION NOT NULL,
    result_count       SMALLINT NOT NULL DEFAULT 1,
    exceedance_flag    SMALLINT NOT NULL,
    high_risk_flag     SMALLINT NOT NULL,
    result_band        TEXT,
    is_extreme_outlier BOOLEAN,
    is_provisional     BOOLEAN,
    load_batch_id      INT NOT NULL
);

-- ---------- Fact 2: site × characteristic × month ----------
CREATE TABLE dw.fact_site_monthly_water_quality (
    location_key       INT NOT NULL REFERENCES dw.dim_monitoring_location,
    characteristic_key INT NOT NULL REFERENCES dw.dim_characteristic,
    month_date_key     INT NOT NULL REFERENCES dw.dim_date,   -- role-playing: first day of month
    sample_count       INT,
    average_result     DOUBLE PRECISION,
    median_result      DOUBLE PRECISION,
    maximum_result     DOUBLE PRECISION,
    minimum_result     DOUBLE PRECISION,
    exceedance_count   INT,
    high_risk_count    INT,
    PRIMARY KEY (location_key, characteristic_key, month_date_key)
);
