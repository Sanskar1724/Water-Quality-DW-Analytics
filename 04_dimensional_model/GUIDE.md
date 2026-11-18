# Guide: `04_dimensional_model/` (Step 5: Designing the Warehouse)

## What this folder does, in plain words
Before building a warehouse we draw its **blueprint**: which tables exist, what one row means, and how tables connect. This folder contains that blueprint (`DESIGN.md`): three possible designs (**star**, **snowflake**, **fact constellation**), a comparison, and the one we chose and why.

> **Analogy:** a shop's sales records. The **fact table** is the list of every sale (what was sold, how much, when). The **dimension tables** are the catalogues that describe each sale: the product catalogue, the calendar, the store list. Here, each "sale" is one water measurement.

## Terms used, explained simply
| Term | Simple meaning | Everyday analogy | In this project | Why it matters |
|---|---|---|---|---|
| **Data warehouse (DW)** | A database designed for analysis and reports, not for day-to-day updates | A library organised for research, not a messy inbox | PostgreSQL warehouse in `05_dw_batch` | Fast, consistent answers to business questions |
| **Dimensional model** | A design of facts (numbers) surrounded by dimensions (descriptions) | Receipts + catalogues | This folder | The standard way to design a DW |
| **Grain** | Exactly what one fact row represents | "One row = one sale" | One measured result at one site, one time | Mixing grains gives wrong totals |
| **Fact table** | The big table of measurements/events | All sales receipts | `FactWaterQualityResult` (3.77M rows) | Holds the numbers we analyse |
| **Measure** | A number in the fact table you can add or average | Sale amount | result_value, result_count, exceedance_flag | What reports calculate |
| **Dimension table** | A table describing the who/what/where/when of a fact | Product catalogue, calendar | Date, Time, Location, Characteristic, Organization-Method | Lets you slice and filter facts |
| **Surrogate key** | A simple number the warehouse assigns as a row ID | A library card number instead of your full name | `location_key`, `result_key` | Fast joins; independent of messy source IDs |
| **Natural / source key** | The ID from the original system | Your Aadhaar number | `site_id`, `result_id` | Traceability back to WQP |
| **Degenerate dimension** | A source ID kept in the fact without its own table | Receipt number on the receipt | `result_id` | Lets any warehouse row be traced to the source |
| **Foreign key (FK)** | A column pointing to a row in another table | "Product code" on a receipt pointing to the catalogue | 5 FKs in the fact | Guarantees every fact has valid descriptions |
| **Referential integrity** | Every foreign key really exists in its dimension | No receipt mentions a product that isn't in the catalogue | Checked after every load | No "orphan" facts |
| **Hierarchy** | Levels from broad to detailed | Country → State → City | Region → State → Site; Year → Quarter → Month → Day | Enables roll-up and drill-down |
| **Star schema** | Fact in the centre, each dimension one table around it | A star with one centre | Our chosen dimension shape | Few joins, simple for Power BI |
| **Snowflake schema** | Dimensions split into smaller linked tables | A star whose points branch out like a snowflake | Region → State → Location tables | Less repetition but more joins |
| **Fact constellation** | Several facts sharing the same dimensions | Two receipt books (daily sales, monthly totals) using the same catalogues | Detail fact + monthly fact | Each grain gets its own fact; numbers agree |
| **Conformed dimension** | One dimension shared by several facts | The same calendar used by every department | DimDate, DimLocation, DimCharacteristic | Consistent slicing across reports |
| **Role-playing dimension** | One dimension used in different roles | The same calendar used for "order date" and "delivery date" | DimDate as the result date and the month date | No duplicate calendar tables |
| **Junk dimension** | Small leftover attributes combined into one table | A "misc" drawer for small items | DimOrganizationMethod (928 combinations) | Avoids many tiny dimensions |
| **Aggregate / snapshot fact** | A pre-summarised fact | A monthly sales summary | FactSiteMonthlyWaterQuality | Much faster trend queries |
| **Denormalised** | Some repetition kept on purpose for speed | Writing the city name on every address card | State/region names on each site row | Faster and simpler queries |
| **Normalised** | Repetition removed into separate tables | Keeping one city list and pointing to it | Snowflake design | Saves space, costs joins |

## Decision in one paragraph
We chose a **fact constellation with star-shaped dimensions**. The data naturally has two levels: individual measurements and site-month summaries, so each gets its own fact table. Both share the same dimension tables, so their numbers always agree. Dimensions are kept as simple star tables because they are small (at most 49K rows) while the fact has 3.77M rows. Snowflaking them would save only kilobytes but add 3 or more joins to every query and make Power BI slower and harder to use.

## Impact on the project
- `05_dw_batch` (PostgreSQL) builds exactly this design.
- `06_dw_distributed` (Citus) distributes the same fact table across worker nodes.
- `08_olap_dashboard` uses the hierarchies for roll-up, drill-down and CUBE, and Power BI connects to the star.
- `09_mining` builds its analytical mart *from* these tables (the brief's integration rule).
