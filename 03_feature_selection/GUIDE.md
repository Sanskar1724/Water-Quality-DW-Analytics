# Guide: `03_feature_selection/` (Step 4: Feature Selection for the Whole Project)

## What this folder does, in plain words
Before building prediction models we decide **which clues (features) the models should use**. Several independent methods each "vote" on every candidate clue, and only clues that most methods agree on are kept. The result, `selected_features.json`, is **shared by all three mining tasks** (regression, decision tree, association rules), as the faculty asked: *apply the best feature-selection methods on the entire data*.

> **Analogy:** choosing a cricket team. The coach, the captain, the stats analyst and the fitness trainer each rank the players. A player who makes most of their lists gets selected. One person's opinion is not enough, and a player who just copies another's role (duplicate skills) is not needed twice.

The data comes from the **analytical mart built from the data warehouse** (`09_mining/build_analytics_mart.py`), never from the raw file.

## What's inside
| File | What it is |
|---|---|
| `01_feature_selection.ipynb` | The notebook: build model tables → run each method → consensus vote → save selection |
| `selected_features.json` | The shared output: chosen features for regression, the decision tree and association rules, plus the leakage exclusions |
| `tables/F*.csv` | Scores of every feature from every method |
| `figures/F*.png` | Charts comparing the methods |

## Terms used, explained simply
| Term | Simple meaning | Everyday analogy | How it's used here | Why it matters |
|---|---|---|---|---|
| **Feature** | A clue given to a model | A symptom given to a doctor | Temperature, season, region, previous DO… | Models can only learn from features |
| **Target** | What the model must predict | The diagnosis | DO value (regression); HighRisk yes/no (tree) | Defines the problem |
| **Feature selection** | Keeping only useful, non-duplicate, non-leaking clues | Picking the best team | This whole folder | Simpler, faster, more honest models |
| **Data leakage** | A feature that secretly contains the answer | Seeing the answer key in the exam | Own result value, result band, exceedance flag excluded | Leakage gives fake, too-good accuracy |
| **Co-measured parameter** | Another parameter measured at the same site on the same day | Blood pressure measured with your temperature | pH, temperature… as clues for DO | Real relationships (Step 3) |
| **Previous result (lag)** | The same site's value on its earlier sampling day | Yesterday's weather to guess today's | `prev_do`, `prev_result` | Strong and leakage-safe, because it is from the past |
| **Pearson / Spearman correlation** | How strongly a feature moves with the target | Taller people weigh more | Filter method | Quick first check |
| **VIF** | How much a feature is just a copy of others (above 5 = too much) | Two players with the same role | Multicollinearity check | Duplicate features make regression unstable |
| **Mutual information** | How much knowing a feature reduces uncertainty about the target, including curved patterns | How much the cloud colour tells you about rain | Filter method | Catches non-linear links correlation misses |
| **ANOVA F-test / f_regression** | Whether the target differs between feature values | Do boys and girls score differently on average? | Filter method | Statistical evidence of a link |
| **Chi-square / Cramér's V** | Whether two categories are related (V from 0 to 1) | Is "rainy day" related to "umbrella sold"? | Categorical features; association item choice | The right test for categories |
| **RFE-CV** | Remove the weakest feature, retrain, repeat; keep the set that scores best on unseen folds | Dropping players one by one and checking the team's score | Wrapper method | Tests features *together*, not one by one |
| **Cross-validation (CV)** | Training and testing on several different splits | Several practice matches, not one | Inside RFE-CV and Lasso | More reliable scores |
| **Lasso** | A regression that pushes useless coefficients to exactly zero | A strict coach who benches unneeded players | Embedded method | Automatic selection while fitting |
| **Random Forest importance** | How much each feature helps the trees split the data | Which questions most often decide the answer in "20 questions" | Embedded method | Captures interactions |
| **Permutation importance** | Shuffle one feature on test data and measure how much worse the model gets | Remove one player and see if the team loses | Model-agnostic method | The most honest measure, done on unseen data |
| **Consensus vote** | A feature is kept only if most methods rank it highly | A selection committee | Regression ≥ 4 of 6 votes; tree ≥ 3 of 5 | Not dependent on one method's bias |
| **"has_x" indicator** | 1 if a co-measured value was actually recorded, 0 if it was filled | A "data missing" checkbox | `has_ph`, `has_co_do`… | The model knows when a value was not observed |
| **Log transform** | Replacing a value by log10(value) | The Richter scale for earthquakes | Turbidity, conductivity, nitrate | Tames very skewed values (Step 3) |
