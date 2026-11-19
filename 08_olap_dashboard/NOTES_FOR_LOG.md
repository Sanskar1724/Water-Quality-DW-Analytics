# Notes for the project log (Step 9: OLAP + Power BI dashboard)

To be copied into `docs/PROJECT_LOG.md` (this step did not edit it).

## 2026-11-19: Step 9 OLAP operations, Power BI views and dashboard guide written
- **What:** Created `08_olap_dashboard/`:
  - `sql/01_olap_operations.sql`: 16 named queries, 2 for each mandatory OLAP operation (brief §13): Roll-Up (O01 Site→Region, O02 Month→Quarter/Year), Drill-Down (O03 Year→Quarter→Month for DO, O04 worst state→sites), Slice (O05 DO only, O06 year 2025 only), Dice (O07 South/West × Summer/Winter × Chemical, O08 Physical × Surface Water × Summer 2025), Pivot (O09 Parameter × Season, O10 Region × Parameter), CUBE (O11 Month × Region × ParameterGroup, the brief's example, O12 Season × ParameterGroup), GROUPING SETS (O13 region/parameter/season/overall, O14 provider/sample type/equipment), ROLLUP (O15 Year→Quarter→Month, O16 ParameterGroup→Characteristic).
  - `olap_runner.py`: reuses `connect()`/`q()` from `05_dw_batch/etl/etl_batch.py`; runs each query 3× (median time), saves `tables/O<id>.csv`, one chart per query `figures/O<id>.png`, and `tables/O00_query_times.csv`; `--views` creates the Power BI views.
  - `sql/02_powerbi_views.sql`: schema `bi` with 7 model views (2 facts, 5 dims) and 6 helper views (exec KPIs, site summary, region×parameter×month, site×month heat map, parameter distribution, cross-parameter).
  - `OLAP_OPERATIONS.md` (brief format per operation), `POWERBI_BUILD_GUIDE.md` (beginner click guide: connection 127.0.0.1:5433, 8 relationships, 3 hierarchies, DAX measures, 4 pages), `FINDINGS_TEMPLATE.md` (10 findings pre-filled from EDA, numbers to confirm), `GUIDE.md`.
- **Why:** Brief §13 requires every OLAP operation on the warehouse with business questions; §14 requires a 4-page dashboard and 10 findings.
- **Design choices:** rates (AVG of 0/1 flags) rather than counts for fair comparisons; the monthly aggregate fact is used for count/rate queries (exact, much faster), the detail fact only where a median is needed; `GROUPING()` labels subtotal rows as `ALL`; exceedance/high-risk are stated everywhere as **derived** fields.
- **Testing done (cloud session, no access to the real DB):** `py_compile` passes. All 16 OLAP queries and all 13 views were **executed successfully on a throw-away PostgreSQL 16 instance with the real schema files (01, 02, 04) and ~200,000 synthetic rows**; the runner produced 16 CSVs and charts end to end (O08 returned 0 rows on synthetic data because of its ≥ 500-result filter, expected to return rows on real data). Synthetic outputs were **not** committed.
- **Result:** _[TO FILL after the local run: rows and median ms per query from `tables/O00_query_times.csv`; headline numbers for F1–F10]_.
- **Next (local):** `python 08_olap_dashboard/olap_runner.py --views` → check the 16 charts → fill `[TO FILL]`/`[CONFIRM]` in `OLAP_OPERATIONS.md` and `FINDINGS_TEMPLATE.md` → build the dashboard with `POWERBI_BUILD_GUIDE.md` → export screenshots/PDF to `figures/`.
- **Files:** `08_olap_dashboard/*`
