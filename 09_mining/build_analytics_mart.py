"""
Builds WaterQualityAnalyticsMart FROM THE BATCH DATA WAREHOUSE (brief §18 integration rule):
Raw → Profiling → Curation → Staging → Dimensional DW → [this mart] → Feature selection / Regression / Association / Decision tree

The mart is one flat, model-ready table: every fact row joined to its dimension attributes.
Output: data/processed/wq_analytics_mart.parquet   (PostgreSQL warehouse must be running: 05_dw_batch)

Usage:  python 09_mining/build_analytics_mart.py
"""
import sys, time
from pathlib import Path
import duckdb
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '05_dw_batch' / 'etl'))
import etl_batch as etl

MART_SQL = '''
SELECT f.result_key, f.result_id, d.full_date AS sample_date, d.year, d.quarter, d.month, d.year_month, d.season,
       d.day_of_week, d.is_weekend, t.hour AS sample_hour, t.time_band,
       l.site_id, l.state, l.region, l.water_type, l.latitude, l.longitude,
       c.characteristic_name AS characteristic, c.short_name AS parameter, c.parameter_group, c.standard_unit AS unit,
       o.organization, o.provider, o.sample_type_group, o.equipment_group, o.result_status, o.value_type,
       f.result_value, f.result_band, f.exceedance_flag, f.high_risk_flag, f.is_extreme_outlier, f.is_provisional, f.load_batch_id
FROM dw.fact_water_quality_result f
JOIN dw.dim_date d ON d.date_key = f.date_key
JOIN dw.dim_time t ON t.time_key = f.time_key
JOIN dw.dim_monitoring_location l ON l.location_key = f.location_key
JOIN dw.dim_characteristic c ON c.characteristic_key = f.characteristic_key
JOIN dw.dim_organization_method o ON o.org_method_key = f.org_method_key'''


def build():
    t = time.time(); out = ROOT / 'data' / 'processed' / 'wq_analytics_mart.parquet'
    tmp = ROOT / 'data' / 'staging' / 'mart.csv'; tmp.parent.mkdir(parents=True, exist_ok=True)
    con = etl.connect()
    with con.cursor() as cur, open(tmp, 'w', encoding='utf-8', newline='') as fh:
        cur.copy_expert(f'COPY ({MART_SQL}) TO STDOUT WITH (FORMAT csv, HEADER true)', fh)
    duckdb.sql(f"COPY (SELECT * FROM read_csv('{tmp.as_posix()}', header=true) ORDER BY sample_date, result_key) "
               f"TO '{out.as_posix()}' (FORMAT parquet, COMPRESSION zstd)")
    tmp.unlink()
    n = duckdb.sql(f"SELECT count(*) FROM '{out.as_posix()}'").fetchone()[0]
    print(f'WaterQualityAnalyticsMart: {n:,} rows -> {out} ({out.stat().st_size / 1e6:.0f} MB) in {time.time() - t:.0f}s')
    return out


if __name__ == '__main__':
    build()
