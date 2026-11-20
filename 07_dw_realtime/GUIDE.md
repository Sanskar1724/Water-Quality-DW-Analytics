# Guide: `07_dw_realtime/` (Step 8: Real-Time / Streaming Data Warehouse)

> ⚠️ **This is a SIMULATION.** The Water Quality Portal publishes historical data, not a live feed. As the brief requires, historical results (December 2025) are **replayed in time order** as if they were arriving live. Every event carries `"simulation": true`, and the dashboard says so at the top.

## What this folder does, in plain words
The batch warehouse (Step 6) is refreshed in big loads, e.g. once a month. A **real-time warehouse** processes each new measurement **seconds after it arrives** and updates a live dashboard. That is what an environmental agency needs for *rapid contamination / exceedance alerts*.

> **Analogy:** the batch warehouse is a monthly bank statement; the real-time warehouse is the instant SMS you get for every card payment.

## The pipeline
```
Python producer ──► Kafka ──► Spark Structured Streaming ──► ClickHouse ──► Grafana
(replays history)   (queue)   (validate, derive, aggregate)   (fast store)    (live dashboard)
```
| Piece | What it does here |
|---|---|
| **Producer** (`producer/producer.py`) | Reads curated results for the replay period, sorts them by sampling time, and sends one JSON event per result to Kafka at a fixed speed (default 300 events/s). Can inject deliberately bad events to demonstrate validation. |
| **Kafka** | Holds the stream of events in topic `wq.results.replay` (3 partitions). The message **key = site_id**, so all events of one site stay in order. |
| **Spark Structured Streaming** (`spark/stream_job.py`) | Every 5 seconds: parse the JSON, apply 5 validation rules, derive exceedance / high-risk / alert level, write valid events and rejected events to ClickHouse, and compute **1-hour event-time window aggregates with a 2-hour watermark**. |
| **ClickHouse** (`clickhouse/init.sql`) | Columnar database built for fast analytics on fresh data: tables `events`, `window_agg`, `rejected`. |
| **Grafana** (`grafana/`) | Live dashboard refreshing every 5 s: the 8 required KPIs plus latency, rejected count and an alert map. |

## Event design (documented as the brief requires)
| Item | Value |
|---|---|
| Topic | `wq.results.replay` |
| Key | `site_id` |
| Event timestamp | `event_time` = when the sample was taken (historical) |
| Replay timestamp | `produced_at` = when the producer sent it |
| Replay speed | `--rate` events per second (default 300) |
| Payload | `event_id, site_id, state, region, organization, characteristic, result_value, unit, event_time, latitude, longitude, produced_at, simulation` |

**Validation rules (Spark):** valid JSON with event_id · valid event_time · site_id present · known characteristic · value present and physically possible (same ranges as Step 2). Failures go to `wq_rt.rejected` with the reason.

**Derived measures (Spark):** `exceedance_flag`, `high_risk_flag` (same documented thresholds as Step 2), `alert_level` (OK / EXCEEDANCE / HIGH RISK), `processed_at`.

## The 8 required live KPIs (Grafana)
| KPI | Panel |
|---|---|
| 1. Results per minute during replay | Stat + bar chart |
| 2. Current parameter values | Latest value per parameter |
| 3. High-risk observations | Stat |
| 4. Exceedances | Stat + per-parameter time series |
| 5. Top monitored sites | Table |
| 6. Parameter coverage | Bar gauge |
| 7. Poor-quality sites | Table (real-time rule: ≥ 5 results and ≥ 30% exceedance, because a short live window has few results per site) |
| 8. Alerts | Latest high-risk events + alerts by state |

## How to run the live demo
```bash
docker compose -f 05_dw_batch/docker-compose.yml stop
docker compose -f 07_dw_realtime/docker-compose.yml up -d
python 07_dw_realtime/producer/producer.py --rate 150 --inject-invalid 25
```
Then open **http://localhost:3300** (Grafana) and watch the dashboard fill in. Spark's own monitoring page is at http://localhost:4040.

## Terms used, explained simply
| Term | Simple meaning | Everyday analogy | In this project | Why it matters |
|---|---|---|---|---|
| **Streaming** | Processing data continuously as it arrives | A live cricket score vs the next day's newspaper | The whole folder | Alerts within seconds |
| **Event** | One small message describing something that happened | One SMS | One measured result as JSON | The unit of the stream |
| **JSON** | A simple text format of named fields | A filled form | Event payload | Readable by every tool |
| **Producer** | The program that sends events | The person sending SMSes | `producer.py` | Starts the stream |
| **Replay / simulation** | Re-sending historical data in time order as if it were live | Re-watching a recorded match | December 2025 replayed | Lets us demo streaming honestly with historical data |
| **Kafka** | A durable queue for streams of events | A post-office sorting conveyor | Topic `wq.results.replay` | Decouples senders and receivers; nothing is lost if Spark is slow |
| **Topic / partition** | A named stream, split into parallel lanes | A mailbox split into 3 slots | 3 partitions | Parallel processing |
| **Message key** | Decides which partition an event goes to | Sorting letters by postcode | site_id | Keeps each site's events in order |
| **Spark Structured Streaming** | Spark's engine for processing streams in small batches | A machine that processes the conveyor every few seconds | 5-second micro-batches | Validation, derivation, aggregation at scale |
| **Micro-batch / trigger** | Processing whatever arrived in the last few seconds | Emptying the mailbox every 5 s | `trigger(processingTime='5 seconds')` | Near-real-time with simple logic |
| **Event time vs processing time** | When it happened vs when we processed it | When a photo was taken vs when you uploaded it | event_time vs processed_at | Correct windows even when events arrive late |
| **Window** | A fixed time bucket for aggregation | Hourly sales | 1-hour event-time windows | Short-window KPIs |
| **Watermark** | How long to wait for late events before closing a window | "Late homework accepted up to 2 hours" | 2 hours | Memory stays bounded; late data handled |
| **Checkpoint** | Spark's saved progress | A bookmark | `/tmp/checkpoints` | Restarts continue without duplicates or gaps |
| **ClickHouse** | A very fast column-oriented analytics database | A spreadsheet that reads only the columns you ask for | `wq_rt` database | Dashboard queries in milliseconds on fresh data |
| **MergeTree / ReplacingMergeTree** | ClickHouse table types; the second keeps only the newest version of a row | Replacing an old version of a document | events / window_agg | Window results can be updated as late data arrives |
| **Grafana** | A live dashboard tool | A car's dashboard | `localhost:3300`, refresh 5 s | The operational monitoring screen |
| **Latency** | Time from sending to being visible | Delay of a live TV broadcast | Median producer → ClickHouse time | Shows how "real-time" the system is |
| **Alert** | A flagged event needing attention | A smoke alarm | High-risk results | The business purpose of the real-time DW |

## Results of the full replay (19 Nov 2026), in simple words
| Item | Result |
|---|---|
| Events replayed | 23,189 (all of December 2025) in about 150 seconds, ≈ 9,000 results per minute |
| Valid / rejected | 23,164 valid + **25 rejected**: exactly the 25 deliberately broken test events |
| Latency (send → visible) | median **4.0 s**, 99% under 6.9 s |
| Exceedances / high-risk | 1,392 / 495 (in winter, pH tops the alerts; DO alerts are fewer in cold water) |
| Check against the batch warehouse | Same results, high-risk count and sites; exceedances differ by 1 (a corrupted test event) |

**What this shows:** the real-time warehouse turns each measurement into a dashboard update within seconds, and its numbers agree with the batch warehouse, which was built by a completely separate pipeline.

## Problems met while building (and fixes)
1. Spark started before the Kafka topic existed and stopped. A one-shot `kafka-init` service now creates the topic first, and Spark waits for it.
2. The producer on Windows could not reach Kafka at `localhost` (resolved to IPv6). Kafka now advertises `127.0.0.1`.
3. The event-time chart showed "data outside time range" (December 2025 vs the dashboard's last 10 minutes). It became a bar chart by sample day.
4. The map panel needed an API key. It was replaced by an "alerts by state" bar panel.
5. No site met the batch "poor quality" rule (≥ 10 results, ≥ 50%) in one winter month. A documented real-time rule (≥ 5, ≥ 30%) is used.

## Files
`realtime_dw_demo.ipynb` (evidence and inferences), `figures/G*.png|jpg` (charts and dashboard screenshots), `tables/G*.csv`.
