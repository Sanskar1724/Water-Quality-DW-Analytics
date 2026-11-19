# Notes for PROJECT_LOG: automatic PPT generator (2026-11-19)

**Built:** `ppt/build_ppt.py` (python-pptx 1.0.2, 16:9) -> `ppt/Water_Quality_DW_Analytics.pptx`, plus `ppt/GUIDE.md`.
Run: `python -I ppt/build_ppt.py` from the repo root. Read-only on all other folders; re-runnable; missing items are skipped with a warning.

**What it does**
- Fixed slides: title (team placeholder), agenda, lifecycle (shapes: Raw -> Profiling -> Curation -> Dimensional DW -> OLAP/Dashboards -> Analytical Mart -> Mining -> Evaluation), dataset.
- Per step folder: divider (purpose from GUIDE.md), one slide per notebook figure (title = section heading; figure left; "Why this chart" + "Inference" right; long inferences continue on an "(inference cont.)" slide once per section), selected CSV tables (max 12 rows x 7 cols, rows trimmed to fit), DESIGN.md grain + model comparison (04), "Key terms" from GUIDE.md (first 8 terms).
- Figure prefix detected from each notebook's `save_fig` helper (`savefig(FIG / f'X{`).
- Closing: Key findings (placeholder), Architecture comparison (placeholder table), Q&A. White theme, #1F3864 titles, teal accent, footer + slide numbers.

**First run (2026-11-19):** 101 slides, 6.4 MB, 44 figure slides
- 01_profiling_curation 24, 02_eda 10, 03_feature_selection 3, 05_dw_batch 1, 09_mining 6 (regression 2, decision tree 3, association 1); 04 and 07 have no figures yet.
- 8 CSV table slides + 2 DESIGN.md slides + 6 Key-terms slides.
- Skipped (warnings): 06_dw_distributed, 08_olap_dashboard, 10_architecture_eval (not created yet); 09_mining has no GUIDE.md (no Key-terms slide, fallback purpose text).
- Note: in sections with several figures (e.g. EDA temporal, 3 charts), each figure slide repeats that section's why/inference text.
