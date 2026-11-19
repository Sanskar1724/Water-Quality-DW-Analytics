# Guide: `ppt/` (Automatic presentation)

## What this folder does, in plain words
This folder builds the project's **PowerPoint presentation automatically**. A small program reads every finished notebook in the step folders, picks up each saved chart together with its "Why this chart" note and its "Inference" text, and places them on slides. It also adds the title, agenda, project lifecycle, dataset overview, one divider per step, selected result tables, the warehouse design (grain and model comparison), and a "Key terms" slide per step taken from that step's `GUIDE.md`.

> **Analogy:** a photo-album printer. You keep taking photos (running notebooks); whenever you press "print", it lays out every photo with its caption in the right chapter. You never paste pictures by hand.

## What's inside
| File | What it is |
|---|---|
| `build_ppt.py` | The generator script |
| `Water_Quality_DW_Analytics.pptx` | The generated deck (re-created on every run) |
| `NOTES_FOR_LOG.md` | Short summary of what was built, for the project log |

## How to run
From the repository root (`EDA_project/`):

```
python -I ppt/build_ppt.py
```

It needs the `python-pptx` package (`python -I -m pip install python-pptx`). It takes a few seconds and only **reads** the other folders; it never changes them. Close the `.pptx` in PowerPoint before re-running, otherwise Windows cannot overwrite it.

At the end it prints the number of slides, the figure slides per folder and a list of **warnings** (things it skipped, e.g. a folder whose notebook has not been run yet). Skipped items appear automatically on the next run once they exist.

## How to edit or regenerate
- **A chart or its explanation changed?** Re-run the notebook, then re-run the script. Text comes straight from the notebook's "Why this chart" and "Inference" cells, so fix wording *there*, not in PowerPoint.
- **New step folder finished** (e.g. `06_dw_distributed/`, `08_olap_dashboard/`, `10_architecture_eval/`)? Nothing to change: the script already looks for them.
- **Add another table:** add a line to the `TABLES` list at the top of `build_ppt.py` (folder, CSV path, slide title).
- **Team names, Key findings, Architecture comparison:** these are placeholders (`<...>`) in `build_ppt.py` (functions `slide_title` and `main`). Fill them there so they survive regeneration.
- **Hand edits in PowerPoint are lost** on the next run. For final polishing, copy the deck to a new file name first and edit the copy.

## Terms used, explained simply
| Term | Simple meaning | Everyday analogy | How it is used here | Why it matters |
|---|---|---|---|---|
| **Slide deck** | The set of slides in a presentation | A stack of flash cards | `Water_Quality_DW_Analytics.pptx` | What we present on demo day |
| **python-pptx** | A Python library that writes PowerPoint files | A robot hand that can operate PowerPoint | Used by `build_ppt.py` to create every slide | Lets the deck be built without clicking |
| **Generator script** | A program that produces a file from other files | A photo-album printer | `build_ppt.py` | One command rebuilds the whole deck |
| **Notebook (.ipynb)** | A file mixing explanations, code and results | A lab notebook with notes and graphs | Source of charts and texts | Single source of truth for every slide |
| **Figure slide** | One slide with one chart | One page of the album | Chart on the left, explanation on the right | Each output gets its own slide, as faculty asked |
| **"Why this chart" box** | Short note on why this chart type was chosen | A caption saying why the photo was taken from this angle | Top of the right column | Shows the visualisation choice is deliberate |
| **Inference box** | The conclusions drawn from the chart | The teacher's remark under a graded answer | Bullets in the right column; long ones continue on a "(inference cont.)" slide | The "so what" of every chart |
| **Section divider** | A slide that starts a new part | A chapter title page | One per step folder, with its one-line purpose | Keeps the story easy to follow |
| **Placeholder** | Text in `<...>` to fill in later | A blank on a form | Team names, key findings, architecture comparison | Marks what still has to be written |
| **Warning** | A message about something skipped | A note "page missing, will be added later" | Printed at the end of each run | Tells you what is not in the deck yet |
| **16:9** | Wide-screen slide shape | A modern TV screen | 13.33 x 7.5 inch slides | Fits projectors and laptops |
