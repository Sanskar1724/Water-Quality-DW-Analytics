# Guide: `01_profiling_curation/` (Step 1: Data Profiling · Step 2: Data Curation)

## What this folder does, in plain words
Before we use any data, we give it a **health check-up**. This folder measures everything that could be wrong with the 4.96 million water measurements: blanks, repeats, wrong units, impossible numbers, bad dates, wrong locations. **We change nothing here; we only measure.** The repairs happen in the next notebook (Step 2), and every repair points back to a number measured here.

> **Analogy:** a doctor runs blood tests *before* prescribing medicine. Profiling is the blood test; curation (Step 2) is the medicine.

## What's inside

| File / folder | What it is |
|---|---|
| `01_data_profiling.ipynb` | The profiling notebook. Every section has: *what we check and why* → code → chart → **Inference** (what it means) |
| `figures/P*.png` | 16 charts (used in the PPT) |
| `tables/P*.csv` | 31 small result tables, the evidence behind every number |
| `tables/P16_profiling_issue_list.csv` | **The hand-over list:** every problem found, its count, and the planned fix |
| `_build/` | Scripts that generate the notebook and write the inferences (for reproducibility) |

**How to run:** open the notebook and *Run All* (about 40 seconds). The first run creates a compressed copy of the data, `data/raw_parquet/wq_raw.parquet`.

---

## Terms used, explained simply

| Term | Simple meaning | Everyday analogy | How it's used here | Why it matters for the project |
|---|---|---|---|---|
| **Row / result** | One measurement: one parameter, at one place, at one time | One line on a shopping receipt | 4,958,238 rows | Everything is counted in rows |
| **Column / field** | One type of information about each row (date, site, value…) | A column heading in Excel | 81 columns in the file | We keep only about 25 useful ones |
| **Parameter** | What was measured | The subject on a report card | Temperature, dissolved oxygen, pH, turbidity, conductivity, nitrate | Every analysis is split by parameter |
| **Data profiling** | Measuring data quality before fixing anything | A medical check-up | This whole notebook | Fixes must be justified by measured numbers |
| **Missing value (null)** | An empty cell | A blank field on a form | e.g. 28.7% of rows have no time of day | Too many blanks can bias results |
| **Missing At Random (MAR)** | Blanks that follow a pattern you can learn from other columns | One teacher never fills the "remarks" box: you can guess *who* left it blank | Blanks depend on the organization (P5) | Justifies using a **Decision Tree / Naive Bayes** to fill labels |
| **Imputation** | Filling a blank with a well-reasoned estimate | Guessing a missing exam mark from the student's other marks | Planned for Step 2, for descriptive labels only | Keeps rows usable without inventing measurements |
| **Duplicate** | The same record appearing twice | Being counted twice in a headcount | 0 exact duplicates; 3.8% likely duplicates | Duplicates inflate counts and averages |
| **Logger** | An automatic sensor left in the water, recording again and again | A CCTV camera vs a single photo | 29% of data comes from one organization's loggers | Repeated values from loggers are **real readings**, not duplicates |
| **Grain** | What exactly one row represents | "One row = one sale" vs "one row = one day's total sales" | 18.6% of rows are daily summaries (mean/min/max), not single readings | Mixing grains gives wrong totals and averages, so they must be separated |
| **Unit** | The scale a number is measured in | ₹ vs $; km vs miles | Temperature in °C *and* °F (31% in °F!) | Must convert to one unit before comparing |
| **Unit conversion** | Changing a number to another unit with a formula | Converting dollars to rupees | °C = (°F − 32) × 5/9; mS/cm × 1000 = µS/cm | 902,542 rows need it |
| **Impossible value** | A number that cannot exist in nature | A person aged 450 | Water at 25,430 °C; pH of 8,325 | Flagged and excluded from analysis (not deleted) |
| **Outlier** | A value far from the rest, but possibly real | One very tall student in a class | Turbidity after a storm | **Kept and flagged**: real extremes are what a safety dashboard must show |
| **IQR (inter-quartile range)** | The spread of the middle 50% of values | Ignoring the very top and bottom scorers to see the "normal" range | Outlier rule: beyond 3×IQR from the box | A standard, explainable way to spot extremes |
| **Median** | The middle value when sorted | The middle student in a height line-up | Typical pH = 7.8 | Not distorted by a few crazy values (unlike the mean) |
| **Mean** | The ordinary average | Total marks ÷ number of students | Raw DO mean 17 vs median 8.1 | Easily distorted by errors, so we prefer the median for skewed data |
| **Skewness** | How lopsided a distribution is | Most people earn a little, a few earn a lot (a long right tail) | Turbidity and nitrate are right-skewed | We use log scales and medians for them |
| **Kurtosis** | How often extreme values occur | How "spiky" the tails of a bell curve are | Very high in raw data because of errors | Shows that bad values dominate the raw statistics |
| **Log scale** | An axis where each step is ×10 | Richter scale for earthquakes | Turbidity, conductivity, nitrate charts | Lets tiny and huge values appear on one chart |
| **Histogram** | Bars showing how many values fall in each range | Counting students in each marks band | P10 distributions | Shows the shape of the data |
| **Box plot** | A box (middle 50%), a line (median), whiskers (normal range), dots (outliers) | A summary card of a whole class's marks | P11 | Shows centre, spread and extremes in one picture |
| **Heat map** | A grid of colours where darker = bigger | A weather map of temperatures | Missingness by parameter / organization | Shows patterns across many numbers at once |
| **Censored value / non-detect** | A value reported only as "below X" | "Less than 5 people attended" | `<0.5` nitrate | Only a limit, not an exact number; kept separately |
| **Quality-control (QC) record** | A test of the equipment, not of the water | A calibration weight on a shop scale | 29,108 rows (blanks, replicates) | Excluded from water analysis, kept for audit |
| **Time zone** | The local clock region (EST, PDT…) | Indian vs US clock time | 28.7% rows have no time or zone | Needed to put events in true time order (the real-time replay) |
| **Coordinates (lat/long)** | Position on Earth | A map pin | Used to draw the site map and find the region | Wrong signs put US sites in Asia! (20 sites found) |
| **DuckDB** | A small database engine inside Python | A pocket calculator for huge tables | Runs every query in this notebook | Handles 4.96M rows on a 7.7 GB laptop |
| **Parquet** | A compressed, column-based file type | A zip file designed for tables | 2.59 GB CSV → 228 MB | Reads about 10× faster; makes the full-data run take 40 seconds |
| **SQL** | The standard language for asking questions of tables | Asking a librarian a precise question | All checks are SQL queries | The same language is used later in the warehouse |

---

## What we found, in simple words

1. **The data is good enough for the project.** 4.96M results, 50,476 sites, 486 organizations, all 24 months of 2024–2025. The key identifiers (site, date, parameter) are never blank.
2. **Temperatures are in two units.** About a third are in °F, so they must be converted. Around 10,800 values labelled "°C" are really °F (they sit at 50–120 "°C").
3. **About 1 in 5 rows is a daily summary, not a single reading.** Daily averages and maximums are mixed in with individual readings, so they must be separated or averages go wrong.
4. **"Duplicates" were mostly not duplicates.** Wisconsin's automatic sensors took many readings a day without recording the time, so they *look* repeated. Only about 3.8% are likely real duplicates.
5. **Blanks follow a pattern.** Some organizations *never* fill certain fields. That pattern means a Decision Tree or Naive Bayes model can learn to fill descriptive labels, which is tested in Step 2.
6. **A few impossible numbers exist (0.3%)**, such as 25,430 °C or pH 8,325. They are flagged and kept out of the analysis.
7. **Coverage is uneven.** 10% of sites hold 76% of the data, and 1 in 5 sites has fewer than 5 results. Averages always need their sample count shown next to them.

## Impact on the rest of the project
| Finding | What changes later |
|---|---|
| Mixed units | Step 2 converts everything to one unit per parameter |
| Daily summaries mixed in | The warehouse gets a *Statistic Type* attribute; summaries are kept apart from single readings |
| Missing labels follow a pattern | Step 2 compares Decision Tree vs Naive Bayes vs simple fill |
| Missing time for 28.7% | The TimeBand attribute gets "Unknown" / "Whole day" values; the real-time replay orders events carefully |
| Uneven site coverage | Dashboard shows sample counts; Step 7 checks data skew in the distributed warehouse |
| No site-type column | Site type comes from the WQP Station file or is derived |

---
---

# Step 2: Data Curation and Missing-Value Treatment (`02_data_curation_imputation.ipynb`)

## What this notebook does, in plain words
Step 1 was the check-up. Step 2 is the **treatment**. It fixes every problem found in Step 1 with a written rule, fills in missing *labels* where that can be done reliably, and saves one clean file: **`data/processed/wq_curated.parquet`**. Every later step (EDA, the three warehouses, the models) reads only this file.

> **The golden rule:** no row is deleted. Every one of the 4,958,238 rows is still in the clean file. A column called `exclusion_reason` says *why* a row is not used in analysis (for example "Quality-control record"), and the counts are checked to add up exactly.

## New terms in Step 2

| Term | Simple meaning | Everyday analogy | How it's used here | Why it matters |
|---|---|---|---|---|
| **Data curation / cleaning** | Fixing, standardising and labelling data so it can be trusted | Sorting, washing and labelling vegetables before cooking | The whole of Step 2 | Wrong data → wrong conclusions |
| **Standard unit** | The one unit every value of a parameter is converted to | Converting all prices to ₹ before comparing | °C, mg/L, pH units, NTU, µS/cm, mg/L as N | Values can be compared and averaged |
| **Flag** | A yes/no marker attached to a row | A sticky note on a file | `is_qc`, `is_duplicate`, `is_impossible`… | Problems are marked, not hidden or deleted |
| **Exclusion reason** | The single main reason a row is left out of analysis | The reason written on a rejected exam paper | 10 reasons, checked in a fixed priority order | Every excluded row can be explained |
| **Analysis-ready** | A row with no exclusion reason | The vegetables that passed sorting | 3.77M rows (76%) | Only these feed charts and models |
| **Reconciliation** | Checking that the counts add up | Balancing a bank statement | raw = curated = analysis-ready + excluded | Proves nothing disappeared |
| **Censored / non-detect** | A value reported only as "below X" | "Less than 5 people came" | Kept in `censor_limit`, left out of averages | Not a real measurement, only a limit |
| **Grain** | What exactly one row represents | One sale vs one day's total sales | Daily summaries are a different grain | Mixing grains gives wrong averages |
| **Derived attribute** | A new column calculated from existing ones | Calculating age from date of birth | Season, TimeBand, ResultBand, ExceedanceFlag… | Needed by the warehouse and models; documented, never presented as original |
| **Threshold** | The limit above or below which a value counts as a problem | The pass mark in an exam | e.g. DO < 5 mg/L = exceedance | Turns numbers into "safe / unsafe" |
| **Exceedance** | A result that breaks a documented threshold | Scoring below the pass mark | `exceedance_flag = 1` | The main water-quality outcome |
| **High risk** | A result that breaks a stricter, more serious threshold | Scoring below 20% | `high_risk_flag = 1` | Separates "concerning" from "serious" |
| **EPA criterion** | An official US Environmental Protection Agency limit | A government safety standard | DO, pH, nitrate thresholds | Makes thresholds defensible; others are labelled *project threshold* |
| **Point-in-polygon** | Testing whether a map point lies inside a shape | Checking whether your house is inside a city boundary | Each site → its US state | Gives exact State and Region |
| **Census region** | The US government's 4 official groups of states | Zones like North/South India | Northeast, Midwest, South, West | The top level of the geography hierarchy |
| **Hierarchy** | Levels from broad to detailed | Country → State → City | Region → State → Site | Lets the warehouse "drill down" |
| **Imputation** | Filling a blank with a reasoned estimate | Guessing a missing exam mark from the student's other marks | Water type, equipment, time band only | Keeps rows useful without inventing measurements |
| **Rule-based imputation** | Filling with a near-certain fact | A person's birthplace is the same on every form | A site's water type is copied to its blank rows | Cheap and very reliable |
| **Decision Tree** | A model that learns a flowchart of yes/no questions | "Is it a fruit? → Is it red? → Apple" | Predicts missing labels | Easy to explain; handles mixed clues |
| **Naive Bayes** | A model where each clue votes with a probability, assuming clues are independent | A doctor combining separate symptoms to guess an illness | Predicts missing labels | Very fast; a good comparison for the tree |
| **Mode (baseline)** | Always guessing the most common answer | Answering "C" to every multiple-choice question | The bar any model must beat | Shows whether a model really adds value |
| **Feature** | A clue given to a model | The symptoms given to a doctor | Organization, parameter, activity type, state, month… | Models learn only from features |
| **Data leakage** | Accidentally giving the model the answer as a clue | Seeing the answer key during the exam | Features never include the label being predicted | Prevents fake, too-good accuracy |
| **Train / test split** | Learning on one part of the data and checking on a hidden part | Practising on old papers, then taking a new exam | 80% train, 20% test | Measures real accuracy |
| **Grouped test** | Hiding whole organizations from training | Testing a student on a topic they never studied | Used for organizations that never fill a field | An honest test for the hardest cases |
| **Accuracy** | % of predictions that are right | Marks scored out of 100 | Must be ≥ 70% to be used | Simple quality measure |
| **Macro-F1** | Average quality across all classes, rare ones counted equally | Checking a teacher grades every student fairly, not just the majority | Reported next to accuracy | Stops a model that ignores rare classes from looking good |
| **Confusion matrix** | Table of true vs predicted labels | A list of which answers a student mixes up | Water-type model | Shows *where* the model goes wrong |
| **IQR on log scale** | Outlier rule applied to log10 of the value | Comparing incomes by "number of zeros" | Turbidity, conductivity, nitrate | Fair outlier detection for skewed data |
| **UTC** | One worldwide reference clock | Converting all meeting times to IST | `ts_utc` from local time + time zone | Puts events from different time zones in true order |
| **Parquet (curated file)** | The compressed output table | A neatly packed, labelled box | `wq_curated.parquet` | Fast for every later step |

## Step 2 results, in simple words
1. **Nothing was deleted.** All 4,958,238 rows are in the clean file. **3,772,033 (76.1%) are analysis-ready**; the rest carry one clear reason for being left out.
2. **The biggest "exclusion" isn't an error.** 908,630 rows are daily summaries (mean/min/max), a different kind of row that gets its own place in the warehouse.
3. **Most "impossible" values were wrong units.** After converting °F to °C and other units, impossible values fell from 14,780 to 5,014. A third of all temperatures were in °F, and 10,848 "°C" values were really °F.
4. **Every site now has a US state and region** (96.6% of sites), using official state boundaries. Wisconsin alone holds 30% of the data, so comparisons use *rates*, not totals.
5. **Missing labels were treated in three levels, and the models had to earn their place:**
   - **Rules first:** sample fraction 100% filled, time band 46%, water type 10.5%.
   - **Decision Tree vs Naive Bayes vs mode:** the Decision Tree won every test. It was **used only for equipment group** (99% accurate, and 88% on organizations it had never seen).
   - **Not used for water type:** simply guessing "Surface Water" was already 97–98% right, so the tree added too little.
   - **Not used for time band:** only 67% accurate, below our 70% bar.
   - Those values are honestly marked **Not Reported**.
   - Naive Bayes failed badly on unseen organizations (23% for water type), because it treats each clue as independent.
6. **Measurements were never invented.** Missing values stay missing.
7. **After cleaning, statistics make physical sense:** typical temperature 17.3 °C, DO 8.0 mg/L, pH 7.8, turbidity 4.3 NTU, conductivity 107 µS/cm, nitrate 0.40 mg/L.
8. **Exceedance rates:** dissolved oxygen 18.2% (often deep-lake water in summer), turbidity 10.5%, pH 8.7%, conductivity 6.1% (often salty coastal sites), temperature 3.4%, nitrate 3.3%.

## Impact on the rest of the project
| Result | Used by |
|---|---|
| `wq_curated.parquet` (clean, flagged, with State/Region and flags) | Every later step |
| `analysis_ready` flag | EDA, models, warehouse "single reading" fact |
| Daily-summary rows (`is_summary`) | A separate summary fact table in the warehouse |
| Exceedance / high-risk flags, ResultBand | Dashboard (Q6), association rules (Q9), decision tree (Q10) |
| Region → State → Site | Warehouse geography hierarchy, OLAP drill-down, map |
| `*_source` columns | Shows which values are original, rule-filled, model-filled or Not Reported |
