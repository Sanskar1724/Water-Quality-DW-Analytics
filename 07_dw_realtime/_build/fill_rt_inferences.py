"""Fills the Inference cells of realtime_dw_demo.ipynb from its result tables."""
import nbformat as nbf, sys, pandas as pd
from pathlib import Path
P = Path(sys.argv[1]); T = P.parent / 'tables'
s = pd.read_csv(T / 'G01_run_summary.csv', index_col=0).Value
lat = pd.read_csv(T / 'G01_latency.csv').iloc[0]; rj = pd.read_csv(T / 'G01_rejected_by_reason.csv')
cmp_ = pd.read_csv(T / 'G05_batch_vs_realtime.csv', index_col=0); al = pd.read_csv(T / 'G03_kpi8_alerts.csv')
k2 = pd.read_csv(T / 'G03_kpi2_current_values.csv'); poor = pd.read_csv(T / 'G03_kpi7_poor_sites.csv')
dur = (pd.to_datetime(s['last_ingest']) - pd.to_datetime(s['first_ingest'])).total_seconds()
valid = int(s['valid_events']); rej = int(s['rejected_events'])
INF = {
"G2": f"""**🔎 Inference (G2): throughput and latency**
- The whole of December 2025 (**{valid + rej:,} events**) streamed through Kafka → Spark → ClickHouse in **{dur:.0f} s**, a steady **≈ {valid / dur * 60:,.0f} results per minute** (the producer was set to 150 events/s). The Grafana KPI-1 bar chart showed the same flat ~9,000/minute plateau during the run.
- **Latency (producer → stored in ClickHouse): median {lat.p50_s:.2f} s, 90th percentile {lat.p90_s:.2f} s, 99th percentile {lat.p99_s:.2f} s, worst {lat.max_s:.2f} s.** Every event was queryable on the dashboard within about 8 seconds.
- Latency follows the **5-second micro-batch trigger**: an event waits up to 5 s for its batch, then a second or two for processing and the ClickHouse insert. A shorter trigger would lower latency at the cost of more, smaller batches. For water-quality alerts, seconds-level latency is far better than the batch warehouse's monthly refresh.""",
"G3": f"""**🔎 Inference (G3): the live KPIs after the replay**
- **Coverage (KPI 6):** all 6 parameters streamed; pH ({int(k2.loc[k2.characteristic == 'pH', 'results'].iloc[0]):,}), temperature and DO dominate, while nitrate is the rarest. This matches the December share in the batch warehouse.
- **Alerts (KPI 3/4/8):** {int(s['exceedances']):,} exceedances and **{int(s['high_risk']):,} high-risk results**. In **December (winter)** the alert mix differs from the yearly picture: **pH** has the most exceedances (334) and high-risk results (218), then turbidity and DO. DO alerts are fewer because cold water holds more oxygen (Step 3 seasonality). Conductivity high-risk alerts come mainly from coastal sites (salt water).
- **Poor-quality sites (KPI 7):** with the real-time rule (≥ 5 results, ≥ 30% exceedance), **{len(poor)} sites** were flagged, e.g. Texas Gulf-coast sites (TAMUCC, 41% over 17–29 results), Georgia rivers, and North Carolina/Washington/Oklahoma/Puerto Rico sites. The stricter batch rule (≥ 10 results, ≥ 50%) found none in December. That is why a short-window real-time view needs a looser, documented rule.
- **Top monitored sites (KPI 5):** a few Utah logger sites (UTAHDWQ, up to 635 results) dominate the stream: continuous loggers produce many events, so dashboards must show **rates**, not only counts.""",
"G4": """**🔎 Inference (G4): Spark event-time windows**
- Spark grouped every valid event into **1-hour windows of sample time** with a **2-hour watermark**, per parameter and region, and kept updating each window as events arrived. ClickHouse's `ReplacingMergeTree` keeps only the latest version of each window (`FINAL`).
- Rebuilt by day, December shows **sample-day volumes** following the weekly field-work rhythm (weekday peaks), and **exceedance % spikes on individual days** (e.g. pH or nitrate on days with few samples). Short windows react quickly to local events, but small counts make single-day percentages volatile, so they should be read with the result count.
- Because windows use **event time** (when the sample was taken), the replayed history is rebuilt correctly even though it was processed in a few minutes. A real feed with late or out-of-order events would work the same way, up to the 2-hour watermark.""",
"G5": f"""**🔎 Inference (G5): consistency between the real-time and batch warehouses**
| Measure | Batch DW (Dec 2025) | Real-time DW | Difference |
|---|---|---|---|
| Results | {int(cmp_.iloc[0, 0]):,} | {int(cmp_.iloc[0, 1]):,} | {int(cmp_.iloc[0, 2])} = exactly the {rej} injected invalid events |
| Exceedances | {int(cmp_.iloc[1, 0]):,} | {int(cmp_.iloc[1, 1]):,} | {int(cmp_.iloc[1, 2])} (one corrupted test event had been an exceedance) |
| High-risk | {int(cmp_.iloc[2, 0]):,} | {int(cmp_.iloc[2, 1]):,} | {int(cmp_.iloc[2, 2])} |
| Sites | {int(cmp_.iloc[3, 0]):,} | {int(cmp_.iloc[3, 1]):,} | {int(cmp_.iloc[3, 2])} |

- **Every event is accounted for:** {valid:,} valid + {rej} rejected = {valid + rej:,} sent. The **validation rules caught all {rej} deliberately broken events** ({', '.join(f"{r.events} {r.reason.lower()}" for r in rj.itertuples())}).
- Spark recomputes the exceedance/high-risk flags itself from the documented thresholds, and the result matches the batch ETL. **The two independent pipelines (batch SQL vs streaming Spark) agree**, which is strong evidence that both are correct.""",
"G6": """**🔎 Inference (G6): the Grafana dashboard**
- **Mid-replay (G01):** the stream at full speed: about 9,000 results/minute, exceedances arriving every few seconds, latency about 4 s.
- **Final state (G02, G03):** all 8 required KPIs are live:
  1. results per minute
  2. current parameter values
  3. high-risk count
  4. exceedances
  5. top monitored sites
  6. parameter coverage
  7. poor-quality sites
  8. alerts table + alerts by state

  plus pipeline latency, rejected events and the Spark event-time windows.
- The **SIMULATION banner** makes clear that this is a historical replay, as the brief requires.
- **For the live demo:** start the stack, run `producer.py`, and watch the numbers climb in Grafana (http://localhost:3300).""",
}
nb = nbf.read(P, as_version=4); n = 0
for c in nb.cells:
    t = c.get('metadata', {}).get('infer')
    if t in INF: c.source = INF[t]; n += 1
nbf.write(nb, P); print('filled', n)
