# Demo Script: Water Quality DW & Analytics (Friday 20 Nov 2026)

**Total time:** ~15–20 minutes + questions. **Open beforehand:** the PPT (`ppt/Water_Quality_DW_Analytics.pptx`), VS Code / Jupyter with the repo, Docker Desktop, the GitHub repo page.

---

## 0 · Before the faculty arrives (10 minutes earlier)
Run these from the repository folder `EDA_project` (PowerShell or Git Bash):

```bash
docker compose -f 05_dw_batch/docker-compose.yml up -d
```
Check that the batch warehouse answers (should print 11 PASS lines):
```bash
python 05_dw_batch/etl/etl_batch.py validate
```
Docker has only 3.9 GB, so **run one warehouse at a time**. To switch to the real-time demo (step 6 below):
```bash
docker compose -f 05_dw_batch/docker-compose.yml stop
```
```bash
docker compose -f 07_dw_realtime/docker-compose.yml up -d
```
Wait about 60 s, then open **http://localhost:3000** (Grafana). Before the live replay, empty the old run so the numbers start from 0:
```bash
docker exec wq_clickhouse clickhouse-client --user wq --password wq_local_dev -q "TRUNCATE TABLE wq_rt.events"
```
```bash
docker exec wq_clickhouse clickhouse-client --user wq --password wq_local_dev -q "TRUNCATE TABLE wq_rt.rejected"
```

---

## 1 · Opening (1 min): slides 1–4
**Say:** *"Our project builds one integrated analytics platform for U.S. Water Quality Portal data: 4.96 million measurements of six parameters (temperature, dissolved oxygen, pH, turbidity, conductivity and nitrate) from 50,476 sites over 2024–2025. The data goes through profiling, cleaning, a dimensional data warehouse in three forms (batch, distributed and real-time), OLAP and dashboards, and finally data-mining models that read from the warehouse."*

Show the **lifecycle slide**: Raw → Profiling → Curation → DW → OLAP → Mart → Mining → Evaluation.

## 2 · Data profiling (2 min): `01_profiling_curation/01_data_profiling.ipynb`
**Show:** chart P5 (missingness heat map by organization) and P8 (units).
**Say:**
- "We profiled **before** cleaning, on all 4.96M rows, with DuckDB because the laptop has 7.7 GB of RAM."
- "Key findings: **31% of temperatures were in °F**, **18.6% of rows were daily summaries** (a different grain), and only about **3.8% of rows were real duplicates**. A naive check said 26%, but most were logger readings without a time."
- "Missing values follow **who collected the data** (P5). Some organizations never fill a field. That pattern is our justification for model-based imputation."

## 3 · Cleaning + missing values with DT / Naive Bayes (2 min): `02_data_curation_imputation.ipynb`
**Show:** chart C11 (DT vs NB vs mode) and the data-quality report table (C14).
**Say:**
- "Nothing was deleted: 4,958,238 rows in, 4,958,238 out. **3,772,033 are analysis-ready**; each excluded row has exactly one documented reason."
- "Missing values in three levels: **rules first** (e.g. a site's water type), then **Decision Tree vs Naive Bayes vs mode**, tested on a random split **and on organizations never seen**."
- "The Decision Tree won and was used for **equipment group: 99% accurate, 88% on unseen organizations**. For **water type** the simple guess was already 97% right, so the model added too little; for **time band** it reached only 67%. Those stay *Not Reported*. We never impute measured values."

## 4 · EDA + feature selection (2 min): `02_eda`, `03_feature_selection`
**Show:** E3f (seasons) and E6c (temperature vs DO with the saturation curve), then F2.
**Say:**
- "Summer is the risk season: **DO exceedance 25.9% in summer vs 7.7% in winter**. The South is worst (**16.4%** vs Midwest 4.2%)."
- "Temperature vs DO correlation is **−0.63** and follows the physics saturation curve, which shows our cleaned data is valid."
- "**Feature selection** used 6 methods (correlation/VIF, mutual information, ANOVA/chi-square, RFE-CV, Lasso, Random Forest + permutation importance) and a **consensus vote**. One shared `selected_features.json` feeds all three models, with leakage excluded."

## 5 · Dimensional model + batch warehouse (3 min): **LIVE**
**Show:** `04_dimensional_model/DESIGN.md` (star, snowflake, constellation table), then run:
```bash
python 05_dw_batch/etl/etl_batch.py validate
```
```bash
python 05_dw_batch/etl/etl_batch.py queries
```
**Say:**
- "Grain: **one row = one measured result at one site and time**. We chose a **fact constellation**: a detail fact with 3.77M rows plus a site-month fact, sharing star dimensions (Date, Time, Location, Characteristic, Organization/Method)."
- "ETL: extract → staging → data-quality rules → dimension lookup / new members → fact → monthly fact."
- "**Incremental load:** December 2025 was held back and loaded later: **23,189 rows and 53 new sites in about 15 seconds, without rebuilding.** All **11 validation checks pass**."
- "The monthly trend takes about **0.2 s on the aggregate fact vs about 6.5 s on the detail fact**, around 30× faster, which is evidence for the constellation design."
- (If asked) "We found and fixed three performance problems with `EXPLAIN`: missing statistics, a null-safe join, and a self-referencing NOT EXISTS. The fact load went from more than 10 minutes to 42 seconds."

## 6 · Real-time warehouse (3 min): **LIVE** (switch Docker as in step 0)
Open Grafana **http://localhost:3000**, then run:
```bash
python 07_dw_realtime/producer/producer.py --rate 150 --inject-invalid 25
```
**Say while the numbers climb:**
- "This is a **simulation**: historical December 2025 results replayed in time order. The banner says so."
- "Producer → **Kafka** (key = site, so each site stays in order) → **Spark Structured Streaming** every 5 s (validation, exceedance/high-risk flags, 1-hour event-time windows with a watermark) → **ClickHouse** → **Grafana** refreshing every 5 s."
- "All 8 KPIs are live: results per minute, current values, high-risk, exceedances, top sites, coverage, poor sites, alerts."
- "We injected **25 broken events on purpose**, and the rejected counter catches exactly 25."
- "Latency is about **4 seconds** median. The stream's totals **match the batch warehouse** for December (same 495 high-risk results), so two independent pipelines agree."

(Backup if anything fails: show `07_dw_realtime/figures/G0*_dashboard*.jpg` and `realtime_dw_demo.ipynb`.)

## 7 · OLAP + dashboard (2 min): `08_olap_dashboard/`
**Show:** `OLAP_OPERATIONS.md` and the O-charts (e.g. O01 roll-up geography, O11 CUBE), then the Power BI file if it is ready.
**Say:**
- "All mandatory OLAP operations run on the warehouse: **roll-up, drill-down, slice, dice, pivot, CUBE, GROUPING SETS, ROLLUP**. Example roll-up to region: Territory 24.3% (warm tropical water), South 16.4%, West 3.5%."
- "Power BI connects to the `bi` views in PostgreSQL. The dashboard has 4 pages: executive, site & geography, temporal and parameters."

## 8 · Data mining (3 min): `09_mining/`
**Show:** R1 (model comparison), D2 (confusion matrix + ROC), A4 (10 rules).
**Say:**
- "All models read the **analytical mart built from the warehouse**, never the raw file. That's the brief's integration rule."
- "**Regression (DO):** Gradient Boosting **R² 0.64, RMSE 1.64 mg/L** on unseen months (Jul–Dec 2025, chronological split); linear 0.51; temperature alone 0.20."
- "**Decision tree (HighRisk):** chronological split, tuned depth and pruning. The best-F1 tree had 1,821 leaves and memorised, so a simplicity rule chose a **275-leaf pruned tree** with **recall 91.7%** and ROC-AUC 0.92. It catches 9 of 10 dangerous results. Clearest path: *previous result high-risk + single-parameter programme → 58% high-risk*."
- "**Association rules:** Apriori and FP-Growth found the same 7,560 itemsets. We removed 933 definitional rules. **Top rule: Temperature + South + Summer → Exceedance, lift 5.5.** 9 of the 10 rules involve summer."

## 9 · Architecture comparison + recommendation (1 min)
| | Batch DW | Distributed DW | Real-time DW |
|---|---|---|---|
| Data arrival | Periodic loads | Large / partitioned | Continuous events |
| Our measured result | Initial 3.75M rows in ~4–6 min; incremental month in ~15 s; queries 0.2–9 s | (teammate's Citus demo) | ~9,000 results/min, ~4 s latency |
| Best for | Historical reporting, mining | Multi-agency big data | Rapid exceedance alerts |

**Say:** *"We recommend a **hybrid**: the batch warehouse for long-term reporting and mining; distributed (Citus) when data grows to multi-agency, multi-year scale; and the real-time stream for contamination / exceedance alerts within seconds."*

## 10 · Close (30 s)
*"Everything is reproducible: every folder has a plain-language GUIDE.md, every step is in `docs/PROJECT_LOG.md`, and the code is on GitHub."*

---

## Likely questions, with short answers
| Question | Answer |
|---|---|
| Why not delete nulls? | Most gaps are in descriptive fields; measurements are 99.75% present. Deleting would lose real data. We filled by rule/model where proven accurate, otherwise *Not Reported*. |
| Why Decision Tree over Naive Bayes? | Higher accuracy everywhere; NB collapsed to 23% on unseen organizations because it assumes independent clues. |
| What is the grain? | One measured result at one site, one time. Daily summaries are a different grain, so they are kept out of the detail fact. |
| Why a fact constellation, not a snowflake? | Two natural grains (result, site-month); dimensions are small (≤ 49K rows) while the fact is 3.77M, so snowflaking saves almost nothing and adds joins. The monthly fact is about 30× faster for trends. |
| How is the incremental load safe? | Natural-key lookup for dimensions, a unique `result_id` index, staging de-duplication, and 11 reconciliation checks. |
| Is the real-time feed real? | No, it is a replay simulation (the brief allows this), labelled on the dashboard and in every event. |
| How do you avoid data leakage? | Chronological train/test split; the previous result comes only from earlier days; the own value, band and flag are excluded from features. |
| Why is decision-tree accuracy (76%) lower than "always no"? | High-risk is rare (4.5%); accuracy is misleading. Recall (92%) and ROC-AUC (0.92) are the right measures for safety alerts. |
| Is distributed always faster? | No. On one laptop the coordination overhead is large; distribution pays off with more data and more machines. |
