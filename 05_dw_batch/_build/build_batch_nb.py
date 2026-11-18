"""Builds 05_dw_batch/batch_dw_demo.ipynb."""
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
# Step 6 · Traditional Batch Data Warehouse (PostgreSQL) · live demo

**Architecture (brief §2A):** `Raw source → Python curation (Step 2) → Staging → ETL → Dimensional warehouse → OLAP → Power BI`

| Piece | Where |
|---|---|
| PostgreSQL 16 in Docker | `05_dw_batch/docker-compose.yml` (port 5433) |
| Schema: staging + fact constellation | `sql/01_create_schema.sql` |
| Static dimensions (Date, Time, Characteristic) | `sql/02_static_dimensions.sql` |
| Per-batch load: DQ rules → dimension lookup / new members → fact → monthly fact | `sql/03_load_batch.sql` |
| Foreign keys + indexes (after the bulk load) | `sql/04_constraints_indexes.sql` |
| Historical analytical queries | `sql/05_analytical_queries.sql` |
| ETL program | `etl/etl_batch.py` |

**Incremental scenario (brief §10):** the **initial load** covers 1 Jan 2024 – 30 Nov 2025. **December 2025 is held back** as "newly arrived data" and loaded later **without rebuilding** the warehouse:
`New period → Staging → DQ rules → existing dimension lookup → insert new dimension members → fact load → validation`

**Before running:** `docker compose -f 05_dw_batch/docker-compose.yml up -d` (the notebook starts it if needed).
""")
code(r"""
import sys, subprocess, time, pandas as pd, matplotlib.pyplot as plt, seaborn as sns
from pathlib import Path
ROOT = Path.cwd().resolve()
for p in [ROOT, *ROOT.parents]:
    if (p / '05_dw_batch' / 'etl').exists(): ROOT = p; break
sys.path.insert(0, str(ROOT / '05_dw_batch' / 'etl'))
import etl_batch as etl
OUT = ROOT / '05_dw_batch'; FIG, TAB = OUT / 'figures', OUT / 'tables'; FIG.mkdir(exist_ok=True); TAB.mkdir(exist_ok=True)
sns.set_theme(style='whitegrid'); pd.set_option('display.width', 200); pd.set_option('display.max_columns', 20)
def save_tab(df, n, index=False): df.to_csv(TAB / f'B{n}.csv', index=index); return df
def save_fig(n): plt.tight_layout(); plt.savefig(FIG / f'B{n}.png', dpi=130, bbox_inches='tight'); plt.show()
r = subprocess.run(['docker', 'compose', '-f', str(OUT / 'docker-compose.yml'), 'up', '-d', '--wait'], capture_output=True, text=True)
print(r.stdout[-300:] or r.stderr[-300:])
print(subprocess.run(['docker', 'ps', '--filter', 'name=wq_batch_dw', '--format', '{{.Names}}  {{.Status}}  {{.Ports}}'], capture_output=True, text=True).stdout)
""")

md(r"""
## 1 · Create the warehouse (staging + dimensions + facts)
Drops and recreates the `stg` and `dw` schemas, then loads the **static dimensions**: every calendar day (DimDate), 24 hours + "Not Reported" (DimTime), and the 6 parameters with their documented thresholds (DimCharacteristic).
""")
code(r"""
con = etl.reset()
display(etl.table_counts(con))
display(etl.q(con, 'SELECT * FROM dw.dim_characteristic'))
display(etl.q(con, "SELECT * FROM dw.dim_date WHERE date_key IN (20240101, 20240706, 20251231)"))
""")

md(r"""
## 2 · Initial load (1 Jan 2024 – 30 Nov 2025)
1. **Extract:** analysis-ready single readings for the period are read from the curated Parquet file and bulk-copied (`COPY`) into `stg.wq_results`.
2. **Data-quality rules:** rows with a missing key, value or date, an unknown parameter, or a date outside the study period are rejected.
3. **Dimensions:** every new site → `dim_monitoring_location` (state, region, coordinates, water type); every new organization/method combination → `dim_organization_method`. Each gets a **surrogate key**.
4. **Fact:** each staged row looks up its 5 surrogate keys and is inserted into `fact_water_quality_result`.
5. **Monthly fact:** `fact_site_monthly_water_quality` is built **from the detail fact** (site × parameter × month).
6. **Constraints and indexes** are added *after* the bulk load (much faster), and from then on they protect every later load.
""")
code(r"""
s1, t1 = etl.load(*etl.INITIAL, con=con)
display(pd.Series(s1, name='Initial load').to_frame())
display(pd.Series(t1, name='seconds').to_frame())
display(etl.table_counts(con))
""")

md(r"""
## 3 · Validation and reconciliation after the initial load
Referential integrity (no fact points to a missing dimension row), no duplicate results, and reconciliation of counts and value sums between staging, the warehouse, and the monthly fact.
*(The check against all curated analysis-ready rows is expected to FAIL here, because December 2025 is deliberately not loaded yet.)*
""")
code(r"""
v1 = etl.validate(con); display(save_tab(v1, '03_validation_after_initial'))
""")

md(r"""
## 4 · Historical analytical queries with execution time
Each query from `sql/05_analytical_queries.sql` is run 3 times; the median time is reported. The last query answers the monthly trend from the **aggregate fact** instead of the 3.7M-row detail fact, to show the benefit of the fact constellation.
""")
code(r"""
tq1, res1 = etl.queries(repeat=3, con=con)
display(save_tab(tq1, '04_query_times_initial'))
for n in ['Q3_worst_sites', 'Q6_exceedance_by_region', 'Q8_water_type']:
    print(n); display(res1[n].head(10))
""")

md(r"""
## 5 · Incremental load: December 2025 arrives
Exactly the same ETL runs for **one new month only**. The existing 3.7M facts are **not touched or rebuilt**. Existing sites and organizations are **looked up** by their natural key; only **new** ones get new surrogate keys. Only the December rows of the monthly fact are rebuilt.
""")
code(r"""
before = etl.table_counts(con).set_index('table_name').rows
s2, t2 = etl.load(*etl.INCREMENTAL, con=con)
after = etl.table_counts(con).set_index('table_name').rows
display(pd.Series(s2, name='Incremental load').to_frame()); display(pd.Series(t2, name='seconds').to_frame())
delta = pd.DataFrame({'Before': before, 'After': after}); delta['Added'] = delta.After - delta.Before
display(save_tab(delta, '05_incremental_delta', index=True))
print('New sites first seen in December 2025:')
display(etl.q(con, '''SELECT site_id, state, region, water_type FROM dw.dim_monitoring_location WHERE first_load_batch = 2 ORDER BY state LIMIT 10'''))
log = etl.q(con, 'SELECT * FROM dw.etl_load_log ORDER BY load_batch_id'); display(save_tab(log, '05_etl_load_log'))
""")

md(r"""
## 6 · Validation after the incremental load
All checks must now PASS, including **warehouse rows = all curated analysis-ready rows** (Step 2), which proves the initial + incremental loads together are complete.
""")
code(r"""
v2 = etl.validate(con); display(save_tab(v2, '06_validation_after_incremental'))
print('ALL CHECKS PASS' if (v2.Status == 'PASS').all() else 'SOME CHECKS FAILED')
""")

md(r"""
## 7 · Queries after the incremental load, and load summary charts
""")
code(r"""
tq2, res2 = etl.queries(repeat=3, con=con)
tq = tq1[['Query', 'Median ms']].merge(tq2[['Query', 'Median ms']], on='Query', suffixes=(' (initial)', ' (after incremental)'))
display(save_tab(tq, '07_query_times'))
m = res2['Q1_monthly_trend']; m['results'] = m.results.astype(int)
fig, axes = plt.subplots(1, 3, figsize=(19, 4.6), gridspec_kw={'width_ratios': [1, 1.2, 1.4]})
lt = pd.DataFrame({'Initial (23 months)': [s1['seconds']], 'Incremental (1 month)': [s2['seconds']]}).T
axes[0].bar(lt.index, lt[0], color=['#4C72B0', '#DD8452']); [axes[0].text(i, v_, f'{v_:.0f}s', ha='center', va='bottom') for i, v_ in enumerate(lt[0])]
axes[0].set(title='B7a · ETL load time', ylabel='seconds')
d = tq.set_index('Query')
d.plot(kind='barh', ax=axes[1], color=['#4C72B0', '#DD8452']); axes[1].set(title='B7b · Query time (median of 3 runs)', xlabel='milliseconds', ylabel='')
axes[2].bar(m.year_month, m.results / 1e3, color=['#DD8452' if x == '2025-12' else '#4C72B0' for x in m.year_month])
axes[2].set(title='B7c · Results per month in the warehouse (orange = incremental load)', ylabel='thousands'); axes[2].tick_params(axis='x', rotation=75, labelsize=7.5)
save_fig('07_load_and_query_summary')
""")
md(r"""**Why these charts:** load time compares the full and incremental ETL runs; query times show how fast the warehouse answers the business questions; the monthly bars show that the incremental month joined the existing history without a rebuild.""")
infer("B7")

md(r"""
## 8 · Warehouse size
""")
code(r"""
sz = etl.q(con, '''SELECT relname AS table_name, pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
                          pg_total_relation_size(c.oid) AS bytes
                   FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                   WHERE n.nspname = 'dw' AND c.relkind = 'r' ORDER BY bytes DESC''')
display(save_tab(sz, '08_table_sizes'))
""")
infer("B8")

nb = nbf.v4.new_notebook(); nb.cells = cells
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, OUT); print('written', OUT, len(cells), 'cells')
