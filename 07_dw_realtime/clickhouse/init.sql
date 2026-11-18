-- Real-time analytical store (ClickHouse). Created automatically on the container's first start.
CREATE DATABASE IF NOT EXISTS wq_rt;

-- One row per validated replayed event (written by Spark every micro-batch)
CREATE TABLE IF NOT EXISTS wq_rt.events
(
    event_id         String,
    site_id          String,
    state            LowCardinality(String),
    region           LowCardinality(String),
    organization     LowCardinality(String),
    characteristic   LowCardinality(String),
    result_value     Float64,
    unit             LowCardinality(String),
    event_time       DateTime,                    -- when the sample was taken (historical, replayed)
    exceedance_flag  UInt8,                       -- derived in Spark from documented thresholds
    high_risk_flag   UInt8,
    alert_level      LowCardinality(String),      -- OK / EXCEEDANCE / HIGH RISK
    latitude         Nullable(Float64),
    longitude        Nullable(Float64),
    produced_at      DateTime64(3),               -- when the producer sent it (replay clock)
    processed_at     DateTime64(3),               -- when Spark processed it
    ingested_at      DateTime64(3) DEFAULT now64(3)
)
ENGINE = MergeTree
ORDER BY (characteristic, event_time, site_id);

-- Short event-time window aggregates (1 hour of sample time), updated by Spark (watermarked)
CREATE TABLE IF NOT EXISTS wq_rt.window_agg
(
    window_start    DateTime,
    window_end      DateTime,
    characteristic  LowCardinality(String),
    region          LowCardinality(String),
    results         UInt64,
    avg_value       Float64,
    max_value       Float64,
    min_value       Float64,
    exceedances     UInt64,
    high_risk       UInt64,
    written_at      DateTime64(3) DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(written_at)
ORDER BY (window_start, characteristic, region);

-- Events that failed validation (bad JSON, missing fields, impossible values)
CREATE TABLE IF NOT EXISTS wq_rt.rejected
(
    raw_value    String,
    reason       LowCardinality(String),
    ingested_at  DateTime64(3) DEFAULT now64(3)
)
ENGINE = MergeTree
ORDER BY ingested_at;
