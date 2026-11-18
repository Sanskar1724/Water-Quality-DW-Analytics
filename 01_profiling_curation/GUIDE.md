# Guide: `01_profiling_curation/` (Step 1: Data Profiling)

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
