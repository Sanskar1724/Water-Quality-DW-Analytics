# Guide: `00_previous_work/`

## What this folder is (in plain words)
This folder holds **all the work done before 18 Nov 2026**, kept exactly as it was.
Think of it as an **archive shelf**: nothing here is deleted or rewritten, so anyone can see what was done first.
All **new work** lives in the numbered folders at the top of the repository (`01_…`, `02_…`, and so on).

> ⚠️ **Important:** the charts and tables in `reports/` come from a **trial run on the first 600,000 rows only** (about 12% of the data, year 2024 only).
> They are useful as a first look, but the **final numbers come from the full 4.96 million rows** in the new folders.

## What is inside

| Item | What it is | In simple words |
|---|---|---|
| `notebooks/phase1_curation_eda/01_data_profiling_and_curation.ipynb` | Cleaning notebook | Checks the raw data for problems and fixes them |
| `notebooks/phase1_curation_eda/02_exploratory_data_analysis.ipynb` | EDA notebook | Draws charts to understand the data |
| `notebooks/phase2_…`, `phase3_…` | Empty placeholders | Plans only; the real work is now in the new folders |
| `reports/figures/` | 20 chart images | Pictures produced by the two notebooks (trial run) |
| `reports/tables/` | 45 small CSV tables | Numbers behind the charts and the data-quality report (trial run) |
| `docs/data_dictionary.md` | Data dictionary | A glossary of every column in the data |
| `docs/project_phases.md` | First project plan | The original 3-phase plan |
| `data/README.md` | Dataset notes | Where the data came from and how to cite it |
| `16_water_quality_…docx` | The assignment | The faculty's project brief |

## Terms used in this folder

| Term | Simple meaning | Everyday analogy | How it's used here | Why it matters |
|---|---|---|---|---|
| **Dataset** | The collection of all measurements | A huge spreadsheet | `resultphyschem.csv`: 4.96M water measurements | Everything in the project starts from it |
| **Notebook (.ipynb)** | A file mixing explanations, code and results | A lab notebook where you write the method and paste the results | The two Phase 1 notebooks | The team can read the reasoning next to the code |
| **Data profiling** | Checking the data's health *before* fixing it | A doctor's check-up before treatment | Counting missing values, duplicates and wrong units | You can't fix what you haven't measured |
| **Data curation / cleaning** | Fixing or flagging bad data | Sorting fruit and removing the rotten ones | Converting °F to °C, flagging impossible pH values | Bad data gives wrong conclusions |
| **Missing value** | A blank cell where information should be | A form with an empty field | e.g. no time of day recorded | Too many blanks can bias results |
| **Duplicate** | The same record appearing twice | Being counted twice in a class headcount | Same site, time, parameter and value repeated | Inflates counts and averages |
| **Outlier** | A value far away from the rest | One 7-foot student in a class | e.g. extremely high turbidity after a storm | Could be an error *or* a real event; we flag it, not delete it |
| **Unit standardisation** | Putting everything in the same unit | Converting all prices to rupees before comparing | °F → °C, mS/cm → µS/cm | Values can only be compared in the same unit |
| **EDA (Exploratory Data Analysis)** | Looking at data with charts and summaries | Walking around a new city before planning a route | Trends, seasons, worst sites | Shows patterns and questions to investigate |
| **Trial / sample run** | Running on a small part of the data first | Tasting a spoonful before cooking the whole pot | First 600K rows were used | Fast to test, but **not** the final answer |
| **Parquet** | A compressed file format for tables | A zip file made for spreadsheets | `wq_curated.parquet` (the cleaned data output) | Much smaller and faster to read than CSV |
| **Git / GitHub** | Version history and online storage for the project | "Track changes" plus Google Drive for code | Every change is saved and shared | Nothing is lost; the team sees the latest work |

## Impact on the project
- This folder shows the **starting point** and the reasoning used first.
- Its cleaning rules (unit conversions, thresholds, flags) are **reused** in `01_profiling_curation/`, which re-runs them on the **full** data and adds Decision Tree / Naive Bayes missing-value treatment.
- If someone asks "why do the old charts show different numbers?", the answer is: **they were a 600K-row trial; the new folders use all 4.96M rows.**

## Note for running the old notebooks
They still run, but they treat this folder as their home: they look for the dataset at `00_previous_work/data/raw/resultphyschem.csv` and write outputs into `00_previous_work/`. For current work, use the new numbered folders.
