"""
Shared data preparation for the mining notebooks (same definitions as Step 4 feature selection).
All tables come from WaterQualityAnalyticsMart (built from the batch DW): data/processed/wq_analytics_mart.parquet
"""
from pathlib import Path
import json, duckdb, numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MART = (ROOT / 'data' / 'processed' / 'wq_analytics_mart.parquet').as_posix()
SELECTED = json.loads((ROOT / '03_feature_selection' / 'selected_features.json').read_text(encoding='utf-8'))


def connect():
    con = duckdb.connect(); con.execute("SET memory_limit='3GB'")
    con.execute(f"CREATE OR REPLACE VIEW mart AS SELECT * FROM '{MART}'")
    con.execute('''
    CREATE OR REPLACE TABLE sd AS
    SELECT site_id, sample_date, any_value(state) state, any_value(region) region, any_value(water_type) water_type,
           mode(organization) organization, mode(sample_type_group) sample_type_group, mode(equipment_group) equipment_group,
           any_value(month) month, any_value(season) season, any_value(latitude) latitude,
           median(result_value) FILTER (WHERE parameter = 'Dissolved oxygen') AS do_val,
           median(result_value) FILTER (WHERE parameter = 'Temperature') AS temperature,
           median(result_value) FILTER (WHERE parameter = 'pH') AS ph,
           median(result_value) FILTER (WHERE parameter = 'Conductivity') AS conductivity,
           median(result_value) FILTER (WHERE parameter = 'Turbidity') AS turbidity,
           median(result_value) FILTER (WHERE parameter = 'Nitrate') AS nitrate
    FROM mart GROUP BY site_id, sample_date''')
    return con


def regression_table(con):
    """Site-days with DO, co-measured parameters and the site's previous DO (<= 31 days earlier)."""
    df = con.execute('''
      SELECT *, CASE WHEN date_diff('day', lag(sample_date) OVER w, sample_date) <= 31 THEN lag(do_val) OVER w END AS prev_do
      FROM (SELECT * FROM sd WHERE do_val IS NOT NULL) WINDOW w AS (PARTITION BY site_id ORDER BY sample_date)
      ORDER BY sample_date''').df()
    for c in ['conductivity', 'turbidity', 'nitrate']:
        df[f'log_{c}'] = np.log10(df[c].clip(lower=0) + 0.01)
    df['month_sin'] = np.sin(2 * np.pi * df.month / 12); df['month_cos'] = np.cos(2 * np.pi * df.month / 12)
    return df


def classification_table(con, sample=1_500_000):
    """Results with leakage-safe predictors: co-measured OTHER parameters + previous result of the same site/parameter."""
    return con.execute(f'''
    WITH r AS (
      SELECT m.*, CASE WHEN date_diff('day', lag(sample_date) OVER w, sample_date) <= 31 THEN lag(result_value) OVER w END AS prev_result,
             CASE WHEN date_diff('day', lag(sample_date) OVER w, sample_date) <= 31 THEN lag(high_risk_flag) OVER w END AS prev_high_risk
      FROM (SELECT * FROM mart USING SAMPLE reservoir({sample} ROWS) REPEATABLE (11)) m
      WINDOW w AS (PARTITION BY site_id, parameter ORDER BY sample_date, result_key))
    SELECT r.sample_date, r.site_id, r.parameter, r.season, r.month, r.region, r.state, r.water_type, r.sample_type_group, r.equipment_group,
           r.organization, r.time_band, r.is_weekend, r.latitude, r.prev_result, r.prev_high_risk,
           CASE WHEN r.parameter <> 'Temperature' THEN s.temperature END AS co_temperature,
           CASE WHEN r.parameter <> 'Dissolved oxygen' THEN s.do_val END AS co_do,
           CASE WHEN r.parameter <> 'pH' THEN s.ph END AS co_ph,
           CASE WHEN r.parameter <> 'Conductivity' THEN s.conductivity END AS co_conductivity,
           CASE WHEN r.parameter <> 'Turbidity' THEN s.turbidity END AS co_turbidity,
           r.high_risk_flag
    FROM r LEFT JOIN sd s ON s.site_id = r.site_id AND s.sample_date = r.sample_date
    ORDER BY r.sample_date''').df()


CAT_CLS = ['parameter', 'season', 'region', 'state', 'water_type', 'sample_type_group', 'equipment_group', 'organization', 'time_band']
NUM_CLS = ['prev_result', 'prev_high_risk', 'co_temperature', 'co_do', 'co_ph', 'co_conductivity', 'co_turbidity', 'latitude', 'month']


def encode_classification(cl, features):
    """Ordinal-encode categoricals and median-fill numerics with has_<x> indicators; keep only `features`."""
    X = pd.DataFrame(index=cl.index); maps = {}
    for c in CAT_CLS:
        cat = cl[c].fillna('Unknown').astype('category'); X[c] = cat.cat.codes; maps[c] = dict(enumerate(cat.cat.categories))
    for c in NUM_CLS:
        if c not in ('latitude', 'month'): X[f'has_{c}'] = cl[c].notna().astype(int)
        X[c] = cl[c].astype(float).fillna(cl[c].astype(float).median())
    X['is_weekend'] = cl.is_weekend.astype(int)
    keep = [f for f in features if f in X.columns]
    return X[keep], maps
