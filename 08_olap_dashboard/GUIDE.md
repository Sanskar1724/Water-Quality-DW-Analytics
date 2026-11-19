# Guide: `08_olap_dashboard/` (Step 9: OLAP + Power BI Dashboard + 10 Findings)

## What this folder does, in plain words
The warehouse built in `05_dw_batch/` is full of clean, organised data. This folder **asks it business questions** in the standard "OLAP" ways (zoom out, zoom in, cut, rotate, summarise everything at once), saves every answer as a table and a chart, and explains how to build a **4-page Power BI dashboard** on top of it. Finally, it turns the answers into **10 findings** with recommendations.

> **Analogy:** the warehouse is a library that is perfectly shelved. OLAP is the set of standard ways a librarian answers questions: "how many books per floor?" (roll-up), "show me the shelves on floor 2" (drill-down), "only history books" (slice), "only history books from the 1990s in English" (dice), "make me a table: subjects across, floors down" (pivot). The dashboard is the noticeboard at the entrance that shows the most important answers at a glance.

## How to run it (on the laptop, warehouse running)
```bash
docker compose -f 05_dw_batch/docker-compose.yml up -d
python 08_olap_dashboard/olap_runner.py --views
```
- Runs all 16 OLAP queries 3 times each and keeps the median time (`tables/O00_query_times.csv`).
- Saves each answer to `tables/O01…O16.csv` and a chart to `figures/O01…O16.png`.
- `--views` also creates the `bi` views that Power BI imports. Use `--repeat 1` for a quicker trial, or give ids (`O11 O15`) to run only some queries.
- Then follow `POWERBI_BUILD_GUIDE.md` to build the dashboard, and fill the `[CONFIRM]` / `[TO FILL]` placeholders in `OLAP_OPERATIONS.md` and `FINDINGS_TEMPLATE.md` with the real numbers.

## What's inside
| File | Purpose |
|---|---|
| `sql/01_olap_operations.sql` | 16 named queries: 2 per OLAP operation (Roll-Up, Drill-Down, Slice, Dice, Pivot, CUBE, GROUPING SETS, ROLLUP) |
| `sql/02_powerbi_views.sql` | Schema `bi`: 7 views for the star model + 6 helper views for the 4 dashboard pages |
| `olap_runner.py` | Runs, times and charts every query; optionally creates the views |
| `OLAP_OPERATIONS.md` | Each operation explained simply, in the brief's format: Question → Dimensions → Measure → Operation → SQL → Output → Interpretation |
| `POWERBI_BUILD_GUIDE.md` | Click-by-click guide: connect, relationships, DAX measures, 4 pages of visuals and slicers |
| `FINDINGS_TEMPLATE.md` | 10 findings (Question → Analysis → Evidence → Interpretation → Recommendation) with placeholders for confirmed numbers |
| `NOTES_FOR_LOG.md` | Summary of this step for the project log |
| `tables/`, `figures/` | Outputs of the runner (created when it is run locally) |

## Justification and inference (why it is built this way)
- **Two queries per operation, on three hierarchies** (Time, Geography, Parameter): every mandatory operation is shown on real business questions, and each hierarchy is used for both zooming out and zooming in. *Inference:* the examiner can see each operation produce a different, meaningful answer, not just syntax.
- **Rates instead of raw counts.** Regions and parameters have very different numbers of results, so comparing counts would just show where most sampling happens. *Inference:* exceedance rate (%) is the fair comparison; counts are kept next to it so small groups can be spotted.
- **The small monthly fact is used when only counts/rates are needed**, the detail fact when a median is needed. *Inference:* the fact-constellation design from Step 5 pays off: the same answer at a fraction of the time (see the Step 6 timings, 0.2 s vs 5 s).
- **Views (`bi`) between Power BI and the warehouse.** *Inference:* Power BI sees friendly names and small helper tables, and a single "Refresh" picks up new incremental loads.
- **Exceedance and high-risk are derived fields.** They are calculated by the project from documented thresholds, not given by the source. Every document says so, and findings talk about *relative* risk, not legal violations.

## Terms used, explained simply
| Term | Simple meaning | Everyday analogy | How used here | Why it matters |
|---|---|---|---|---|
| **OLAP** | Online Analytical Processing: fast ways to summarise and explore a warehouse from many angles | Looking at a Rubik's cube from different sides | 16 queries in `01_olap_operations.sql` | The brief requires all operations, and it is how managers explore data |
| **Data cube** | The data seen as a block with one axis per dimension (time, place, parameter) and numbers inside | A box of chocolates arranged by row, column and layer | Month × Region × Parameter group | Every OLAP operation is a way of cutting or summarising the cube |
| **Dimension** | A way to describe or group the data | The labels on folders | Date, Location, Characteristic, Organisation/method | Decides *by what* we can group |
| **Measure** | A number we add up or average | The amount on a receipt | Results, exceedance rate, median value | Decides *what* we count |
| **Hierarchy** | Levels of a dimension from general to detailed | Country → city → street | Year → Quarter → Month → Day; Region → State → Site; Group → Characteristic | Makes roll-up and drill-down possible |
| **Roll-Up** | Summarising up a hierarchy | Daily expenses → monthly total | Sites → regions (O01), months → quarters (O02) | Big picture |
| **Drill-Down** | Going down a hierarchy into detail | Opening the monthly statement to see each purchase | Year → month for DO (O03); worst state → its sites (O04) | Finds the cause behind a total |
| **Slice** | Fix one dimension to one value | One slice of bread | Only dissolved oxygen (O05); only 2025 (O06) | Focus on one thing |
| **Dice** | Filter several dimensions at once | Cutting a small cube from a cake | South/West × Summer/Winter × Chemical (O07) | Focused comparisons |
| **Pivot** | Swap rows and columns | Turning a spreadsheet sideways | Seasons as columns (O09), parameters as columns (O10) | Easier to compare side by side |
| **CUBE** | SQL that gives every combination and every subtotal | A report with totals by every possible grouping | `GROUP BY CUBE(month, region, group)` (O11) | One query instead of eight |
| **ROLLUP** | SQL that gives subtotals along one hierarchy | A bank statement with monthly and yearly subtotals | `ROLLUP(year, quarter, month)` (O15) | Totals at every level in one result |
| **GROUPING SETS** | SQL that gives exactly the groupings you list | Ordering three separate reports in one go | Region / parameter / season / overall (O13) | One scan of 3.77 M rows instead of four |
| **GROUPING()** | Tells whether a row is a subtotal for that column | A "TOTAL" label on a line | Turns the blank into "ALL" | Subtotal rows are not confused with missing data |
| **Exceedance rate** | Share of results outside the threshold (**derived**) | Share of exam answers that were wrong | `100 × avg(exceedance_flag)` | Fair comparison across groups of different size |
| **High-risk rate** | Share of results far outside the threshold (**derived**) | Share of answers that were badly wrong | `100 × avg(high_risk_flag)` | Separates severe cases from moderate ones |
| **Median** | The middle value when sorted | The middle person in a height line-up | `percentile_cont(0.5)`, DAX `MEDIAN` | Not distorted by extreme values; only meaningful within one parameter |
| **View** | A saved query that looks like a table but stores no data | A window onto a room | Schema `bi` | Power BI reads clean, always-current data |
| **Power BI** | Microsoft's dashboard tool | A smart noticeboard | 4-page dashboard | Required by the brief, interactive for managers |
| **DAX** | Power BI's formula language for measures | Excel formulas, for whole tables | `Exceedance Rate % = DIVIDE([Exceedances],[Results])` | Measures recalculate for every filter and click |
| **Relationship** | A link between a fact and a dimension in Power BI | A line connecting a receipt to the product list | 8 links in the model | Lets slicers on dimensions filter the facts |
| **Slicer** | A clickable filter on a dashboard page | TV channel buttons | Year, season, region, parameter | Lets users slice and dice themselves |
| **Median of 3 timing** | Each query run 3 times, the middle time kept | Timing a run three times and taking the middle | `O00_query_times.csv` | Removes one-off slow or fast runs |
