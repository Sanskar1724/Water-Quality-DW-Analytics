"""Builds 09_mining/03_association_rules.ipynb."""
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
# Step 10c · Association Rule Mining: frequent combinations of water-quality conditions (Q9)

**Problem (brief §16):** find which conditions **occur together**, e.g. *"Summer + Dissolved oxygen + South → Exceedance"*.
**Data:** results from `WaterQualityAnalyticsMart` (built from the batch DW). **Item attributes:** chosen in Step 4 by Cramér's V (`selected_features.json`), plus the outcome items.

**How it works, simply:** each result becomes a *basket* of items, for example `{Parameter=Dissolved oxygen, Season=Summer, Region=South, WaterType=Surface Water, ResultBand=Low, Exceedance=Yes}`. The algorithm finds item combinations that appear often (**frequent itemsets**) and turns them into rules **A → B**.

| Metric | Meaning | Example |
|---|---|---|
| **Support** | Share of all baskets containing A and B | 0.02 = 2% of results |
| **Confidence** | Of baskets with A, the share that also have B | 0.60 = 60% of "Summer + DO + South" results exceed |
| **Lift** | Confidence ÷ how common B is overall; > 1 means A makes B *more* likely than usual | 3.0 = three times the normal exceedance rate |

**Discretisation:** continuous values are already turned into **ResultBand** (Very Low … Very High) using the documented thresholds from Step 2, as the brief requires.
**Algorithms:** **Apriori** (mandatory) and **FP-Growth** (recommended extension); both must find the same itemsets, and their run times are compared.
**Quality rules for reporting:**
- minimum support 0.5%, so rare flukes with a huge lift are not presented as important
- rules whose antecedent contains *ResultBand* while the consequent is *Exceedance/HighRisk* are **definitional** (the band already implies the flag), so they are filtered out
""")
code(r"""
import sys, time, json, numpy as np, pandas as pd, matplotlib.pyplot as plt, seaborn as sns
from pathlib import Path
from mlxtend.frequent_patterns import apriori, fpgrowth, association_rules
ROOT = Path.cwd().resolve()
for p in [ROOT, *ROOT.parents]:
    if (p / '09_mining' / 'mining_data.py').exists(): ROOT = p; break
sys.path.insert(0, str(ROOT / '09_mining')); import mining_data as md_
OUT = ROOT / '09_mining'; FIG, TAB = OUT / 'figures', OUT / 'tables'; FIG.mkdir(exist_ok=True); TAB.mkdir(exist_ok=True)
sns.set_theme(style='whitegrid'); pd.set_option('display.width', 220); pd.set_option('display.max_colwidth', 120)
def save_tab(df, n, index=False): df.to_csv(TAB / f'A{n}.csv', index=index); return df
def save_fig(n): plt.tight_layout(); plt.savefig(FIG / f'A{n}.png', dpi=130, bbox_inches='tight'); plt.show()
ATTR = [a for a in md_.SELECTED['association']['item_attributes'] if a not in ('exceedance_flag', 'high_risk_flag', 'result_band')]
print('Item attributes from Step 4:', ATTR)
con = md_.connect()
cols = ', '.join(ATTR)
tx = con.execute(f'''SELECT {cols}, result_band, exceedance_flag, high_risk_flag FROM mart USING SAMPLE reservoir(600000 ROWS) REPEATABLE (21)''').df()
NAMES = {'parameter': 'Parameter', 'parameter_group': 'Group', 'season': 'Season', 'region': 'Region', 'water_type': 'WaterType',
         'sample_type_group': 'SampleType', 'equipment_group': 'Equipment', 'time_band': 'TimeBand', 'is_weekend': 'Weekend', 'year': 'Year'}
items = pd.DataFrame(index=tx.index)
for a in ATTR:
    v = tx[a].astype(str)
    if a == 'water_type': v = v.where(v != 'Not Reported')            # unknown water type is not an informative item
    for cat in v.dropna().unique(): items[f'{NAMES.get(a, a)}={cat}'] = (v == cat)
for b in tx.result_band.dropna().unique(): items[f'ResultBand={b}'] = tx.result_band == b
items['Exceedance=Yes'] = tx.exceedance_flag == 1; items['Exceedance=No'] = tx.exceedance_flag == 0
items['HighRisk=Yes'] = tx.high_risk_flag == 1
items = items.loc[:, items.mean() >= 0.001]
print(f'Transactions (results): {len(items):,} · distinct items: {items.shape[1]}')
display(items.mean().sort_values(ascending=False).rename('support').to_frame().head(15))
""")

md(r"""## 1 · Frequent itemsets: Apriori vs FP-Growth""")
code(r"""
MIN_SUP = 0.005
t = time.time(); fi_ap = apriori(items, min_support=MIN_SUP, use_colnames=True, max_len=4); t_ap = time.time() - t
t = time.time(); fi_fp = fpgrowth(items, min_support=MIN_SUP, use_colnames=True, max_len=4); t_fp = time.time() - t
same = set(map(frozenset, fi_ap.itemsets)) == set(map(frozenset, fi_fp.itemsets))
cmp_ = pd.DataFrame({'Apriori': [len(fi_ap), round(t_ap, 2)], 'FP-Growth': [len(fi_fp), round(t_fp, 2)]}, index=['Frequent itemsets', 'Seconds'])
display(save_tab(cmp_, '01_apriori_vs_fpgrowth', index=True)); print('Same itemsets found by both:', same)
""")
infer("A1")

md(r"""## 2 · Rules, filtering and the 10 most meaningful rules""")
code(r"""
rules = association_rules(fi_ap, metric='confidence', min_threshold=0.3)
rules['antecedents_s'] = rules.antecedents.map(lambda s: ' + '.join(sorted(s))); rules['consequents_s'] = rules.consequents.map(lambda s: ' + '.join(sorted(s)))
outcome = rules.consequents_s.str.contains('Exceedance=Yes|HighRisk=Yes')
definitional = rules.antecedents_s.str.contains('ResultBand=|Exceedance=|HighRisk=') & outcome
print(f'All rules: {len(rules):,} · rules predicting an exceedance/high-risk outcome: {outcome.sum():,} · removed as definitional: {definitional.sum():,}')
keep = rules[outcome & ~definitional & (rules.lift > 1.2) & (rules.support >= MIN_SUP)].copy()
keep = keep.sort_values(['lift', 'confidence'], ascending=False)
# avoid near-duplicates: keep the shortest antecedent for each consequent/lift level
keep['n_items'] = keep.antecedents.map(len)
top = keep.drop_duplicates(subset=['consequents_s', 'antecedents_s']).head(40)
display(save_tab(top[['antecedents_s', 'consequents_s', 'support', 'confidence', 'lift', 'n_items']].round(4), '02_outcome_rules_top40'))
other = rules[~outcome & ~rules.antecedents_s.str.contains('ResultBand=|Exceedance=|HighRisk=') & ~rules.consequents_s.str.contains('ResultBand=|Exceedance=|HighRisk=')
              & (rules.lift > 1.5) & (rules.confidence > 0.6)].sort_values('lift', ascending=False)
display(save_tab(other[['antecedents_s', 'consequents_s', 'support', 'confidence', 'lift']].head(15).round(4), '03_monitoring_pattern_rules'))
""")

md(r"""## 3 · Rule map""")
code(r"""
fig, ax = plt.subplots(figsize=(11, 6))
sc = ax.scatter(rules.support, rules.confidence, c=rules.lift.clip(upper=8), s=8, cmap='viridis', alpha=0.4, label='all rules')
ax.scatter(top.head(10).support, top.head(10).confidence, s=90, facecolors='none', edgecolors='red', linewidths=2, label='top-10 outcome rules')
for i, r in top.head(10).reset_index().iterrows(): ax.annotate(str(i + 1), (r.support, r.confidence), fontsize=9, color='red', xytext=(4, 2), textcoords='offset points')
plt.colorbar(sc, label='lift (capped at 8)'); ax.set_xscale('log')
ax.set(title='A3 · Support vs confidence of all rules (colour = lift); red = the 10 reported rules', xlabel='support (log)', ylabel='confidence'); ax.legend()
save_fig('03_rule_map')
""")
md(r"""**Why this chart:** each dot is a rule. Good rules sit to the right (common enough) and high (reliable), with a bright colour (strong lift). The numbered red circles are the 10 rules interpreted below.""")
infer("A3")
md(r"""## 4 · The 10 reported rules with interpretation""")
code(r"""
ten = top.head(10)[['antecedents_s', 'consequents_s', 'support', 'confidence', 'lift']].reset_index(drop=True)
ten.index = [f'Rule {i + 1}' for i in range(len(ten))]
display(save_tab(ten.round(4), '04_ten_rules', index=True))
""")
infer("A4")

nb = nbf.v4.new_notebook(); nb.cells = cells
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, OUT); print('written', OUT, len(cells), 'cells')
