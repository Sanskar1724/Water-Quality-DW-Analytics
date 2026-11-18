# Project Log: Water Quality DW & Analytics

This file records **everything done on the project**, in order: what was done, why, what we found, and which files changed.
It is written so that anyone, including people without a technical background, can follow the story of the project.

**How to read an entry**
- **What:** the action taken
- **Why:** the reason it was needed
- **Result:** what we found or produced (with real numbers)
- **Files:** where to look

**Every folder also has a `GUIDE.md`** that explains, in simple words, the terms used in that folder, how they are used, and why they matter.

---

## 2026-10-27: Phase 1 notebooks created (before this log started)
- **What:** Wrote two notebooks: one to *profile and clean* the data, one to *explore* it with charts (EDA).
- **Why:** Before building anything, we need to know what is wrong with the data and what it looks like.
- **Result:** The notebooks were tested on only the **first 600,000 rows** (a quick trial run). The tables and charts in `reports/` come from that trial, which covers **2024 only**.
- **Files:** `notebooks/phase1_curation_eda/`, `docs/data_dictionary.md`, `docs/project_phases.md`

## 2026-11-18: Project brief read and understood
- **What:** Read the assignment document (`16_water_quality_TY_BTech_DW_Project_Assignment.docx`).
- **Why:** To know exactly what must be delivered.
- **Result:** The project has 10 parts (A–J) worth 100 marks. It needs **three data warehouses** (batch, distributed and real-time), OLAP, dashboards and three data-mining models, all connected as one pipeline.

## 2026-11-18: Full dataset checked
- **What:** Read the full dataset file `resultphyschem.csv` (2.58 GB) piece by piece ("in chunks"), because it is too big to open in one go.
- **Why:** To confirm the dataset meets the brief and to get the true numbers.
- **Result:**

| Item | Value |
|---|---|
| Rows (measurements) | 4,958,238 |
| Monitoring sites | 50,476 |
| Organizations that collected data | 486 |
| Period | Jan 2024 – Dec 2025 (all 24 months present) |
| Parameters | Water temperature 2.86M, dissolved oxygen 773K, pH 741K, turbidity 372K, conductivity 157K, nitrate 53K |
| Data source systems | STORET 99.8%, NWIS 8,477 rows |

- **Important finding:** The existing Phase 1 results used only 600K of the 4.96M rows, so they **must be re-run on the full data** before the warehouse is built.
- **Units found:** temperature appears in both °C and °F, conductivity in three different units, and pH is sometimes wrongly reported in mV. The cleaning notebook already handles all of these.

## 2026-11-18: Faculty review targets recorded
The faculty asked for:
1. Profiling charts with our **own written inferences**.
2. Missing values treated with **justification**, using rule-based methods and **Decision Tree / Naive Bayes** models.
3. **Feature selection** applied across the whole project.
4. Every chart with justification and inference, and **a PPT slide for every output**.
5. **Live warehouse demos.**
6. Batch DW, distributed DW and real-time DW kept in **separate folders**.

Status reported at review: profiling, regression and distributed DW shown. **Pending:** batch DW, real-time DW, dashboard, decision tree, association rules. **Demo: Friday 2026-11-20.**

## 2026-11-18: GitHub repository set up
- **What:** Connected the project to the new GitHub repository https://github.com/Sanskar1724/Water-Quality-DW-Analytics and uploaded the existing work. The old repo (`EDA_Project`) is kept only as a backup link.
- **Why:** One shared place where the team and faculty can always see the latest version.
- **Note:** The dataset itself (2.58 GB) is **not** uploaded; GitHub is for code and results. The trial-run charts are also held back until the full-data run replaces them.

## 2026-11-18: Laptop capacity checked
- **What:** Checked the computer's resources.
- **Result:** 7.7 GB RAM, 12 CPU cores, Docker running with 3.9 GB of memory, Java 26.
- **Impact on the plan:**
  - The full dataset won't fit in memory all at once, so we read only the needed columns and store text compactly.
  - Each warehouse runs in Docker **one at a time**.
  - Spark runs inside Docker, because Spark does not support Java 26.

## 2026-11-18: Implementation plan agreed
12 steps: setup → profiling → cleaning + DT/NB imputation → EDA → feature selection → dimensional modelling → batch DW → distributed DW → real-time DW → OLAP + dashboard → data mining → architecture evaluation + PPT + demo.
Working rule: **explain each step first, then build it, then walk through the results**, and log it here with a `GUIDE.md` in its folder.

## 2026-11-18: Repository reorganised (old work archived, new work separate)
- **What:** Moved **all existing work** into one folder, `00_previous_work/`: the Phase 1 notebooks, the trial-run charts and tables, the data dictionary, the first plan, data notes and the assignment document. Nothing inside was edited. New work will go into numbered folders (`01_…` to `10_…`, `ppt/`) at the top level.
- **Why:** To avoid mixing two structures. Anyone can see at a glance what was done before and what is new.
- **How:** Files were moved with `git mv`, which keeps their full change history. `.gitignore` was updated so the dataset stays excluded at the new paths and small result tables (`tables/*.csv`) are still uploaded.
- **Also:** The trial-run charts and tables (600K rows, 2024 only) are now uploaded **inside the archive**, clearly labelled as a trial in `00_previous_work/GUIDE.md`. The README was rewritten to explain the new layout.
- **Files:** `00_previous_work/` (+ `GUIDE.md`), `README.md`, `.gitignore`

## 2026-11-18: Step 0, setup
- **What:** Created the step folders (`01_profiling_curation` … `10_architecture_eval`, `ppt`). Installed and listed all libraries in `requirements.txt` (DuckDB, scikit-learn, mlxtend, statsmodels, psycopg2, kafka-python, clickhouse-connect, python-pptx).
- **What:** Made a one-time compressed copy of the dataset: `data/raw_parquet/wq_raw.parquet`. It has the same 4,958,238 rows × 81 columns, with all values kept as original text. **2.59 GB → 228 MB** in 61 seconds. It is not uploaded to GitHub.
- **Why:** The laptop has 7.7 GB of RAM. DuckDB plus Parquet let us query the full file without loading it all into memory.

## 2026-11-18: Step 1, data profiling on the full dataset
- **What:** Built and ran `01_profiling_curation/01_data_profiling.ipynb` on **all 4.96M rows** (about 40 seconds). It has 17 sections, 16 charts and 31 tables, and every chart has a written inference. Also wrote `01_profiling_curation/GUIDE.md` (30 terms explained simply).
- **Key results:**

| Check | Result |
|---|---|
| Complete columns | 11 of 81; 5 columns completely empty |
| Core identifiers (site, date, parameter, organization) | 0% missing |
| Measured value missing | 0.25% (12,274), all with a non-detect note |
| Time of day missing | 28.7% (1.42M) |
| Water type / collection method / fraction missing | 78% / 63% / 58% |
| Exact duplicates / repeated result IDs | 0 / 0 |
| Likely real duplicates (field visits) | 186,497 (3.8%) |
| Daily-summary rows (mean/min/max/7DADM), a different grain | 921,023 (18.6%) |
| Rows needing unit conversion | 902,542 (18.2%), mainly 885K temperatures in °F |
| Unusable units (e.g. pH in mV) | 42,481 (0.9%) |
| Physically impossible values | 14,780 (0.3%) |
| Quality-control rows / rejected / suspect | 29,108 / 175 / 91,600 |
| Sites with valid coordinates | 49,063 of 50,476 (97.2%) |
| Busiest 10% of sites hold | 76.2% of results |

- **Corrections made during the work (recorded for honesty):**
  1. The first duplicate check flagged 25.9% of rows. Investigation showed most were **logger readings without a time** (Wisconsin DNR alone ≈ 380K) and **depth profiles**, not duplicates. The check was redesigned to separate likely duplicates from genuine repeated readings.
  2. pH units were first counted wrongly. 708K pH rows store the unit as the text `None` (correct, since pH has no unit), and the rule was fixed.
  3. The coordinate check was tightened after the map showed US sites appearing in Asia (missing minus sign): 20 sites, 1,058 rows.
- **Why it matters:** The issue list (`tables/P16_profiling_issue_list.csv`) is the input to Step 2. Missing labels follow organization patterns (MAR), which is the justification for Decision Tree / Naive Bayes imputation.
- **Files:** `01_profiling_curation/` (notebook, `figures/`, `tables/`, `GUIDE.md`, `_build/`), `requirements.txt`

## 2026-11-18: Step 2, data curation and missing-value treatment (DT vs NB)
- **What:** Built and ran `01_profiling_curation/02_data_curation_imputation.ipynb` on all 4.96M rows. It produces **`data/processed/wq_curated.parquet`** (134 MB, every row kept, flags + derived attributes + State/Region), the data-quality report in the brief's format, and the DT vs NB vs mode comparison.
- **Downloaded (with approval):** US state boundaries, `data/reference/us-states.json` (89 KB, from the PublicaMundi MappingAPI repository on GitHub). Used to place each site in its state, then its US Census region.
- **Key results:**

| Item | Result |
|---|---|
| Rows deleted | **0** (reconciliation passed exactly) |
| Analysis-ready rows | **3,772,033 (76.1%)** |
| Daily summaries (separate grain) | 908,630 |
| Duplicate copies flagged | 186,285 |
| Temperatures °F → °C / "°C" corrected as °F | 885,447 / 10,848 |
| Impossible values (raw units → after unit fixes) | 14,780 → 5,014 |
| Sites with a US state | 96.6% (90.5% inside the boundary, 6.2% nearest within ~25 km) |
| Equipment group imputed by Decision Tree | 2.68M rows (accuracy 99.1% random / 88.1% unseen orgs; mode 47%) |
| Water type | Rule (same site) 405K; model **not used** (gain over the 97% mode only +0.3 to +2.1 points) → Not Reported |
| Time band | Rule (summary = whole day) 921K; model **not used** (66.6% < 70%) → Not Reported |
| Exceedance rate | DO 18.2% · turbidity 10.5% · pH 8.7% · conductivity 6.1% · temperature 3.4% · nitrate 3.3% |

- **Problems met and fixed (recorded honestly):**
  1. The first full run **filled the L: drive** (a 5.6 GB work database, because every stage was kept as a full copy). Fixed by deleting each stage once the next exists and using small lookup tables for model inputs; the work database now deletes itself.
  2. The before/after check showed conductivity up to 272,000,000 µS/cm and turbidity 97,225 NTU still passing. **Physical upper limits were added** (turbidity ≤ 10,000 NTU, conductivity ≤ 200,000 µS/cm, nitrate ≤ 100 mg/L as N) and the notebook was re-run. Conductivity skewness fell from 67 to 6.7.
  3. Two small code errors (a SQL reserved word, nested quotes) were fixed.
- **Decision rule for imputation (fixed before seeing results):** use the best model only if it is ≥ 70% accurate on the matching test **and** at least +10 points better than the mode; otherwise *Not Reported*. Two tests were used: random (organizations seen) and grouped (organizations never seen).
- **Files:** `01_profiling_curation/02_data_curation_imputation.ipynb`, `tables/C*.csv`, `figures/C*.png`, `GUIDE.md` (Step 2 section), `_build/`
