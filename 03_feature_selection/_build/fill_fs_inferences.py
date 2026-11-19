"""Fills the Inference cells of 01_feature_selection.ipynb (numbers from the executed run)."""
import nbformat as nbf, sys
P = sys.argv[1]
INF = {
"F2": """**🔎 Inference (F2): regression features (target = dissolved oxygen)**
- **Four features win all 6 votes: temperature, previous DO, latitude and pH.**
  - **Temperature** has the strongest single link (Spearman −0.62, mutual information 0.41). This is the physics found in Step 3: warm water holds less oxygen.
  - **Previous DO** at the same site (+0.53) shows that a site's oxygen level is persistent from one sampling day to the next.
  - **Latitude** (+0.36) captures the north–south climate gradient (cooler northern waters hold more oxygen).
  - **pH** (+0.32) reflects photosynthesis, which raises both oxygen and pH.
- **Selected with 4–5 votes:** water type (groundwater is naturally low in oxygen), month (as sin/cos, so December and January are neighbours), season and region.
- **Rejected:**
  - log turbidity, log nitrate, log conductivity: only 2 votes, near-zero correlations (|r| ≤ 0.06). They add little to DO prediction, matching Step 3 ("turbidity is independent").
  - equipment and sample type: about how the data was measured, not about the water.
  - **organization (3 votes) and state (1 vote):** they score high on mutual information but don't hold up in the model tests. They mostly *re-encode location*, which latitude and region already provide, and with 468 and 54 categories they would invite overfitting.
- **No multicollinearity problem:** every numeric VIF is between 1.0 and 1.4, far below the warning level of 5. The selected features carry different information.
- A Random Forest using the candidates explains **R² = 0.71** of DO variation on held-out site-days. That is the ceiling the Step 10 regression models can be compared with.""",
"F3": """**🔎 Inference (F3): decision-tree features (target = HighRisk)**
- **15 of 26 candidates selected.** The five unanimous ones (5/5 votes):
  - **parameter:** high risk depends strongly on *which* parameter is measured (DO has 8.6% high-risk results, temperature 0.2%)
  - **previous result** and **previous high-risk flag:** a site that was high-risk last time is very likely high-risk again (ANOVA F = 313,396, the strongest signal)
  - **co-measured pH**
  - **latitude**
- **Organization and state** are selected here (unlike in regression): which monitoring programme and which state a result comes from changes the high-risk rate a lot (Cramér's V 0.18 and 0.15).
- The **"has_co_…" indicators** (whether DO or temperature was measured that day) are selected. *Whether* a parameter was co-measured tells the model what kind of monitoring visit it was (e.g. a full multi-parameter field visit vs a single logger reading).
- **Rejected:** season and region (their information is already carried by month, latitude and state), water type (mostly *Not Reported*), conductivity values, and the weekend flag.
- **Leakage check:** the result's own value, band and exceedance flag, and the site-day median of its *own* parameter, were never offered as candidates. The previous-result features use only **earlier** days.
- A Random Forest on all candidates reaches **ROC-AUC 0.97** on held-out results, so the selected clues carry strong, honest signal for the decision tree.""",
"F4": """**🔎 Inference (F4): attributes for association rules**
- The strongest links with exceedance (Cramér's V) are **region (0.21)** and **parameter (0.21)**, then parameter group (0.16), equipment (0.15), **season (0.14)**, water type (0.14) and time band (0.12). These are all used as items.
- **Weekend (0.06)** is just above the 0.05 cut-off and is kept as an item.
- **Sample type (0.03) and year (0.01)** are dropped: the year carries almost no information about whether a result exceeds, which supports treating 2024 and 2025 as one pooled period.
- So the rules in Step 10c combine *where* (region), *what* (parameter / group), *when* (season, time band) and *how* (equipment), with the outcome items (ResultBand, Exceedance, HighRisk).""",
"F5": """**🔎 Inference (F5): shared selection saved**
`selected_features.json` is the **single source of truth** for the three mining notebooks. All of them load it, so the whole project uses one consistent, evidence-based feature set, and the leakage exclusions are written down next to the selection for the viva.""",
}
nb = nbf.read(P, as_version=4); n = 0
for c in nb.cells:
    t = c.get('metadata', {}).get('infer')
    if t in INF: c.source = INF[t]; n += 1
nbf.write(nb, P); print('filled', n)
