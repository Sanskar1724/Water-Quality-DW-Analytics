# Guide: `05_dw_batch/` (Step 6: Traditional Batch Data Warehouse)

## What this folder does, in plain words
This folder **builds the real warehouse**: a PostgreSQL database (running in Docker) organised exactly as designed in `04_dimensional_model`. It loads the 3.77 million clean measurements, checks that everything is correct, answers the business questions with SQL, and shows how **new data (December 2025) is added later without rebuilding everything**.

> **Analogy:** a warehouse for goods. Trucks arrive (*extract*), goods wait in the receiving area (*staging*), are checked (*data-quality rules*), labelled with shelf codes (*surrogate keys*) and placed on shelves (*fact and dimension tables*). When next month's truck comes, you only shelve the new goods (*incremental load*), not the whole warehouse again.

## How to run the demo
```bash
docker compose -f 05_dw_batch/docker-compose.yml up -d
python 05_dw_batch/etl/etl_batch.py reset
python 05_dw_batch/etl/etl_batch.py initial
python 05_dw_batch/etl/etl_batch.py incremental
python 05_dw_batch/etl/etl_batch.py validate
python 05_dw_batch/etl/etl_batch.py queries
```
Or open **`batch_dw_demo.ipynb`** and *Run All*: the same steps, with explanations, outputs and inferences (the best option for the viva).
Connect from Power BI / pgAdmin / DBeaver: server `localhost`, port `5433`, database `wq_dw`, user `wq` (local test password in `docker-compose.yml`).

## What's inside
| File | Purpose |
|---|---|
| `docker-compose.yml` | Starts PostgreSQL 16 in a container (port 5433, data kept in a Docker volume) |
| `sql/01_create_schema.sql` | Creates the staging area and the warehouse tables |
| `sql/02_static_dimensions.sql` | Fills Date (731 days), Time (25 slots), Characteristic (6 parameters + thresholds) |
| `sql/03_load_batch.sql` | The per-batch ETL: DQ rules → new dimension members → fact → monthly fact |
| `sql/04_constraints_indexes.sql` | Foreign keys, checks and indexes, added after the bulk load |
| `sql/05_analytical_queries.sql` | 8 timed queries answering Q1–Q8 |
| `etl/etl_batch.py` | The ETL program (reset / initial / incremental / validate / queries) |
| `batch_dw_demo.ipynb` | Step-by-step demo with inferences |
| `figures/`, `tables/` | Charts and evidence tables (`B*`) |

## Terms used, explained simply
| Term | Simple meaning | Everyday analogy | In this project | Why it matters |
|---|---|---|---|---|
| **PostgreSQL** | A free, professional relational database | A very organised digital filing cabinet | Our batch warehouse engine | Industry-standard, supports SQL, constraints, indexes |
| **Docker / container** | A packaged mini-computer running one program | A shipping container that works on any ship | PostgreSQL runs inside Docker | Same setup on every laptop, one command to start |
| **Port** | A numbered door on the computer that programs listen at | An apartment number in a building | 5433 | Power BI and Python connect through it |
| **Schema (database)** | A folder of tables inside the database | A drawer in the cabinet | `stg` (staging) and `dw` (warehouse) | Keeps raw landing tables apart from final tables |
| **ETL** | Extract → Transform → Load | Buy → wash & cut → cook | `etl_batch.py` + `03_load_batch.sql` | The pipeline that fills the warehouse |
| **Staging area** | A temporary landing table for each batch | The receiving bay of a warehouse | `stg.wq_results` | Data is checked here before entering the warehouse |
| **Bulk load / COPY** | Loading millions of rows in one fast stream | Unloading a whole truck with a forklift instead of carrying boxes by hand | 3.75M rows copied in about a minute | Far faster than inserting row by row |
| **Initial load** | The first full load of history | Stocking a new shop | Jan 2024 – Nov 2025 | Builds the warehouse |
| **Incremental load** | Adding only new data | Restocking only what arrived this week | December 2025 | No rebuild needed; this is how real warehouses grow |
| **Data-quality rule** | A check that rejects bad rows | Rejecting damaged boxes at the dock | Missing key/value/date, unknown parameter, out-of-period date | Keeps the warehouse trustworthy |
| **Surrogate key** | A number the warehouse assigns as an ID | A shelf code | `location_key`, `org_method_key` | Short, fast joins |
| **Dimension lookup** | Finding the existing surrogate key for a natural key | Looking up a product's shelf code | Each site ID → its location_key | Existing members are reused, not duplicated |
| **New dimension member** | A new row added to a dimension | A new product added to the catalogue | 53 new sites in December 2025 | The warehouse grows correctly |
| **Referential integrity / foreign key** | Every fact must point to a real dimension row | No receipt for a product that doesn't exist | 5 foreign keys on the fact | No "orphan" facts |
| **Index** | A lookup structure that speeds up searches | The index at the back of a book | On date, location, characteristic, result_id | Faster queries and safe re-runs |
| **Unique index** | An index that forbids duplicates | One roll number per student | `result_id` | The same result can never be loaded twice |
| **Reconciliation** | Proving counts and totals match between stages | Counting cash in the till against the receipts | Staging = warehouse = curated rows; detail = monthly totals | Nothing lost or doubled |
| **Audit log** | A record of every load | A delivery logbook | `dw.etl_load_log` | Shows when each batch was loaded and what it added |
| **Query execution time** | How long a question takes to answer | Time to find a book | Median of 3 runs per query | Evidence for the architecture comparison |
| **Query plan / EXPLAIN** | The database's step-by-step plan for a query | A route chosen by a GPS | Used to find a slow join during the build | Explains and fixes slow queries |
| **Statistics / ANALYZE** | Row counts and value spreads the database keeps about each table | A GPS knowing which roads are busy | Run right after each staging load | Without them the database chose a plan ~20× slower |
| **Hash join** | Joining tables by building a quick lookup in memory | Matching names using an alphabetical index | All fact-to-dimension joins | Joins millions of rows in seconds |

## Problems met while building (and how they were fixed)
1. **The first fact insert ran more than 10 minutes.** The join compared blank values with a null-safe operator, which blocked fast hash joins. Fix: blanks become "Not Reported" in staging, so plain `=` joins can be used.
2. **It was still slow inside the full pipeline.** The "skip already-loaded results" check pointed at the very table being filled, so each new row rescanned the growing table. Fix: already-loaded rows are removed from *staging* first using the unique index, and the insert has no self-check. The fact insert dropped to under a minute.
3. **The database needed statistics.** `ANALYZE` now runs right after each staging copy, so PostgreSQL knows the table is large and picks hash joins.
4. **A semicolon inside a text value** split one SQL statement in two; the text was changed.

## Impact on the project
- This is the **historical analytics** warehouse in the final architecture (Q1–Q8 queries, Power BI).
- The same tables are distributed with Citus in `06_dw_distributed`.
- OLAP (roll-up, drill-down, CUBE) in `08_olap_dashboard` runs on these tables.
- The analytical mart for mining (`09_mining`) is built from this warehouse.
