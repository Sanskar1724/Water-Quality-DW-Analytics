"""Builds 07_dw_realtime/realtime_dw_demo.ipynb (evidence of the live replay, read from ClickHouse)."""
import nbformat as nbf, sys
from pathlib import Path
OUT = Path(sys.argv[1]); cells = []
def md(s, infer=None):
    c = nbf.v4.new_markdown_cell(s.strip())
    if infer: c.metadata["infer"] = infer
    cells.append(c)
def code(s): cells.append(nbf.v4.new_code_cell(s.strip()))
def infer(tag): md(f"**🔎 Inference ({tag}):** _written after the run_", infer=tag)

md(r"""
# Step 8 · Real-Time Data Warehouse: evidence of the live replay

> ⚠️ **SIMULATION.** Historical WQP results for **December 2025** were **replayed in time order** as live events (`producer/producer.py`). This is not a live feed.

**Pipeline:** Python producer → **Kafka** (topic `wq.results.replay`, key = site_id) → **Spark Structured Streaming** (5-second micro-batches: parse, 5 validation rules, derived exceedance / high-risk / alert level, 1-hour event-time windows with a 2-hour watermark) → **ClickHouse** (`wq_rt.events`, `window_agg`, `rejected`) → **Grafana** dashboard (refresh 5 s).

This notebook reads the results **back from ClickHouse** to document the run: throughput, latency, validation, the 8 KPIs, the window aggregates, and a **consistency check against the batch warehouse**.
""")
code(r"""
import clickhouse_connect, duckdb, pandas as pd, numpy as np, matplotlib.pyplot as plt, seaborn as sns
from pathlib import Path
ROOT = Path.cwd().resolve()
for p in [ROOT, *ROOT.parents]:
    if (p / '07_dw_realtime').exists(): ROOT = p; break
OUT = ROOT / '07_dw_realtime'; FIG, TAB = OUT / 'figures', OUT / 'tables'; FIG.mkdir(exist_ok=True); TAB.mkdir(exist_ok=True)
sns.set_theme(style='whitegrid'); pd.set_option('display.width', 200)
def save_tab(df, n, index=False): df.to_csv(TAB / f'G{n}.csv', index=index); return df
def save_fig(n): plt.tight_layout(); plt.savefig(FIG / f'G{n}.png', dpi=130, bbox_inches='tight'); plt.show()
ch = clickhouse_connect.get_client(host='127.0.0.1', port=8123, username='wq', password='wq_local_dev', database='wq_rt')
q = lambda sql: ch.query_df(sql)
""")

md(r"""## 1 · Did every event arrive? (counts, validation, latency)""")
code(r"""
log = (OUT / 'producer' / 'replay.log').read_text(encoding='utf-8', errors='replace')
print(log.strip().splitlines()[0]); print(log.strip().splitlines()[-2])
ev = q('''SELECT count() AS valid_events, uniqExact(site_id) AS sites, uniqExact(characteristic) AS parameters,
                 sum(exceedance_flag) AS exceedances, sum(high_risk_flag) AS high_risk,
                 min(event_time) AS first_sample_time, max(event_time) AS last_sample_time,
                 min(ingested_at) AS first_ingest, max(ingested_at) AS last_ingest FROM events''')
rj = q('SELECT reason, count() AS events FROM rejected GROUP BY reason ORDER BY events DESC')
lat = q('''SELECT quantile(0.5)(d) AS p50_s, quantile(0.9)(d) AS p90_s, quantile(0.99)(d) AS p99_s, max(d) AS max_s
           FROM (SELECT dateDiff('millisecond', produced_at, ingested_at) / 1000 AS d FROM events)''')
summary = ev.T.rename(columns={0: 'Value'})
summary.loc['rejected_events'] = int(rj.events.sum()); summary.loc['valid + rejected'] = int(ev.valid_events[0] + rj.events.sum())
summary.loc['replay duration (s)'] = round((ev.last_ingest[0] - ev.first_ingest[0]).total_seconds(), 1)
display(save_tab(summary, '01_run_summary', index=True)); display(save_tab(rj, '01_rejected_by_reason')); display(save_tab(lat.round(2), '01_latency'))
""")

md(r"""## 2 · Throughput and latency over the replay""")
code(r"""
tp = q('''SELECT toStartOfInterval(ingested_at, INTERVAL 5 SECOND) AS t, count() AS events, sum(exceedance_flag) AS exceedances,
                 quantile(0.5)(dateDiff('millisecond', produced_at, ingested_at)) / 1000 AS median_latency_s
          FROM events GROUP BY t ORDER BY t''')
tp['sec'] = (tp.t - tp.t.min()).dt.total_seconds(); save_tab(tp, '02_throughput')
fig, axes = plt.subplots(1, 3, figsize=(19, 4.5))
axes[0].bar(tp.sec, tp.events * 12, width=4, color='#4C72B0'); axes[0].set(title='G2a · KPI 1: results per minute (5-s micro-batches × 12)', xlabel='seconds since start', ylabel='results / minute')
axes[1].plot(tp.sec, tp.median_latency_s, marker='.', color='#55A868'); axes[1].set(title='G2b · Median latency per batch (producer → ClickHouse)', xlabel='seconds since start', ylabel='seconds')
lt = q("SELECT dateDiff('millisecond', produced_at, ingested_at) / 1000 AS d FROM events").d
axes[2].hist(lt, bins=40, color='#55A868'); axes[2].set(title='G2c · Latency distribution, all events', xlabel='seconds')
save_fig('02_throughput_latency')
""")
md(r"""**Why these charts:** throughput shows the stream really is continuous (results per minute, the brief's KPI 1); latency shows how *real-time* it is, i.e. the delay between an event being sent and being queryable on the dashboard.""")
infer("G2")

md(r"""## 3 · The 8 live KPIs (final state after the replay)""")
code(r"""
k2 = q('''SELECT characteristic, round(argMax(result_value, (event_time, ingested_at)), 2) AS latest_value, any(unit) AS unit,
                 count() AS results, round(100 * avg(exceedance_flag), 2) AS exceedance_pct FROM events GROUP BY characteristic ORDER BY results DESC''')
k5 = q('''SELECT site_id, any(state) AS state, count() AS results, uniqExact(characteristic) AS parameters,
                 round(100 * avg(exceedance_flag), 1) AS exceedance_pct FROM events GROUP BY site_id ORDER BY results DESC LIMIT 10''')
k7 = q('''SELECT site_id, any(state) AS state, count() AS results, sum(exceedance_flag) AS exceedances, round(100 * avg(exceedance_flag), 1) AS exceedance_pct
          FROM events GROUP BY site_id HAVING results >= 5 AND exceedance_pct >= 30 ORDER BY exceedance_pct DESC, results DESC''')
k8 = q('''SELECT characteristic, alert_level, count() AS alerts, uniqExact(site_id) AS sites FROM events WHERE alert_level <> 'OK'
          GROUP BY characteristic, alert_level ORDER BY alerts DESC''')
for n, d, t in [('03_kpi2_current_values', k2, 'KPI 2 + 6 · current values and parameter coverage'), ('03_kpi5_top_sites', k5, 'KPI 5 · top monitored sites'),
                ('03_kpi7_poor_sites', k7, 'KPI 7 · poor-quality sites (real-time rule: >= 5 results and >= 30% exceedance)'), ('03_kpi8_alerts', k8, 'KPI 8 · alerts by parameter and level')]:
    print(t); display(save_tab(d, n))
fig, axes = plt.subplots(1, 2, figsize=(16, 4.5))
axes[0].barh(k2.characteristic, k2.results, color='#4C72B0'); axes[0].invert_yaxis(); axes[0].set(title='G3a · KPI 6: parameter coverage (results)')
for i, (r, e) in enumerate(zip(k2.results, k2.exceedance_pct)): axes[0].text(r, i, f' {r:,} · exc {e:.1f}%', va='center', fontsize=8)
p8 = k8.pivot(index='characteristic', columns='alert_level', values='alerts').fillna(0)
p8.plot(kind='barh', stacked=True, ax=axes[1], color=['#DD8452', '#C44E52'][:p8.shape[1]]); axes[1].set(title='G3b · KPI 3/4/8: exceedance and high-risk alerts by parameter', xlabel='alerts')
save_fig('03_kpis')
""")
md(r"""**Why these charts:** coverage shows how much of each parameter flowed through the stream; the stacked bars split alerts into *exceedance* vs *high risk*, which is exactly what an operations team would triage.""")
infer("G3")

md(r"""## 4 · Spark event-time windows (1 hour of sample time, 2-hour watermark)""")
code(r"""
w = q('''SELECT window_start, characteristic, sum(results) AS results, sum(exceedances) AS exceedances
         FROM window_agg FINAL GROUP BY window_start, characteristic ORDER BY window_start''')
w['exceedance_pct'] = w.exceedances / w.results * 100; save_tab(w, '04_window_agg')
daily = w.assign(day=w.window_start.dt.date).groupby(['day', 'characteristic'])[['results', 'exceedances']].sum().reset_index()
daily['exceedance_pct'] = daily.exceedances / daily.results * 100
fig, axes = plt.subplots(1, 2, figsize=(17, 4.5))
for c, d in daily.groupby('characteristic'): axes[0].plot(pd.to_datetime(d.day), d.results, marker='.', label=c)
axes[0].set(title='G4a · Results per sample day (from 1-hour windows)', ylabel='results'); axes[0].legend(fontsize=7); axes[0].tick_params(axis='x', rotation=45)
hm = daily.pivot(index='characteristic', columns='day', values='exceedance_pct')
sns.heatmap(hm, cmap='OrRd', ax=axes[1], cbar_kws={'label': 'exceedance %'}); axes[1].set(title='G4b · Exceedance % by parameter and sample day', xlabel='', ylabel='')
save_fig('04_event_time_windows')
print('window rows (after FINAL de-duplication):', len(q('SELECT * FROM window_agg FINAL')), '· raw rows written incl. updates:', q('SELECT count() n FROM window_agg').n[0])
""")
md(r"""**Why these charts:** the windows are aggregated by **when the sample was taken** (event time), not when it was processed, so the replayed December history is correctly rebuilt day by day, as a real stream with late or out-of-order events would require.""")
infer("G4")

md(r"""## 5 · Consistency check: real-time DW vs batch DW (December 2025)
The same December 2025 results were loaded into the **batch** warehouse by the incremental ETL (Step 6). If both pipelines are correct, the valid streamed events and their exceedance / high-risk counts must match the batch numbers (minus the deliberately injected invalid events).""")
code(r"""
mart = (ROOT / 'data' / 'processed' / 'wq_analytics_mart.parquet').as_posix()
b = duckdb.sql(f'''SELECT count(*) AS results, sum(exceedance_flag) AS exceedances, sum(high_risk_flag) AS high_risk, count(DISTINCT site_id) AS sites
                   FROM '{mart}' WHERE sample_date >= DATE '2025-12-01' ''').df()
r = q('SELECT count() AS results, sum(exceedance_flag) AS exceedances, sum(high_risk_flag) AS high_risk, uniqExact(site_id) AS sites FROM events')
cmp_ = pd.DataFrame({'Batch DW (Dec 2025)': b.iloc[0], 'Real-time DW (valid events)': r.iloc[0]})
cmp_['Difference'] = cmp_.iloc[:, 0] - cmp_.iloc[:, 1]
display(save_tab(cmp_, '05_batch_vs_realtime', index=True))
print('Injected invalid events (rejected):', int(rj.events.sum()))
""")
infer("G5")

md(r"""## 6 · Dashboard screenshots (Grafana)""")
code(r"""
from IPython.display import Image, display as dsp
for f in sorted(FIG.glob('G0*_dashboard*.jpg')) + sorted(FIG.glob('G0*_dashboard*.png')):
    print(f.name); dsp(Image(filename=str(f), width=1100))
""")
infer("G6")

nb = nbf.v4.new_notebook(); nb.cells = cells
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, OUT); print('written', OUT, len(cells), 'cells')
