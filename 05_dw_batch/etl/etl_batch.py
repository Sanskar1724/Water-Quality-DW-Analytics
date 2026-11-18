"""
Batch ETL for the Water Quality data warehouse (PostgreSQL).

Flow (brief §9-10):  curated Parquet → Extract → Staging (stg) → data-quality rules → dimension lookup /
                     new members → fact load → monthly fact → validation / reconciliation.

Usage (from the repository root, after `docker compose -f 05_dw_batch/docker-compose.yml up -d`):
    python 05_dw_batch/etl/etl_batch.py reset          # drop and recreate schemas + static dimensions
    python 05_dw_batch/etl/etl_batch.py initial        # initial bulk load: 2024-01-01 … 2025-11-30
    python 05_dw_batch/etl/etl_batch.py incremental    # incremental load of the held-back month: 2025-12
    python 05_dw_batch/etl/etl_batch.py validate       # integrity + reconciliation checks
    python 05_dw_batch/etl/etl_batch.py queries        # run and time the analytical queries
"""
import sys, time, re, os
from pathlib import Path
import duckdb, pandas as pd, psycopg2

ROOT = Path(__file__).resolve().parents[2]
SQL = ROOT / '05_dw_batch' / 'sql'
CURATED = ROOT / 'data' / 'processed' / 'wq_curated.parquet'
STAGE_DIR = ROOT / 'data' / 'staging'
DSN = dict(host='127.0.0.1', port=5433, dbname='wq_dw', user='wq', password=os.environ.get('WQ_PG_PASSWORD', 'wq_local_dev'))

INITIAL = (1, 'initial', '2024-01-01', '2025-11-30')
INCREMENTAL = (2, 'incremental', '2025-12-01', '2025-12-31')

STG_COLS = ['load_batch_id', 'result_id', 'site_id', 'state', 'region', 'state_match', 'latitude', 'longitude', 'water_type',
            'characteristic', 'result_value', 'standard_unit', 'sample_date', 'sample_hour', 'time_band', 'organization',
            'provider', 'sample_type_group', 'equipment_group', 'result_status', 'value_type', 'result_band',
            'exceedance_flag', 'high_risk_flag', 'is_extreme_outlier', 'is_provisional']


def connect(retries=20):
    """Connect to the warehouse; retries briefly because PostgreSQL restarts once on its very first start."""
    for i in range(retries):
        try:
            c = psycopg2.connect(**DSN, client_encoding='UTF8'); c.autocommit = True; return c
        except psycopg2.OperationalError:
            if i == retries - 1: raise
            time.sleep(1.5)


def run_sql_file(con, name, batch=None):
    """Run a .sql file statement by statement; ':batch' is replaced by the batch id."""
    text = (SQL / name).read_text(encoding='utf-8')
    text = re.sub(r'--[^\n]*', '', text)
    if batch is not None: text = text.replace(':batch', str(batch))
    with con.cursor() as cur:
        for stmt in [s.strip() for s in text.split(';') if s.strip()]:
            cur.execute(stmt)


def q(con, sql):
    with con.cursor() as cur:
        cur.execute(sql)
        return pd.DataFrame(cur.fetchall(), columns=[d[0] for d in cur.description])


def reset():
    """Drop and recreate the stg/dw schemas and load the static dimensions (Date, Time, Characteristic)."""
    con = connect(); t = time.time()
    run_sql_file(con, '01_create_schema.sql'); run_sql_file(con, '02_static_dimensions.sql')
    print(f'Schema created and static dimensions loaded in {time.time() - t:.1f}s'); return con


def extract_to_staging(con, batch, start, end):
    """EXTRACT: analysis-ready single readings for the period → CSV → COPY into stg.wq_results."""
    STAGE_DIR.mkdir(parents=True, exist_ok=True); f = STAGE_DIR / f'batch_{batch}.csv'
    duckdb.sql(f'''COPY (SELECT {batch} AS load_batch_id, result_id, site, state, region, state_match, lat, lon, water_type,
                         param, value_std, unit_std, CAST(dt AS DATE), hour, time_band, org, coalesce(provider, 'Not Reported'),
                         coalesce(sample_type_group, 'Not Reported'), coalesce(equipment_group, 'Not Reported'),
                         coalesce(status, 'Not Reported'), coalesce(value_type, 'Not Reported'), result_band, exceedance_flag, high_risk_flag,
                         is_extreme_outlier, is_provisional
                  FROM '{CURATED.as_posix()}'
                  WHERE analysis_ready AND dt BETWEEN DATE '{start}' AND DATE '{end}')
                  TO '{f.as_posix()}' (HEADER, DELIMITER ',')''')
    with con.cursor() as cur, open(f, encoding='utf-8') as fh:
        cur.copy_expert(f"COPY stg.wq_results ({', '.join(STG_COLS)}) FROM STDIN WITH (FORMAT csv, HEADER true)", fh)
        cur.execute('ANALYZE stg.wq_results')   # fresh statistics so PostgreSQL picks fast hash joins
    f.unlink()
    return int(q(con, f'SELECT count(*) n FROM stg.wq_results WHERE load_batch_id = {batch}').n[0])


def load(batch, mode, start, end, con=None):
    """Full ETL for one batch, with timing of each stage and an audit row in dw.etl_load_log."""
    con = con or connect(); timings = {}; t0 = time.time(); started = pd.Timestamp.now()
    before = q(con, '''SELECT (SELECT count(*) FROM dw.dim_monitoring_location) n_loc, (SELECT count(*) FROM dw.dim_organization_method) om,
                              (SELECT count(*) FROM dw.fact_water_quality_result) fact''').iloc[0]
    t = time.time(); staged = extract_to_staging(con, batch, start, end); timings['1. Extract → staging'] = time.time() - t
    t = time.time(); run_sql_file(con, '03_load_batch.sql', batch); timings['2. DQ rules, dimensions, facts, monthly fact'] = time.time() - t
    after = q(con, f'''SELECT (SELECT count(*) FROM dw.dim_monitoring_location) n_loc, (SELECT count(*) FROM dw.dim_organization_method) om,
                              (SELECT count(*) FROM dw.fact_water_quality_result) fact,
                              (SELECT count(*) FROM stg.wq_results WHERE load_batch_id = {batch}) staged_after,
                              (SELECT count(*) FROM dw.fact_site_monthly_water_quality) monthly''').iloc[0]
    if mode == 'initial':
        t = time.time(); run_sql_file(con, '04_constraints_indexes.sql'); timings['3. Constraints + indexes (after bulk load)'] = time.time() - t
    else:
        with con.cursor() as cur: cur.execute('ANALYZE dw.fact_water_quality_result')
    secs = time.time() - t0
    stats = dict(load_batch_id=batch, load_mode=mode, period_start=start, period_end=end, staged_rows=staged,
                 rejected_rows=int(staged - after.staged_after), new_locations=int(after.n_loc - before.n_loc),
                 new_org_methods=int(after.om - before.om), fact_rows_inserted=int(after.fact - before.fact),
                 monthly_rows=int(after.monthly), started_at=started, finished_at=pd.Timestamp.now(), seconds=round(secs, 1))
    with con.cursor() as cur:
        cur.execute('DELETE FROM dw.etl_load_log WHERE load_batch_id = %s', (batch,))
        cur.execute(f"INSERT INTO dw.etl_load_log VALUES ({', '.join(['%s'] * len(stats))})", list(stats.values()))
    return stats, {k: round(v, 1) for k, v in timings.items()}


def validate(con=None):
    """Referential integrity + reconciliation checks. Every check must show status = PASS."""
    con = con or connect()
    checks = [
        ('Fact rows = staged rows (all batches)',
         'SELECT (SELECT count(*) FROM dw.fact_water_quality_result) a, (SELECT count(*) FROM stg.wq_results) b'),
        ('Fact rows = curated analysis-ready rows', None),
        ('Orphan date_key', 'SELECT count(*) a, 0 b FROM dw.fact_water_quality_result f LEFT JOIN dw.dim_date d USING (date_key) WHERE d.date_key IS NULL'),
        ('Orphan location_key', 'SELECT count(*) a, 0 b FROM dw.fact_water_quality_result f LEFT JOIN dw.dim_monitoring_location d USING (location_key) WHERE d.location_key IS NULL'),
        ('Orphan characteristic_key', 'SELECT count(*) a, 0 b FROM dw.fact_water_quality_result f LEFT JOIN dw.dim_characteristic d USING (characteristic_key) WHERE d.characteristic_key IS NULL'),
        ('Orphan org_method_key', 'SELECT count(*) a, 0 b FROM dw.fact_water_quality_result f LEFT JOIN dw.dim_organization_method d USING (org_method_key) WHERE d.org_method_key IS NULL'),
        ('Orphan time_key', 'SELECT count(*) a, 0 b FROM dw.fact_water_quality_result f LEFT JOIN dw.dim_time d USING (time_key) WHERE d.time_key IS NULL'),
        ('Duplicate result_id in fact', 'SELECT count(*) - count(DISTINCT result_id) a, 0 b FROM dw.fact_water_quality_result'),
        ('Monthly fact sample_count = detail fact rows',
         'SELECT (SELECT sum(sample_count) FROM dw.fact_site_monthly_water_quality) a, (SELECT count(*) FROM dw.fact_water_quality_result) b'),
        ('Monthly fact exceedances = detail fact exceedances',
         'SELECT (SELECT sum(exceedance_count) FROM dw.fact_site_monthly_water_quality) a, (SELECT sum(exceedance_flag) FROM dw.fact_water_quality_result) b'),
        ('Sum of result_value: warehouse vs staging (rounded)',
         'SELECT round(sum(result_value)::numeric, 0) a, (SELECT round(sum(result_value)::numeric, 0) FROM stg.wq_results) b FROM dw.fact_water_quality_result'),
    ]
    rows = []
    for name, sql in checks:
        if sql is None:
            a = int(q(con, 'SELECT count(*) n FROM dw.fact_water_quality_result').n[0])
            b = int(duckdb.sql(f"SELECT count(*) FROM '{CURATED.as_posix()}' WHERE analysis_ready").fetchone()[0])
        else:
            r = q(con, sql).iloc[0]; a, b = r.a, r.b
        rows.append({'Check': name, 'Warehouse': a, 'Expected': b, 'Status': 'PASS' if a == b else 'FAIL'})
    return pd.DataFrame(rows)


def table_counts(con=None):
    con = con or connect()
    return q(con, '''SELECT 'dim_date' AS table_name, count(*) AS rows FROM dw.dim_date UNION ALL SELECT 'dim_time', count(*) FROM dw.dim_time
      UNION ALL SELECT 'dim_monitoring_location', count(*) FROM dw.dim_monitoring_location
      UNION ALL SELECT 'dim_characteristic', count(*) FROM dw.dim_characteristic
      UNION ALL SELECT 'dim_organization_method', count(*) FROM dw.dim_organization_method
      UNION ALL SELECT 'fact_water_quality_result', count(*) FROM dw.fact_water_quality_result
      UNION ALL SELECT 'fact_site_monthly_water_quality', count(*) FROM dw.fact_site_monthly_water_quality''')


def queries(repeat=3, con=None):
    """Run each named analytical query `repeat` times; return timings (median ms) and the last results."""
    con = con or connect()
    text = (SQL / '05_analytical_queries.sql').read_text(encoding='utf-8')
    blocks = re.findall(r'-- name: (\S+) \| ([^\n]+)\n(.*?);', text, flags=re.S)
    timing, results = [], {}
    for name, question, sql in blocks:
        ts = []
        for _ in range(repeat):
            t = time.perf_counter(); df = q(con, sql); ts.append((time.perf_counter() - t) * 1000)
        results[name] = df
        timing.append({'Query': name, 'Question': question, 'Rows returned': len(df),
                       'Median ms': round(sorted(ts)[len(ts) // 2], 1), 'Min ms': round(min(ts), 1)})
    return pd.DataFrame(timing), results


if __name__ == '__main__':
    pd.set_option('display.width', 200); pd.set_option('display.max_columns', 20)
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'help'
    if cmd == 'reset': reset()
    elif cmd == 'initial': s, t = load(*INITIAL); print(s); print(t)
    elif cmd == 'incremental': s, t = load(*INCREMENTAL); print(s); print(t)
    elif cmd == 'validate': print(validate().to_string())
    elif cmd == 'queries': print(queries()[0].to_string())
    else: print(__doc__)
