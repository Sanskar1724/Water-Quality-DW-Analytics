# Water Quality DW & Analytics
### Batch, Distributed & Real-Time Data Warehouse with OLAP, Dashboards and Data Mining

TY B.Tech Data Warehousing project built on the **Water Quality Portal (WQP)** dataset (USGS + U.S. EPA + National Water Quality Monitoring Council): **4,958,238** physical/chemical results from **50,476** monitoring sites and **486** organizations, covering **Jan 2024 – Dec 2025**.

Parameters: **water temperature, dissolved oxygen, pH, turbidity, conductivity, nitrate**.

📖 **New here?** Every folder has a `GUIDE.md` that explains its terms in plain language, and [docs/PROJECT_LOG.md](docs/PROJECT_LOG.md) records every step taken, in order.

---

## Repository layout

```
├── README.md
├── docs/PROJECT_LOG.md        # running record of everything done (what, why, result, files)
├── requirements.txt
├── resultphyschem/            # the 2.58 GB dataset (kept locally, NOT uploaded to GitHub)
│
├── 00_previous_work/          # ARCHIVE: all work before 18 Nov 2026, kept as-is
│                              #   (Phase 1 notebooks, 600K-row trial charts/tables, first plan)
│
│   ── new work, one folder per step ──
├── 01_profiling_curation/     # profiling + cleaning + Decision Tree / Naive Bayes imputation
├── 02_eda/                    # charts with justification and inference
├── 03_feature_selection/      # one feature-selection step used by all models
├── 04_dimensional_model/      # star, snowflake, fact constellation
├── 05_dw_batch/               # PostgreSQL batch warehouse (initial + incremental load)
├── 06_dw_distributed/         # Spark → Citus distributed warehouse
├── 07_dw_realtime/            # Kafka → Spark Streaming → ClickHouse → Grafana (simulated replay)
├── 08_olap_dashboard/         # OLAP queries, Power BI dashboard, 10 findings
├── 09_mining/                 # analytical mart → regression, decision tree, association rules
├── 10_architecture_eval/      # batch vs distributed vs real-time comparison
└── ppt/                       # one slide per output
```
Numbered folders are created as each step is built; see the log for progress.

---

## Project status

| Step | Status |
|---|---|
| 00 Previous work (Phase 1 notebooks, 600K-row trial) | ✅ archived |
| 01–10, PPT | ⏳ in progress (see [docs/PROJECT_LOG.md](docs/PROJECT_LOG.md)) |

---

## Dataset
Put `resultphyschem.csv` at `resultphyschem/resultphyschem.csv` in the repo root. It is too large for GitHub and is excluded by `.gitignore`.

**Citation:** Water Quality Portal. Washington (DC): National Water Quality Monitoring Council, United States Geological Survey (USGS), Environmental Protection Agency (EPA); 2021. https://doi.org/10.5066/P9QRKUVJ. Data downloaded via https://www.epa.gov/waterdata/water-quality-data-download.
