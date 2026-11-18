"""Fills the Inference cells of 02_data_curation_imputation.ipynb from final run numbers (keeps outputs)."""
import nbformat as nbf, sys, pandas as pd
from pathlib import Path
P = Path(sys.argv[1]); T = P.parent / 'tables'
rd = lambda n, **k: pd.read_csv(T / f'{n}.csv', **k)
ex = rd('C08_exclusion_reasons').set_index('reason').rows
rec = rd('C08_reconciliation', index_col=0).Rows
rates = rd('C09_exceedance_rates', index_col=0)
ba = pd.read_csv(T / 'C13_before_after_stats.csv', header=[0, 1], index_col=0)
fl = rd('C04_validity_flags', index_col=0).Rows
oc = rd('C07_outlier_fences').set_index('param')
rp = rd('C08_ready_by_parameter').set_index('param')
A = lambda prm, col: ba.loc[prm, ('After (curated, standard unit)', col)]
B = lambda prm, col: ba.loc[prm, ('Before (raw, main unit)', col)]
ready = int(rec['5. Analysis-ready (3 − 4)']); excl = int(rec['4. Excluded from analysis (flagged, kept)'])

INF = {
"C3": f"""**🔎 Inference (C3): unit standardisation**
- **885,447 temperatures (31%) were converted from °F**, and **10,848 values labelled "°C" between 50 and 120** were corrected as mislabelled °F. In the *before* histogram these form the separate bump at 50–70; in the *after* histogram they join the normal 0–35 °C range. That the bump vanishes is the visual proof that the correction is right.
- **Conductivity:** 14,270 rows converted (mS/cm ×1000 etc.). **Nitrate:** 5,921 rows converted, mainly "mg/L as NO₃" → "mg/L as N" (×0.2259). This is more than the 2,825 counted in Step 1, because the chemical form (*speciation*) is stored in a separate column that Step 1 did not read.
- **Unusable units stay out of numeric analysis:** pH 29,049 (mostly mV, the raw electrode voltage), turbidity 4,098, nitrate 3,485, temperature 2,991, conductivity 1,371 and DO 685. **9,074 DO rows in % saturation** are kept separately.
- **Value fixes:** 9,708 "=" prefixes repaired, **14,958 censored/non-detect values** kept with their limit, and 22,285 text placeholders left empty.
- **Impact:** about 18% of the data would have been wrong without unit standardisation. This step also explains most of the "impossible" values from Step 1 (see C8): they were unit errors, not bad measurements.""",

"C6": """**🔎 Inference (C6): geography → state → region**
- **48,757 of 50,476 sites (96.6%) now have a US state**: **90.5%** fall inside a state boundary and **6.2%** were matched to the nearest boundary within ~25 km (coastal and estuary sites that fall just outside the simplified outline). Only **1,719 sites (3.4%)** remain *Unknown*, almost all of them sites with no usable coordinates.
- The data covers **54 states/areas** (50 states + DC + Puerto Rico + other territories), but it is **highly concentrated**:
  - **Wisconsin alone has 1.47M results (29.7%)**, then Oregon (714K), Washington (526K), Florida (337K) and Minnesota (328K).
  - **Florida has the most sites (11,061)** but far fewer results per site: many sites sampled a few times, versus Wisconsin's few intensive sites.
- **By Census region:** Midwest 40.9% of results, West 31.3%, South 21.4%, Northeast 5.9%. The **South has the most sites (21,163)** but only a fifth of the results.
- The 20 wrong-sign sites (1,058 rows) stay *Unknown* and are listed as `flip_candidate`, so they can be corrected later if the Station file confirms them.
- **Impact:** the warehouse gets a real **Region → State → Site** hierarchy for drill-down. Because volume is so uneven, regional comparisons must use **rates per result**, never raw totals (otherwise "Wisconsin" simply means "most measured").""",

"C8": f"""**🔎 Inference (C8): exclusion reasons and reconciliation**
- **Reconciliation passed exactly:** raw 4,958,238 = curated 4,958,238 (**0 rows deleted**) = **{ready:,} analysis-ready ({ready / 4958238 * 100:.1f}%)** + **{excl:,} excluded with a reason**.
- **The largest exclusion is not an error:** **{int(ex['Summary statistic (separate grain)']):,} daily summaries** (mean/min/max) are a different grain and will feed a separate summary fact. The real quality exclusions are much smaller:
  - duplicates {int(ex['Duplicate copy']):,}
  - unusable units {int(ex['Unusable unit']):,}
  - QC records {int(ex['Quality-control record']):,}
  - censored {int(ex['Censored / non-detect']):,}
  - physically impossible {int(ex['Physically impossible']):,}
  - rejected {int(ex['Rejected by provider']):,}
- **Physically impossible values dropped from 14,780 (Step 1, raw units) to about {int(ex['Physically impossible']):,} after unit standardisation.** Most "impossible" values were really **unit mistakes** that are now fixed, not bad measurements.
- **Only {int(ex['Suspect (provider flag)']):,} rows are excluded *because* they are suspect**, although 91,600 carry the suspect flag. The rest were already excluded for a higher-priority reason (mostly daily summaries), which shows why one reason per row avoids double-counting.
- **Temperature has the lowest analysis-ready share ({rp.loc['Temperature', '% ready']:.1f}%)** because most daily summaries are temperatures (logger programmes report daily mean/min/max). The other parameters are 81–90% analysis-ready.
- **Impact:** {ready / 1e6:.2f}M high-quality single readings remain, which is plenty for the warehouse and models, and every excluded row can be explained.""",

"C9": f"""**🔎 Inference (C9): derived flags and thresholds**
- **Dissolved oxygen has by far the highest exceedance rate: {rates.loc['Dissolved oxygen', 'exceed_pct']:.1f}%** of results are below 5 mg/L, and **{rates.loc['Dissolved oxygen', 'high_risk_pct']:.1f}% are below 2 mg/L (hypoxia)**. Many come from **lake depth profiles**, where deep water is naturally low in oxygen in summer. This is a real ecological signal, but it means DO exceedances must be read **with depth and season** in mind.
- **Turbidity {rates.loc['Turbidity', 'exceed_pct']:.1f}%** (above 25 NTU) and **pH {rates.loc['pH', 'exceed_pct']:.1f}%** (outside 6.5–9) come next.
- **Conductivity {rates.loc['Conductivity', 'exceed_pct']:.1f}%:** its high-risk rate ({rates.loc['Conductivity', 'high_risk_pct']:.1f}%) is almost as high as its exceedance rate. That pattern is typical of **ocean and estuary sites**, which are naturally salty, so conductivity "exceedances" are not pollution by themselves.
- **Temperature ({rates.loc['Temperature', 'exceed_pct']:.1f}%) and nitrate ({rates.loc['Nitrate', 'exceed_pct']:.1f}%)** exceed least often. Nitrate above the 10 mg/L drinking-water limit is rare (about 1,400 results).
- **ResultBand** shows most results in the *Normal* band for every parameter, with the problem bands concentrated in DO (Low/Very Low) and turbidity (High/Very High).
- **Impact:** these flags are the **outcome variables** for the dashboard (Q6), the association rules (Q9) and the decision tree (Q10). Because the thresholds are documented with their source, every exceedance can be justified in the viva.""",

"C10": """**🔎 Inference (C10): Level 1 rule-based filling**
- **Sample fraction: 100% of the gaps (2.89M) filled by rule.** Temperature, pH, conductivity and turbidity are properties of the whole water ("Not applicable"), DO is "Dissolved" by definition, and only nitrate is left as "Not Reported".
- **Time band: 921,023 gaps (46%) filled by rule.** Daily-summary rows cover the whole day. 1,083,510 rows still need a decision (Level 2).
- **Water type: 405,080 rows (10.5%) filled by the "same site" rule.** A site never changes from river to well, so this is near-certain.
- **Equipment: 0 filled by the "same activity" rule.** Organizations either record equipment for a whole sampling activity or not at all, so there is nothing to copy within an activity. This is itself evidence that missingness depends on the organization (as Step 1 found), which motivates Level 2.
- **Collection method** (600+ free-text wordings) is set to "Not Reported" when missing. Predicting free text is not reliable, and the cleaner *equipment group* carries the useful information.
- **Impact:** cheap, explainable rules solve 4.2M gaps before any model is used. Models are only needed for the harder remainder.""",

"C11": """**🔎 Inference (C11): Decision Tree vs Naive Bayes vs mode**
- **The Decision Tree wins every comparison**, but *winning* is not enough. It must also beat the simple mode guess by a clear margin, and the results differ sharply by field:
  - **Equipment group (4 classes): clear success.**
    - Random test: tree **99.1%** vs mode 47.7%, macro-F1 0.89.
    - Grouped test (organizations never seen): tree **88.1%** vs mode 46.5%.
    - Naive Bayes is good too (93.2% / 79.7%), but lower.
  - **Water type: the model is accurate, but it adds almost nothing.** The tree is 99.4% / 98.8% accurate, but **the mode ("Surface Water") is already 97.3% / 98.4%**. Known water types are overwhelmingly surface water, so "accuracy" is high for any method. Macro-F1 shows the tree is better at the rare classes (0.49 vs 0.14), but the overall gain is only **+2.1 and +0.3 points**.
  - **Time band: not good enough.** The tree reaches **66.6%** on the random test (below the 70% bar). On unseen organizations it is **worse than the mode** (58.3% vs 63.8%), because the time of day depends on each organization's habits, which cannot be learned for an organization never seen.
- **Naive Bayes collapses on unseen organizations for water type (22.7%).** Because it assumes clues are independent, an unseen organization's "zero evidence" distorts its probabilities. The tree simply falls back on the other clues. That is a concrete, data-backed reason to prefer the tree here.
- **Why two tests matter:** the grouped test is the honest one for the 352K–3.3M rows from organizations that **never** record a field. A random test alone would have overstated quality, for example for time band.""",

"C11b": """**🔎 Inference (C11b): confusion matrix, water type**
- **Surface Water** (the dominant class) is recognised almost perfectly, and rows of the large minority classes (Groundwater, Ocean Water) are mostly correct too.
- Very small classes (e.g. stormwater, effluents) are often predicted as Surface Water. That is why **macro-F1 (0.49) is far below accuracy (99%)**: the overall accuracy is driven by the big class.
- **Decision applied:** although the tree is 98–99% accurate, it beats the mode by only 0.3–2.1 points, below the pre-set +10 rule. So the missing water types are honestly marked **"Not Reported"** rather than filled with a near-certain but low-value guess. In analysis, **water type is reported only where it is known** (30% of rows), and known values are 97% surface water.""",

"C12": """**🔎 Inference (C12): how every field is now filled**
- **Equipment group is now complete:** 45.9% original + **54.1% predicted by the Decision Tree**, accepted because it passed both tests (99% / 88%). Every predicted value is labelled `Model: Decision Tree` in `equipment_source`.
- **Sample fraction is complete:** 41.6% original + 58.4% by the parameter-definition rule.
- **Time band:** 59.6% original + 18.6% *Whole day* (rule) + **21.9% Not Reported**. The model was below the 70% bar, so it was not used.
- **Water type:** 22.0% original + 8.2% by the same-site rule + **69.9% Not Reported** (the model gain over the mode was too small).
- **Collection method:** 37.1% original + 62.9% Not Reported.
- **Impact:** the result is a **mix of three methods chosen field by field from evidence**, not one blanket fill. This is exactly the faculty's requirement: rule-based where certain, Decision Tree where it proved accurate, and an honest *Not Reported* where neither was good enough. Nothing original was overwritten, and every filled value carries its source.""",

"C13": f"""**🔎 Inference (C13): before vs after cleaning**
- **Means now match medians.**
  - **Temperature:** mean {A('Temperature', 'mean'):.1f} vs median {A('Temperature', 'median'):.1f} °C; skewness {B('Temperature', 'skewness'):.0f} → **{A('Temperature', 'skewness'):.2f}**.
  - **DO:** mean {B('Dissolved oxygen', 'mean'):.1f} → **{A('Dissolved oxygen', 'mean'):.2f} mg/L** (median {A('Dissolved oxygen', 'median'):.2f}); maximum 6.9 million → {A('Dissolved oxygen', 'max'):.0f}.
  - **pH:** maximum 8,325 → **{A('pH', 'max'):.2f}**.
  - These three are now near-symmetric (skewness close to 0), which shows the absurd values were removed.
- **Temperature's median rose from 15.4 to {A('Temperature', 'median'):.1f} °C** because the 885K °F values (mostly summer logger readings) were converted and joined the °C data, and many cold-season daily summaries left the single-reading set.
- **Turbidity, conductivity and nitrate stay right-skewed** (skewness {A('Turbidity', 'skewness'):.0f}, {A('Conductivity', 'skewness'):.0f}, {A('Nitrate', 'skewness'):.0f}). That is their **natural shape**: most water is clear, fresh and low in nitrate, and a few storm, estuary and farm sites are very high. Medians (turbidity {A('Turbidity', 'median'):.1f} NTU, conductivity {A('Conductivity', 'median'):.0f} µS/cm, nitrate {A('Nitrate', 'median'):.2f} mg/L) are the right summary, with log scales in charts and possibly log transforms in regression.
- **Impact:** the curated data now gives physically sensible statistics, which is the foundation for trustworthy EDA, OLAP and models.""",

"C14": f"""**🔎 Inference (C14): curated file and data-quality report**
- **`wq_curated.parquet`** holds all **4,958,238 rows** (unique IDs confirmed), **{ready:,} analysis-ready**, in about 134 MB. It has clean columns, flags, derived attributes and a *source* column for every filled value, and is sorted by event time, ready for the real-time replay.
- The **data-quality report** follows the brief's format: problem, field, count, treatment, justification. Every decision is **attribute-specific** (no "all nulls removed"), and each count matches the Step 1 profiling or the reconciliation.
- **Key messages for the viva:**
  1. Nothing was deleted; everything is flagged and explained.
  2. Unit errors, not bad sensors, caused most "impossible" values.
  3. Daily summaries were separated as a different grain.
  4. Missing labels were treated by **rule → Decision Tree (only where it proved ≥ 70% accurate and +10 points better than the mode) → Not Reported**.
  5. Measured values were **never** imputed.""",
}
nb = nbf.read(P, as_version=4); n = 0
for c in nb.cells:
    t = c.get('metadata', {}).get('infer')
    if t in INF: c.source = INF[t]; n += 1
nbf.write(nb, P); print('filled', n, 'of', len(INF))
