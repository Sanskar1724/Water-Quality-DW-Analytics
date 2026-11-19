# Guide: `09_mining/` (Step 10: Data Mining: Regression, Decision Tree, Association Rules)

## What this folder does, in plain words
This folder uses the cleaned, warehoused data to **learn patterns and make predictions**:
1. **Regression:** predict how much **dissolved oxygen** (DO) a river or lake will have on a given day.
2. **Decision tree:** predict whether a measurement will be **high-risk** (dangerous), as a set of yes/no rules.
3. **Association rules:** discover which **conditions occur together** with exceedances (e.g. *South + Summer + Temperature → Exceedance*).

> **Integration rule (brief §18):** the data comes from the **data warehouse**, not the raw file:
> `Raw → Profiling → Curation → Staging → Data Warehouse → Analytical Mart → Mining`.
> `build_analytics_mart.py` exports the warehouse (fact + dimensions) into one flat table, `WaterQualityAnalyticsMart`. All models use the features chosen in Step 4 (`03_feature_selection/selected_features.json`).

## What's inside
| File | What it is |
|---|---|
| `build_analytics_mart.py` | Builds the analytical mart from the PostgreSQL warehouse (3,772,033 rows) |
| `mining_data.py` | Shared code that builds the model tables (site-day table, result table) |
| `01_regression.ipynb` | DO prediction: simple and multiple linear, Ridge, Lasso, Random Forest, Gradient Boosting |
| `02_decision_tree.ipynb` | High-risk classification with tuning, pruning, evaluation and 3 decision paths |
| `03_association_rules.ipynb` | Apriori + FP-Growth, filtering, 10 meaningful rules |
| `tables/` (R*, D*, A*), `figures/` | Results and charts |

## Results in one table
| Task | Result on unseen months (Jul–Dec 2025) | Meaning |
|---|---|---|
| Regression (DO) | **Gradient Boosting R² 0.64, RMSE 1.64 mg/L**; multiple linear R² 0.51; temperature-only R² 0.20 | Predicts DO within about ±1.1–1.6 mg/L |
| Decision tree (HighRisk) | **Recall 91.7%**, precision 14.6%, ROC-AUC 0.919, pruned to 275 leaves | Catches about 9 of 10 dangerous results; about 1 in 7 alerts is truly high-risk |
| Association rules | 7,560 frequent itemsets (Apriori = FP-Growth); top rule *Temperature + South + Summer → Exceedance*, lift 5.5 | Summer in the South is the riskiest combination |

## Terms used, explained simply
| Term | Simple meaning | Everyday analogy | How it's used here | Why it matters |
|---|---|---|---|---|
| **Analytical mart** | A flat, model-ready table built from the warehouse | A ready-to-cook meal kit made from the pantry | `wq_analytics_mart.parquet` | Mining uses warehouse data, as the brief requires |
| **Regression** | Predicting a number | Guessing a house's price from its size and location | DO in mg/L | Estimates oxygen where it wasn't measured |
| **Classification** | Predicting a category | Spam / not spam | High-risk yes/no | Early warning |
| **Linear regression** | Fitting a straight-line relationship | "Every extra °C lowers DO by about x mg/L" | Simple and multiple linear models | Easy to explain |
| **Coefficient** | How much the prediction changes per unit of a feature | Price per extra square metre | Temperature −0.93 mg/L per standard deviation | Shows direction and strength |
| **Ridge / Lasso** | Linear regression that shrinks coefficients (Lasso can set them to zero) | A strict teacher reducing extreme marks | Compared with plain linear | Guards against overfitting and overlap |
| **Random Forest / Gradient Boosting** | Many decision trees combined (voting / correcting each other) | Asking many experts and combining their answers | Best DO models | Capture curved relationships and interactions |
| **R²** | Share of the variation explained (0–1) | Exam score out of 100% | 0.64 for Gradient Boosting | Overall fit quality |
| **MAE / RMSE** | Average error / error that punishes big misses more, in mg/L | Average distance from the bullseye | RMSE 1.64 mg/L | Error size in real units |
| **Residual** | Actual minus predicted | How far each dart landed from the bullseye | Residual plots | Reveals patterns the model misses |
| **Multicollinearity / VIF** | Features that overlap (VIF > 5 = a problem) | Two witnesses telling the same story | All VIF < 4 | Stable coefficients |
| **Heteroscedasticity** | Errors getting bigger in some ranges | A weighing scale that is less accurate for heavy items | Breusch–Pagan test p ≈ 0 | Linear standard errors are optimistic |
| **Chronological split** | Train on earlier months, test on later months | Practise on last year's papers, sit this year's exam | Test = Jul–Dec 2025 | No peeking into the future (leakage-safe) |
| **Decision tree** | A flowchart of yes/no questions | "Is it raining? → Do you have an umbrella?" | High-risk prediction | Transparent rules |
| **Pruning / ccp_alpha** | Cutting branches that add little | Trimming a bush | 1,821 → 275 leaves, *better* test AUC | Avoids memorising noise |
| **Overfitting** | Learning the training data too exactly | Memorising answers instead of understanding | Train vs validation F1 gap | Poor performance on new data |
| **Class imbalance / class_weight** | One class is very rare; weighting gives it more importance | Finding a few red balls among many white | High-risk = 2.7% | Otherwise the tree ignores the rare danger |
| **Precision / recall / F1** | Share of alerts that are right / share of real cases caught / their balance | A smoke alarm's false alarms vs missed fires | Recall 91.7%, precision 14.6% | Recall matters most for safety |
| **ROC-AUC** | How well the model ranks positives above negatives (0.5 = guessing, 1 = perfect) | Sorting patients by risk correctly | 0.919 | Threshold-independent quality |
| **Confusion matrix** | Table of right and wrong answers by type | A report card of mistakes | Missed vs false alarms | Shows what kind of errors happen |
| **Decision path** | The chain of questions from the root to one leaf | Directions from home to a shop | 3 paths explained | Turns the model into readable rules |
| **Association rule (A → B)** | "When A occurs, B tends to occur" | Bread → butter in shopping baskets | South + Summer + Temperature → Exceedance | Finds risky combinations |
| **Support / confidence / lift** | How common / how reliable / how much stronger than chance | Share of baskets, chance of butter given bread, butter's boost | Lift 5.5 = 5.5× the normal rate | Judge rule importance |
| **Apriori / FP-Growth** | Two algorithms to find frequent item combinations | Checking every combination vs a smart summary tree | Same 7,560 itemsets; FP-Growth 2.3× faster | Brief requires Apriori; FP-Growth scales better |
| **Definitional rule** | A rule that is true by definition, not a discovery | "All squares are rectangles" | ResultBand → Exceedance, Nitrate → Nutrient removed | Only real discoveries reported |
