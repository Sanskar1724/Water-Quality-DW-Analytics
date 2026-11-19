"""
Kafka producer: REPLAYS historical WQP results as simulated live events (this is NOT a live feed).

Reads analysis-ready rows from data/processed/wq_curated.parquet for a chosen period, sorts them by sampling time
(event time) and sends them one by one to Kafka at a fixed rate, so the pipeline behaves like a live stream.

Usage (repository root, after the real-time stack is up):
    python 07_dw_realtime/producer/producer.py                      # December 2025, 300 events/second
    python 07_dw_realtime/producer/producer.py --rate 100 --start 2025-07-01 --end 2025-07-07
    python 07_dw_realtime/producer/producer.py --inject-invalid 20  # also send 20 deliberately bad events (validation demo)

Event JSON (one message per measured result), key = site_id (all events of a site go to the same partition, in order):
{ "event_id", "site_id", "state", "region", "organization", "characteristic", "result_value", "unit",
  "event_time" (sampling time, ISO), "latitude", "longitude", "produced_at" (replay clock, ISO), "simulation": true }
"""
import argparse, json, time, random
from datetime import datetime, timezone
from pathlib import Path
import duckdb
from kafka import KafkaProducer

ROOT = Path(__file__).resolve().parents[2]
CURATED = ROOT / 'data' / 'processed' / 'wq_curated.parquet'

ap = argparse.ArgumentParser()
ap.add_argument('--bootstrap', default='127.0.0.1:9092')
ap.add_argument('--topic', default='wq.results.replay')
ap.add_argument('--start', default='2025-12-01'); ap.add_argument('--end', default='2025-12-31')
ap.add_argument('--rate', type=float, default=300, help='events per second (replay speed)')
ap.add_argument('--limit', type=int, default=0, help='stop after N events (0 = all)')
ap.add_argument('--inject-invalid', type=int, default=0, help='send N deliberately invalid events to demonstrate validation')
a = ap.parse_args()

rows = duckdb.sql(f'''
    SELECT result_id AS event_id, site AS site_id, state, region, org AS organization, param AS characteristic,
           value_std AS result_value, unit_std AS unit, strftime(ts_local, '%Y-%m-%dT%H:%M:%S') AS event_time,
           lat AS latitude, lon AS longitude
    FROM '{CURATED.as_posix()}'
    WHERE analysis_ready AND dt BETWEEN DATE '{a.start}' AND DATE '{a.end}'
    ORDER BY ts_local, result_id {f"LIMIT {a.limit}" if a.limit else ''}''').fetchall()
cols = ['event_id', 'site_id', 'state', 'region', 'organization', 'characteristic', 'result_value', 'unit', 'event_time', 'latitude', 'longitude']
print(f'SIMULATION: replaying {len(rows):,} historical WQP results ({a.start} … {a.end}) to topic {a.topic} at {a.rate:.0f} events/s')

prod = KafkaProducer(bootstrap_servers=a.bootstrap, key_serializer=lambda k: k.encode(), value_serializer=lambda v: json.dumps(v).encode(),
                     linger_ms=20, acks=1)
bad = set(random.Random(7).sample(range(len(rows)), min(a.inject_invalid, len(rows)))) if a.inject_invalid else set()
t0 = time.time(); sent = 0
for i, r in enumerate(rows):
    ev = dict(zip(cols, r)); ev['produced_at'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]; ev['simulation'] = True
    if i in bad:   # deliberately broken events for the validation demo
        kind = i % 3
        if kind == 0: ev['result_value'] = -999.0
        elif kind == 1: ev['characteristic'] = 'Unknown parameter'
        else: ev.pop('event_time')
    prod.send(a.topic, key=ev['site_id'] or 'unknown', value=ev); sent += 1
    wait = t0 + sent / a.rate - time.time()
    if wait > 0: time.sleep(wait)
    if sent % 2000 == 0: print(f'  sent {sent:,} events · replay clock {ev.get("event_time")} · {sent / (time.time() - t0):.0f} ev/s', flush=True)
prod.flush()
print(f'Done: {sent:,} events in {time.time() - t0:.0f}s ({sent / (time.time() - t0):.0f} events/s), {len(bad)} deliberately invalid')
