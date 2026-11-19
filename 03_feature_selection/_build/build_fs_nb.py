"""Builds 03_feature_selection/01_feature_selection.ipynb."""
import nbformat as nbf, sys
from pathlib import Path
OUT = Path(sys.argv[1]); cells = []
def md(s, infer=None):
    c = nbf.v4.new_markdown_cell(s.strip())
    if infer: c.metadata["infer"] = infer
    cells.append(c)
def code(s): cells.append(nbf.v4.new_code_cell(s.strip()))
def infer(tag): md(f"**🔎 Inference ({tag}):** _written after the run_", infer=tag)

md(r"""
# Step 4 · Feature Selection for the Whole Project

**Input:** `data/processed/wq_analytics_mart.parquet`, the analytical mart **built from the batch data warehouse** (brief §18: no raw-file shortcuts).
**Faculty requirement:** *apply the best feature-selection methods on the entire data*, so one shared step whose output (`selected_features.json`) is used by **regression**, the **decision tree** and **association rules**.

## What is a "feature" and why select them?
A **feature** is a clue given to a model (temperature, season, region…). More clues are not always better:
- **useless** clues add noise and slow training
- **duplicate** clues (two features saying the same thing) make regression coefficients unstable (*multicollinearity*)
- **leaking** clues secretly contain the answer and give fake accuracy

So each candidate feature is judged by **several independent methods**, and a feature is kept only if most methods agree it is useful (**consensus**).

| Family | Method | Idea in simple words |
|---|---|---|
| Filter | **Correlation (Pearson/Spearman)** | Does the feature move together with the target? |
| Filter | **VIF** (variance inflation factor) | Is the feature just a copy of other features? (VIF > 5 = too much overlap) |
| Filter | **Mutual information** | How much does knowing the feature reduce uncertainty about the target? (catches non-linear links) |
| Filter | **ANOVA F-test / f_regression** | Is the target different across values of the feature? |
| Filter | **Chi-square / Cramér's V** | For categories: are the feature and the outcome related? |
| Wrapper | **RFE-CV** (recursive feature elimination with cross-validation) | Train, drop the weakest feature, repeat; keep the set that scores best on unseen folds |
| Embedded | **Lasso** | Linear model that pushes useless coefficients to exactly zero |
| Embedded | **Random Forest importance** | How much each feature improves the trees' splits |
| Model-agnostic | **Permutation importance** | Shuffle one feature on test data: how much worse does the model get? |

## Three selection problems
1. **Regression (Q10a):** predict **dissolved oxygen (mg/L)** at a site-day from co-measured parameters, site/place and time.
2. **Classification (Q10b, decision tree):** predict whether a result is **high-risk**.
3. **Association rules (Q9):** which categorical attributes are worth turning into items.
""")
code(r"""
import duckdb, json, time, warnings, numpy as np, pandas as pd, matplotlib.pyplot as plt, seaborn as sns
from pathlib import Path
from sklearn.feature_selection import mutual_info_regression, mutual_info_classif, f_regression, f_classif, chi2, RFECV
from sklearn.linear_model import LinearRegression, LassoCV
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.model_selection import train_test_split, KFold, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.outliers_influence import variance_inflation_factor
from scipy.stats import chi2_contingency
warnings.filterwarnings('ignore'); sns.set_theme(style='whitegrid'); pd.set_option('display.width', 200)
ROOT = Path.cwd().resolve()
for p in [ROOT, *ROOT.parents]:
    if (p / 'data' / 'processed' / 'wq_analytics_mart.parquet').exists(): ROOT = p; break
MART = (ROOT / 'data' / 'processed' / 'wq_analytics_mart.parquet').as_posix()
OUT = ROOT / '03_feature_selection'; FIG, TAB = OUT / 'figures', OUT / 'tables'; FIG.mkdir(exist_ok=True); TAB.mkdir(exist_ok=True)
def save_tab(df, n, index=False): df.to_csv(TAB / f'F{n}.csv', index=index); return df
def save_fig(n): plt.tight_layout(); plt.savefig(FIG / f'F{n}.png', dpi=130, bbox_inches='tight'); plt.show()
con = duckdb.connect(); con.execute("SET memory_limit='3GB'")
con.execute(f"CREATE VIEW mart AS SELECT * FROM '{MART}'")
print(con.execute('SELECT count(*) AS n_rows, count(DISTINCT site_id) AS n_sites FROM mart').df())
RNG = 42
""")

md(r"""
## 1 · Build the modelling tables from the mart
**Site-day table:** one row per site per day, with the median of each parameter measured that day (co-located data).
**Previous result:** the same site's value on its **previous sampling day** (within 31 days). It is genuinely available *before* the day being predicted, so it is a legitimate (leakage-safe) predictor.
Skewed parameters (turbidity, conductivity, nitrate) are log-transformed (Step 3 finding). Missing co-measured parameters get a median fill **plus a "was measured" indicator**, so the model knows the value was not observed.
""")
code(r"""
con.execute('''
CREATE OR REPLACE TABLE sd AS
SELECT site_id, sample_date, any_value(state) AS state, any_value(region) AS region, any_value(water_type) AS water_type,
       mode(organization) AS organization, mode(sample_type_group) AS sample_type_group, mode(equipment_group) AS equipment_group,
       any_value(month) AS month, any_value(season) AS season, any_value(day_of_week) AS day_of_week, any_value(latitude) AS latitude, any_value(longitude) AS longitude,
       median(result_value) FILTER (WHERE parameter = 'Dissolved oxygen') AS do_val,
       median(result_value) FILTER (WHERE parameter = 'Temperature') AS temperature,
       median(result_value) FILTER (WHERE parameter = 'pH') AS ph,
       median(result_value) FILTER (WHERE parameter = 'Conductivity') AS conductivity,
       median(result_value) FILTER (WHERE parameter = 'Turbidity') AS turbidity,
       median(result_value) FILTER (WHERE parameter = 'Nitrate') AS nitrate,
       max(high_risk_flag) FILTER (WHERE parameter = 'Dissolved oxygen') AS do_high_risk
FROM mart GROUP BY site_id, sample_date''')
con.execute('''
CREATE OR REPLACE TABLE sd AS
SELECT *, CASE WHEN date_diff('day', lag(sample_date) OVER w, sample_date) <= 31 THEN lag(do_val) OVER w END AS prev_do
FROM (SELECT * FROM sd WHERE do_val IS NOT NULL) WINDOW w AS (PARTITION BY site_id ORDER BY sample_date)''')
reg = con.execute('SELECT * FROM sd').df()
print(f'Regression table (site-days with DO): {len(reg):,} rows · sites {reg.site_id.nunique():,}')

def prep_numeric(df, cols_log, cols_lin):
    X = pd.DataFrame(index=df.index)
    for c in cols_lin + cols_log:
        v = np.log10(df[c].clip(lower=0) + 0.01) if c in cols_log else df[c]
        name = f'log_{c}' if c in cols_log else c
        X[f'has_{c}'] = v.notna().astype(int); X[name] = v.fillna(v.median())
    return X
REG_NUM = prep_numeric(reg, ['conductivity', 'turbidity', 'nitrate'], ['temperature', 'ph', 'prev_do'])
REG_NUM['latitude'] = reg.latitude.fillna(reg.latitude.median())
REG_NUM['month_sin'] = np.sin(2 * np.pi * reg.month / 12); REG_NUM['month_cos'] = np.cos(2 * np.pi * reg.month / 12)
REG_CAT = reg[['season', 'region', 'state', 'water_type', 'sample_type_group', 'equipment_group', 'organization']].fillna('Unknown').astype('category')
y_reg = reg.do_val.values
display(REG_NUM.describe().T.round(2))
""")

md(r"""
## 2 · Regression features (target: dissolved oxygen, mg/L)
### 2a · Filter methods: correlation, VIF, f_regression, mutual information
""")
code(r"""
nums = ['temperature', 'ph', 'log_conductivity', 'log_turbidity', 'log_nitrate', 'prev_do', 'latitude', 'month_sin', 'month_cos']
idx = np.random.default_rng(RNG).choice(len(reg), size=min(150_000, len(reg)), replace=False)
Xn = REG_NUM[nums].iloc[idx]; yn = y_reg[idx]
f_stat, f_p = f_regression(Xn, yn)
mi = mutual_info_regression(Xn, yn, random_state=RNG)
# mutual information for categorical features (ordinal codes, discrete)
Xc = REG_CAT.iloc[idx].apply(lambda s: s.cat.codes)
mi_cat = mutual_info_regression(Xc, yn, discrete_features=True, random_state=RNG)
# ANOVA-style F for categoricals: does mean DO differ between categories?
f_cat = [f_classif(yn.reshape(-1, 1), Xc[c])[0][0] for c in Xc]
filt = pd.DataFrame({'feature': nums + list(Xc.columns),
                     'pearson_r': [np.corrcoef(Xn[c], yn)[0, 1] for c in nums] + [np.nan] * Xc.shape[1],
                     'spearman_r': [pd.Series(Xn[c]).corr(pd.Series(yn, index=Xn.index), method='spearman') for c in nums] + [np.nan] * Xc.shape[1],
                     'F_stat': list(f_stat) + f_cat, 'mutual_info': list(mi) + list(mi_cat)})
Xv = Xn[[c for c in nums if c not in ('month_sin', 'month_cos')]].assign(const=1.0)
vif = pd.Series([variance_inflation_factor(Xv.values, i) for i in range(Xv.shape[1] - 1)], index=Xv.columns[:-1], name='VIF')
filt = filt.merge(vif.rename_axis('feature').reset_index(), on='feature', how='left')
display(save_tab(filt.round(4).sort_values('mutual_info', ascending=False), '02a_regression_filter'))
""")
md(r"""### 2b · Wrapper and embedded methods: RFE-CV, Lasso, Random Forest and permutation importance""")
code(r"""
Xall = pd.concat([REG_NUM[nums], pd.get_dummies(REG_CAT[['season', 'region', 'water_type', 'sample_type_group', 'equipment_group']], drop_first=True, dtype=float)], axis=1)
Xs = StandardScaler().fit_transform(Xall.iloc[idx]);
t = time.time()
lasso = LassoCV(cv=5, random_state=RNG, alphas=40).fit(Xs, yn)
lasso_coef = pd.Series(lasso.coef_, index=Xall.columns)
rfe = RFECV(LinearRegression(), step=1, cv=KFold(5, shuffle=True, random_state=RNG), scoring='r2', min_features_to_select=3).fit(Xs, yn)
rfe_sel = pd.Series(rfe.support_, index=Xall.columns)
print(f'Lasso alpha = {lasso.alpha_:.4f}; RFE-CV kept {rfe.n_features_} of {Xall.shape[1]} columns ({time.time() - t:.0f}s)')

Xrf = pd.concat([REG_NUM[nums], REG_CAT.apply(lambda s: s.cat.codes)], axis=1).iloc[idx]
Xtr, Xte, ytr, yte = train_test_split(Xrf, yn, test_size=0.25, random_state=RNG)
rf = RandomForestRegressor(n_estimators=150, max_depth=16, min_samples_leaf=20, n_jobs=-1, random_state=RNG).fit(Xtr, ytr)
perm = permutation_importance(rf, Xte.iloc[:30000], yte[:30000], n_repeats=3, random_state=RNG, n_jobs=-1)
print(f'Random Forest R² on held-out site-days: {rf.score(Xte, yte):.3f}')

def group_of(col):  # map one-hot columns back to their source feature
    for g in ['season', 'region', 'water_type', 'sample_type_group', 'equipment_group']:
        if col.startswith(g + '_'): return g
    return col
emb = pd.DataFrame({'feature': Xall.columns, 'lasso_abs_coef': lasso_coef.abs().values, 'rfe_selected': rfe_sel.values})
emb['feature'] = emb.feature.map(group_of)
emb = emb.groupby('feature').agg(lasso_abs_coef=('lasso_abs_coef', 'max'), rfe_selected=('rfe_selected', 'max')).reset_index()
tree = pd.DataFrame({'feature': Xrf.columns, 'rf_importance': rf.feature_importances_, 'permutation_importance': perm.importances_mean})
regsum = filt[['feature', 'spearman_r', 'mutual_info', 'F_stat', 'VIF']].merge(emb, on='feature', how='outer').merge(tree, on='feature', how='outer')
display(regsum.round(4).sort_values('permutation_importance', ascending=False))
""")
md(r"""### 2c · Consensus vote (regression)
Each method votes for a feature if it ranks in that method's **top half** (Lasso: coefficient not zero; RFE-CV: selected). A feature is **selected with ≥ 4 of 6 votes**. VIF is used as a veto: a feature with VIF > 5 is dropped from the *linear* model if a stronger correlated feature is kept.""")
code(r"""
def consensus(df, methods, min_votes):
    v = pd.DataFrame({'feature': df.feature})
    for m, kind in methods.items():
        s = df[m]
        if kind == 'bool': v[m] = s.fillna(False).astype(bool)
        elif kind == 'nonzero': v[m] = s.fillna(0).abs() > 1e-6
        else:
            r = s.abs().rank(ascending=False); v[m] = (r <= s.notna().sum() / 2) & s.notna()
    v['votes'] = v[list(methods)].sum(axis=1); v['selected'] = v.votes >= min_votes
    return v.sort_values('votes', ascending=False)
reg_vote = consensus(regsum, {'mutual_info': 'rank', 'F_stat': 'rank', 'lasso_abs_coef': 'nonzero', 'rfe_selected': 'bool',
                              'rf_importance': 'rank', 'permutation_importance': 'rank'}, 4)
display(save_tab(reg_vote.merge(regsum[['feature', 'VIF']], on='feature', how='left'), '02c_regression_consensus'))
REG_SELECTED = reg_vote[reg_vote.selected].feature.tolist(); print('Selected for regression:', REG_SELECTED)

fig, axes = plt.subplots(1, 3, figsize=(19, 5.2))
d = regsum.set_index('feature')
for ax, col, t_ in [(axes[0], 'mutual_info', 'Mutual information'), (axes[1], 'rf_importance', 'Random Forest importance'), (axes[2], 'permutation_importance', 'Permutation importance (held-out)')]:
    s = d[col].dropna().sort_values(); ax.barh(s.index, s.values, color=['#DD8452' if f in REG_SELECTED else '#AAAAAA' for f in s.index]); ax.set(title=t_)
fig.suptitle('F2 · Regression (target = dissolved oxygen): feature scores; orange = selected by consensus', y=1.02, fontsize=13)
save_fig('02_regression_feature_scores')
""")
md(r"""**Why this chart:** three independent scoring methods side by side. A feature that is long in all three bars is robustly useful; orange marks the consensus selection.""")
infer("F2")

md(r"""
## 3 · Classification features (target: HighRisk result, for the decision tree)
Each **result** gets: its parameter, place, time and method attributes; the **other** parameters measured at the same site that day (its *own* parameter is blanked, so the answer is not leaked); and the **previous result** of the same parameter at the same site (≤ 31 days earlier) plus whether that previous result was high-risk.

**Leakage exclusions (never used as features):** `result_value` (contains the answer), `result_band` and `exceedance_flag` (derived from the value), the site-day median of the row's *own* parameter.
""")
code(r"""
con.execute('''
CREATE OR REPLACE TABLE cls AS
WITH r AS (
  SELECT m.*, CASE WHEN date_diff('day', lag(sample_date) OVER w, sample_date) <= 31 THEN lag(result_value) OVER w END AS prev_result,
         CASE WHEN date_diff('day', lag(sample_date) OVER w, sample_date) <= 31 THEN lag(high_risk_flag) OVER w END AS prev_high_risk
  FROM (SELECT * FROM mart USING SAMPLE reservoir(1500000 ROWS) REPEATABLE (11)) m
  WINDOW w AS (PARTITION BY site_id, parameter ORDER BY sample_date, result_key))
SELECT r.parameter, r.season, r.month, r.region, r.state, r.water_type, r.sample_type_group, r.equipment_group, r.organization,
       r.time_band, r.is_weekend, r.latitude, r.prev_result, r.prev_high_risk,
       CASE WHEN r.parameter <> 'Temperature' THEN s.temperature END AS co_temperature,
       CASE WHEN r.parameter <> 'Dissolved oxygen' THEN s.do_val END AS co_do,
       CASE WHEN r.parameter <> 'pH' THEN s.ph END AS co_ph,
       CASE WHEN r.parameter <> 'Conductivity' THEN s.conductivity END AS co_conductivity,
       CASE WHEN r.parameter <> 'Turbidity' THEN s.turbidity END AS co_turbidity,
       r.high_risk_flag
FROM r LEFT JOIN sd s ON s.site_id = r.site_id AND s.sample_date = r.sample_date''')
cl = con.execute('SELECT * FROM cls').df()
y_cls = cl.high_risk_flag.values
print(f'Classification sample: {len(cl):,} results · high-risk rate {y_cls.mean() * 100:.2f}%')
CL_CAT = cl[['parameter', 'season', 'region', 'state', 'water_type', 'sample_type_group', 'equipment_group', 'organization', 'time_band']].fillna('Unknown').astype('category')
CL_NUM = pd.DataFrame(index=cl.index)
for c in ['prev_result', 'prev_high_risk', 'co_temperature', 'co_do', 'co_ph', 'co_conductivity', 'co_turbidity', 'latitude', 'month']:
    CL_NUM[f'has_{c}'] = cl[c].notna().astype(int) if c not in ('latitude', 'month') else 1
    CL_NUM[c] = cl[c].astype(float).fillna(cl[c].astype(float).median())
CL_NUM['is_weekend'] = cl.is_weekend.astype(int)
CL_NUM = CL_NUM.loc[:, CL_NUM.nunique() > 1]
Xcl = pd.concat([CL_CAT.apply(lambda s: s.cat.codes), CL_NUM], axis=1)
print('candidate features:', Xcl.shape[1])
""")
code(r"""
t = time.time()
cat_cols = list(CL_CAT.columns); num_cols = list(CL_NUM.columns)
chi_s, chi_p = chi2(Xcl[cat_cols], y_cls)
cram = []
for ccol in cat_cols:
    tab = pd.crosstab(CL_CAT[ccol], y_cls); c2 = chi2_contingency(tab)[0]
    cram.append(np.sqrt(c2 / (tab.values.sum() * (min(tab.shape) - 1))))
f_num, _ = f_classif(Xcl[num_cols], y_cls)
mi_c = mutual_info_classif(Xcl.iloc[:300000], y_cls[:300000], discrete_features=[c in cat_cols for c in Xcl.columns], random_state=RNG)
Xtr, Xte, ytr, yte = train_test_split(Xcl, y_cls, test_size=0.25, stratify=y_cls, random_state=RNG)
rfc = RandomForestClassifier(n_estimators=150, max_depth=18, min_samples_leaf=20, class_weight='balanced_subsample', n_jobs=-1, random_state=RNG).fit(Xtr, ytr)
permc = permutation_importance(rfc, Xte.iloc[:40000], yte[:40000], n_repeats=3, scoring='roc_auc', random_state=RNG, n_jobs=-1)
sub = np.random.default_rng(RNG).choice(len(Xtr), 120000, replace=False)
rfec = RFECV(DecisionTreeClassifier(max_depth=10, min_samples_leaf=50, class_weight='balanced', random_state=RNG), step=1,
             cv=StratifiedKFold(4, shuffle=True, random_state=RNG), scoring='roc_auc', min_features_to_select=3).fit(Xtr.iloc[sub], ytr[sub])
print(f'done in {time.time() - t:.0f}s · RF test ROC-AUC = {__import__("sklearn.metrics", fromlist=["roc_auc_score"]).roc_auc_score(yte, rfc.predict_proba(Xte)[:, 1]):.3f} · RFE-CV kept {rfec.n_features_}')
clssum = pd.DataFrame({'feature': Xcl.columns})
clssum['type'] = ['categorical' if c in cat_cols else 'numeric' for c in Xcl.columns]
clssum['chi2'] = clssum.feature.map(dict(zip(cat_cols, chi_s))); clssum['cramers_v'] = clssum.feature.map(dict(zip(cat_cols, cram)))
clssum['anova_F'] = clssum.feature.map(dict(zip(num_cols, f_num))); clssum['mutual_info'] = mi_c
clssum['rf_importance'] = rfc.feature_importances_; clssum['permutation_auc_drop'] = permc.importances_mean; clssum['rfe_selected'] = rfec.support_
clssum['filter_score'] = clssum.cramers_v.fillna(0) + 0  # placeholder to rank categoricals and numerics together below
clssum['filter_rank_score'] = np.where(clssum.type == 'categorical', clssum.chi2.rank(pct=True), clssum.anova_F.rank(pct=True))
cls_vote = consensus(clssum, {'filter_rank_score': 'rank', 'mutual_info': 'rank', 'rf_importance': 'rank', 'permutation_auc_drop': 'rank',
                              'rfe_selected': 'bool'}, 3)
cls_vote = cls_vote.merge(clssum.drop(columns=['filter_score']), on='feature')
display(save_tab(cls_vote.round(4), '03_classification_consensus'))
CLS_SELECTED = cls_vote[cls_vote.selected].feature.tolist(); print('Selected for the decision tree:', CLS_SELECTED)

fig, axes = plt.subplots(1, 3, figsize=(19, 6))
d = clssum.set_index('feature')
for ax, col, t_ in [(axes[0], 'mutual_info', 'Mutual information'), (axes[1], 'rf_importance', 'Random Forest importance'), (axes[2], 'permutation_auc_drop', 'Permutation importance (ROC-AUC drop)')]:
    s = d[col].sort_values().tail(18); ax.barh(s.index, s.values, color=['#DD8452' if f in CLS_SELECTED else '#AAAAAA' for f in s.index]); ax.set(title=t_)
fig.suptitle('F3 · Classification (target = HighRisk): top feature scores; orange = selected by consensus', y=1.02, fontsize=13)
save_fig('03_classification_feature_scores')
""")
md(r"""**Why this chart:** the same three-view comparison for the decision-tree problem; consensus-selected features are orange. A "has_…" feature means *whether* a co-measured parameter was recorded, which can itself carry information about the monitoring programme.""")
infer("F3")

md(r"""
## 4 · Attributes for association rules (Q9)
Association mining needs **categorical items**. Candidate attributes are ranked by **Cramér's V** with `ExceedanceFlag` (0 = unrelated, 1 = perfectly related). Attributes with V ≥ 0.05 are used as items, together with the outcome items (ResultBand, Exceedance, HighRisk), which the brief requires.
""")
code(r"""
assoc_cand = ['parameter', 'parameter_group', 'season', 'region', 'water_type', 'sample_type_group', 'equipment_group', 'time_band', 'is_weekend', 'year']
asum = con.execute('SELECT ' + ', '.join(assoc_cand) + ', exceedance_flag FROM mart USING SAMPLE reservoir(800000 ROWS) REPEATABLE (5)').df()
rows = []
for c in assoc_cand:
    tab = pd.crosstab(asum[c].astype(str), asum.exceedance_flag); c2, p, *_ = chi2_contingency(tab)
    rows.append({'attribute': c, 'categories': tab.shape[0], 'cramers_v': np.sqrt(c2 / (tab.values.sum() * (min(tab.shape) - 1))), 'chi2_p_value': p})
av = pd.DataFrame(rows).sort_values('cramers_v', ascending=False); av['use_as_items'] = av.cramers_v >= 0.05
display(save_tab(av.round(4), '04_association_attributes'))
ASSOC_SELECTED = av[av.use_as_items].attribute.tolist() + ['result_band', 'exceedance_flag', 'high_risk_flag']
fig, ax = plt.subplots(figsize=(9, 4)); ax.barh(av.attribute[::-1], av.cramers_v[::-1], color=['#DD8452' if u else '#AAAAAA' for u in av.use_as_items[::-1]])
ax.axvline(0.05, color='red', ls='--'); ax.set(title="F4 · Cramér's V with ExceedanceFlag (orange = used as association items)", xlabel="Cramér's V")
save_fig('04_association_attributes')
""")
infer("F4")

md(r"""## 5 · Save the shared selection (`selected_features.json`)""")
code(r"""
LEAKAGE = {'regression': ['do_val (target)', 'DO result_band / exceedance / high-risk flags of the same site-day (derived from the target)'],
           'classification': ['result_value', 'result_band', 'exceedance_flag', 'site-day median of the row\'s own parameter'],
           'association': ['none (descriptive mining of co-occurrence; outcome items are intended)']}
sel = {'source': 'data/processed/wq_analytics_mart.parquet (built from the batch DW)',
       'regression': {'target': 'dissolved oxygen (mg/L), site-day median', 'selected': REG_SELECTED, 'all_scores_table': 'tables/F02c_regression_consensus.csv'},
       'classification': {'target': 'high_risk_flag', 'selected': CLS_SELECTED, 'all_scores_table': 'tables/F03_classification_consensus.csv'},
       'association': {'outcome': 'exceedance_flag', 'item_attributes': ASSOC_SELECTED, 'table': 'tables/F04_association_attributes.csv'},
       'leakage_excluded': LEAKAGE}
(OUT / 'selected_features.json').write_text(json.dumps(sel, indent=2), encoding='utf-8'); print(json.dumps(sel, indent=2))
""")
infer("F5")

nb = nbf.v4.new_notebook(); nb.cells = cells
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, OUT); print('written', OUT, len(cells), 'cells')
