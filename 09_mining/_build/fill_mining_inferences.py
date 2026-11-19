"""Fills the Inference cells of the three mining notebooks from their result tables (keeps outputs).
Usage: python 09_mining/_build/fill_mining_inferences.py <reg|assoc|dt>"""
import nbformat as nbf, sys, pandas as pd
from pathlib import Path
M = Path(__file__).resolve().parents[1]; T = M / 'tables'
which = sys.argv[1]

if which == 'reg':
    r = pd.read_csv(T / 'R01_model_comparison.csv', index_col=0); v = pd.read_csv(T / 'R03_vif.csv', index_col=0).VIF
    g, ml, s1, rf = r.loc['Gradient Boosting'], r.loc['Multiple linear'], r.loc['Simple linear (temperature only)'], r.loc['Random Forest']
    P = M / '01_regression.ipynb'
    INF = {
"R1": f"""**🔎 Inference (R1): model comparison on unseen months (Jul–Dec 2025)**
- **Simple linear regression (DO ~ temperature)** explains **R² = {s1['Test R²']:.2f}** of DO on the test months (RMSE {s1['Test RMSE']:.2f} mg/L). Temperature alone is a real but incomplete predictor.
- **Multiple linear regression** with the Step 4 features reaches **R² = {ml['Test R²']:.2f}** (RMSE **{ml['Test RMSE']:.2f} mg/L**, MAE {ml['Test MAE']:.2f}). Adding previous DO, pH, latitude, season and water type more than doubles the explained variation.
- **Ridge and Lasso give the same result as plain linear regression** ({r.loc['Ridge', 'Test R²']:.3f} / {r.loc['Lasso', 'Test R²']:.3f}). With 240K training rows and well-chosen, low-overlap features there is little overfitting for shrinkage to fix.
- **Non-linear models are best:** **Gradient Boosting R² = {g['Test R²']:.2f}, RMSE {g['Test RMSE']:.2f} mg/L, MAE {g['Test MAE']:.2f} mg/L**; Random Forest is close ({rf['Test R²']:.2f}). DO depends on its predictors in curved and interacting ways (e.g. the temperature effect differs by region and season), which trees capture and straight lines cannot.
- **Overfitting check:** Random Forest scores **R² {rf['Train R²']:.2f} on training vs {rf['Test R²']:.2f} on test**, a clear gap. Gradient Boosting's gap is smaller ({g['Train R²']:.2f} → {g['Test R²']:.2f}) and it scores higher on test, so it **generalises best**.
- **In practice:** a typical prediction is within about **±1.1–1.6 mg/L** of the measured DO. That is good enough to flag likely low-oxygen site-days for checking (the threshold is 5 mg/L), but not a replacement for measurement.
- **Honest limitation:** all test months are in the second half of 2025, which contains more summer/autumn data than the training period, so performance is checked against a genuinely different season mix (a strict, leakage-safe test).""",
"R2": f"""**🔎 Inference (R2): coefficients, multicollinearity and heteroscedasticity**
- **Strongest effects** (mg/L change in DO per 1-standard-deviation change, all p < 0.001):
  - **previous DO +0.93**: a site's oxygen level persists between visits
  - **temperature −0.93**: warmer water, less oxygen (physics)
  - **pH +0.64**: photosynthesis raises both
  - **latitude +0.64**: cooler northern waters
  - the South region and winter/spring seasons are slightly higher once temperature is accounted for
- The large coefficients for the **water-type dummies** (e.g. Surface Water +2.7 relative to the reference category) are measured against a *tiny* reference group (a rare water type). They mean "surface water has much more oxygen than that rare group", consistent with groundwater/effluent being low in oxygen. They should not be read as absolute effects.
- **Multicollinearity is acceptable:** VIF of temperature {v['temperature']:.1f} and latitude {v['latitude']:.1f} (they overlap: the south is warmer), all others < 2. Everything is below the warning level of 5, so the coefficients are stable.
- **Heteroscedasticity is present** (Breusch–Pagan p ≈ 0): errors are larger at some prediction levels (see R3). The linear coefficients stay unbiased, but their standard errors are optimistic. This is one more reason the tree-based models, which make no constant-variance assumption, are preferred for prediction.""",
"R3": """**🔎 Inference (R3): residuals**
- **Multiple linear:** residuals fan out and curve. Errors are small for mid-range DO and larger at the extremes, so the straight-line model under-predicts very high (super-saturated) DO and over-predicts very low DO. This is the heteroscedasticity and non-linearity found above.
- **Gradient Boosting:** residuals are more evenly centred on zero across the range, with a narrower, roughly symmetric error distribution. Most errors fall within about ±2 mg/L, with a few large misses (outliers), mainly very low-oxygen site-days that are hard to predict from co-measured parameters alone.
- **Conclusion:** the non-linear model is the better predictor. The linear model remains useful for **explaining** direction and size of effects.
- **Limitations:** no flow, depth, weather or algae data are available in WQP results; sites without a previous DO value are predicted less accurately; and results are site-day medians.""",
    }
elif which == 'assoc':
    c = pd.read_csv(T / 'A01_apriori_vs_fpgrowth.csv', index_col=0); ten = pd.read_csv(T / 'A04_ten_rules.csv', index_col=0)
    P = M / '03_association_rules.ipynb'
    rows = '\n'.join(f"| {i} | {r.antecedents_s} | {r.consequents_s} | {r.support:.4f} | {r.confidence:.3f} | {r.lift:.2f} |" for i, r in ten.iterrows())
    INF = {
"A1": f"""**🔎 Inference (A1): Apriori vs FP-Growth**
- Both algorithms found **exactly the same {int(c.loc['Frequent itemsets', 'Apriori']):,} frequent itemsets** (min support 0.5%, up to 4 items) from 250,000 result baskets with 41 items. This is the expected result: they are two methods for the same answer.
- **FP-Growth was faster ({c.loc['Seconds', 'FP-Growth']:.1f} s vs {c.loc['Seconds', 'Apriori']:.1f} s).** Apriori generates and tests candidate combinations level by level, while FP-Growth compresses the baskets into a tree and never generates candidates.
- **Memory lesson:** the first Apriori attempt on 600,000 baskets tried to allocate **13 GB** and failed. Apriori's `low_memory` mode and a 250K sample solved it. FP-Growth's design avoids this problem, which is why it scales better to big data.""",
"A3": """**🔎 Inference (A3): rule map**
- About 27,900 rules were generated, but **933 of the 946 "→ Exceedance/HighRisk" rules were definitional** (their antecedent already contained a ResultBand that *implies* the exceedance) and were removed. Only genuine, explanatory rules remain.
- The 10 reported rules (red) all have **support ≥ 0.6%** (thousands of results each), **confidence 31–43%** and **lift 4.0–5.5**. They are common enough to matter and make an exceedance 4–5 times more likely than the 7.8% overall rate.
- High-lift rules with tiny support (far left) are deliberately **not** reported as important, as the brief requires.""",
"A4": f"""**🔎 Inference (A4): the 10 meaningful rules**
| # | If (antecedent) | Then | Support | Confidence | Lift |
|---|---|---|---|---|---|
{rows}

**What they say, in plain words:**
- **Summer is the common thread.** 9 of the 10 rules include *Season = Summer*: most exceedance combinations happen in warm months.
- **The South in summer** (rules 1, 4, 7, 8, 10) is the riskiest combination: southern summer **temperature** readings exceed 43% of the time (lift 5.5), and southern summer **DO** readings 35% of the time.
- **Low oxygen in summer surface water** (rules 3, 6, 9) is a nationwide pattern, including the Midwest (rule 9).
- **Equipment = Other / grab sampler** items (rules 2, 5, 6, 8) reflect *which monitoring programmes* sample problem waters in summer. This is a monitoring pattern, not a cause.

**Possible use:**
- Schedule extra summer DO/temperature monitoring and alerts for southern surface waters.
- Use these combinations as alert rules in the real-time dashboard.
- These are co-occurrences, not proof of cause.""",
    }
elif which == 'dt':
    met = pd.read_csv(T / 'D03_test_metrics.csv', index_col=0)['Decision tree']; imp = pd.read_csv(T / 'D04_feature_importance.csv', index_col=0).importance
    paths = pd.read_csv(T / 'D06_decision_paths.csv'); split = pd.read_csv(T / 'D01_split.csv', index_col=0)
    P = M / '02_decision_tree.ipynb'
    top = ', '.join(f'{k} ({v:.2f})' for k, v in imp.head(5).items())
    pth = '\n'.join(f"  {i + 1}. **{r['high-risk share']:.0f}% high-risk** among {int(r['training results']):,} training results: `{r.path[:420]}{'…' if len(r.path) > 420 else ''}`" for i, r in paths.iterrows())
    INF = {
"D1": f"""**🔎 Inference (D1): tuning and overfitting**
- Training F1 keeps rising with depth, while validation F1 grows much more slowly: deeper trees start to **memorise** the training months.
- The tree with the very best validation F1 had about 1,800 leaves, and one of its paths depended on a value window of 12.90–12.91 (pure memorisation). The **simplicity rule** (fewest leaves within 0.02 F1 of the best) selected a **pruned tree** (cost-complexity pruning `ccp_alpha` > 0) that is far smaller with almost the same F1 and a **higher validation ROC-AUC**. This is the brief's "pruning / complexity control" in action.
- **Class balance shifts over time:** high-risk results are {split.iloc[0, 1]:.2f}% of training, {split.iloc[1, 1]:.2f}% of validation and **{split.iloc[2, 1]:.2f}% of the test months** (summer–autumn 2025). The chronological split therefore tests the model on a genuinely different period, as it would be used in practice.""",
"D2": f"""**🔎 Inference (D2): test performance (Jul–Dec 2025, never seen during training)**
- **Recall {met['Recall']:.1%}:** the tree catches about **{met['Recall'] * 10:.0f} out of 10 real high-risk results**. That is the most important number for a safety alert.
- **Precision {met['Precision']:.1%}:** about 1 in {1 / met['Precision']:.0f} alerts is truly high-risk. This trade-off was chosen deliberately (`class_weight='balanced'`), because *missing* a dangerous result costs more than checking a false alarm.
- **ROC-AUC {met['ROC-AUC']:.3f}:** the tree ranks high-risk results above normal ones about {met['ROC-AUC']:.0%} of the time. **F1 {met['F1-score']:.3f}** is modest because the class is rare.
- **Accuracy {met['Accuracy']:.1%} is lower than the useless "always not high-risk" baseline (95.5%)**, which shows why accuracy is misleading for rare classes. The baseline catches 0% of high-risk results.
- **Most important features:** {top}. Whether **temperature was co-measured** separates monitoring programmes (multi-parameter field visits vs single-parameter loggers). The **previous high-risk flag** and **previous result** show that problems persist at a site, **latitude** reflects the north–south climate gradient, and **parameter** captures that some parameters (DO) are high-risk far more often.""",
"D3": f"""**🔎 Inference (D3): three real decision paths (from the trained tree)**
{pth}

**Reading them in plain words:**
- **Path 2 is the clearest rule:** *if temperature was **not** co-measured (a single-parameter programme, often a continuous logger or lab sample) **and** the previous result at this site was high-risk → 58% of results are high-risk again* (vs 2.7% overall, about 21× the normal rate), based on 1,317 training results. **Problems persist at a site.**
- **Paths 1 and 3** describe multi-parameter field visits (temperature and DO co-measured) on **DO and conductivity** results at **mid-southern latitudes (~30–35°N)**, where co-measured pH is above 7.1. They reach 79% and 55% high-risk.
- Both also contain a **very narrow condition on the previous result (12.90 < value ≤ 12.91)**. This is a very specific split learned from a few sites with exactly that previous reading (it appears in several organizations, not one faulty sensor). It shows that even a pruned tree keeps some very fine, data-specific rules, so such leaves should be used with caution and confirmed with more data before acting on them.
- `state ∈ {{…}}`, `organization ∈ {{…}}` and `equipment_group ∈ {{…}}` list the categories that go down that branch (categorical features are ordinal-coded).

**Use:**
- The tree turns into transparent screening rules: *re-sample sites whose last result was high-risk first*.
- Single-parameter programmes at sites with a high-risk history need the closest follow-up.
- For a classroom-sized explanation, the top 3 levels (D3 figure) are the most robust part of the tree.""",
    }

nb = nbf.read(P, as_version=4); n = 0
for cell in nb.cells:
    t = cell.get('metadata', {}).get('infer')
    if t in INF: cell.source = INF[t]; n += 1
nbf.write(nb, P); print(which, 'filled', n, 'of', len(INF))
