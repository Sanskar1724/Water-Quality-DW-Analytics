# Guide: `02_eda/` (Step 3: Exploratory Data Analysis)

## What this folder does, in plain words
EDA means **getting to know the data with charts and summaries** before building anything. Using the clean file from Step 2 (3.77 million analysis-ready measurements), it answers: *What is normal? What changes with the seasons? Where is water quality worst? Which parameters move together?* It also gives the first, evidence-based answers to the brief's mandatory questions Q1–Q8.

> **Analogy:** before planning a road trip you look at the map, the weather and the traffic. EDA is that look at the data before designing the warehouse and the models.

## What's inside
| File | What it is |
|---|---|
| `01_exploratory_data_analysis.ipynb` | The EDA notebook: 8 sections, each *what & why → code → chart → inference* |
| `figures/E*.png` | 10 chart files (about 20 charts), used in the PPT |
| `tables/E*.csv` | 30 evidence tables |
| `_build/` | Scripts that generate the notebook and write the inferences |

**How to run:** open the notebook and *Run All* (about 80 seconds). It needs `data/processed/wq_curated.parquet` from Step 2.

## Terms used, explained simply
| Term | Simple meaning | Everyday analogy | How it's used here | Why it matters |
|---|---|---|---|---|
| **EDA** | Exploring data with charts and summaries | Walking around a new city before planning a route | This whole folder | Finds patterns and problems before modelling |
| **Variance / standard deviation** | How spread out values are | How much students' marks differ from the class average | Section 1 table | Shows how variable each parameter is |
| **CV (coefficient of variation)** | Spread ÷ average | "How big is the wobble compared to the size?" | Turbidity 9.6 vs pH 0.10 | Compares variability across different units |
| **Quartiles (Q1, Q3)** | The values below which 25% and 75% of data lie | The marks of the 25th and 75th student in a line of 100 | Box plots, IQR | Describe the "middle half" of the data |
| **Frequency / % contribution** | How often each category appears | How many students chose each subject | Section 2 | Shows which categories dominate |
| **Rare category** | A category with less than 1% of rows | A subject only 2 students chose | Groundwater, effluents, Pump | Too small for reliable statistics; often grouped as "Other" |
| **Cross-tabulation** | A table crossing two categories | Pass rate by subject *and* by class | Region × parameter exceedance | Shows which *combinations* have problems |
| **Rate vs count** | How *often* vs how *many* | Accident *rate* per km vs total accidents | Wisconsin: most results, lowest rate | High volume ≠ high risk (a key rule of the brief) |
| **Seasonality** | A pattern that repeats every year | Ice-cream sales peak every summer | DO falls every summer | Season becomes a model feature |
| **Composition effect** | A change caused by *which* sites are sampled, not by the water changing | Class average drops because weaker students joined, not because anyone got worse | 2025 monthly jumps with fewer sites | Prevents false "trends" |
| **Minimum sample size** | Only rank a site with enough results (here ≥ 30) | Not calling a batsman "best" after one innings | Worst-site lists | Avoids rankings driven by luck |
| **Correlation** | How strongly two things move together (−1 to +1) | Taller people tend to weigh more | Temperature–DO −0.63 | Guides which features to use in regression |
| **Pearson correlation** | Measures straight-line relationships | Fitting a straight ruler through points | Section 6 | Sensitive to extreme values |
| **Spearman correlation** | Correlation of *ranks* | Comparing class rank in maths vs science | Section 6 | Works for skewed data and curved relationships |
| **Co-located data** | Parameters measured at the same site on the same day | Height and weight measured at the same check-up | 404,327 site-days | Relationships are only meaningful for matched measurements |
| **Hexbin plot** | A scatter plot where dense areas become coloured hexagons | A heat map of where people stand in a crowd | Temperature vs DO | Readable even with 285,000 points |
| **Saturation curve** | The maximum oxygen water can hold at each temperature | How much sugar dissolves in hot vs cold tea | Red line in E6c | A physics check that the data is valid |
| **Hypoxia** | Very low oxygen (below 2 mg/L) | A room with too little air | 8.6% of DO results | Harmful or deadly for fish |
| **Estuary** | Where a river meets the sea (salty water) | | Georgia coastal sites | Explains "high conductivity" naturally |

## What we found, in simple words
1. **Normal water in this dataset:** about 17 °C, 8 mg/L oxygen, pH 7.8, clear (4 NTU), fresh (107 µS/cm), low nitrate (0.4 mg/L).
2. **Summer is the risky season.** Water warms, oxygen drops, and low-oxygen problems jump from 7.7% (winter) to 25.9% (summer). This happens in both 2024 and 2025.
3. **The South has the most problems.** Florida, Georgia and Alabama have exceedance rates around 18–20%, while Wisconsin, the most monitored state, has only 2%.
4. **Warm water holds less oxygen.** The data shows this clearly (correlation −0.63) and follows the textbook physics curve, which shows the cleaned data is trustworthy.
5. **Some "problems" are natural:** ocean and estuary water is salty, groundwater has little oxygen, and tropical water is warm. Context matters when reading exceedances.
6. **Monitoring is uneven.** 10 organizations provide 64% of the data, and only 55 of 468 monitor every month.
7. **Late 2025 is incomplete in the source**, so 2024 vs 2025 totals are not a real trend.

## Impact on the rest of the project
| Finding | What it changes later |
|---|---|
| Temperature, season, site/state strongly related to DO | Key features for regression (Step 10) and feature selection (Step 4) |
| Skewed turbidity, conductivity, nitrate | Log transforms in models; medians in the dashboard |
| Rate ≠ count | Dashboard shows both, and ranks by rate with ≥ 30 results |
| Natural exceedances (ocean, groundwater) | Water type / location type kept as a dimension; noted in findings |
| Summer DO risk | Real-time alerts tuned for low DO; a dashboard finding |
| Rare categories | Grouped as "Other" in association rules and the decision tree |
