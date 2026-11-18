"""Fills the 'Inference' markdown cells of the executed profiling notebook (keeps all outputs)."""
import nbformat as nbf, sys
P = sys.argv[1]
INF = {
"P1": """**🔎 Inference (P1): dataset overview**
- The file has **4,958,238 results** from **50,476 sites** and **486 organizations**, covering **1 Jan 2024 – 31 Dec 2025 (all 24 months)**. This meets the brief's requirement of *multiple sites across states and at least two years*.
- **Temperature dominates (57.7%, 2.86M rows)**. Dissolved oxygen (15.6%) and pH (14.9%) follow, and nitrate is only **1.1% (53K rows)**.
- **Impact:**
  - A plain "average of all results" would really be a temperature average, so every later analysis must be **split by parameter**.
  - For nitrate, 53K rows is still enough for analysis, but site-level nitrate statistics will be thinner than for the other parameters.
  - Converting to Parquet shrank 2.59 GB to 228 MB (**11× smaller**), which is why the full file can be profiled on a 7.7 GB laptop.""",

"P2": """**🔎 Inference (P2): completeness of all 81 columns**
- Only **11 of 81 columns are complete** and another 9 are almost complete (under 5% missing).
- **52 columns are more than half empty**, and **5 are completely empty** (taxonomic name, tissue anatomy, particle-size basis, method URL, lab-preparation URL). These empty columns belong to biological and lab-tissue data, which this physical/chemical extract does not contain.
- **Impact:**
  - The 5 empty columns carry no information and will be **dropped**.
  - The many half-empty columns are mostly optional lab or comment fields that we do not need.
  - The warehouse will therefore use a **small, curated set of columns** (about 25) rather than all 81, which also keeps the warehouse small and fast.""",

"P3": """**🔎 Inference (P3): important fields**
- **All core identifiers are complete (0% missing):** site, date, parameter, organization, status, activity type. Every result can be placed in time, space and parameter, so the warehouse's main dimensions have no gaps.
- **The measured value is missing in only 0.25% (12,274 rows)**, and the unit (excluding pH) in only 0.16%.
- **Coordinates are missing in 0.17% (8,477 rows).**
- **Large gaps are only in descriptive fields:**
  - water type 78%
  - sampling depth 77%
  - collection method 63%
  - sample fraction 58%
  - equipment 54%
  - **time of day 28.7% (1.42M rows)**
- The brief's attribute *MonitoringLocationTypeName* (site type) is **not in this file**. It must come from the WQP *Station* file or be derived (for example from the water-type field).
- **Impact:** the gaps sit in *descriptive* columns, not in the measurements. So we do **not** need to drop rows; we need a strategy to **fill descriptive labels** (rule-based, Decision Tree or Naive Bayes) and to mark the rest *Not Reported*.""",

"P4": """**🔎 Inference (P4): missingness by parameter**
- Missingness is **not uniform**:
  - Time of day is missing for **34.7% of temperature** rows but only **10% of nitrate** rows.
  - Sample fraction is missing for 88% of conductivity but **0% of nitrate**.
  - Water type is missing for 94% of conductivity vs 69% of DO.
- The measured value itself is almost always present, **except nitrate (12.4% missing)**, mostly *non-detects* where the value was below what the lab could measure.
- **Impact:**
  - Because missingness changes with the parameter, it is **not completely random**. The parameter is an informative input for predicting missing labels.
  - For nitrate, the missing values are mostly *below detection*, which is real information ("very low") rather than missing data, and must be kept as *censored / non-detect* rather than treated as unknown.""",

"P5": """**🔎 Inference (P5): missingness by organization (key finding for imputation)**
- The heat map shows **solid rows of 0% and 100%**: missingness is decided mainly by **who collected the data**. For example:
  - **CTUIR_WQX never records time** (100% missing).
  - **WIDNR_WQX**, the largest organization with **1.42M rows (29% of all data)**, never records collection method, equipment or water type.
  - **MNPCA always records water type and fraction.**
- For **water type, 81.9%** of rows come from organizations that *always or never* fill it. For the other fields it is **40–55%**.
- **Impact (justification for model-based imputation):**
  - Because missingness is strongly tied to organization and the other fields, it is **Missing At Random (MAR)**, not completely random. A **Decision Tree** or **Naive Bayes** can learn "this kind of organization/site/activity usually has value X" and predict missing labels better than filling with the most common value.
  - Where an organization *never* records a field, there is nothing inside that organization to learn from, so the model must rely on *other* rows (similar sites and activities). Step 2 measures whether the prediction is accurate enough before using it; otherwise the value stays **Not Reported**.""",

"P6": """**🔎 Inference (P6): duplicates**
- **No exact duplicates (0)** and **no repeated ResultIdentifier (0)**: no record was loaded twice, and every row has a unique source ID.
- **Separating "looks repeated" from "is repeated" was essential.** A naive check (same site, date, time, parameter and value) first flagged **25.9%** of the data as duplicates. Inspection showed most are **not**:
  - **Logger activities (78,570 extra rows):** many readings share one activity ID with no per-reading time. These are separate readings.
  - **Same value, different activities, time missing (373,617):** **WIDNR_WQX** alone accounts for **380K** of these. Its temperature loggers report several readings per day without the time, so equal values on the same day are expected.
  - **Field-visit activities with the same value repeated (186,497; 3.8%):** the **likely real duplicates**. They will be flagged, with only one copy used in analysis.
  - **Conflicting repeats in field visits (559,272 rows, 11.3%):** same site, time and depth with *different* values, typically replicate readings in one visit. Both are kept and averaged per visit for site-level analysis.
- **Impact:** blindly removing "duplicates" would have deleted about a quarter of the data, mostly real logger readings. Instead, duplicates are **flagged by type**, and the warehouse grain uses `ResultIdentifier` as the unique source key.""",

"P6b": """**🔎 Inference (P6b): mixed grain (single readings vs daily summaries)**
- **921,023 rows (18.6%) are not single measurements** but **summary statistics** from **52 organizations**: daily mean (4.8%), daily maximum/minimum (2.4% each), 24-hour mean/min/max, and the **7-day average daily maximum (7DADM, 1.6%)**, a temperature metric used for fish-habitat standards.
- The largest suppliers of summary rows are **OREGONDEQ (131K)**, **HOHTRIBE_WQX (88K)**, **COQUILLE_WA (83K)** and **CTUIR_WQX (75K)**.
- **Impact (important for the warehouse design):**
  - The brief says *one fact row = one measured result* and that a fact table *must not mix grains*. Mixing a "daily maximum" with single readings would push averages up, and the same day would be counted 3 times (mean, min and max).
  - So summary rows get a **`StatisticType`** attribute and are kept **separate** from single readings, either filtered out of the main fact or placed in their own summary fact. This is a strong example of profiling changing the dimensional model.""",

"P7": """**🔎 Inference (P7): can the value be read as a number?**
- **99.0% of values are clean numbers.** Of the rest:
  - **22,285 text placeholders** such as `NA` (19,554), `Null`, `Not Reported` and `NF`: no measurement inside, so excluded from numeric analysis.
  - **9,708 values with an "=" prefix** (pH 4,952, turbidity 4,756): the number is fine, so we **strip the "="** and keep them.
  - **1,279 censored values** like `<0.5`: only a limit; flagged and the limit stored separately.
  - **12,274 empty values**, and **every one of them carries a detection-condition note** (for example *Not Detected*), mostly nitrate (6,618). So an empty value here means "too low to measure", not "unknown".
- **Nitrate is the most affected parameter (13.1% not numeric)**, mostly because concentrations are often below the lab's detection limit.
- **Impact:**
  - Fixing the "=" prefix rescues about 10K valid measurements.
  - Nitrate non-detects are kept as their own category ("below detection") so the nitrate picture is not biased toward high values.""",

"P8": """**🔎 Inference (P8): units**
- **Temperature: 31% (885,447 rows) is in °F**, so averaging without conversion would be badly wrong. These convert exactly with °C = (°F − 32) × 5/9.
- **Conductivity: 3 equivalent spellings** (µS/cm, µmho/cm, which are identical) plus **mS/cm (14,037)**, which needs ×1000.
- **Nitrate: 7+ units** (mg/L, µg/L, µeq/L, µmol/L…). 2,825 rows are convertible by formula; 4,287 are unusable (blank or impossible units).
- **pH: 708,012 rows have the unit written as the text "None"**, which is correct because pH has no unit. But **27,623 pH rows are in mV** (millivolts, the raw electrode signal). These **cannot** be turned into pH without calibration data, so they are unusable.
- **DO: 9,074 rows are % saturation**, a different measure from mg/L, so they are kept separate.
- **Totals:**
  - **902,542 rows (18.2%) need a unit conversion**
  - **42,481 rows (0.9%) have an unusable unit**
- **Impact:** unit standardisation is the **single largest cleaning step** by row count. Without it, temperature and conductivity analysis, exceedance flags and every model would be wrong.""",

"P9": """**🔎 Inference (P9): zero, negative and impossible values**
- **14,780 values (0.3%) are physically impossible** in their stated unit. Examples:
  - Temperature up to **25,430 °C**
  - DO up to **6,936,396 mg/L**
  - pH from **−24 to 8,325**
  - Turbidity down to **−6,419 NTU**
- **Temperature has the most impossible values (11,115)**. About **10,848 of them lie between 50 and 120 "°C"**, exactly the range of normal water temperatures in **°F**. These are most likely **°F values labelled as °C**, a unit-entry error, not real heat.
- **Zero values are mostly plausible:** 0 °C (ice-cold water), 0 nitrate (below detection), 0 turbidity (very clear water). Zero is **not** treated as an error.
- **Impact:** impossible values are **flagged and excluded from analysis, not deleted**, so the warehouse still counts them in data-quality reports. Without this step the raw maximums would destroy every average and chart (see P10).""",

"P10": """**🔎 Inference (P10): raw distributions and statistics (before cleaning)**
- **The raw means are distorted by bad values:**
  - The DO mean is **17.0 mg/L** but the median is **8.1 mg/L**, with skewness **873**, because of a few impossible values (up to 6.9 million).
  - Temperature's skewness is **589** and pH's is **508** for the same reason.
  - After cleaning, these should become near-symmetric (skewness close to 0).
- **The typical (median) values are realistic:** temperature **15.4 °C**, DO **8.1 mg/L**, pH **7.8**, turbidity **4.2 NTU**, conductivity **109 µS/cm**, nitrate **0.45 mg/L**.
- **Turbidity, conductivity and nitrate are genuinely right-skewed** (most values small, a few very large), so they are shown on a log scale. The conductivity histogram has a **second peak around 10,000–50,000 µS/cm**: these are **estuary and ocean-water sites** (salt water), a real group, not an error.
- **The temperature histogram shows a small bump around 60–65 "°C"**, the °F mislabelling found in P9. The **DO histogram has a spike near 0–1 mg/L (47,101 rows)**: low-oxygen (hypoxic) water, often from deep lake layers in depth profiles, which is a real and important water-quality signal.
- **Impact:**
  - Use **medians and IQR** (not means) for skewed parameters.
  - Use **log scales** in charts.
  - Consider **log transforms** for turbidity, conductivity and nitrate in regression.""",

"P11": """**🔎 Inference (P11): outliers (IQR rule)**
- **Extreme outliers (beyond 3×IQR):**
  - Temperature 0.6%, DO 0.17%, pH 0.44%
  - **Turbidity 6.9%, conductivity 7.6%, nitrate 7.0%**
- The high outlier shares for turbidity, conductivity and nitrate are **expected for skewed data**. The IQR rule assumes a roughly symmetric shape, so on a long-tailed distribution it labels many *real* high values as outliers: storm turbidity, salty estuary conductivity, nitrate near farms.
- **Impact:**
  - Outliers are **kept and flagged (`IsExtremeOutlier`)**, not removed, because high turbidity or nitrate is exactly what an exceedance dashboard must show.
  - Only **physically impossible** values (P9) are excluded.
  - For skewed parameters, Step 2 also computes outliers on the **log scale**, which is fairer.""",

"P12": """**🔎 Inference (P12): dates and times**
- **Dates are clean:** 0 unreadable and 0 outside 2024–2025, so every result fits the Date dimension.
- **Strong seasonal sampling rhythm:**
  - Volume peaks in **May (about 556K results in both 2024 and 2025)** and stays high through October.
  - It falls to about 25–85K in winter months, because many sites are only sampled in the ice-free season.
  - **2025 has fewer results than 2024 from July onward** (Nov–Dec 2025 only 31K and 25K), probably because recent data is still being uploaded to WQP.
- **Time of day is missing for 28.7%**, and **all 1.42M rows without a time also have no time zone**, so they cannot be converted to UTC.
- **Midnight spike:** 539,046 rows are at exactly 00:00:00. **98% of them (529,625) come from loggers / daily summaries**, where midnight means "this day" rather than a real reading time. In discrete field visits only **0.34%** are at midnight, mostly placeholders.
- **94 rows** have an end time earlier than the start time.
- **Impact:**
  - The **TimeBand** attribute needs care: logger midnight rows count as *whole-day*, and discrete midnight rows as *unknown*.
  - The month pattern means seasonal comparisons must use **rates/medians, not raw counts**.
  - For the **real-time replay**, events are ordered by date and then time, with unknown times placed at a fixed point of the day.""",

"P13": """**🔎 Inference (P13): coded fields**
- **Activity type:** **92.8% are field measurements** (sensor/probe readings), 6.6% lab samples, and **29,108 rows (0.6%) are quality-control records** across **19 QC activity types** (field blanks, replicates, calibration checks), plus 1,691 *Unknown*.
- **Result status:** **91.6% Final** and 6.1% Accepted. Only **175 rows are Rejected**. About 92K are Unreviewed / Raw / Preliminary / Provisional (not yet final).
- **Value type:** 83% *Actual* and **16.8% *Calculated***, which matches the summary-statistic rows from P6b.
- **Water type:** 78% blank. Of the known values, **Surface Water** dominates (21.2%), then Groundwater (0.5%) and Ocean Water (0.2%).
- **Qualifier:** **91,600 rows (1.85%) are flagged *SUS* (suspect)** by the provider.
- **Impact:**
  - **QC rows test the equipment, not the water**, so they are excluded from water-quality analysis but kept for audit.
  - **Rejected and suspect** values are excluded from analysis.
  - **Not-yet-final** results are kept with an `IsProvisional` flag so the dashboard can filter them.
  - *Unknown* activity types become an explicit **Unknown** dimension member rather than being dropped.""",

"P14": """**🔎 Inference (P14): geography**
- **49,063 of 50,476 sites (97.2%) have valid coordinates.** The map clearly traces the **USA mainland, Alaska, Hawaii and Puerto Rico**, which confirms that latitude and longitude are mostly correct.
- **All 8,477 rows without coordinates come from NWIS (USGS)**. In this extract the location is given only at station level, so these sites need the WQP Station file to be placed on a map.
- **Problem coordinates:**
  - **343 rows at exactly 0**, plus **261 rows near (0°, 0°)**: placeholders, not real places.
  - **1,058 rows at 20 sites with a positive longitude north of 20°N**. Flipping the sign puts them at −123°, −106° and −75°, which are real US locations (Oregon, New Mexico, the East Coast). This is a **missing minus sign**.
  - **71 sites** have coordinates that change by more than about 1 km between records.
- **Impact:**
  - Suspect coordinates are **set to missing** (Region = *Unknown*) rather than silently corrected, because the true sign cannot be confirmed for certain. Step 2 records the flip candidates for transparency.
  - Since there is **no state column**, the Region dimension is built from coordinates (later enriched from the Station file).""",

"P15": """**🔎 Inference (P15): coverage across sites**
- **Coverage is very uneven:**
  - The **median site has only 20 results**, but the mean is 98 and the busiest site has **25,502**.
  - **19.8% of sites (9,973) have fewer than 5 results.**
  - **The busiest 10% of sites hold 76.2% of all results**, and only **750 sites** have 1,000 or more.
- **Impact:**
  - **Site averages from a handful of samples are unreliable**, so the dashboard will always show the **sample count next to an average**, and site rankings will use a minimum sample size.
  - Such skew matters for the **distributed warehouse**. Distributing by `LocationKey` across many shards spreads it reasonably, but a few heavy sites can make one shard larger than the others. Step 7 measures this.
  - High volume does not mean high risk: busy sites are simply monitored more (the brief warns against confusing volume with rate).""",

"P16": """**🔎 Inference (P16): what profiling tells us overall**
1. **The data is fit for the project.** Identifiers, dates and values are almost complete, there are no exact duplicates, and only 0.3% of values are physically impossible.
2. **The biggest real problems were found by profiling, not by assumption:**
   - **18.2% of rows need unit conversion** (mostly °F temperatures).
   - **18.6% are daily summaries mixed with single readings** (a grain problem).
   - **28.7% have no time of day.**
3. **"Duplicates" needed careful separation.** Only about 3.8% are likely real duplicates; most repeated-looking rows are genuine logger readings.
4. **Missing descriptive labels follow organization patterns (MAR)**, which justifies **Decision Tree / Naive Bayes imputation** in Step 2, compared against a simple mode fill.
5. **Measurements are never invented.** Missing values stay missing and are excluded from numeric statistics.

Every row of the table above is a decision Step 2 must apply, with the affected-row count recorded so the data-quality report can be reconciled back to these numbers.""",
}
nb = nbf.read(P, as_version=4)
done = 0
for c in nb.cells:
    tag = c.get('metadata', {}).get('infer')
    if tag in INF:
        c.source = INF[tag]; done += 1
nbf.write(nb, P)
print('filled', done, 'of', len(INF))
