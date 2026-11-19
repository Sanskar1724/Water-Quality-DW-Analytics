"""Automatic PowerPoint generator for the Water Quality DW & Analytics project.

Run from the repository root:
    python -I ppt/build_ppt.py
Output:
    ppt/Water_Quality_DW_Analytics.pptx

The script reads (never writes) the step folders: executed notebooks (*.ipynb),
their saved figures (<folder>/figures/*.png), selected tables (*.csv), each
folder's GUIDE.md and 04_dimensional_model/DESIGN.md. Anything missing is
skipped with a warning, so the script can be re-run at any time.
"""
import csv
import json
import re
import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

try:
    from PIL import Image
except ImportError:  # python-pptx depends on Pillow, so this is unlikely
    Image = None

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "ppt" / "Water_Quality_DW_Analytics.pptx"

# ---------------------------------------------------------------- theme ----
DARK_BLUE = RGBColor(0x1F, 0x38, 0x64)
ACCENT = RGBColor(0x00, 0x8C, 0x95)      # teal accent
TEXT = RGBColor(0x26, 0x26, 0x26)
GREY = RGBColor(0x7F, 0x7F, 0x7F)
LIGHT = RGBColor(0xE8, 0xF4, 0xF5)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT = "Calibri"
FOOTER = "Water Quality DW & Analytics"
SLIDE_W, SLIDE_H = 13.333, 7.5
INFER_LIMIT = 900   # characters of inference per slide before continuing

FOLDERS = [
    ("01_profiling_curation", "Step 1-2: Data Profiling & Curation"),
    ("02_eda", "Step 3: Exploratory Data Analysis"),
    ("03_feature_selection", "Step 4: Feature Selection"),
    ("04_dimensional_model", "Step 5: Dimensional Model"),
    ("05_dw_batch", "Step 6: Batch Data Warehouse"),
    ("06_dw_distributed", "Step 7: Distributed Data Warehouse"),
    ("07_dw_realtime", "Step 8: Real-Time Data Warehouse"),
    ("08_olap_dashboard", "Step 9: OLAP & Dashboards"),
    ("09_mining", "Step 10: Data Mining"),
    ("10_architecture_eval", "Step 11: Architecture Evaluation"),
]
FALLBACK_PURPOSE = {
    "09_mining": "Data mining on the analytical mart: regression, decision tree "
                 "classification and association rules.",
}
TABLES = {
    "01_profiling_curation": [
        ("tables/C14_data_quality_report.csv", "Data quality report"),
        ("tables/C11_imputation_decisions.csv", "Imputation decisions (DT / NB vs mode)"),
    ],
    "03_feature_selection": [
        ("tables/F02c_regression_consensus.csv", "Regression feature consensus"),
    ],
    "05_dw_batch": [
        ("tables/B06_validation_after_incremental.csv", "Validation after incremental load"),
        ("tables/B05_etl_load_log.csv", "ETL load log"),
    ],
    "09_mining": [
        ("tables/D06_decision_paths.csv", "Decision tree: high-risk decision paths"),
        ("tables/A04_ten_rules.csv", "Association rules: top ten rules"),
        ("tables/R01_model_comparison.csv", "Regression: model comparison"),
    ],
}

WARNINGS = []
STATS = {}   # folder -> number of figure slides


def log(msg):
    """ASCII-only print (Windows cp1252 consoles crash on arrows/emoji)."""
    print(str(msg).encode("ascii", "replace").decode("ascii"))


def warn(msg):
    WARNINGS.append(msg)
    log("  WARNING: " + msg)


# ------------------------------------------------------------ text utils ----
EMOJI_RE = re.compile("[\U00010000-\U0010FFFF☀-➿️‍]")


def clean(text):
    """Strip emoji the font may not render; keep the words."""
    text = EMOJI_RE.sub("", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def strip_md(text):
    """Markdown inline formatting -> plain text."""
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"\1", text)
    text = text.replace("`", "")
    text = re.sub(r"<[^>]+>", "", text)
    return clean(text)


def heading_title(line):
    t = line.lstrip("#").strip()
    # "2 · Read values · 3 · Unit standardisation" (two steps in one heading) -> keep both, drop numbers
    t = re.sub(r"\s·\s\d+[a-z]?\s·\s", " & ", t)
    t = re.sub(r"^(Step\s+)?\d+[a-z]?(\.\d+)*\s*[·.:)\-–—]?\s+", "", t)
    return strip_md(t)


def md_to_bullets(text):
    """Markdown block -> list of (level, plain text). Tables become 'a | b' lines."""
    out = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        s = raw.rstrip()
        if re.match(r"^\s*\|?\s*:?-{2,}", s):           # table separator
            continue
        indent = len(s) - len(s.lstrip(" "))
        st = s.strip()
        m = re.match(r"^([-*+]|\d+[.)])\s+(.*)$", st)
        if m:
            out.append((min(indent // 2, 3), strip_md(m.group(2))))
        elif st.startswith("|"):
            cells = [strip_md(c) for c in st.strip("|").split("|")]
            out.append((0, " | ".join(c for c in cells if c)))
        elif st.startswith(">"):
            out.append((0, strip_md(st.lstrip("> "))))
        elif st.startswith("#"):
            out.append((0, heading_title(st)))
        elif out and raw.startswith((" ", "\t")):
            out[-1] = (out[-1][0], out[-1][1] + " " + strip_md(st))  # wrapped bullet text
        else:
            out.append((0, strip_md(st)))
    return [(lv, t) for lv, t in out if t]


def chunk_bullets(bullets, limit=INFER_LIMIT):
    chunks, cur, size = [], [], 0
    for b in bullets:
        if cur and size + len(b[1]) > limit:
            chunks.append(cur)
            cur, size = [], 0
        cur.append(b)
        size += len(b[1])
    if cur:
        chunks.append(cur)
    return chunks


def read_text(path):
    return Path(path).read_text(encoding="utf-8", errors="replace")


# ------------------------------------------------------------ pptx utils ----
prs = Presentation()
prs.slide_width = Inches(SLIDE_W)
prs.slide_height = Inches(SLIDE_H)
BLANK = prs.slide_layouts[6]


def new_slide():
    s = prs.slides.add_slide(BLANK)
    bg = s.background.fill
    bg.solid()
    bg.fore_color.rgb = WHITE
    return s


def add_text(slide, x, y, w, h, text="", size=14, bold=False, color=TEXT,
             align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    style(r, size, bold, color)
    return tf


def style(run, size, bold=False, color=TEXT):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color


def add_para(tf, text, size=12, bold=False, color=TEXT, level=0, bullet=False,
             space_before=0):
    p = tf.add_paragraph() if (tf.paragraphs[0].runs or len(tf.paragraphs) > 1) else tf.paragraphs[0]
    p.level = level
    if space_before:
        p.space_before = Pt(space_before)
    prefix = ("• " if level == 0 else "– ") if bullet else ""
    if bullet and level:
        prefix = "    " * level + prefix
    r = p.add_run()
    r.text = prefix + text
    style(r, size, bold, color)
    return p


def title_bar(slide, title, subtitle=None):
    size = 26 if len(title) <= 60 else (22 if len(title) <= 85 else 18)
    add_text(slide, 0.5, 0.25, SLIDE_W - 1.0, 0.85, title, size=size, bold=True,
             color=DARK_BLUE, anchor=MSO_ANCHOR.MIDDLE)
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.5), Inches(1.12),
                                  Inches(1.6), Inches(0.06))
    line.fill.solid()
    line.fill.fore_color.rgb = ACCENT
    line.line.fill.background()
    if subtitle:
        add_text(slide, 2.3, 1.0, SLIDE_W - 2.8, 0.3, subtitle, size=11, color=GREY)


def add_picture_fit(slide, path, x, y, w, h):
    if Image is not None:
        with Image.open(path) as im:
            iw, ih = im.size
    else:
        iw, ih = 4, 3
    scale = min(w / iw, h / ih)
    pw, ph = iw * scale, ih * scale
    slide.shapes.add_picture(str(path), Inches(x + (w - pw) / 2), Inches(y + (h - ph) / 2),
                             Inches(pw), Inches(ph))


def finish_decorations():
    total = len(prs.slides)
    for i, s in enumerate(prs.slides, start=1):
        if i == 1:
            continue
        add_text(s, 0.5, 7.05, 6, 0.3, FOOTER, size=10, color=GREY)
        add_text(s, SLIDE_W - 1.5, 7.05, 1.0, 0.3, f"{i} / {total}", size=10, color=GREY,
                 align=PP_ALIGN.RIGHT)
        bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(7.42),
                                 Inches(SLIDE_W), Inches(0.08))
        bar.fill.solid()
        bar.fill.fore_color.rgb = DARK_BLUE
        bar.line.fill.background()


# ---------------------------------------------------------- fixed slides ----
def slide_title():
    s = new_slide()
    band = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.35))
    band.fill.solid(); band.fill.fore_color.rgb = DARK_BLUE; band.line.fill.background()
    add_text(s, 0.8, 1.6, SLIDE_W - 1.6, 1.0, "Water Quality Monitoring Analytics",
             size=40, bold=True, color=DARK_BLUE)
    add_text(s, 0.8, 2.6, SLIDE_W - 1.6, 1.0,
             "Batch, Distributed & Real-Time Data Warehousing with OLAP and Data Mining",
             size=24, color=ACCENT)
    tf = add_text(s, 0.8, 3.9, SLIDE_W - 1.6, 1.2,
                  "Dataset: Water Quality Portal (WQP) - 4.96M results, 50,476 sites, 2024-2025",
                  size=16, color=TEXT)
    add_para(tf, "Team: <Member 1>, <Member 2>, <Member 3>, <Member 4>", size=16, color=TEXT,
             space_before=10)
    add_para(tf, "Guide: <Faculty name>   |   MIT Academy of Engineering", size=14, color=GREY,
             space_before=6)


def slide_bullets(title, bullets, size=18):
    s = new_slide()
    title_bar(s, title)
    tf = add_text(s, 0.8, 1.5, SLIDE_W - 1.6, 5.3, "", size=size)
    for lv, t in bullets:
        add_para(tf, t, size=size - 2 * lv, level=lv, bullet=True, space_before=6)
    return s


def slide_agenda(present):
    bullets = [(0, "Project lifecycle and dataset")]
    bullets += [(0, label) for folder, label in FOLDERS if folder in present]
    bullets += [(0, "Key findings, architecture comparison, Q&A")]
    slide_bullets("Agenda", bullets, size=18)


def slide_lifecycle():
    s = new_slide()
    title_bar(s, "Project lifecycle")
    steps = ["Raw data", "Profiling", "Curation", "Dimensional DW", "OLAP / Dashboards",
             "Analytical Mart", "Mining", "Evaluation"]
    n = len(steps)
    gap, x0 = 0.08, 0.5
    w = (SLIDE_W - 1.0 - gap * (n - 1)) / n
    for i, name in enumerate(steps):
        shp = s.shapes.add_shape(MSO_SHAPE.CHEVRON if i else MSO_SHAPE.PENTAGON,
                                 Inches(x0 + i * (w + gap)), Inches(2.6), Inches(w), Inches(1.3))
        shp.fill.solid()
        shp.fill.fore_color.rgb = DARK_BLUE if i % 2 == 0 else ACCENT
        shp.line.fill.background()
        tf = shp.text_frame
        tf.word_wrap = True
        tf.margin_left = Inches(0.25 if i else 0.08)
        tf.margin_right = Inches(0.15)
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = name; style(r, 12, True, WHITE)
    notes = ["WQP CSV\n4.96M rows", "quality\ncheck-up", "clean, impute,\nflag",
             "star schema\nPostgreSQL", "cubes, slice\n& dice", "model-ready\nfeatures",
             "regression, DT,\nrules", "batch vs dist.\nvs real-time"]
    for i, t in enumerate(notes):
        add_text(s, x0 + i * (w + gap), 4.05, w, 0.9, t, size=11, color=GREY, align=PP_ALIGN.CENTER)
    add_text(s, 0.8, 5.3, SLIDE_W - 1.6, 1.2,
             "Each step lives in its own numbered folder with a notebook, figures, tables and a "
             "plain-language GUIDE.md. Every chart in this deck is generated automatically from "
             "those notebooks.", size=14, color=TEXT)


def slide_dataset():
    slide_bullets("Dataset: Water Quality Portal (WQP)", [
        (0, "Source: Water Quality Portal (USGS / EPA / NWQMC), physical-chemical results"),
        (0, "Volume: 4.96 million results from 50,476 monitoring sites"),
        (0, "Period: January 2024 - December 2025"),
        (0, "After curation: 3.77 million analysis-ready single readings"),
        (1, "duplicates, unit problems, impossible values and daily summaries handled in Step 2"),
        (0, "Six parameters: temperature, dissolved oxygen, pH, specific conductance, turbidity, nitrate"),
        (0, "Used for: batch, distributed and real-time warehouses, OLAP and data mining"),
    ], size=18)


# -------------------------------------------------------- folder content ----
def guide_info(folder):
    """Return (purpose, terms_rows) from <folder>/GUIDE.md."""
    path = ROOT / folder / "GUIDE.md"
    if not path.exists():
        return FALLBACK_PURPOSE.get(folder), []
    lines = read_text(path).splitlines()
    purpose = None
    for i, ln in enumerate(lines):
        if i == 0 or not ln.strip() or ln.lstrip().startswith(("#", ">", "|", "-")):
            continue
        purpose = strip_md(ln)
        break
    if purpose and len(purpose) > 260:
        cut = purpose[:260]
        purpose = cut[:cut.rfind(" ")] + " ..."
    terms = []
    for i, ln in enumerate(lines):
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if ln.strip().startswith("|") and cells and strip_md(cells[0]).lower() == "term":
            hdr = [strip_md(c).lower() for c in cells]
            idx = [hdr.index(c) if c in hdr else None for c in
                   ("term", "simple meaning", "everyday analogy")]
            for ln2 in lines[i + 2:]:
                if not ln2.strip().startswith("|"):
                    break
                row = [c.strip() for c in ln2.strip().strip("|").split("|")]
                terms.append([strip_md(row[j]) if j is not None and j < len(row) else ""
                              for j in idx])
                if len(terms) >= 8:
                    break
            break
    return purpose or FALLBACK_PURPOSE.get(folder), terms


def slide_divider(label, folder, purpose):
    s = new_slide()
    band = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(2.3), prs.slide_width, Inches(2.4))
    band.fill.solid(); band.fill.fore_color.rgb = DARK_BLUE; band.line.fill.background()
    add_text(s, 0.8, 2.45, SLIDE_W - 1.6, 1.0, label, size=34, bold=True, color=WHITE)
    add_text(s, 0.8, 3.4, SLIDE_W - 1.6, 1.2, purpose or "", size=16, color=WHITE)
    add_text(s, 0.8, 4.9, SLIDE_W - 1.6, 0.4, f"Folder: {folder}/", size=12, color=GREY)


def nb_figures(nb_path):
    """Yield dicts {title, file, why, infer} for each save_fig call in a notebook."""
    nb = json.loads(read_text(nb_path))
    cells = nb.get("cells", [])
    src = ["".join(c.get("source", "")) for c in cells]
    prefix = None
    for s in src:
        m = re.search(r"savefig\(FIG\s*/\s*f['\"](\w)\{", s)
        if m:
            prefix = m.group(1)
            break
    if not prefix:
        warn(f"{nb_path.name}: no save_fig helper found")
        return []
    items, title = [], nb_path.stem
    for i, c in enumerate(cells):
        if c.get("cell_type") == "markdown":
            heads = [ln for ln in src[i].splitlines() if re.match(r"^#{1,4}\s", ln)]
            if heads:
                title = heading_title(heads[-1])
            continue
        if c.get("cell_type") != "code":
            continue
        names = re.findall(r"save_fig\(\s*['\"]([^'\"]+)['\"]\s*\)", src[i])
        if not names:
            continue
        why = infer = None
        for j in range(i + 1, len(cells)):
            if cells[j].get("cell_type") == "code" and "save_fig(" in src[j]:
                break
            if cells[j].get("cell_type") != "markdown":
                continue
            t = src[j].lstrip()
            if t.startswith("#"):
                break
            if why is None and t.startswith("**Why this chart"):
                why = t
            elif infer is None and (cells[j].get("metadata", {}).get("infer")
                                    or t.startswith("**\U0001F50E Inference")):
                infer = t
        for k, n in enumerate(names):
            items.append(dict(title=title, file=nb_path.parent / "figures" / f"{prefix}{n}.png",
                              why=why, infer=infer, first=(k == 0), last=(k == len(names) - 1)))
    return items


def parse_why(text):
    t = re.sub(r"^\*\*Why (this chart|these charts)\s*:?\s*\*\*\s*:?\s*", "", text.strip())
    t = strip_md(" ".join(t.split()))
    return t[:1].upper() + t[1:]


def parse_infer(text):
    lines = text.strip().splitlines()
    head = strip_md(lines[0]) if lines else "Inference"
    return head, md_to_bullets("\n".join(lines[1:]))


def figure_slides(folder, nb_path):
    items = nb_figures(nb_path)
    count = 0
    for it in items:
        if not it["file"].exists():
            warn(f"{nb_path.name}: figure {it['file'].name} not found (notebook not executed yet?)")
            continue
        s = new_slide()
        title_bar(s, it["title"], subtitle=f"{nb_path.name}  |  {it['file'].name}")
        add_picture_fit(s, it["file"], 0.4, 1.45, 7.7, 5.5)
        why = parse_why(it["why"]) if it["why"] else ""
        head, bullets = parse_infer(it["infer"]) if it["infer"] else ("", [])
        chunks = chunk_bullets(bullets) if bullets else []
        if why or chunks:
            box = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(8.35), Inches(1.45),
                                     Inches(4.6), Inches(5.5))
            box.fill.solid(); box.fill.fore_color.rgb = LIGHT; box.line.fill.background()
            total = len(why) + (sum(len(b[1]) for b in chunks[0]) if chunks else 0)
            size = 12 if total < 700 else (11 if total < 1100 else 10)
            tf = add_text(s, 8.45, 1.5, 4.4, 5.4, "", size=size)
            if why:
                add_para(tf, "Why this chart", size=size + 1, bold=True, color=ACCENT)
                add_para(tf, why, size=size)
            if chunks:
                add_para(tf, "Inference", size=size + 1, bold=True, color=ACCENT,
                         space_before=8 if why else 0)
                for lv, t in chunks[0]:
                    add_para(tf, t, size=size - (1 if lv else 0), level=lv, bullet=True,
                             space_before=2)
        count += 1
        # continuation slides for long inferences: only once per group (after its last figure)
        if it["last"] and len(chunks) > 1:
            for ch in chunks[1:]:
                s2 = new_slide()
                title_bar(s2, f"{it['title']} (inference cont.)", subtitle=head)
                tf = add_text(s2, 0.8, 1.5, SLIDE_W - 1.6, 5.4, "", size=15)
                for lv, t in ch:
                    add_para(tf, t, size=15 - (1 if lv else 0), level=lv, bullet=True,
                             space_before=4)
    return count


def fmt_cell(v):
    v = (v or "").strip()
    try:
        f = float(v)
        if "." in v and "-" not in v[1:]:
            v = f"{f:.4g}" if abs(f) < 1e6 else f"{f:,.0f}"
    except ValueError:
        pass
    v = clean(v)
    return v if len(v) <= 160 else v[:157] + "..."


def table_slide(title, header, rows, note=None):
    rows = rows[:12]
    header = header[:7]
    rows = [r[:7] + [""] * (len(header) - len(r[:7])) for r in rows]
    ncol = len(header)
    lens = [max([len(header[c])] + [len(r[c]) for r in rows]) for c in range(ncol)]
    weights = [min(max(l, 6), 60) for l in lens]
    width = SLIDE_W - 1.0
    longest = max(sum(lens) / max(ncol, 1), 1)
    size = 11 if longest < 25 and len(rows) <= 9 else 10
    # estimate wrapped row heights so the table stays on the slide (max 5.4 in)
    cpi = 13.0 if size == 10 else 12.0                       # characters per inch
    colw = [width * w / sum(weights) for w in weights]
    def row_h(r):
        lines = max(-(-max(len(r[c]), 1) // max(int(colw[c] * cpi), 1)) for c in range(ncol))
        return 0.08 + lines * size * 1.2 / 72
    used, keep = row_h(header), []
    for r in rows:
        if used + row_h(r) > 5.4:
            break
        used += row_h(r)
        keep.append(r)
    if len(keep) < len(rows):
        note = (note + "  |  " if note else "") + f"{len(keep)} rows fit on the slide"
    rows = keep or rows[:1]
    nrow = len(rows) + 1
    s = new_slide()
    title_bar(s, title, subtitle=note)
    shp = s.shapes.add_table(nrow, ncol, Inches(0.5), Inches(1.45), Inches(width),
                             Inches(min(5.4, 0.35 * nrow)))
    tbl = shp.table
    for c in range(ncol):
        tbl.columns[c].width = Inches(width * weights[c] / sum(weights))
    for r in range(nrow):
        for c in range(ncol):
            cell = tbl.cell(r, c)
            cell.margin_left = cell.margin_right = Inches(0.05)
            cell.margin_top = cell.margin_bottom = Inches(0.02)
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            run = p.add_run()
            run.text = header[c] if r == 0 else rows[r - 1][c]
            style(run, size, bold=(r == 0), color=WHITE if r == 0 else TEXT)
            cell.fill.solid()
            cell.fill.fore_color.rgb = DARK_BLUE if r == 0 else (LIGHT if r % 2 else WHITE)
    return s


def csv_table_slide(folder, rel, title):
    path = ROOT / folder / rel
    if not path.exists():
        warn(f"table {folder}/{rel} not found")
        return False
    with open(path, encoding="utf-8-sig", newline="") as fh:
        data = list(csv.reader(fh))
    if not data:
        warn(f"table {folder}/{rel} is empty")
        return False
    header = [clean(h) or ("Rule" if i == 0 else f"col{i}") for i, h in enumerate(data[0])]
    rows = [[fmt_cell(v) for v in r] for r in data[1:] if any(x.strip() for x in r)]
    note = f"{Path(rel).name}  |  {len(rows)} rows"
    if len(rows) > 12 or len(header) > 7:
        note += f" (showing first {min(12, len(rows))} rows, {min(7, len(header))} of {len(header)} columns)"
    table_slide(title, header, rows, note)
    return True


def md_table(lines, start):
    """Parse a markdown table starting at lines[start] -> (header, rows)."""
    def split(ln):
        return [strip_md(c.strip()) for c in ln.strip().strip("|").split("|")]
    header = split(lines[start])
    rows = []
    for ln in lines[start + 2:]:
        if not ln.strip().startswith("|"):
            break
        rows.append(split(ln))
    return header, rows


def design_slides():
    path = ROOT / "04_dimensional_model" / "DESIGN.md"
    if not path.exists():
        warn("04_dimensional_model/DESIGN.md not found")
        return 0
    lines = read_text(path).splitlines()
    n = 0
    # grain section
    sec = None
    for i, ln in enumerate(lines):
        if ln.startswith("## ") and "grain" in ln.lower():
            sec = i
            break
    if sec is not None:
        body = []
        for ln in lines[sec + 1:]:
            if ln.startswith("## "):
                break
            body.append(ln)
        bullets = md_to_bullets("\n".join(body))
        slide_bullets(heading_title(lines[sec]), bullets, size=18)
        n += 1
    else:
        warn("DESIGN.md: grain section not found")
    # comparison table
    for i, ln in enumerate(lines):
        if ln.startswith("## ") and "comparison" in ln.lower():
            for j in range(i + 1, len(lines)):
                if lines[j].strip().startswith("|"):
                    header, rows = md_table(lines, j)
                    table_slide(heading_title(ln), header, rows, "From DESIGN.md")
                    n += 1
                    break
                if lines[j].startswith("## "):
                    break
            break
    else:
        warn("DESIGN.md: comparison section not found")
    return n


def terms_slide(label, terms):
    if not terms:
        return
    table_slide(f"Key terms: {label.split(': ', 1)[-1]}",
                ["Term", "Simple meaning", "Everyday analogy"], terms, "From the folder's GUIDE.md")


# ------------------------------------------------------------------ main ----
def main():
    log(f"Building deck from {ROOT}")
    present = []
    for folder, _ in FOLDERS:
        d = ROOT / folder
        has_nb = any(p for p in d.glob("*.ipynb")) if d.exists() else False
        if d.exists() and (has_nb or (d / "GUIDE.md").exists() or (d / "DESIGN.md").exists()):
            present.append(folder)
        else:
            warn(f"folder {folder}/ has no notebook or GUIDE.md yet - skipped")

    slide_title()
    slide_agenda(present)
    slide_lifecycle()
    slide_dataset()

    for folder, label in FOLDERS:
        if folder not in present:
            continue
        log(f"[{folder}]")
        purpose, terms = guide_info(folder)
        if not purpose:
            warn(f"{folder}: no purpose text found")
        slide_divider(label, folder, purpose)
        figs = 0
        for nb in sorted((ROOT / folder).glob("*.ipynb")):
            try:
                c = figure_slides(folder, nb)
                figs += c
                log(f"  {nb.name}: {c} figure slides")
            except Exception as e:  # keep going if one notebook is mid-execution / corrupt
                warn(f"{nb.name}: could not be read ({type(e).__name__}: {e})")
        STATS[folder] = figs
        if folder == "04_dimensional_model":
            log(f"  DESIGN.md: {design_slides()} slides")
        for rel, title in TABLES.get(folder, []):
            if csv_table_slide(folder, rel, title):
                log(f"  table {Path(rel).name}")
        terms_slide(label, terms)
        if not terms:
            warn(f"{folder}: no terms table in GUIDE.md")

    slide_bullets("Key findings", [
        (0, "<Finding 1: data quality - e.g. share of results that were analysis-ready>"),
        (0, "<Finding 2: EDA - seasonality / worst regions / count vs rate>"),
        (0, "<Finding 3: warehouse - load and query performance>"),
        (0, "<Finding 4: mining - best regression model, decision-tree accuracy, top rule>"),
        (0, "<Finding 5: recommendation for monitoring agencies>"),
    ])
    table_slide_rows = [["Latency", "<hours>", "<minutes>", "<seconds>"],
                        ["Data volume handled", "<...>", "<...>", "<...>"],
                        ["Query speed (Q1-Q8)", "<...>", "<...>", "<...>"],
                        ["Complexity / cost", "<...>", "<...>", "<...>"],
                        ["Best used for", "<...>", "<...>", "<...>"]]
    table_slide("Architecture comparison", ["Criterion", "Batch DW", "Distributed DW", "Real-time DW"],
                table_slide_rows, "Placeholder - fill from 10_architecture_eval")
    s = new_slide()
    add_text(s, 0.8, 2.6, SLIDE_W - 1.6, 1.2, "Thank you - Questions?", size=44, bold=True,
             color=DARK_BLUE, align=PP_ALIGN.CENTER)
    add_text(s, 0.8, 3.9, SLIDE_W - 1.6, 0.6, "Q&A", size=24, color=ACCENT, align=PP_ALIGN.CENTER)

    finish_decorations()
    OUT.parent.mkdir(exist_ok=True)
    prs.save(OUT)
    log("")
    log(f"Saved {OUT.relative_to(ROOT)}  ({len(prs.slides)} slides, "
        f"{OUT.stat().st_size / 1e6:.1f} MB)")
    log("Figure slides per folder: " + ", ".join(f"{k}={v}" for k, v in STATS.items()))
    log(f"Warnings: {len(WARNINGS)}")
    for w in WARNINGS:
        log("  - " + w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
