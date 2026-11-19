"""
Step 9: run, time and chart every OLAP operation on the batch warehouse.

Reads 08_olap_dashboard/sql/01_olap_operations.sql. Each block starts with a marker line
    -- name: <id> | <operation> | <business question>
and ends at the first semicolon. For every block the runner:
    1. runs it `--repeat` times (default 3) and keeps the median time,
    2. saves the result to 08_olap_dashboard/tables/<id>.csv   (ids already start with "O"),
    3. draws one chart to 08_olap_dashboard/figures/<id>.png.
It also writes tables/O00_query_times.csv (timing summary for all operations).

Usage (from the repository root, with the batch DW container running):
    python 08_olap_dashboard/olap_runner.py               # all queries
    python 08_olap_dashboard/olap_runner.py O11 O15       # only ids starting with these prefixes
    python 08_olap_dashboard/olap_runner.py --repeat 1    # quicker trial run
    python 08_olap_dashboard/olap_runner.py --views       # also (re)create the bi.* views for Power BI
Connection settings come from 05_dw_batch/etl/etl_batch.py (127.0.0.1:5433, db wq_dw, user wq,
password from WQ_PG_PASSWORD or the local test default).
"""
import re
import sys
import time
import argparse
from decimal import Decimal
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / '05_dw_batch' / 'etl'))
from etl_batch import connect, q  # noqa: E402  (reuse the batch DW connection helpers)

SQL_FILE = HERE / 'sql' / '01_olap_operations.sql'
VIEWS_FILE = HERE / 'sql' / '02_powerbi_views.sql'
TABLES = HERE / 'tables'
FIGURES = HERE / 'figures'
MARKER = re.compile(r'^-- name: (O\d+\w*) \| ([^|\n]+?) \| ([^\n]+)\n(.*?);', flags=re.S | re.M)

COLORS = ['#2a6f97', '#e07a5f', '#81b29a', '#f2cc8f', '#6d597a', '#3d405b', '#b56576', '#8d99ae']
SEASONS = ['Winter', 'Spring', 'Summer', 'Autumn']


# ---------------------------------------------------------------- query handling
def load_blocks(path=SQL_FILE):
    """Return [(id, operation, question, sql)] in file order."""
    text = path.read_text(encoding='utf-8')
    return [(i, op.strip(), qn.strip(), sql.strip()) for i, op, qn, sql in MARKER.findall(text)]


def to_numeric(df):
    """psycopg2 returns NUMERIC as Decimal: convert those columns to float so pandas/matplotlib can use them."""
    for col in df.columns:
        if df[col].map(lambda v: isinstance(v, Decimal)).any():
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def run_timed(con, sql, repeat):
    times, df = [], None
    for _ in range(repeat):
        t = time.perf_counter()
        df = q(con, sql)
        times.append((time.perf_counter() - t) * 1000)
    times.sort()
    return to_numeric(df), times[len(times) // 2], times[0]


def create_views(con):
    """Run 02_powerbi_views.sql statement by statement (comments removed first)."""
    text = re.sub(r'--[^\n]*', '', VIEWS_FILE.read_text(encoding='utf-8'))
    with con.cursor() as cur:
        for stmt in [s.strip() for s in text.split(';') if s.strip()]:
            cur.execute(stmt)
    print('bi views created')


# ---------------------------------------------------------------- chart helpers
def _finish(fig, ax, title, path, ylabel=None):
    ax.set_title(title, fontsize=11, loc='left')
    if ylabel:
        ax.set_ylabel(ylabel)
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def bar(df, x, y, title, path, ylabel='Exceedance rate (%)', horizontal=False):
    fig, ax = plt.subplots(figsize=(9, 5))
    if horizontal:
        d = df.iloc[::-1]
        ax.barh(d[x].astype(str), d[y], color=COLORS[0])
        ax.set_xlabel(ylabel)
        ax.grid(axis='x', alpha=0.3)
        _finish(fig, ax, title, path)
        return
    ax.bar(df[x].astype(str), df[y], color=COLORS[0])
    for i, v in enumerate(df[y]):
        if pd.notna(v):
            ax.text(i, v, f'{v:.1f}', ha='center', va='bottom', fontsize=8)
    plt.setp(ax.get_xticklabels(), rotation=30, ha='right')
    _finish(fig, ax, title, path, ylabel)


def grouped_bar(pivot, title, path, ylabel='Exceedance rate (%)'):
    fig, ax = plt.subplots(figsize=(10, 5))
    pivot.plot(kind='bar', ax=ax, color=COLORS[:pivot.shape[1]], width=0.8)
    plt.setp(ax.get_xticklabels(), rotation=0)
    ax.legend(fontsize=8, frameon=False)
    _finish(fig, ax, title, path, ylabel)


def heatmap(pivot, title, path, fmt='{:.1f}', cmap='YlOrRd', label='Exceedance rate (%)'):
    fig, ax = plt.subplots(figsize=(max(7, 0.55 * pivot.shape[1] + 3), max(4, 0.45 * pivot.shape[0] + 2)))
    im = ax.imshow(pivot.values.astype(float), aspect='auto', cmap=cmap)
    ax.set_xticks(range(pivot.shape[1]), [str(c) for c in pivot.columns], rotation=45, ha='right', fontsize=8)
    ax.set_yticks(range(pivot.shape[0]), [str(r) for r in pivot.index], fontsize=8)
    if pivot.size <= 120:
        for i in range(pivot.shape[0]):
            for j in range(pivot.shape[1]):
                v = pivot.values[i, j]
                if pd.notna(v):
                    ax.text(j, i, fmt.format(v), ha='center', va='center', fontsize=7)
    fig.colorbar(im, ax=ax, label=label)
    ax.set_title(title, fontsize=11, loc='left')
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def line(df, x, ys, title, path, ylabel='Exceedance rate (%)'):
    fig, ax = plt.subplots(figsize=(10, 5))
    for i, y in enumerate(ys):
        ax.plot(df[x].astype(str), df[y], marker='o', color=COLORS[i], label=y)
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right', fontsize=8)
    if len(ys) > 1:
        ax.legend(frameon=False)
    _finish(fig, ax, title, path, ylabel)


def season_order(cols):
    return [s for s in SEASONS if s in cols] + [c for c in cols if c not in SEASONS]


# ---------------------------------------------------------------- one chart per query
def chart(qid, op, df, path):
    """Draw the chart that best shows this OLAP operation. Unknown ids get a generic bar of the last % column."""
    if df.empty:
        return False
    t = f'{qid} ({op})'
    if qid.startswith('O01'):
        bar(df, 'region', 'exceedance_pct', f'{t}: exceedance rate rolled up to Region', path)
    elif qid.startswith('O02'):
        bar(df, 'year_quarter', 'exceedance_pct', f'{t}: exceedance rate by Year-Quarter', path)
    elif qid.startswith('O03'):
        line(df, 'year_month', ['exceedance_pct', 'high_risk_pct'], f'{t}: dissolved oxygen, drilled to month', path, 'Rate (%)')
    elif qid.startswith('O04'):
        st = df['state'].iloc[0]
        bar(df, 'site_id', 'exceedances', f'{t}: top sites in worst state ({st})', path, 'Exceedances (count)', horizontal=True)
    elif qid.startswith('O05'):
        p = df.pivot(index='region', columns='season', values='exceedance_pct')
        heatmap(p[season_order(list(p.columns))], f'{t}: DO exceedance %, Region x Season', path)
    elif qid.startswith('O06'):
        bar(df, 'short_name', 'exceedance_pct', f'{t}: exceedance rate per parameter, 2025 only', path)
    elif qid.startswith('O07'):
        d = df.assign(cell=df['region'] + ' / ' + df['short_name'])
        p = d.pivot(index='cell', columns='season', values='exceedance_pct')
        grouped_bar(p[season_order(list(p.columns))], f'{t}: South/West, Chemical, Summer vs Winter', path)
    elif qid.startswith('O08'):
        bar(df.assign(lbl=df['state'].astype(str)), 'lbl', 'exceedance_pct',
            f'{t}: Physical, surface water, summer 2025, by state', path, horizontal=True)
    elif qid.startswith('O09'):
        p = df.set_index('short_name')[['winter_pct', 'spring_pct', 'summer_pct', 'autumn_pct']]
        p.columns = SEASONS
        heatmap(p, f'{t}: exceedance %, Parameter x Season', path)
    elif qid.startswith('O10'):
        p = df.set_index('region').drop(columns=['all_parameters_pct'])
        p.columns = [c.replace('_pct', '').replace('_', ' ') for c in p.columns]
        heatmap(p, f'{t}: exceedance %, Region x Parameter', path)
    elif qid.startswith('O11'):
        # Two panels: the Month x Region cell values (ParameterGroup = ALL) and the per-group monthly subtotal lines
        fig, axes = plt.subplots(1, 2, figsize=(15, 5.5), gridspec_kw={'width_ratios': [3, 2]})
        a = df[(df.year_month != 'ALL') & (df.region != 'ALL') & (df.parameter_group == 'ALL')]
        p = a.pivot(index='region', columns='year_month', values='exceedance_pct')
        im = axes[0].imshow(p.values.astype(float), aspect='auto', cmap='YlOrRd')
        axes[0].set_xticks(range(p.shape[1]), p.columns, rotation=60, fontsize=7)
        axes[0].set_yticks(range(p.shape[0]), p.index, fontsize=8)
        axes[0].set_title('Month x Region (all parameter groups)', fontsize=10, loc='left')
        fig.colorbar(im, ax=axes[0], label='Exceedance rate (%)')
        b = df[(df.year_month != 'ALL') & (df.region == 'ALL') & (df.parameter_group != 'ALL')]
        for i, (g, s) in enumerate(b.groupby('parameter_group')):
            axes[1].plot(s['year_month'], s['exceedance_pct'], marker='.', color=COLORS[i], label=g)
        tot = df[(df.year_month != 'ALL') & (df.region == 'ALL') & (df.parameter_group == 'ALL')]
        axes[1].plot(tot['year_month'], tot['exceedance_pct'], color='black', lw=2, label='ALL groups')
        plt.setp(axes[1].get_xticklabels(), rotation=60, fontsize=7)
        axes[1].legend(frameon=False, fontsize=8)
        axes[1].set_title('Month x ParameterGroup subtotals (all regions)', fontsize=10, loc='left')
        axes[1].spines[['top', 'right']].set_visible(False)
        fig.suptitle(f'{t}: CUBE(Month, Region, ParameterGroup)', x=0.01, ha='left', fontsize=11)
        fig.tight_layout()
        fig.savefig(path, dpi=130)
        plt.close(fig)
    elif qid.startswith('O12'):
        p = df.pivot(index='parameter_group', columns='season', values='high_risk_pct')
        heatmap(p[season_order(list(p.columns))], f'{t}: high-risk %, incl. ALL subtotals', path,
                fmt='{:.2f}', label='High-risk rate (%)')
    elif qid.startswith('O13') or qid.startswith('O14'):
        dims = list(dict.fromkeys(df['dimension']))
        fig, axes = plt.subplots(1, len(dims), figsize=(4.2 * len(dims), 4.5), sharey=True)
        axes = [axes] if len(dims) == 1 else axes
        for ax, dname in zip(axes, dims):
            s = df[df.dimension == dname]
            ax.bar(s['member'].astype(str), s['exceedance_pct'], color=COLORS[dims.index(dname) % len(COLORS)])
            ax.set_title(dname, fontsize=10)
            plt.setp(ax.get_xticklabels(), rotation=40, ha='right', fontsize=8)
            ax.spines[['top', 'right']].set_visible(False)
        axes[0].set_ylabel('Exceedance rate (%)')
        fig.suptitle(f'{t}: one query, several summaries', x=0.01, ha='left', fontsize=11)
        fig.tight_layout()
        fig.savefig(path, dpi=130)
        plt.close(fig)
    elif qid.startswith('O15'):
        m = df[df.level == 'Month'].assign(ym=lambda d: d['year'] + '-' + d['month'])
        fig, ax = plt.subplots(figsize=(11, 5))
        ax.plot(m['ym'], m['exceedance_pct'], marker='o', color=COLORS[0], label='Month')
        qs = df[df.level == 'Quarter subtotal']
        for _, r in qs.iterrows():   # draw each quarter subtotal as a flat step over its 3 months
            months = m[(m.year == r['year']) & (m.quarter == r['quarter'])]['ym']
            if len(months):
                ax.hlines(r['exceedance_pct'], months.iloc[0], months.iloc[-1], color=COLORS[1], lw=3)
        ys = df[df.level == 'Year subtotal']
        for _, r in ys.iterrows():
            ax.axhline(r['exceedance_pct'], ls='--', lw=1, color=COLORS[4])
            ax.text(len(m) - 1, r['exceedance_pct'], f"{r['year']} total ", fontsize=8, color=COLORS[4], va='bottom', ha='right')
        ax.plot([], [], color=COLORS[1], lw=3, label='Quarter subtotal')
        ax.plot([], [], color=COLORS[4], ls='--', label='Year subtotal')
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right', fontsize=8)
        ax.legend(frameon=False)
        _finish(fig, ax, f'{t}: ROLLUP(Year, Quarter, Month)', path, 'Exceedance rate (%)')
    elif qid.startswith('O16'):
        d = df[df.level != 'Grand total'].copy()
        d['lbl'] = d.apply(lambda r: f"{r['parameter_group']} - TOTAL" if r['level'] == 'Group subtotal'
                           else f"{r['parameter_group']} / {r['characteristic']}", axis=1)
        fig, ax = plt.subplots(figsize=(9, 5.5))
        cols = [COLORS[1] if lv == 'Group subtotal' else COLORS[0] for lv in d['level']]
        ax.barh(d['lbl'][::-1], d['exceedance_pct'][::-1], color=cols[::-1])
        g = df[df.level == 'Grand total']['exceedance_pct']
        if len(g):
            ax.axvline(g.iloc[0], ls='--', color='black', lw=1, label=f'Grand total {g.iloc[0]:.1f}%')
            ax.legend(frameon=False)
        ax.set_xlabel('Exceedance rate (%)')
        ax.grid(axis='x', alpha=0.3)
        _finish(fig, ax, f'{t}: ROLLUP(ParameterGroup, Characteristic)', path)
    else:
        pct = [c for c in df.columns if c.endswith('_pct')]
        if not pct:
            return False
        bar(df.head(25), df.columns[0], pct[0], t, path)
    return True


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description='Run and time the OLAP operations')
    ap.add_argument('only', nargs='*', help='query id prefixes to run (default: all)')
    ap.add_argument('--repeat', type=int, default=3)
    ap.add_argument('--views', action='store_true', help='also create the bi.* views for Power BI')
    args = ap.parse_args()

    TABLES.mkdir(exist_ok=True)
    FIGURES.mkdir(exist_ok=True)
    con = connect()
    if args.views:
        create_views(con)

    blocks = [b for b in load_blocks() if not args.only or any(b[0].startswith(p) for p in args.only)]
    print(f'Running {len(blocks)} OLAP queries, {args.repeat} time(s) each')
    timing = []
    for qid, op, question, sql in blocks:
        df, med, mn = run_timed(con, sql, args.repeat)
        df.to_csv(TABLES / f'{qid}.csv', index=False)
        drew = chart(qid, op, df, FIGURES / f'{qid}.png')
        timing.append({'Query': qid, 'Operation': op, 'Business question': question, 'Rows returned': len(df),
                       'Median ms': round(med, 1), 'Min ms': round(mn, 1), 'Chart': 'yes' if drew else 'no (empty)'})
        print(f'  {qid:<34} {op:<14} rows={len(df):>5}  median={med:>9.1f} ms')
    t = pd.DataFrame(timing)
    if args.only and (TABLES / 'O00_query_times.csv').exists():   # partial run: update rows, keep the others
        old = pd.read_csv(TABLES / 'O00_query_times.csv')
        t = pd.concat([old[~old['Query'].isin(t['Query'])], t]).sort_values('Query')
    t.to_csv(TABLES / 'O00_query_times.csv', index=False)
    print(f'Saved tables to {TABLES} and figures to {FIGURES}')
    con.close()


if __name__ == '__main__':
    main()
