# Power BI Build Guide: 4-page Water Quality Dashboard (brief §14)

A click-by-click guide for someone who has **never used Power BI**. Follow the parts in order. Total time: about 2–3 hours the first time.

> **Before you start**
> 1. The batch warehouse must be running and loaded: `docker compose -f 05_dw_batch/docker-compose.yml up -d` (see `05_dw_batch/GUIDE.md`).
> 2. Create the Power BI views (run once, from the repository root):
>    ```bash
>    python 08_olap_dashboard/olap_runner.py --views
>    ```
>    This creates the schema `bi` with 7 model views + 6 helper views (see `sql/02_powerbi_views.sql`).
> 3. Install **Power BI Desktop** (free, Windows, Microsoft Store).

---

## Part A: Connect to PostgreSQL

1. Open Power BI Desktop → **Blank report**.
2. **Home → Get data → More…** → search **PostgreSQL database** → **Connect**.
   - If it says a component is missing: Power BI Desktop (recent versions) ships the Npgsql driver. If not, install *Npgsql* (version 4.0.x with "GAC installation" ticked) and restart Power BI.
3. **Server:** `127.0.0.1:5433` **Database:** `wq_dw` → **Data Connectivity mode: Import** → **OK**.
4. Credentials: choose the **Database** tab (left) → **User name:** `wq` **Password:** the local test password from `05_dw_batch/docker-compose.yml` → **Connect**.
   - If asked about encryption: click **OK** to connect without encryption (it is a local container on your own laptop).
5. In the **Navigator**, expand `wq_dw` and tick these 13 views (all start with `bi.`):

| Tick | Rows (approx.) | Role |
|---|---|---|
| `bi.fact_result` | 3.77 M | main fact (one row per measurement) |
| `bi.fact_site_month` | site × parameter × month | monthly fact (fast trends) |
| `bi.dim_date`, `bi.dim_time`, `bi.dim_location`, `bi.dim_characteristic`, `bi.dim_org_method` | small | dimensions |
| `bi.v_exec_kpis`, `bi.v_site_summary`, `bi.v_region_param_month`, `bi.v_site_month_heat`, `bi.v_parameter_distribution`, `bi.v_cross_parameter` | small | helper tables for pages 1–4 |

6. Click **Load** (not *Transform*). Loading 3.77 M rows takes a few minutes. Save the file as `08_olap_dashboard/water_quality_dashboard.pbix`.
   - *Laptop too slow?* Untick `bi.fact_result` and build everything from `bi.fact_site_month` and the helper views. You lose only the exact median measure and the drill to individual results.

7. **Rename the tables** (right-click the table in the **Data** pane → *Rename*), removing the `bi ` prefix: `fact_result`, `fact_site_month`, `dim_date`, `dim_time`, `dim_location`, `dim_characteristic`, `dim_org_method`, `v_exec_kpis`, … The DAX below uses these short names.

---

## Part B: Relationships (the star schema)

Click the **Model view** icon (third icon on the left bar). Power BI may already have drawn some lines. Delete any line that is not in this table (click the line → Delete) and create the missing ones by **dragging the key column from the fact onto the same column in the dimension**.

| From (many side, fact) | To (one side, dimension) | Cardinality | Cross-filter |
|---|---|---|---|
| `fact_result[date_key]` | `dim_date[date_key]` | Many-to-one | Single |
| `fact_result[time_key]` | `dim_time[time_key]` | Many-to-one | Single |
| `fact_result[location_key]` | `dim_location[location_key]` | Many-to-one | Single |
| `fact_result[characteristic_key]` | `dim_characteristic[characteristic_key]` | Many-to-one | Single |
| `fact_result[org_method_key]` | `dim_org_method[org_method_key]` | Many-to-one | Single |
| `fact_site_month[date_key]` | `dim_date[date_key]` | Many-to-one | Single |
| `fact_site_month[location_key]` | `dim_location[location_key]` | Many-to-one | Single |
| `fact_site_month[characteristic_key]` | `dim_characteristic[characteristic_key]` | Many-to-one | Single |

The helper views (`v_…`) stay **unconnected**: each one feeds its own visuals. Slicers from the dimensions do **not** filter them, so put them on pages or use their own columns as slicers (noted per visual below).

Then:
1. `dim_date` → right-click → **Mark as date table** → column `full_date`.
2. `dim_date[month_name]` → Column tools → **Sort by column** → `month`. Same: `season` sorted by `season_order`, `time_band` by `time_band_order`.
3. `dim_location[latitude]` → Column tools → **Data category: Latitude**, `longitude` → **Longitude**, `state` → **State or Province**.
4. Hide key columns in report view (right-click → *Hide in report view*): every `*_key` column in the facts.
5. **Hierarchies** (right-click the top column → *Create hierarchy*, then right-click the next column → *Add to hierarchy*):
   - `dim_date`: **Time** = year → quarter → month_name → full_date
   - `dim_location`: **Geography** = region → state → site_id
   - `dim_characteristic`: **Parameter** = parameter_group → short_name

---

## Part C: DAX measures

Create an empty table to keep measures together: **Home → Enter data** → name it `_Measures` → Load. Then select `_Measures` and click **New measure** for each line below (paste, press Enter).

```DAX
Results = COUNTROWS ( fact_result )

Sites = DISTINCTCOUNT ( fact_result[location_key] )

Parameters = DISTINCTCOUNT ( fact_result[characteristic_key] )

Exceedances = SUM ( fact_result[exceedance_flag] )

High-Risk Results = SUM ( fact_result[high_risk_flag] )

Organizations = CALCULATE ( DISTINCTCOUNT ( dim_org_method[organization] ), fact_result )

Exceedance Rate % = DIVIDE ( [Exceedances], [Results] )

High-Risk Rate % = DIVIDE ( [High-Risk Results], [Results] )

Median Value = MEDIAN ( fact_result[result_value] )

Results (monthly fact) = SUM ( fact_site_month[sample_count] )

Exceedance Rate % (monthly fact) =
    DIVIDE ( SUM ( fact_site_month[exceedance_count] ), SUM ( fact_site_month[sample_count] ) )

Sampled Months = DISTINCTCOUNT ( fact_site_month[date_key] )

Exceedance Rate % vs All Regions =
    [Exceedance Rate %] - CALCULATE ( [Exceedance Rate %], REMOVEFILTERS ( dim_location ) )
```

Formatting (select the measure → **Measure tools**): set `Exceedance Rate %`, `High-Risk Rate %` and both other rate measures to **Percentage, 1 decimal**; counts to **Whole number with thousands separator**.

> **Important for honesty:** `exceedance_flag` and `high_risk_flag` are **derived by the project** from documented thresholds (see `dim_characteristic[exceedance_rule]`, `[threshold_source]`). Put a small text box on each page: *"Exceedance = result outside the project/EPA threshold for that parameter (derived field)."*

> **Why `Organizations` uses `CALCULATE(…, fact_result)`:** relationships filter from dimension to fact only, so a plain `DISTINCTCOUNT(dim_org_method[organization])` would ignore a Region or Year slicer. Passing `fact_result` as a filter counts only organisations that have results in the current selection.

> **Median Value** is only meaningful when **one** parameter is selected (pH and conductivity have different units). Use it with a parameter slicer or with `short_name` on an axis.

---

## Part D: Report pages

General look: **View → Themes** → pick a simple light theme. Page size: default 16:9. Put the same **slicer panel** on the left of every page: `dim_date[year]` (tile), `dim_date[season]`, `dim_location[region]`, `dim_characteristic[short_name]`. To keep slicers in sync across pages: **View → Sync slicers** → tick all pages.

How to add a visual: click an empty spot on the canvas → choose the icon in the **Visualizations** pane → drag fields from the **Data** pane into the wells (X-axis, Y-axis, Legend, Values…).

### Page 1: Executive overview
Rename the page tab (double-click) to **Executive**.

| # | Visual | Fields | Notes |
|---|---|---|---|
| 1–6 | **Card** ×6 (or one *Multi-row card*) | `Results`, `Sites`, `Parameters`, `Exceedances`, `High-Risk Results`, `Organizations` | Title each card; these are the 6 KPIs required by the brief |
| 7 | **Card** ×2 | `Exceedance Rate %`, `High-Risk Rate %` | |
| 8 | **Clustered bar chart** | Y-axis `dim_characteristic[short_name]`, X-axis `Exceedance Rate %` | Sort descending. Expected order (EDA): DO, turbidity, pH, conductivity, temperature, nitrate |
| 9 | **Line chart** | X-axis `dim_date[year_month]`, Y-axis `Results` and `Exceedance Rate %` (secondary axis) | Use *Line and clustered column chart*: Results as columns, rate as line |
| 10 | **Donut chart** | Legend `dim_characteristic[parameter_group]`, Values `Results` | Shares of Physical / Chemical / Nutrient |

Check: the cards with no slicer selected must equal `v_exec_kpis` (drag `v_exec_kpis[results]` into a table to compare).

### Page 2: Site & Geography

| # | Required item | Visual | Fields |
|---|---|---|---|
| 1 | **Map** | **Map** (or *Azure Map*; enable *File → Options → Security → Use Map and Filled Map visuals*) | Latitude `dim_location[latitude]`, Longitude `dim_location[longitude]`, Bubble size `Results`, Tooltips `Exceedance Rate %`, `dim_location[site_id]` |
| 2 | **Regional quality** | **Clustered column** | X `dim_location[region]` (use the *Geography* hierarchy to allow drill-down to state and site), Y `Exceedance Rate %`, `High-Risk Rate %` |
| 3 | **Exceedances by site** | **Table** | `dim_location[site_id]`, `state`, `Results`, `Exceedances`, `Exceedance Rate %`. Filter pane → *Results* is greater than or equal to 30 → Top N 20 by `Exceedances` |
| 4 | **Site comparison** | **Matrix** | Rows `dim_location[site_id]` (Top N 15 by Results), Columns `dim_characteristic[short_name]`, Values `Median Value`. Conditional formatting → Background color on values |
| 5 | **Coverage** | **Clustered bar** | Y `dim_location[state]`, X `Sites` (Top N 20). Second visual: **Card** from `v_site_summary` → *Average of months_sampled* ("average months a site is sampled per parameter") |
| 6 | Filled map (optional) | **Filled map** | Location `dim_location[state]`, color saturation `Exceedance Rate %` |

Tip for the viva: click **South** in the regional chart: every other visual on the page cross-filters to the South (this is a *slice*). Right-click a bar → *Drill down* to show **drill-down**.

### Page 3: Temporal analysis

| # | Required item | Visual | Fields |
|---|---|---|---|
| 1 | **Monthly trend** | **Line chart** | X `dim_date[year_month]`, Y `Exceedance Rate %`, Legend `dim_location[region]` |
| 2 | **Seasonal variation** | **Clustered column** | X `dim_date[season]`, Y `Exceedance Rate %`, Legend `dim_characteristic[short_name]`. Expected: DO summer ≫ winter |
| 3 | **Sampling frequency** | **Column chart** | X `dim_date[year_month]`, Y `Results (monthly fact)`. Second option: X `dim_time[time_band]`, Y `Results` (time of day of sampling) |
| 4 | **Parameter trend** | **Line chart** | X `dim_date[year_month]`, Y `Median Value`, **small multiples** `dim_characteristic[short_name]` (Format → Small multiples → independent Y axes ON) |
| 5 | **Site × time heat map** | **Matrix** from `v_site_month_heat` | Rows `site_id`, Columns `year_month`, Values `exceedance_pct` (Sum). Format → Cell elements → **Background color** ON (white → red). Only the 30 most-sampled sites are included, by design |
| 6 | Drill-down demo | **Column chart** | X the **Time** hierarchy, Y `Exceedance Rate %`. Turn on drill mode (down-arrow) and click a year → quarters → months |

### Page 4: Parameter analytics

Add a page-level filter or use one visual per parameter (Filters pane → *Filters on this visual* → `short_name` = …).

| # | Required item | Visual | Fields |
|---|---|---|---|
| 1 | **pH** | **Line chart** from `v_parameter_distribution` (filter `short_name` = pH) | X `year_month`, Y `p10`, `median_value`, `p90`. Add constant lines at 6.5 and 9.0 (Analytics pane → *Constant line*) |
| 2 | **Dissolved oxygen** | **Clustered column** | X `dim_date[season]`, Y `Exceedance Rate %`, Legend `dim_location[region]`, visual filter `short_name` = Dissolved oxygen. Constant line: none (rate) |
| 3 | **Turbidity** | **Bar chart** | Y `dim_location[water_type]`, X `Median Value` and `Exceedance Rate %` (tooltip), filter Turbidity |
| 4 | **Nutrients** | **Column chart** | X `dim_location[region]`, Y `Exceedance Rate %`, filter `parameter_group` = Nutrient (Nitrate). Add `Median Value` to tooltips |
| 5 | **Conductivity** | **Line chart** from `v_parameter_distribution`, filter Conductivity | X `year_month`, Y `median_value`, `p90`; constant line at 1,500 µS/cm |
| 6 | **Cross-parameter** | **Scatter chart** from `v_cross_parameter` | X `temperature_c`, Y `dissolved_oxygen_mgl`, Legend `region`, Values (details) `site_id`. Turn on Analytics → *Trend line*. Expected: DO falls as temperature rises |
| 7 | Parameter matrix (pivot) | **Matrix** | Rows `dim_characteristic[short_name]`, Columns `dim_date[season]`, Values `Exceedance Rate %` with background color = **Pivot** in Power BI |

---

## Part E: Finish and export

1. On each page add a **Text box** title, a one-line "how to read" note and the derived-field note from Part C.
2. **File → Save**. Then **File → Export → Export to PDF** → save as `08_olap_dashboard/figures/dashboard_export.pdf` (evidence for the report).
3. Take a screenshot of each page (Windows: `Win + Shift + S`) → save as `figures/PBI_1_executive.png`, `PBI_2_geography.png`, `PBI_3_temporal.png`, `PBI_4_parameters.png`.
4. After a new incremental ETL load: open the .pbix → **Home → Refresh**. The `bi` views always show the current warehouse, so nothing else changes.

## Troubleshooting

| Problem | Fix |
|---|---|
| "We couldn't authenticate with the credentials provided" | Use the **Database** tab (not Windows) in the credential dialog; check the container is running (`docker ps`) |
| "The remote certificate is invalid" / SSL error | Accept the prompt to connect without encryption, or File → Options → Data source settings → Edit permissions → untick *Encrypt connections* |
| Map shows nothing | Enable map visuals (File → Options → Security); set Data category of latitude/longitude |
| A slicer does not filter a helper visual | Expected: `v_…` tables have no relationships. Use their own columns (`region`, `short_name`) as visual filters |
| Load is very slow / out of memory | Untick `fact_result` and use `fact_site_month` + helper views (see Part A step 6) |
| Months in wrong order | `dim_date[month_name]` → Sort by column → `month`; for `year_month` text the order is already correct |
