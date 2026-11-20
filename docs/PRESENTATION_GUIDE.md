# Presentation Guide: Water Quality DW & Analytics

*Everything needed to run and explain the project in the demo / viva: what to show, which command to run, what each term means, and what our results are.*

**Repository:** https://github.com/Sanskar1724/Water-Quality-DW-Analytics
**Dataset:** Water Quality Portal (USGS + U.S. EPA + National Water Quality Monitoring Council): **4,958,238 results · 50,476 sites · 486 organizations · Jan 2024 – Dec 2025 · 6 parameters** (water temperature, dissolved oxygen, pH, turbidity, conductivity, nitrate)

---

## 1. The project in one paragraph
We built **one integrated analytics platform**. Raw water-quality measurements are **profiled** (checked), **cleaned** (with Decision Tree / Naive Bayes for missing labels), and explored (**EDA**). They are loaded into a **dimensional data warehouse** in three forms: **batch** (PostgreSQL), **distributed** (Citus) and **real-time** (Kafka → Spark → ClickHouse → Grafana). The warehouse is analysed with **OLAP** and dashboards, and an **analytical mart built from the warehouse** feeds **feature selection** and three **data-mining models** (regression, decision tree, association rules).

```
Raw data → Profiling → Cleaning (DT/NB) → EDA → Dimensional model → Batch DW → Real-time DW → OLAP / Dashboards
                                                              └→ Analytical mart → Feature selection → Regression · Decision tree · Association rules
```

## 2. Folder map (what to open for each part)
| Folder | What it contains | Key file to show |
|---|---|---|
| `01_profiling_curation/` | Data profiling + cleaning + DT/NB imputation | `01_data_profiling.ipynb`, `02_data_curation_imputation.ipynb` |
| `02_eda/` | Exploratory data analysis, Q1–Q8 | `01_exploratory_data_analysis.ipynb` |
| `03_feature_selection/` | 6 selection methods + consensus | `01_feature_selection.ipynb`, `selected_features.json` |
| `04_dimensional_model/` | Star / snowflake / fact constellation | `DESIGN.md` |
| `05_dw_batch/` | PostgreSQL warehouse, ETL, incremental load | `batch_dw_demo.ipynb`, `etl/etl_batch.py` |
| `07_dw_realtime/` | Kafka, Spark, ClickHouse, Grafana | `realtime_dw_demo.ipynb`, Grafana dashboard |
| `08_olap_dashboard/` | OLAP operations, Power BI views and guide | `OLAP_OPERATIONS.md`, `figures/O*.png` |
| `09_mining/` | Regression, decision tree, association rules | `01_regression.ipynb`, `02_decision_tree.ipynb`, `03_association_rules.ipynb` |
| `ppt/` | Auto-generated deck (one slide per chart) | `Water_Quality_DW_Analytics.pptx` |
| `docs/` | Project log, demo script, this guide | `PROJECT_LOG.md` |

Every folder has a **GUIDE.md** that explains its terms in plain language.

---

## 3. Docker: what it is and the commands

### 3.1 What Docker does for us
- **Docker** runs programs inside **containers**: small, ready-made boxes, each with one program (PostgreSQL, Kafka, Spark, ClickHouse, Grafana).
- **Docker Compose** starts a **group** of containers from a recipe file, `docker-compose.yml` (which programs, ports, memory, connections).
- **Why we use it:** one command starts a whole warehouse; the setup is the same on every laptop; nothing is installed into Windows; it is how companies run such systems.
- **Where the code runs:** everything runs **on the laptop**. The data never leaves it, and GitHub stores only code and results.

### 3.2 Memory rule
Docker has **3.9 GB**, so **run one warehouse at a time**: batch about 2 GB, real-time about 3 GB.

### 3.3 Commands (run from the `EDA_project` folder)
| Purpose | Command |
|---|---|
| Start the **batch** warehouse | `docker compose -f 05_dw_batch/docker-compose.yml up -d` |
| Check the batch warehouse (11 PASS lines) | `python 05_dw_batch/etl/etl_batch.py validate` |
| Run and time the analytical queries | `python 05_dw_batch/etl/etl_batch.py queries` |
| Demo the incremental load (safe to repeat) | `python 05_dw_batch/etl/etl_batch.py incremental` |
| Stop the batch warehouse (keeps data) | `docker compose -f 05_dw_batch/docker-compose.yml stop` |
| Start the **real-time** stack (wait ~60 s) | `docker compose -f 07_dw_realtime/docker-compose.yml up -d` |
| Empty the previous real-time run | `docker exec wq_clickhouse clickhouse-client --user wq --password wq_local_dev -q "TRUNCATE TABLE wq_rt.events"` |
| … and the rejected table | `docker exec wq_clickhouse clickhouse-client --user wq --password wq_local_dev -q "TRUNCATE TABLE wq_rt.rejected"` |
| Start the live replay (~2.5 min) | `python 07_dw_realtime/producer/producer.py --rate 150 --inject-invalid 25` |
| Stop the real-time stack | `docker compose -f 07_dw_realtime/docker-compose.yml stop` |
| See what is running | `docker ps` |
| Read a container's messages | `docker logs wq_spark` |

| Command word | Meaning |
|---|---|
| `-f <file>` | Use this recipe file |
| `up -d` | Start in the background (*detached*); the data is kept |
| `stop` | Switch off; everything is remembered |
| `down` | Remove the containers (data volumes kept); **`down -v` also deletes the data, so don't use it before the demo** |
| `exec` | Run a command **inside** a running container |
| `TRUNCATE TABLE` | Delete all rows but keep the table |

### 3.4 Addresses (always use **127.0.0.1**, because `localhost` hangs on this laptop through IPv6)
| Service | Open in the browser / tool | Login (local test values) |
|---|---|---|
| **Grafana** (live dashboard) | **http://127.0.0.1:3300** | anonymous view; admin / wq_local_dev to edit |
| **ClickHouse** (SQL page) | **http://127.0.0.1:18123/play** | wq / wq_local_dev |
| **PostgreSQL** (batch DW, for Power BI or pgAdmin) | server 127.0.0.1, port **5433**, database **wq_dw** | wq / wq_local_dev |
| **Spark** monitoring page | http://127.0.0.1:4040 | none |
| Kafka (used by the producer) | 127.0.0.1:9092 | none |

`ports: "3300:3000"` in the recipe means *laptop port 3300 → container port 3000*.

---

## 4. Batch data warehouse (what to say)
- **Grain:** one row in `fact_water_quality_result` = **one measured result, at one site, at one sampling time**. Daily summaries are a different grain, so they are kept out.
- **Model:** a **fact constellation** with star-shaped dimensions. The detail fact (3,772,033 rows) and a site × parameter × month fact (995,875 rows) share the dimensions **Date, Time, Monitoring Location (Region → State → Site), Characteristic (Group → Parameter), Organization/Method**.
- **ETL:** extract → **staging** → data-quality rules → **dimension lookup / new members** (surrogate keys) → fact → monthly fact → validation.
- **Incremental load:** December 2025 was held back. Loading it later added **23,189 rows and 53 new sites in about 15 s, without rebuilding.**
- **Validation:** **11 of 11 checks PASS**: no orphan keys, no duplicates, warehouse rows = curated rows, monthly totals = detail totals, value sums equal.
- **Speed evidence:** monthly trend **≈ 0.2 s from the monthly fact vs ≈ 6.5 s from the detail fact (≈ 30× faster)**.

## 5. Real-time data warehouse: the flow from scratch

> ⚠️ **It is a SIMULATION.** WQP is historical, so December 2025 is **replayed in time order** as live events, as the brief allows. The dashboard and every event say so.

```
① Producer ─► ② Kafka ─► ③ Spark Structured Streaming ─► ④ ClickHouse ─► ⑤ Grafana
 (sends)       (queues)    (checks + calculates, every 5 s)  (stores)        (shows, every 5 s)
```

| Step | Component | What it does | Simple analogy |
|---|---|---|---|
| ① | **Producer** (Python) | Reads December's clean results **sorted by sampling time**, turns each into a JSON **event**, sends 150 per second; 25 are broken on purpose for testing | A person sending SMS messages |
| ② | **Kafka** | Holds events in topic `wq.results.replay` (3 partitions, **key = site** so each site stays in order); **buffers** them if the next step is slow, so nothing is lost | A post-office conveyor belt |
| ③ | **Spark Structured Streaming** | Every **5 s** (micro-batch): parse JSON → **5 validation rules** → derive **exceedance**, **high-risk**, **alert level** from the documented thresholds → **1-hour event-time windows** with a **2-hour watermark** | An inspector and a calculator |
| ④ | **ClickHouse** | Fast analytical database: tables `events` (valid), `rejected` (bad + reason), `window_agg` (hourly summaries) | A fast filing cabinet |
| ⑤ | **Grafana** | Live dashboard that queries ClickHouse every 5 s | A car's dashboard |

**Event (JSON) example:**
`{"site_id": "Site B", "state": "Texas", "characteristic": "Dissolved oxygen", "result_value": 1.5, "event_time": "2025-12-12T10:20", "produced_at": "<now>", "simulation": true}`
- `event_time` = when the water was sampled; `produced_at` = when it was sent.

### 5.1 Worked example: 8 measurements through the pipeline
| # | Site / state | Parameter | Value | Spark result |
|---|---|---|---|---|
| 1 | A · Alabama | pH | 5.8 | valid → exceedance (< 6.5) → **HIGH RISK** (< 6.0) |
| 2 | A · Alabama | Temperature | 14 °C | valid → OK |
| 3 | B · Texas | Dissolved oxygen | 1.5 mg/L | valid → exceedance (< 5) → **HIGH RISK** (< 2) |
| 4 | B · Texas | Turbidity | 40 NTU | valid → **EXCEEDANCE** (> 25, not > 100) |
| 5 | C · Utah | pH | 7.6 | valid → OK |
| 6 | C · Utah | Temperature | 6 °C | valid → OK |
| 7 | D · Georgia | pH | −999 | ❌ **rejected**: physically impossible |
| 8 | E · Ohio | "Chlorine" | 2.0 | ❌ **rejected**: unknown characteristic |

**The KPIs on this example:** results received **6**; rejected **2**; exceedances **3** (events 1, 3, 4); high-risk **2** (events 1, 3); current pH = **7.6** (the newest pH); coverage pH 2 / temperature 2 / DO 1 / turbidity 1; top sites A, B, C with 2 each; poor-quality sites **none** (fewer than 5 results per site); alerts = events 3 and 1; window 12 Dec 10:00–11:00 = 3 of 6 = **50% exceedance**.

### 5.2 Two ideas explained simply

**(a) "9,000 events per minute": how fast the stream runs**
- The producer is told to send **150 events every second** (`--rate 150`).
- 150 per second × 60 seconds = **9,000 per minute**. That is the speed of the replay, i.e. the **throughput**.
- December has 23,189 results, so the whole month streams in 23,189 ÷ 150 ≈ **155 seconds (about 2.5 minutes)**. In real life those results arrived over 31 days; the replay compresses a month into minutes.
- The green bars on Grafana count events every 10 seconds (≈ 1,500) and multiply by 6 to show "per minute" (≈ 9,000).
- The speed is a setting: `--rate 50` would give ≈ 3,000 per minute and take ≈ 8 minutes.

**(b) The "1-hour window": a summary per hour of sample time**
- A **window** is a **time bucket**. Spark puts every event into the bucket of the **hour the water was sampled** (its *event time*), e.g. everything sampled on 12 Dec between 10:00 and 11:00 goes into the "12 Dec 10:00–11:00" bucket.
- For each bucket (and each parameter and region) Spark keeps a running summary: **how many results, how many exceedances, how many high-risk, average/max/min value**.
- Analogy: a shop sorting receipts into **hourly envelopes** by the time printed on the receipt, not by when the receipt reaches the office.
- **Why sample time and not arrival time?** In the replay, a whole month arrives in 2.5 minutes. If we grouped by arrival time, all of December would land in 2–3 buckets, which is useless. Grouping by **sample time** rebuilds December correctly, hour by hour. In a real feed it also handles **late events**: a reading sampled at 10:50 but arriving at 11:20 still goes into the 10:00–11:00 bucket.
- **Watermark (2 hours):** how long Spark keeps a bucket open for late events. After the stream has moved 2 hours of sample time past a bucket, Spark closes it and stops updating it. This keeps memory small.
- **Worked example:** events 1–6 of section 5.1 were all sampled between 10:00 and 11:00 on 12 Dec, so they form one window: 6 results, 3 exceedances, 2 high-risk, so **50% exceedance for that hour**.
- **On the dashboard:** the bottom chart adds the 24 hourly windows of each day together and shows **exceedance % per sample day** for December.

### 5.3 Thresholds used (same as the batch warehouse)
| Parameter | Exceedance | High risk | Source |
|---|---|---|---|
| Dissolved oxygen | < 5 mg/L | < 2 mg/L | EPA aquatic-life criteria |
| pH | < 6.5 or > 9.0 | < 6.0 or > 9.5 | EPA criterion (+ project margin) |
| Nitrate | > 10 mg/L as N | > 20 | EPA drinking-water limit (+ project) |
| Temperature | > 28 °C | > 32 °C | Project threshold |
| Turbidity | > 25 NTU | > 100 NTU | Project threshold |
| Conductivity | > 1,500 µS/cm | > 3,000 µS/cm | Project threshold |

---

## 6. The Grafana dashboard: every KPI explained (results of the full December replay)

| KPI | Simple question | How it is calculated | Our result | What it means |
|---|---|---|---|---|
| **Results received** | How many good measurements arrived? | count of `events` | **23,164** | + 25 rejected = **23,189 = every December result**; nothing lost |
| **KPI 1 · Results per minute** | How fast is data flowing? | events stored in the last 60 s (chart: per 10 s × 6) | **≈ 9,000 / min** during the run; **0** after it ends | Steady stream of 150 events/s; the first tall bar (≈ 22,000) was Spark catching up on events Kafka had buffered while Spark started |
| **KPI 4 · Exceedances** | How many broke a safety limit? | sum of `exceedance_flag` | **1,392** (6.0%) | In winter, **pH and turbidity** lead; fewer DO problems because cold water holds more oxygen |
| **KPI 3 · High-risk observations** | How many broke the danger limit? | sum of `high_risk_flag` | **495** | pH 218, conductivity 126 (salty coastal sites), DO 90 (< 2 mg/L), turbidity 59, temperature 2. Every high-risk result is also an exceedance: **897 + 495 = 1,392** |
| **Rejected by validation** | How many bad events were refused? | count of `rejected` | **25** | Exactly the 25 broken on purpose: 9 unknown parameter, 9 impossible value, 7 missing time. The validation rules work |
| **Pipeline latency** | How long from sending to showing? | median of `ingested_at − produced_at` | **≈ 4 s** (90% < 6 s, max 7.6 s) | Mostly the wait for Spark's 5-s micro-batch; a batch warehouse would show it only after the next monthly load |
| **KPI 2 · Current parameter values** | What is the newest value of each parameter? | value with the latest sample time per parameter | conductivity 142 µS/cm · DO 10.6 mg/L · nitrate 0.25 mg/L · temperature 10 °C · turbidity 2 NTU · pH 7.32 | All normal at the end of December (cold, well-oxygenated, clear water) |
| **KPI 6 · Parameter coverage** | How many results per parameter? | count per parameter | pH 6,302 · temperature 6,109 · DO 5,573 · turbidity 3,219 · conductivity 1,345 · nitrate 616 | All 6 parameters flowed; nitrate is rare because it needs a lab test |
| **KPI 5 · Top monitored sites** | Which sites sent the most? | count per site | Utah sites (UTAHDWQ), up to **635** | Automatic **loggers** send many readings; busy ≠ bad, so we also look at rates |
| **KPI 7 · Poor-quality sites** | Which sites exceed often? | sites with **≥ 5 results** and **≥ 30% exceedance** | Texas Gulf coast (TAMUCC ≈ 41%), Georgia rivers (50%), North Carolina, Washington, Oklahoma, Puerto Rico (60%) | Sites to inspect first. The batch rule (≥ 10, ≥ 50%) finds none in one winter month, so a documented real-time rule is used |
| **KPI 8 · Alerts** | What are the latest dangerous results? | high-risk events, newest first | recent low-DO alerts in **Louisiana** | The early-warning list, the purpose of the real-time warehouse |
| **Alerts by state** | Which states have the most high-risk results? | high-risk count per state | **South Carolina, Arizona, Washington** lead | Where to focus attention this month |
| **Spark event-time windows** | Exceedance % per sample day | Spark's 1-hour windows summed per day | one bar per December day | Rebuilt by **sample time**, though all processed in ≈ 2.5 min; single-day spikes come from days with few samples |

**Why some panels show "No data" after the run:** the charts and the latency tile follow the **time picker** (top right). If the replay ended before that time range, choose *Last 6 hours* or re-run the replay. **KPI 1 = 0** after the run is correct: nothing new is arriving.

**Consistency check (strongest point):** December in the real-time warehouse vs the batch warehouse: **same 495 high-risk results, same 4,565 sites**; 23,164 + 25 = 23,189 results; exceedances differ by 1 (one corrupted test event). **Two independent pipelines agree.**

### 6.1 Real-time terms
| Term | Simple meaning |
|---|---|
| Streaming | Processing data continuously as it arrives |
| Event | One small message describing one measurement |
| JSON | A simple "name: value" text format |
| Topic / partition / key | A named queue / its parallel lanes / what decides the lane (site) |
| Micro-batch / trigger | Spark processes whatever arrived every 5 s |
| Event time vs processing time | When it was sampled vs when it was processed |
| Window | A time bucket (1 hour) for summarising |
| Watermark | How long to wait for late events (2 hours) |
| Checkpoint | Spark's saved progress, so a restart doesn't duplicate or lose data |
| Latency | Delay from sending to showing |
| Throughput | Events processed per minute |
| Validation | Automatic checks that refuse bad data |
| Alert | A flagged high-risk result |

---

## 7. ClickHouse: run SQL live
**Open:** **http://127.0.0.1:18123/play**, enter user **wq** and password **wq_local_dev** at the top right, type a query, and press **Ctrl + Enter**.

**Totals (= the Grafana tiles)**
```sql
SELECT count() AS results, sum(exceedance_flag) AS exceedances, sum(high_risk_flag) AS high_risk, uniqExact(site_id) AS sites
FROM wq_rt.events
```
**Rejected events and why**
```sql
SELECT reason, count() AS events FROM wq_rt.rejected GROUP BY reason ORDER BY events DESC
```
**Latency**
```sql
SELECT round(quantile(0.5)(d), 2) AS median_s, round(quantile(0.9)(d), 2) AS p90_s, round(max(d), 2) AS max_s
FROM (SELECT dateDiff('millisecond', produced_at, ingested_at) / 1000 AS d FROM wq_rt.events)
```
**By parameter**
```sql
SELECT characteristic, count() AS results, sum(exceedance_flag) AS exceedances, sum(high_risk_flag) AS high_risk,
       round(100 * avg(exceedance_flag), 1) AS exceedance_pct
FROM wq_rt.events GROUP BY characteristic ORDER BY exceedances DESC
```
**Latest alerts**
```sql
SELECT event_time, site_id, state, characteristic, result_value, unit, alert_level
FROM wq_rt.events WHERE high_risk_flag = 1 ORDER BY event_time DESC LIMIT 20
```
**Poor-quality sites**
```sql
SELECT site_id, any(state) AS state, count() AS results, round(100 * avg(exceedance_flag), 1) AS exceedance_pct
FROM wq_rt.events GROUP BY site_id HAVING results >= 5 AND exceedance_pct >= 30 ORDER BY exceedance_pct DESC
```
**Spark's 1-hour windows** (`FINAL` = show only the latest version of each window)
```sql
SELECT window_start, characteristic, region, results, exceedances, high_risk
FROM wq_rt.window_agg FINAL ORDER BY window_start, characteristic LIMIT 50
```
**One raw event**
```sql
SELECT * FROM wq_rt.events LIMIT 5
```

---

## 8. Other parts: key numbers to quote
| Part | Result |
|---|---|
| Profiling | 31% of temperatures in °F; 18.6% daily summaries (a different grain); only ~3.8% real duplicates; missing values depend on the organization |
| Cleaning | 0 rows deleted; **3,772,033 analysis-ready (76.1%)**; Decision Tree imputes equipment (99% / 88% on unseen organizations); water type and time band left *Not Reported* (the model didn't beat simple rules enough); measured values never imputed |
| EDA | Typical water: 17.3 °C, DO 8.0 mg/L, pH 7.76; **DO exceedance 25.9% in summer vs 7.7% in winter**; South 16.4% vs Midwest 4.2%; temperature–DO correlation −0.63 |
| Feature selection | 6 methods + consensus vote; regression: temperature, previous DO, pH, latitude, water type, month, season, region |
| OLAP | Roll-up, drill-down, slice, dice, pivot, CUBE, GROUPING SETS, ROLLUP (16 queries); region roll-up: Territory 24.3%, South 16.4%, West 3.5% |
| Regression (DO) | Gradient Boosting **R² 0.64, RMSE 1.64 mg/L**; linear 0.51; temperature only 0.20 (test: Jul–Dec 2025) |
| Decision tree (HighRisk) | Pruned 275-leaf tree: **recall 91.7%**, ROC-AUC 0.92; key rule: previous result high-risk → likely high-risk again |
| Association rules | Apriori = FP-Growth (7,560 itemsets); top rule **Temperature + South + Summer → Exceedance, lift 5.5** |
| Architecture | Hybrid recommendation: batch for history and mining, distributed for multi-agency big data, real-time for alerts within seconds |

## 9. Demo order (15–20 min)
1. Slides 1–4: the project and the lifecycle.
2. Profiling + cleaning charts (P5, P8, C11).
3. EDA + feature selection (E3f, E6c, F2).
4. **Live:** batch warehouse `validate` + `queries`; explain grain, constellation, incremental load.
5. **Live:** stop batch → start real-time → Grafana → run the producer → explain the KPIs as they climb → ClickHouse queries 1–2.
6. OLAP charts; mining results (R1, D2, A4).
7. Architecture comparison → hybrid recommendation → close.

**Backup if something fails live:** the screenshots in `07_dw_realtime/figures/` and the executed notebooks.

## 10. Likely questions
| Question | Answer |
|---|---|
| Is the real-time feed real? | No, it is a labelled replay of historical data, allowed by the brief. |
| Why Kafka between the producer and Spark? | It buffers and orders events, so nothing is lost if Spark is slow or restarts. |
| Why event time and a watermark? | Windows use the sample time, so late or out-of-order events still land in the right hour; the watermark limits how long we wait. |
| Why is latency ~4 s? | Spark's 5-second micro-batch plus the insert time; a shorter trigger lowers it. |
| How do you know the numbers are right? | The real-time totals match the batch warehouse for December (same 495 high-risk, same 4,565 sites). |
| Why not delete nulls? | Measurements are 99.75% present; the gaps are in descriptive fields. Rules/models fill them only where proven, otherwise *Not Reported*. |
| Why a fact constellation? | Two grains (result, site-month); small dimensions; the monthly fact is ~30× faster for trends. |
| How do you avoid leakage? | Chronological train/test split; previous values come only from earlier days; the own value, band and flag are excluded. |
| Why is decision-tree accuracy lower than "always no"? | High-risk is rare (4.5%); recall 92% and ROC-AUC 0.92 are the right measures for safety. |
| Is distributed always faster? | No. On one machine the coordination overhead is high; it pays off with more data and more machines. |
