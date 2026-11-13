"""Prototype of the dashboard query language (docs/specs/DASHBOARDS.md).

Parses each example query, runs it over mock data, and draws the PNGs in examples/.
It is a sketch for discussing the grammar, not the portal's implementation: the real
one will run in the API, under the viewer's access rules.

Run from the repository root (Inter is copied from the web container; without it the
charts fall back to DejaVu Sans):

    mkdir -p /tmp/inter && for w in 300 400 500 600; do
      docker compose cp web:/app/node_modules/@fontsource/inter/files/inter-latin-$w-normal.woff2 /tmp/inter/; done
    docker run --rm -v "$PWD:/w" -v /tmp/inter:/fonts -w /w python:3.12-slim sh -c \
      "pip -q install matplotlib fonttools brotli && python docs/specs/dashboards/prototype.py"
"""
from __future__ import annotations

import math
import os
import random
import re
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

NOW = datetime(2026, 11, 13, 14, 0)
OUT = Path(__file__).parent / 'examples'

# ---------------------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------------------
STATUSES = ['draft', 'ready', 'sent', 'fixing', 'retesting', 'fixed', 'risk_accepted']
DATE_KEYS = {
    'created': 'created_at', 'updated': 'updated_at', 'sent': 'sent_at', 'accepted': 'accepted_at',
    'fixing': 'fixing_at', 'retesting': 'retesting_at', 'fixed': 'fixed_at', 'risk': 'risk_accepted_at',
}
DIMS = ['status', 'severity', 'source', 'report', 'operator']
UNITS = ['day', 'week', 'month', 'quarter', 'year']
CHARTS = ['number', 'bar', 'hbar', 'line', 'table']
CLAUSES = ['by', 'over', 'where', 'top', 'as', 'title']
AGGS = ['avg', 'median', 'min', 'max']
MIN_SAMPLE = 3  # a duration from fewer findings is shown as a dash
SEVERITIES = ['critical', 'high', 'medium', 'low', 'none']

LABEL = {
    'status': {'draft': 'Rascunho', 'ready': 'Pronta', 'sent': 'Enviada', 'fixing': 'Em correção',
               'retesting': 'Em reteste', 'fixed': 'Corrigida', 'risk_accepted': 'Risco assumido'},
    'severity': {'critical': 'Crítica', 'high': 'Alta', 'medium': 'Média', 'low': 'Baixa', 'none': 'Nenhuma'},
}
DIM_TITLE = {'status': 'Status', 'severity': 'Severidade', 'source': 'Fonte', 'report': 'Relatório', 'operator': 'Operador'}
AGG_TITLE = {'avg': 'Média', 'median': 'Mediana', 'min': 'Mínimo', 'max': 'Máximo'}
OTHERS = '\u0000others'
NO_REPORT = '\u0000none'


def severity(cvss):
    if cvss is None or cvss == 0:
        return 'none'
    return 'low' if cvss < 4 else 'medium' if cvss < 7 else 'high' if cvss < 9 else 'critical'


# ---------------------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------------------
class QueryError(Exception):
    def __init__(self, message, pos):
        super().__init__(f'{message} (posição {pos + 1})')
        self.pos = pos


@dataclass
class Tok:
    text: str
    start: int
    end: int
    quoted: bool


@dataclass
class Query:
    measure: tuple                      # ('count',) or ('duration', agg, from_key, to_key)
    by: list = field(default_factory=list)
    over: tuple | None = None           # (date_key, unit)
    where: str = ''
    top: int | None = None
    chart: str | None = None
    title: str | None = None


def tokenize(text):
    toks, i, n = [], 0, len(text)
    while i < n:
        if text[i].isspace():
            i += 1
            continue
        start, quoted = i, False
        while i < n and not text[i].isspace():
            if text[i] == '"':
                j = text.find('"', i + 1)
                if j < 0:
                    raise QueryError('aspas sem fechamento', i)
                i, quoted = j + 1, True
            else:
                i += 1
        toks.append(Tok(text[start:i], start, i, quoted))
    return toks


def is_clause(tok):
    return not tok.quoted and tok.text in CLAUSES


def parse(text, period=None):
    if period is not None:
        text = text.replace('{period}', period)
    toks = tokenize(text)
    if not toks:
        raise QueryError('consulta vazia', 0)

    # measure
    first = toks[0]
    if first.text == 'count':
        measure, i = ('count',), 1
    elif first.text in AGGS or re.fullmatch(r'p([1-9][0-9])', first.text):
        if len(toks) < 3 or toks[1].text != 'days':
            raise QueryError(f'depois de "{first.text}" vem "days <data>..<data>"', toks[1].start if len(toks) > 1 else len(text))
        a, sep, b = toks[2].text.partition('..')
        if not sep:
            raise QueryError('o intervalo é <data>..<data>, por exemplo sent..fixed', toks[2].start)
        for k in (a, b):
            if k not in DATE_KEYS:
                raise QueryError(f'"{k}" não é uma data; use {", ".join(DATE_KEYS)}', toks[2].start)
        if not sep or a == b:
            raise QueryError('o intervalo tem duas datas diferentes: sent..fixed', toks[2].start)
        measure, i = ('duration', first.text, a, b), 3
    else:
        raise QueryError(f'a consulta começa com count, avg, median, min, max ou pNN; veio "{first.text}"', first.start)

    q = Query(measure)
    seen = set()
    while i < len(toks):
        kw = toks[i]
        if not is_clause(kw):
            raise QueryError(f'esperava {", ".join(CLAUSES)}; veio "{kw.text}"', kw.start)
        if kw.text in seen:
            raise QueryError(f'"{kw.text}" aparece duas vezes', kw.start)
        seen.add(kw.text)
        i += 1
        args = []
        while i < len(toks) and not is_clause(toks[i]):
            args.append(toks[i])
            i += 1
        if not args:
            raise QueryError(f'"{kw.text}" sem valor', kw.end)
        a0 = args[0]

        if kw.text == 'by':
            dims = [d for d in ''.join(a.text for a in args).split(',')]
            for d in dims:
                if d not in DIMS:
                    raise QueryError(f'não dá para agrupar por "{d}"; use {", ".join(DIMS)}', a0.start)
            if len(dims) > 2 or len(set(dims)) != len(dims):
                raise QueryError('by aceita um ou dois agrupamentos diferentes', a0.start)
            q.by = dims
        elif kw.text == 'over':
            if len(args) != 3 or args[1].text != 'per':
                raise QueryError('over <data> per day|week|month|quarter|year', a0.start)
            if args[0].text not in DATE_KEYS:
                raise QueryError(f'"{args[0].text}" não é uma data', a0.start)
            if args[2].text not in UNITS:
                raise QueryError(f'"{args[2].text}": use {", ".join(UNITS)}', args[2].start)
            q.over = (args[0].text, args[2].text)
        elif kw.text == 'where':
            q.where = text[a0.start:args[-1].end]
            parse_filter(q.where, strict=True, offset=a0.start)
        elif kw.text == 'top':
            if len(args) != 1 or not args[0].text.isdigit() or int(args[0].text) < 1:
                raise QueryError('top <número>, por exemplo top 5', a0.start)
            q.top = int(args[0].text)
        elif kw.text == 'as':
            if len(args) != 1 or args[0].text not in CHARTS:
                raise QueryError(f'as {"|".join(CHARTS)}', a0.start)
            q.chart = args[0].text
        elif kw.text == 'title':
            t = ' '.join(a.text for a in args)
            if not (len(args) == 1 and a0.quoted and t.startswith('"') and t.endswith('"')):
                raise QueryError('o título vai entre aspas: title "Abertas"', a0.start)
            q.title = t[1:-1]

    # chart: default and compatibility
    if q.chart is None:
        if q.over:
            q.chart = 'line'
        elif not q.by:
            q.chart = 'number'
        else:
            q.chart = 'hbar' if q.by[0] in ('source', 'report', 'operator') else 'bar'
    if q.chart == 'number' and (q.by or q.over):
        raise QueryError('as number mostra um único valor: sem by nem over', 0)
    if q.chart == 'line' and not q.over:
        raise QueryError('as line precisa de over', 0)
    if q.chart == 'hbar' and (q.over or not q.by):
        raise QueryError('as hbar precisa de by e não aceita over', 0)
    if q.chart in ('bar', 'hbar') and not (q.by or q.over):
        raise QueryError(f'as {q.chart} precisa de by ou over', 0)
    if q.over and len(q.by) > 1:
        raise QueryError('com over, by aceita um só agrupamento (as séries)', 0)
    if q.top and not q.by:
        raise QueryError('top precisa de by', 0)
    return q


# ---------------------------------------------------------------------------------------
# The Hub filter (a port of frontend/src/filterQuery.js, plus status:a,b = either)
# ---------------------------------------------------------------------------------------
def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    y += d.year
    day = min(d.day, [31, 29 if y % 4 == 0 and (y % 100 or y % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m])
    return d.replace(year=y, month=m + 1, day=day)


def calendar_span(text):
    if m := re.fullmatch(r'(\d{2})-(\d{2})-(\d{4})', text):
        try:
            start = datetime(int(m[3]), int(m[2]), int(m[1]))
        except ValueError:
            return None
        return start, start + timedelta(days=1)
    if m := re.fullmatch(r'(\d{2})-(\d{4})', text):
        if not 1 <= int(m[1]) <= 12:
            return None
        start = datetime(int(m[2]), int(m[1]), 1)
        return start, add_months(start, 1)
    if m := re.fullmatch(r'(\d{4})', text):
        return datetime(int(m[1]), 1, 1), datetime(int(m[1]) + 1, 1, 1)
    return None


def parse_period(text, now=NOW):
    v = text.strip().lower()
    today = datetime(now.year, now.month, now.day)
    if m := re.fullmatch(r'(\d{1,4})([dmy])', v):
        n = int(m[1])
        if n < 1:
            return None
        if m[2] == 'd':
            return today - timedelta(days=n - 1), None
        return add_months(today, -n if m[2] == 'm' else -12 * n), None
    parts = v.split('.')
    if len(parts) == 1:
        parts = ['', parts[0], '']
    if len(parts) != 3:
        return None
    spans = [calendar_span(p) if p else False for p in parts]
    if None in spans:
        return None
    d1, d2, d3 = spans
    if d1 or d3:
        if d1 and d3 and d3[1] <= d1[0]:
            return None
        return (d1[0] if d1 else None), (d3[1] if d3 else None)
    return (d2[0], d2[1]) if d2 else None


def filter_tokens(text):
    return re.findall(r'-?(?:[a-z]+:)?(?:"[^"]*"|\S+)', text)


def parse_filter(text, strict=False, offset=0):
    """[(negate, key, value)]. The Hub drops invalid tokens while you type; a query
    (strict) rejects them, because a saved chart must not silently count something else."""
    out = []

    def bad(msg, raw):
        if strict:
            raise QueryError(f'{msg}: "{raw}"', offset + text.find(raw))

    for raw in filter_tokens(text):
        neg = raw.startswith('-') and len(raw) > 1
        body = raw[1:] if neg else raw
        key, sep, val = body.partition(':')
        if not sep or key not in ('status', 'cvss', 'report', 'operator', 'source', *DATE_KEYS):
            key, val = 'text', body
        val = val.strip('"')
        if key in DATE_KEYS:
            val = parse_period(val)
            if val is None:
                bad('período inválido; use 7d, 3m, 1y ou d1.d2.d3 (dd-mm-aaaa, mm-aaaa, aaaa)', raw)
                continue
        elif key == 'cvss':
            try:
                val = float(val)
            except ValueError:
                bad('cvss é um número de 0 a 10', raw)
                continue
        elif key == 'status':
            wrong = [s for s in val.lower().split(',') if s not in STATUSES]
            if wrong:
                bad(f'status desconhecido; use {", ".join(STATUSES)}', raw)
            val = [s for s in val.lower().split(',') if s in STATUSES]
            if not val:
                continue
        out.append((neg, key, val))
    return out


def match(row, tokens):
    for neg, key, val in tokens:
        if key == 'text':
            ok = val.lower() in row['identifier'].lower()
        elif key == 'status':
            ok = row['status'] in val
        elif key == 'cvss':
            ok = row['cvss'] is not None and row['cvss'] >= val
        elif key == 'report':
            ok = row['report'] is None if val.lower() == 'none' else bool(row['report']) and val.lower() in row['report'].lower()
        elif key in ('operator', 'source'):
            ok = val.lower() in (row[key] or '').lower()
        else:
            d, (lo, hi) = row[DATE_KEYS[key]], val
            ok = d is not None and (lo is None or d >= lo) and (hi is None or d < hi)
        if ok == neg:
            return False
    return True


# ---------------------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------------------
def bucket(d, unit):
    if unit == 'day':
        return datetime(d.year, d.month, d.day)
    if unit == 'week':
        return datetime(d.year, d.month, d.day) - timedelta(days=d.weekday())
    if unit == 'month':
        return datetime(d.year, d.month, 1)
    if unit == 'quarter':
        return datetime(d.year, 3 * ((d.month - 1) // 3) + 1, 1)
    return datetime(d.year, 1, 1)


def next_bucket(b, unit):
    return {'day': lambda: b + timedelta(days=1), 'week': lambda: b + timedelta(days=7),
            'month': lambda: add_months(b, 1), 'quarter': lambda: add_months(b, 3),
            'year': lambda: b.replace(year=b.year + 1)}[unit]()


def dim_value(row, dim):
    if dim == 'severity':
        return severity(row['cvss'])
    if dim == 'report':
        return row['report'] or NO_REPORT
    return row[dim] or '—'


def aggregate(measure, rows):
    if measure[0] == 'count':
        return len(rows)
    _, agg, a, b = measure
    days = sorted((r[DATE_KEYS[b]] - r[DATE_KEYS[a]]).total_seconds() / 86400 for r in rows
                  if r[DATE_KEYS[a]] and r[DATE_KEYS[b]] and r[DATE_KEYS[b]] >= r[DATE_KEYS[a]])
    if len(days) < MIN_SAMPLE:
        return None
    if agg == 'avg':
        return statistics.fmean(days)
    if agg == 'median':
        return statistics.median(days)
    if agg == 'min':
        return days[0]
    if agg == 'max':
        return days[-1]
    p = int(agg[1:]) / 100                     # pNN, linear interpolation
    k = (len(days) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return days[lo] + (days[hi] - days[lo]) * (k - lo)


def sample_size(measure, rows):
    if measure[0] == 'count':
        return len(rows)
    _, _, a, b = measure
    return sum(1 for r in rows if r[DATE_KEYS[a]] and r[DATE_KEYS[b]] and r[DATE_KEYS[b]] >= r[DATE_KEYS[a]])


@dataclass
class Result:
    query: Query
    order: list                  # values of by[0], in display order ([None] without by)
    series: list                 # values of by[1] (or of by[0] with over), [None] if none
    buckets: list | None         # bucket starts with over
    cells: dict                  # (bucket|None, group|None, series|None) -> value
    sizes: dict                  # same keys -> how many findings behind the value


def natural_order(dim, groups, weight):
    if dim == 'status':
        return [s for s in STATUSES if s in groups]
    if dim == 'severity':
        return [s for s in SEVERITIES if s in groups]
    rest = sorted((g for g in groups if g not in (OTHERS, NO_REPORT)), key=lambda g: (-weight[g], str(g)))
    return rest + [g for g in (NO_REPORT, OTHERS) if g in groups]


def evaluate(q: Query, rows):
    tokens = parse_filter(q.where)
    buckets = None
    if q.over:
        key, unit = DATE_KEYS[q.over[0]], q.over[1]
        # The window: the where filter's period on the over date, else the data's first date.
        # It starts on a whole bucket: fixed:12m per month = 12 whole months + this one.
        window = [t for t in tokens if t[1] == q.over[0] and not t[0]]
        tokens = [t for t in tokens if t not in window]
        rows = [r for r in rows if r[key] and match(r, tokens)]
        lo, hi = window[-1][2] if window else (None, None)
        lo = bucket(lo or min((r[key] for r in rows), default=NOW), unit)
        hi = min(hi or NOW + timedelta(seconds=1), NOW + timedelta(seconds=1))
        rows = [r for r in rows if lo <= r[key] < hi]
        buckets, b = [], lo
        while b < hi:
            buckets.append(b)
            b = next_bucket(b, unit)
    else:
        rows = [r for r in rows if match(r, tokens)]

    dims = list(q.by)
    if q.top and dims:
        weight = {}
        for r in rows:
            weight[dim_value(r, dims[0])] = weight.get(dim_value(r, dims[0]), 0) + 1
        keep = set(sorted(weight, key=lambda g: -weight[g])[:q.top])
    else:
        keep = None

    def key_of(r):
        g = dim_value(r, dims[0]) if dims else None
        if keep is not None and g not in keep:
            g = OTHERS
        s = dim_value(r, dims[1]) if len(dims) > 1 else None
        if q.over:
            return bucket(r[DATE_KEYS[q.over[0]]], q.over[1]), None, g   # with over, by[0] is the series
        return None, g, s

    grouped = {}
    for r in rows:
        grouped.setdefault(key_of(r), []).append(r)
    cells = {k: aggregate(q.measure, v) for k, v in grouped.items()}
    sizes = {k: sample_size(q.measure, v) for k, v in grouped.items()}

    weight = {}
    for (b, g, s), n in sizes.items():
        weight[g] = weight.get(g, 0) + n
        weight[s] = weight.get(s, 0) + n
    if q.over:
        groups = [None]
        series = natural_order(dims[0], {k[2] for k in cells}, weight) if dims else [None]
    else:
        groups = natural_order(dims[0], {k[1] for k in cells}, weight) if dims else [None]
        series = natural_order(dims[1], {k[2] for k in cells}, weight) if len(dims) > 1 else [None]
    if not dims:
        cells.setdefault((None, None, None), aggregate(q.measure, []) if q.measure[0] != 'count' else 0)
    return Result(q, groups, series, buckets, cells, sizes)


# ---------------------------------------------------------------------------------------
# Mock data: about 420 findings over 15 months, with a plausible lifecycle
# ---------------------------------------------------------------------------------------
def mock_rows(seed=7):
    rnd = random.Random(seed)
    reports = [  # name, date of the operation
        ('Rede do Data Center', datetime(2025, 9, 8)), ('Portal do Cliente', datetime(2025, 11, 17)),
        ('VPN Corporativa', datetime(2026, 1, 26)), ('Active Directory', datetime(2026, 3, 16)),
        ('App Mobile', datetime(2026, 5, 11)), ('Wi-Fi Matriz', datetime(2026, 7, 6)),
        ('ERP Financeiro', datetime(2026, 8, 24)), ('Phishing T3', datetime(2026, 9, 28)),
        ('API de Pagamentos', datetime(2026, 10, 26)),
    ]
    sources = [('manual', 5), ('nuclei', 3), ('burp', 3), ('nessus', 2), ('bloodhound', 1)]
    operators = ['alice', 'bruno', 'carla', 'diego']
    fix_days = {'critical': 9, 'high': 21, 'medium': 45, 'low': 75, 'none': 90}

    def lognorm(median, spread=0.7):
        return timedelta(days=max(0.2, rnd.lognormvariate(math.log(median), spread)))

    def at_work_hours(d):
        return d.replace(hour=rnd.randint(9, 18), minute=rnd.randint(0, 59))

    rows = []
    for n in range(420):
        if rnd.random() < 0.85:
            report, op_day = rnd.choice(reports)
            created = op_day + timedelta(days=rnd.uniform(0, 18))
        else:
            report, created = None, NOW - timedelta(days=rnd.uniform(0, 430))
        if created > NOW:
            created = NOW - timedelta(days=rnd.uniform(0, 3))
        created = at_work_hours(created)
        cvss = round(min(10.0, max(0.0, rnd.choice([rnd.gauss(8.6, 1.0), rnd.gauss(6.3, 1.4), rnd.gauss(4.2, 1.6)]))), 1)
        sev = severity(cvss)
        row = dict(identifier=f'RT-{1000 + n}', report=report, cvss=cvss,
                   source=rnd.choices([s for s, _ in sources], [w for _, w in sources])[0],
                   operator=rnd.choice(operators), created_at=created, sent_at=None, accepted_at=None,
                   fixing_at=None, retesting_at=None, fixed_at=None, risk_accepted_at=None)
        steps = [('ready', created + lognorm(3))]
        sent = steps[-1][1] + lognorm(4)
        steps.append(('sent', sent))
        if rnd.random() < 0.07 and sev in ('medium', 'low', 'none'):
            steps.append(('risk_accepted', sent + lognorm(20)))
        else:
            accepted = sent + lognorm(3 if sev in ('critical', 'high') else 6, 0.9)
            steps.append(('fixing', accepted))
            retest = accepted + lognorm(fix_days[sev], 0.6)
            steps.append(('retesting', retest))
            if rnd.random() < 0.15:  # the retest failed once
                steps.append(('fixing', retest + lognorm(3)))
                retest = steps[-1][1] + lognorm(fix_days[sev] / 2, 0.6)
                steps.append(('retesting', retest))
            steps.append(('fixed', retest + lognorm(3)))
        status = 'draft'
        for st, when in steps:
            if when > NOW:
                break
            status = st
            when = at_work_hours(when)
            if st == 'sent':
                row['sent_at'] = when
            elif st == 'fixing':
                row['accepted_at'] = row['accepted_at'] or when
                row['fixing_at'] = when
            elif st in ('retesting', 'fixed'):
                row[f'{st}_at'] = when
            elif st == 'risk_accepted':
                row['risk_accepted_at'] = when
        row['status'] = status
        row['updated_at'] = max(d for d in (row['created_at'], row['sent_at'], row['fixing_at'],
                                            row['retesting_at'], row['fixed_at'], row['risk_accepted_at']) if d)
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------------------
LIGHT = dict(bg='#ffffff', text='#0f1b2a', text2='#334155', muted='#5f6d7e', dim='#97a2b0', line='#e8ebef',
             accent='#4f46e5', warn='#a5560a', others='#c3cad3',
             severity={'critical': '#9f1239', 'high': '#d1242f', 'medium': '#e08a1e', 'low': '#8a96a6', 'none': '#c3cad3'},
             status={'draft': '#b4bdc8', 'ready': '#0369a1', 'sent': '#6d3fd6', 'fixing': '#c26a12',
                     'retesting': '#d4a514', 'fixed': '#137a3d', 'risk_accepted': '#5f6d7e'},
             palette=['#4f46e5', '#0891b2', '#16a34a', '#d97706', '#db2777', '#64748b', '#7c3aed', '#0d9488'])
DARK = dict(bg='#0b121a', text='#e6edf3', text2='#c4d0dc', muted='#8a9bb0', dim='#5b6b7d', line='#223042',
            accent='#8b85ff', warn='#f0a14a', others='#4a5868',
            severity={'critical': '#ff4d6d', 'high': '#ff8a3d', 'medium': '#f5c542', 'low': '#7d8fa6', 'none': '#4a5868'},
            status={'draft': '#5b6b7d', 'ready': '#38a3e0', 'sent': '#9b7bff', 'fixing': '#f0a14a',
                    'retesting': '#f5c542', 'fixed': '#3ccf7b', 'risk_accepted': '#8a9bb0'},
            palette=['#8b85ff', '#38bdf8', '#4ade80', '#fbbf24', '#f472b6', '#94a3b8', '#c084fc', '#2dd4bf'])
MONTHS = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']


def fmt(v, measure):
    if v is None:
        return '—'
    if measure[0] == 'count':
        return f'{int(v):,}'.replace(',', '.')
    return f'{v:.1f}'.replace('.', ',') + ' d'


def label(dim, g):
    if g == OTHERS:
        return 'Outros'
    if g == NO_REPORT:
        return 'Sem relatório'
    return LABEL.get(dim, {}).get(g, str(g))


def color(theme, dim, g, i):
    if g == OTHERS or g == NO_REPORT:
        return theme['others']
    if dim in ('status', 'severity'):
        return theme[dim][g]
    if dim is None:
        return theme['accent']
    return theme['palette'][i % len(theme['palette'])]


def bucket_label(b, unit, first):
    if unit == 'month':
        return MONTHS[b.month - 1] + (f'\n{b.year}' if first or b.month == 1 else '')
    if unit == 'quarter':
        return f'T{(b.month - 1) // 3 + 1}' + (f'\n{b.year}' if first or b.month == 1 else '')
    if unit == 'year':
        return str(b.year)
    return f'{b.day:02d}/{b.month:02d}'


def measure_caption(q):
    if q.measure[0] == 'count':
        return 'vulnerabilidades'
    _, agg, a, b = q.measure
    agg = AGG_TITLE.get(agg, f'Percentil {agg[1:]}')
    return f'{agg} de dias, de {a} a {b}'


def style_axes(ax, theme, grid_axis=None):
    ax.set_facecolor(theme['bg'])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(colors=theme['muted'], length=0, labelsize=9)
    if grid_axis:
        ax.grid(axis=grid_axis, color=theme['line'], linewidth=0.8)
        ax.set_axisbelow(True)


def title(ax, theme, q, size=12.5):
    ax.text(0, 1.10, q.title or '', transform=ax.transAxes, ha='left', va='bottom',
            fontsize=size, fontweight=500, color=theme['text'])


def legend(ax, theme, items, y=1.0):
    from matplotlib.patches import Patch
    leg = ax.legend(handles=[Patch(color=c, label=t) for t, c in items], loc='lower left', bbox_to_anchor=(0, y),
                    ncol=len(items), frameon=False, fontsize=8.5, handlelength=0.8, handleheight=0.8,
                    handletextpad=0.4, columnspacing=1.2, borderaxespad=0, borderpad=0)
    for t in leg.get_texts():
        t.set_color(theme['muted'])


def draw_number(ax, res, theme, big=54):
    q = res.query
    ax.axis('off')
    v = res.cells[(None, None, None)]
    ax.text(0, 1.0, q.title or '', transform=ax.transAxes, ha='left', va='top', fontsize=12.5,
            fontweight=500, color=theme['text'])
    ax.text(0, 0.42, fmt(v, q.measure).replace(' d', ''), transform=ax.transAxes, ha='left', va='center',
            fontsize=big, fontweight=300, color=theme.get('number', theme['text']))
    caption = measure_caption(q)
    if q.measure[0] != 'count':
        caption = 'dias · ' + caption.replace(' de dias', '').lower()
    ax.text(0, 0.02, caption,
            transform=ax.transAxes, ha='left', va='bottom', fontsize=9.5, color=theme['muted'])


def draw_bars(ax, res, theme, horizontal=False):
    q = res.query
    style_axes(ax, theme)
    groups, series = res.order, res.series
    dim0, dim1 = (q.by + [None, None])[:2]
    pos = range(len(groups))
    base = [0.0] * len(groups)
    totals = [sum(res.cells.get((None, g, s)) or 0 for s in series) for g in groups]
    for si, s in enumerate(series):
        vals = [res.cells.get((None, g, s)) or 0 for g in groups]
        cols = [color(theme, dim1, s, si) if dim1 else color(theme, dim0, g, gi) for gi, g in enumerate(groups)]
        if dim0 not in ('status', 'severity') and not dim1:
            cols = [theme['accent'] if g not in (OTHERS, NO_REPORT) else theme['others'] for g in groups]
        if horizontal:
            ax.barh(list(pos), vals, left=base, color=cols, height=0.62)
        else:
            ax.bar(list(pos), vals, bottom=base, color=cols, width=0.62)
        base = [b + v for b, v in zip(base, vals)]
    labels = [label(dim0, g) for g in groups]
    top = max(totals or [1]) or 1
    for i, t in enumerate(totals):
        txt = fmt(t if q.measure[0] == 'count' else res.cells.get((None, groups[i], None)), q.measure)
        if horizontal:
            ax.text(t + top * 0.012, i, txt, va='center', ha='left', fontsize=9.5, color=theme['text2'])
        else:
            ax.text(i, t + top * 0.02, txt, ha='center', va='bottom', fontsize=9.5, color=theme['text2'])
    if horizontal:
        ax.set_yticks(list(pos), labels, fontsize=9.5, color=theme['text2'])
        ax.invert_yaxis()
        ax.set_xticks([])
        ax.set_xlim(0, top * 1.12)
    else:
        ax.set_xticks(list(pos), labels, fontsize=9.5, color=theme['text2'])
        ax.set_yticks([])
        ax.set_ylim(0, top * 1.15)
    title(ax, theme, q)
    if dim1:
        legend(ax, theme, [(label(dim1, s), color(theme, dim1, s, i)) for i, s in enumerate(series)])


def draw_over(ax, res, theme):
    q = res.query
    style_axes(ax, theme, 'y')
    unit = q.over[1]
    xs = list(range(len(res.buckets)))
    dim = q.by[0] if q.by else None
    peak = 0
    if q.chart == 'bar':
        base = [0.0] * len(xs)
        for si, s in enumerate(res.series):
            vals = [res.cells.get((b, None, s)) or 0 for b in res.buckets]
            ax.bar(xs, vals, bottom=base, color=color(theme, dim, s, si), width=0.68)
            base = [a + v for a, v in zip(base, vals)]
        peak = max(base or [1])
    else:
        for si, s in enumerate(res.series):
            vals = [res.cells.get((b, None, s)) for b in res.buckets]
            if q.measure[0] == 'count':
                vals = [v or 0 for v in vals]
            pts = [(x, v) for x, v in zip(xs, vals) if v is not None]
            col = color(theme, dim, s, si)
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color=col, linewidth=1.8,
                    marker='o', markersize=3.2, solid_capstyle='round')
            if pts and len(res.series) == 1:
                ax.text(pts[-1][0] + 0.25, pts[-1][1], fmt(pts[-1][1], q.measure), fontsize=9,
                        color=col, va='center', ha='left')
            peak = max([peak] + [p[1] for p in pts])
    step = max(1, math.ceil(len(xs) / 14))
    ax.set_xticks(xs[::step], [bucket_label(b, unit, i == 0) for i, b in enumerate(res.buckets)][::step],
                  fontsize=8.5, color=theme['muted'])
    ax.set_ylim(0, (peak or 1) * 1.15)
    ax.set_xlim(-0.6, len(xs) - 0.4 + (0.9 if q.chart == 'line' and len(res.series) == 1 else 0))
    ax.yaxis.set_major_formatter(__import__('matplotlib').ticker.FuncFormatter(
        lambda v, _: f'{int(v)}' if q.measure[0] == 'count' else f'{int(v)} d'))
    title(ax, theme, q)
    if dim:
        shown = [(i, s) for i, s in enumerate(res.series) if any(res.cells.get((b, None, s)) for b in res.buckets)]
        legend(ax, theme, [(label(dim, s), color(theme, dim, s, i)) for i, s in shown])


def draw_table(ax, res, theme):
    q = res.query
    cnt = q.measure[0] == 'count'
    cell = lambda v: fmt(v if v is not None or not cnt else 0, q.measure)
    ax.axis('off')
    dim0, dim1 = (q.by + [None, None])[:2]
    if q.over:
        head = ['Período'] + ([label(dim0, s) for s in res.series] if dim0 else [measure_caption(q)])
        body = [[bucket_label(b, q.over[1], True).replace('\n', ' ')] +
                [cell(res.cells.get((b, None, s))) for s in res.series] for b in res.buckets]
    elif dim1:
        head = [DIM_TITLE[dim0]] + [label(dim1, s) for s in res.series] + ['Total']
        body = [[label(dim0, g)] + [cell(res.cells.get((None, g, s))) for s in res.series] +
                [fmt(sum(res.cells.get((None, g, s)) or 0 for s in res.series), q.measure)] for g in res.order]
    else:
        head = [DIM_TITLE.get(dim0, '')] + [measure_caption(q).capitalize()] + (['Achados'] if q.measure[0] != 'count' else [])
        body = [[label(dim0, g), fmt(res.cells.get((None, g, None)), q.measure)] +
                ([str(res.sizes.get((None, g, None), 0))] if q.measure[0] != 'count' else []) for g in res.order]
    ncol = len(head)
    first = 0.34 if ncol <= 3 else 0.12
    widths = [first] + [((1 - first) / (ncol - 1))] * (ncol - 1)
    xs = [sum(widths[:i]) for i in range(ncol)]
    rowh = 1 / (len(body) + 1.4)
    y = 1 - rowh / 2
    for i, h in enumerate(head):
        ax.text(xs[i] + (widths[i] - 0.01 if i else 0), y, h, ha='right' if i else 'left', va='center',
                fontsize=8.5 if ncol > 4 else 9, fontweight=500, color=theme['muted'], transform=ax.transAxes)
    for r in body:
        ax.plot([0, 1], [y - rowh / 2] * 2, color=theme['line'], linewidth=0.8, transform=ax.transAxes)
        y -= rowh
        for i, c in enumerate(r):
            ax.text(xs[i] + (widths[i] - 0.01 if i else 0), y, c, ha='right' if i else 'left', va='center',
                    fontsize=9.5, color=theme['text'] if i == 0 else theme['text2'], transform=ax.transAxes)
    ax.text(0, 1 + rowh * 0.6, q.title or '', transform=ax.transAxes, ha='left', va='bottom', fontsize=12.5,
            fontweight=500, color=theme['text'])


def draw(ax, res, theme):
    q = res.query
    if q.chart == 'number':
        draw_number(ax, res, theme)
    elif q.chart == 'table':
        draw_table(ax, res, theme)
    elif q.over:
        draw_over(ax, res, theme)
    else:
        draw_bars(ax, res, theme, horizontal=q.chart == 'hbar')


def setup_fonts():
    import matplotlib
    from matplotlib import font_manager
    font_dir = Path(os.environ.get('FONT_DIR', '/fonts'))
    files = sorted(font_dir.glob('*.woff2')) if font_dir.exists() else []
    if files:
        from fontTools.ttLib import TTFont
        ttf_dir = Path('/tmp/inter-ttf')
        ttf_dir.mkdir(exist_ok=True)
        for f in files:
            t = TTFont(str(f))
            t.flavor = None
            out = ttf_dir / (f.stem + '.ttf')
            t.save(str(out))
            font_manager.fontManager.addfont(str(out))
        matplotlib.rcParams['font.family'] = 'Inter'
    else:
        print('Inter not found; using DejaVu Sans')
    matplotlib.rcParams['font.weight'] = 400


def render(path, res, theme, size):
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=size, dpi=150, facecolor=theme['bg'])
    left = 0.2 if res.query.chart == 'hbar' else 0.06
    ax = fig.add_axes([left, 0.14, 0.96 - left, 0.66])
    if res.query.chart == 'number':
        ax.set_position([0.06, 0.08, 0.88, 0.78])
    elif res.query.chart == 'table':
        h = size[1]
        ax.set_position([0.06, 0.25 / h, 0.88, (h - 0.85) / h])
    draw(ax, res, theme)
    fig.savefig(path, facecolor=theme['bg'])
    plt.close(fig)


# ---------------------------------------------------------------------------------------
# Examples
# ---------------------------------------------------------------------------------------
OPEN = 'status:sent,fixing,retesting'
EXAMPLES = [
    ('01-abertas', f'count where {OPEN} title "Abertas"'),
    ('02-criticas-abertas', f'count where {OPEN} cvss:9 title "Críticas abertas"'),
    ('03-aguardando-aceite', 'count where status:sent -sent:15d title "Aguardando aceite há mais de 15 dias"'),
    ('04-mediana-correcao', 'median days sent..fixed where fixed:90d title "Tempo até a correção (90 dias)"'),
    ('05-abertas-por-severidade', f'count by severity where {OPEN} title "Abertas por severidade"'),
    ('06-funil-por-status', 'count by status where -status:draft -status:ready title "Depois do envio"'),
    ('07-abertas-por-relatorio', f'count by report, severity top 6 where {OPEN} as hbar title "Abertas por relatório"'),
    ('08-novas-por-fonte', 'count by source where created:90d title "Encontradas nos últimos 90 dias, por fonte"'),
    ('09-enviadas-por-mes', 'count over sent per month where sent:12m title "Enviadas por mês"'),
    ('10-corrigidas-por-mes', 'count by severity over fixed per month where fixed:12m as bar title "Corrigidas por mês"'),
    ('11-tempo-ate-aceite', 'p90 days sent..accepted by severity over sent per quarter where sent:01-2026.. '
                            'title "Tempo até o aceite (p90), por trimestre"'),
    ('12-tabela-tempo-correcao', 'median days sent..fixed by severity where fixed:{period} as table '
                                 'title "Mediana de dias até a correção"'),
    ('13-tabela-severidade-status', 'count by severity, status where -status:draft -status:ready as table '
                                    'title "Severidade × status"'),
]
# The defense team's TV: only status, severity and source groups, no report names or people.
TV = [
    f'count where {OPEN} title "Abertas"',
    f'count where {OPEN} cvss:9 title "Críticas abertas"',
    'count where status:sent -sent:15d title "Aguardando aceite > 15 dias"',
    f'count by severity where {OPEN} title "Abertas por severidade"',
    'count by severity over fixed per week where fixed:3m as bar title "Corrigidas por semana"',
    f'count by status where {OPEN} title "Em andamento"',
]
TV_DIMS = {'status', 'severity', 'source'}

ERRORS = [
    'count by host',
    'count where status:sent as pie',
    'median days sent fixed',
    'count by report title Abertas',
    'count over fixed per month as number',
    'count by severity over fixed per week where fixed:12w',
    'count where status:open',
]


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    setup_fonts()
    rows = mock_rows()
    OUT.mkdir(exist_ok=True)
    print(f'{len(rows)} mock findings; statuses:',
          {s: sum(r["status"] == s for r in rows) for s in STATUSES})

    for name, text in EXAMPLES:
        q = parse(text, period='01-08-2026..31-10-2026')
        res = evaluate(q, rows)
        size = (4.2, 2.6) if q.chart == 'number' else (7.2, 4.0)
        if q.chart == 'table':
            size = (7.2, 1.0 + 0.32 * (len(res.buckets or res.order) + 1))
        render(OUT / f'{name}.png', res, LIGHT, size)
        print(f'{name}: {q.chart}')

    # TV board, dark, 1920x1080
    for t in TV:
        q = parse(t)
        assert set(q.by) <= TV_DIMS, t
    fig = plt.figure(figsize=(16, 9), dpi=120, facecolor=DARK['bg'])
    fig.text(0.04, 0.94, 'Remediação', fontsize=22, fontweight=500, color=DARK['text'], va='center')
    fig.text(0.96, 0.94, '13/11/2026  14:00', fontsize=16, fontweight=300, color=DARK['muted'], va='center', ha='right')
    fig.text(0.96, 0.905, 'atualizado há 1 min', fontsize=10, color=DARK['dim'], va='center', ha='right')
    cells = [(0.04, 0.62, 0.27, 0.22), (0.37, 0.62, 0.27, 0.22), (0.70, 0.62, 0.27, 0.22),
             (0.04, 0.09, 0.27, 0.40), (0.37, 0.09, 0.30, 0.40), (0.73, 0.09, 0.24, 0.40)]
    for (x, y, w, h), t in zip(cells, TV):
        res = evaluate(parse(t), rows)
        theme = dict(DARK, number=DARK['warn']) if 'aceite' in t else DARK
        ax = fig.add_axes([x, y, w, h])
        if res.query.chart == 'number':
            draw_number(ax, res, theme, big=72)
        else:
            draw(ax, res, theme)
    fig.savefig(OUT / 'tv-remediacao.png', facecolor=DARK['bg'])
    plt.close(fig)
    print('tv-remediacao: board')

    for text in ERRORS:
        try:
            parse(text)
            print(f'NOT REJECTED: {text}')
        except QueryError as e:
            print(f'{text!r:45} -> {e}')


if __name__ == '__main__':
    main()
