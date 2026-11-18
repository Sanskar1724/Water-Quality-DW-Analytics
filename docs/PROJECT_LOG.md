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
