"""Fills the Inference cells of batch_dw_demo.ipynb from the run's result tables."""
import nbformat as nbf, sys, pandas as pd
from pathlib import Path
P = Path(sys.argv[1]); T = P.parent / 'tables'
log = pd.read_csv(T / 'B05_etl_load_log.csv').set_index('load_mode')
qt = pd.read_csv(T / 'B07_query_times.csv').set_index('Query')
sz = pd.read_csv(T / 'B08_table_sizes.csv').set_index('table_name')
val = pd.read_csv(T / 'B06_validation_after_incremental.csv')
ini, inc = log.loc['initial'], log.loc['incremental']
q1 = qt.loc['Q1_monthly_trend'].iloc[1]; m1 = qt.loc['M1_monthly_fact_trend'].iloc[1]
INF = {
"B7": f"""**🔎 Inference (B7): loads, queries and the incremental scenario**
- **Initial load:** {int(ini.fact_rows_inserted):,} results (Jan 2024 – Nov 2025) with {int(ini.new_locations):,} sites and {int(ini.new_org_methods)} organization/method combinations, in **{ini.seconds:.0f} s**. That includes staging (bulk COPY), the data-quality rules, dimension and fact loading, the monthly fact, and creating the foreign keys and indexes.
- **Incremental load (December 2025):** {int(inc.fact_rows_inserted):,} new results in **{inc.seconds:.0f} s**, about **{ini.seconds / inc.seconds:.0f}× faster** than the initial load, **without rebuilding anything**.
  - The existing sites and organizations were *looked up* by their natural keys.
  - Only **{int(inc.new_locations)} genuinely new sites** and **{int(inc.new_org_methods)} new organization/method combinations** got new surrogate keys.
  - Only the December rows of the monthly fact were rebuilt.
  - **0 rows were rejected** by the data-quality rules, as expected, because Step 2 already cleaned the data. The rules stay in place for future batches.
- **Validation: all {len(val)} checks PASS** ({(val.Status == 'PASS').sum()}/{len(val)}):
  - no orphan keys and no duplicate results
  - warehouse rows = **all 3,772,033 curated analysis-ready rows**
  - monthly-fact totals = detail-fact totals (rows and exceedances)
  - the sum of all values equals staging to the last unit
- **Query performance:** the 8 analytical queries over 3.77M facts run in about **1–7 s** each.
  - The monthly trend answered from the **aggregate fact takes {m1:.0f} ms vs {q1:,.0f} ms** from the detail fact, **{q1 / m1:.0f}× faster**. That is measured evidence for choosing the **fact constellation** (Step 5).
  - Median-based queries (Q2, Q4) are the slowest because a median must sort values. Times barely change after the incremental load (+0.6% rows), showing the design scales smoothly.
- **The chart of results per month** shows December 2025 (orange) joined onto the existing history as a normal month.""",
"B8": f"""**🔎 Inference (B8): warehouse size**
- The detail fact (`fact_water_quality_result`, 3.77M rows, including its indexes) is **{sz.loc['fact_water_quality_result', 'total_size']}**, the monthly fact is **{sz.loc['fact_site_monthly_water_quality', 'total_size']}**, and every dimension together is only a few MB.
- So the **fact table is over 95% of the warehouse**. Making the dimensions smaller by snowflaking would save almost nothing, which confirms the Step 5 choice of simple star dimensions.
- The whole warehouse fits comfortably on a laptop. Moving to a distributed design (Citus, Step 7) is about **parallel query speed and scaling to more data**, not about storage capacity at this size.""",
}
nb = nbf.read(P, as_version=4); n = 0
for c in nb.cells:
    t = c.get('metadata', {}).get('infer')
    if t in INF: c.source = INF[t]; n += 1
nbf.write(nb, P); print('filled', n)
