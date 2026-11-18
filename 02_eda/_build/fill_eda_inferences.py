"""Fills the Inference cells of 02_eda/01_exploratory_data_analysis.ipynb (keeps outputs)."""
import nbformat as nbf, sys
P = sys.argv[1]
INF = {
"E1": """**🔎 Inference (E1): numerical analysis**
- **Typical (median) values after cleaning:** temperature **17.3 °C**, dissolved oxygen **8.0 mg/L**, pH **7.76**, turbidity **4.3 NTU**, conductivity **107 µS/cm**, nitrate **0.40 mg/L as N**. These describe ordinary fresh surface water: slightly alkaline, well oxygenated, mostly clear, and low in nitrate.
- **Temperature, DO and pH are near-symmetric** (skewness −0.25, −0.50, −1.11), so mean ≈ median and both are fair summaries.
  - pH's negative skew and high kurtosis (4.6) come from a **tail of acidic readings** (down to pH 4–5), for example blackwater streams in the South.
  - DO's IQR (6.0–9.8 mg/L) shows most water is healthy, while its lower tail reaches 0 (hypoxia).
- **Turbidity, conductivity and nitrate are strongly right-skewed** (skewness 16.7, 6.7, 7.7; CV 9.6, 4.7, 2.6):
  - **Turbidity:** mean 33.7 vs median 4.3 NTU.
  - **Conductivity:** mean 2,022 vs median 107 µS/cm, inflated by salty coastal sites.
  - **Nitrate:** mean 1.75 vs median 0.40 mg/L.
  - A small number of very high values (storms, estuaries, farm drainage) pull the mean far above the typical value.
- **Impact:**
  - Dashboards and site comparisons should use **medians and percentiles**.
  - Charts for these three use **log scales**.
  - Regression should consider **log-transforming** turbidity, conductivity and nitrate (Step 10).""",

"E2": """**🔎 Inference (E2): categorical analysis**
- **Region:**
  - **Midwest holds 49.4%** of analysis-ready results but has a low exceedance rate (4.2%).
  - **South (27.3%) has the highest rate of the four main regions: 16.4%**, about **4× the Midwest**.
  - *Territory* (0.3%, mostly Puerto Rico) shows 24.3%, driven by **warm tropical water** (temperature exceedance 69%). This is natural, not pollution.
- **Water type:** 77% *Not Reported* (from Step 2). Among known values, **groundwater exceeds more often (23.7%) than surface water (14.3%)**. In the cross-tab, groundwater's **DO exceedance is 76.7%**. Groundwater is *naturally* low in oxygen (median DO 0.57 mg/L), so the 5 mg/L aquatic-life threshold does not really apply to wells. **Ocean water** shows **87.5% conductivity exceedance** (seawater is salty by nature).
- **Sample type:** field measurements 83%, loggers 8.8%, lab samples 8.0%. Lab samples have the highest rate (10.1%), possibly because lab sampling is targeted at suspected problems.
- **Time band:** morning (43%) and afternoon (25%) dominate. *Not Reported* rows have a low exceedance rate (2.6%), mostly Wisconsin temperature loggers.
- **Rare categories (< 1%):** groundwater, ocean, effluents, stormwater, *Pump* equipment, *Raw/Preliminary* status. In the warehouse and the models these can be **grouped into "Other"** to avoid unstable estimates.
- **Region × parameter:**
  - The South leads in DO (23.3%), temperature (18.8%) and conductivity (10.0%).
  - The **Northeast has the highest pH exceedance (19.8%)**, consistent with acidic, poorly buffered waters.
  - The **West leads in turbidity (15.1%) and nitrate (8.2%)**.
- **Impact:** problems are **parameter-specific and regional**. A single "bad region" label would be misleading, and some exceedances reflect *natural* water types, so interpretation must consider water type.""",

"E3": """**🔎 Inference (E3): temporal analysis (Q1, Q4)**
- **Q1, volume over time:**
  - 2024 has **2.23M** results (39,330 sites) and 2025 has **1.54M** (30,512 sites).
  - **Peak month: May 2025 (486,189)**; May 2024 is almost equal (478,712). **Lowest: December 2025 (23,189).**
  - Quarter 2 is the busiest every year. The **late-2025 drop** (Q4 2025: 117K vs 350K in Q4 2024) reflects **data not yet uploaded to WQP**, not less monitoring, so 2024-vs-2025 totals must not be compared as a trend.
- **Sampling rhythm:**
  - **Monday–Wednesday carry the most results**, and weekends are low (Saturday 170K vs Tuesday 989K): field crews work weekdays.
  - Weekend exceedance rates are lower (2–3%), because weekend data is mostly continuous loggers in healthier waters.
  - **Morning (43%)** is the main sampling time.
- **Q4, seasons (medians):**
  - **Temperature** rises from 9.8 °C (winter) to **19.3 °C (summer)**.
  - **Dissolved oxygen falls** from 9.7 to **7.3 mg/L** in summer, exactly what physics predicts: warm water holds less oxygen.
  - **The DO exceedance rate jumps to 25.9% in summer** (vs 7.7% in winter), and temperature exceedance to 8.3%.
  - **Turbidity** is highest in spring (5.8 NTU, snowmelt and rain runoff); its exceedance peaks in autumn (13.3%).
  - **Nitrate** is higher in winter–spring (0.46–0.50) than summer (0.32): plants and algae take up nitrate in the growing season, and spring runoff carries fertiliser.
  - **Conductivity** is highest in winter (217 µS/cm), possibly road salt and low flow.
- **2024 vs 2025 (E3e):** the **same seasonal shape repeats in both years** for temperature and DO, so the pattern is real, not a one-year accident. Month-to-month jumps in 2025 pH, turbidity and conductivity come from **fewer sites being sampled** (a changing site mix), not a real change in water.
- **Quarterly exceedance:** Q3 (summer) is worst both years (12.9% and 13.7%).
- **Impact:**
  - Seasonal comparisons must use **rates and medians** (sampling volume varies 20× across months).
  - **Season and month are strong predictors** for the models, especially for DO.
  - The real-time dashboard should expect **summer DO alerts**.""",

"E4": """**🔎 Inference (E4): sites, states, organizations (Q2, Q3, Q7, Q8)**
- **Q2, comparing sites (≥ 30 results each):** site medians spread widely.
  - Temperature: P10–P90 **11.0–26.0 °C**.
  - DO: **4.3–9.8 mg/L**.
  - pH: **6.9–8.3**.
  - Turbidity: **0.5–16.6 NTU**.
  - Conductivity: **40–2,526 µS/cm**.
  - Nitrate: **0.003–2.9 mg/L**.
  - Site *location* explains a lot of the variation, so **site/state is an important model feature**.
- **Q3, worst sites (fair ranking with ≥ 30 results):**
  - **Conductivity:** Georgia coastal sites (21GAEPD, median ~42,000–53,000 µS/cm). These are **estuaries**, salty by nature.
  - **DO:** Miami-Dade, Florida sites (21FLDADE) at **100% exceedance**, some with median DO below 1 mg/L.
  - **pH:** Alabama (21AWIC) and Virginia sites with **acidic** water (median pH 5.1–5.9).
  - **Turbidity:** Arkansas and Minnesota sites with medians around 100 NTU.
  - **Temperature:** Gulf-coast sites (Mississippi, Alabama, Florida, Puerto Rico).
  - **Nitrate:** Iowa and Minnesota farm-belt sites (up to 28% exceedance).
  - **"Poor" sites (≥ 50% exceedance):** **14% of DO sites** and 12.8% of conductivity sites, but **0% of nitrate sites**.
- **Map (E4a):** problem sites cluster along the **Gulf Coast and Florida** (warm, low-oxygen water), while the northern states, Pacific Northwest and Alaska are mostly green.
- **Volume ≠ rate (E4b):**
  - **Wisconsin** has the most results (1.35M) but one of the **lowest exceedance rates (2.1%)**.
  - **Florida** has the most sites (11,059) and **the highest rate (20.3%)**; Georgia (19.6%) and Alabama (17.6%) follow.
- **Q7, coverage:**
  - 468 organizations; **the top 10 supply 63.7% of all results**.
  - Only **55 organizations cover all 24 months** and only **33 measure all six parameters**; the median organization monitors 20 sites.
  - The site × month heat map (E4c) shows the busiest sites are **monitored continuously**, while many others have seasonal gaps (winter).
- **Q8, location types (proxy: water type):**
  - **Groundwater** is warmer (22.5 °C), **very low in oxygen (0.57 mg/L)**, clearer (0.86 NTU) and **higher in nitrate (2.4 mg/L)** than surface water (DO 7.1, nitrate 0.36).
  - **Ocean water** is cold, oxygen-rich (10.8 mg/L) and salty (41,825 µS/cm).
  - Location type therefore changes what "normal" means, so thresholds should ideally be **location-type-specific** (a recommendation for later).""",

"E5": """**🔎 Inference (E5): outcome analysis, counts vs rates (Q6)**
- **292,571 exceedances (7.8%)** and **97,752 high-risk results (2.6%)** among 3.77M analysis-ready results.
- **By parameter:** DO is first by **both count (125,770) and rate (18.2%)**, with 59,111 high-risk results (DO < 2 mg/L) across **14,636 sites**.
- **Count vs rate tells different stories:**
  - **Temperature** has the 2nd-highest *count* (64,652) only because it is measured most (1.9M results); its *rate* is low (3.4%).
  - **Turbidity (10.5%) and pH (8.7%)** have higher rates than temperature despite fewer results.
  - **Nitrate** exceeds rarely (3.3%, 1,421 results at 380 sites).
- **Organizations (E5c):**
  - **MNPCA (Minnesota)** has the most exceedances (32,455) at a moderate rate (11.9%).
  - **WIDNR (Wisconsin)** is 2nd by count (24,575) but has the **lowest rate (1.9%)**: big volume, not big risk.
  - Smaller southern organizations (**21MSWQ 28.9%, 21FLSFWM 25.9%, 21FLDADE 23.8%**) have the **highest rates**.
- **No causal claim:** a high rate may reflect *where* an organization monitors (warm, coastal, problem waters), not worse water management. Organizations often target known problem sites.
- **Impact:** the dashboard must show **both counts and rates**, and rank sites/organizations by **rate with a minimum sample size**, as the brief requires.""",

"E6": """**🔎 Inference (E6): relationships among parameters (Q5)**
- Based on **404,327 site-days** where parameters were measured together. The common pairs (temperature, DO and pH) have 275K–286K site-days each; nitrate pairs only 15K–26K.
- **Temperature vs DO: strong negative relationship (Spearman −0.63, Pearson −0.59).** Warmer water holds less oxygen. In the hexbin plot (E6c) most points sit **just below the theoretical 100%-saturation curve**, which confirms the cleaned data follows known physics (a strong validity check). Points far below the curve are **oxygen-depleted waters** (e.g. deep lake layers, polluted reaches).
- **pH vs DO: moderate positive (+0.33).** Photosynthesis by algae raises both oxygen and pH at the same time.
- **pH vs conductivity: moderate positive (Spearman +0.45, but Pearson only +0.04).** A monotonic but non-linear relationship: harder, mineral-rich water is both more alkaline and more conductive. The big gap between Spearman and Pearson shows why rank correlation is needed for skewed parameters.
- **Temperature vs nitrate: weak negative (−0.21).** This matches the seasonal pattern: less nitrate in warm months.
- **Turbidity is almost unrelated** to the other parameters (|r| ≤ 0.08). It is driven by rain events, not by water chemistry.
- **Impact for modelling (Step 10):**
  - **Temperature is the strongest predictor of DO**, with pH and conductivity as secondary predictors.
  - Turbidity adds little to predicting DO.
  - Use **Spearman/log transforms** for skewed parameters.
  - These are associations, not proof of cause.""",

"E7": """**🔎 Inference (E7): EDA answers to the mandatory questions**
| Q | Short answer from the data |
|---|---|
| Q1 | Monitoring peaks in May (≈480K results/month) and is lowest in December. Q2 is busiest; late 2025 is incomplete in WQP. |
| Q2 | Site medians vary widely (e.g. DO 4.3–9.8 mg/L between P10 and P90 sites), so location matters a lot. |
| Q3 | Worst: Georgia estuaries (conductivity), Miami-Dade sites (DO < 1–3 mg/L), Alabama/Virginia acidic streams (pH 5–6), Iowa/Minnesota farm sites (nitrate). 14% of DO sites are "poor". |
| Q4 | Summer: temperature ↑ (19.3 °C), DO ↓ (7.3 mg/L), DO exceedance 25.9% vs 7.7% in winter. The pattern repeats in 2024 and 2025. |
| Q5 | Temperature–DO −0.63 (physics confirmed); pH–DO +0.33; pH–conductivity +0.45; turbidity independent. |
| Q6 | 292,571 exceedances (7.8%), 97,752 high-risk. DO is highest by count and rate (18.2%). |
| Q7 | 468 organizations, the top 10 = 63.7% of results; only 55 cover all 24 months and 33 measure all 6 parameters. |
| Q8 | Groundwater: very low DO (0.57) and higher nitrate (2.4); ocean: salty (41,825 µS/cm). Location type changes what is "normal". |

These EDA answers are confirmed with warehouse OLAP queries (Step 9). Q9–Q10 are answered by the mining models (Step 10).""",
}
nb = nbf.read(P, as_version=4); n = 0
for c in nb.cells:
    t = c.get('metadata', {}).get('infer')
    if t in INF: c.source = INF[t]; n += 1
nbf.write(nb, P); print('filled', n, 'of', len(INF))
