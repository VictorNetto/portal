"""The chart query language (D18, docs/specs/DASHBOARDS.md §2).

    count by severity over fixed per month where fixed:$periodo as bar title "Corrigidas"

`parse(text, variables)` returns a `Query` or raises `QueryError`. Errors carry a code, a
position in the text the user typed and parameters; the browser turns them into a sentence
(`dash.err.<code>` in frontend/src/i18n.js), so they read in the user's language.

The `where` part is the Hub filter (frontend/src/filterQuery.js), with two rules of its own:
`status:a,b` means either (the Hub accepts it too), and a token it can't read is an error,
because a saved chart must not silently count something else. tests/test_dashboards.py and
the browser tests share the cases that keep the two filters the same.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

STATUSES = ["draft", "ready", "sent", "fixing", "retesting", "fixed", "risk_accepted"]
DATE_KEYS = {
    "created": "created_at", "updated": "updated_at", "sent": "sent_at", "accepted": "accepted_at",
    "fixing": "fixing_at", "retesting": "retesting_at", "fixed": "fixed_at", "risk": "risk_accepted_at",
}
DIMS = ["status", "severity", "source", "report", "operator"]
TV_DIMS = {"status", "severity", "source"}  # no report name or person on a TV
UNITS = ["day", "week", "month", "quarter", "semester", "year"]
CHARTS = ["number", "bar", "hbar", "line", "table"]
CLAUSES = ["by", "over", "where", "top", "as", "title"]
AGGS = ["avg", "median", "min", "max"]
FILTER_KEYS = {"status", "cvss", "report", "operator", "source", *DATE_KEYS}
VAR_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")
VAR_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
MAX_QUERY = 1000
MAX_TOP = 50


class QueryError(Exception):
    def __init__(self, code: str, pos: int = 0, **params):
        super().__init__(code)
        self.code, self.pos, self.params = code, pos, params

    def as_dict(self) -> dict:
        return {"code": self.code, "pos": self.pos, "params": self.params}


@dataclass
class Tok:
    text: str
    start: int
    end: int
    quoted: bool


@dataclass
class Query:
    measure: tuple                    # ("count",) or ("duration", agg, from_key, to_key)
    by: list[str] = field(default_factory=list)
    over: tuple[str, str] | None = None   # (date key, unit)
    where: list = field(default_factory=list)  # parsed filter tokens
    top: int | None = None
    chart: str = "number"
    title: str | None = None


# --- variables ------------------------------------------------------------------------

def expand(text: str, variables: dict[str, str]) -> tuple[str, callable]:
    """Replace `$name` with its value. Returns the text and a function that maps a position
    in it back to the text the user typed (an error inside a value points at its `$name`).
    Values are not expanded again, so variables can't loop."""
    out, spans, last = [], [], 0          # spans: (start in out, end in out, start in text)
    size = 0
    for m in VAR_RE.finditer(text):
        name = m.group(1)
        if name not in variables:
            raise QueryError("undefined_var", m.start(), name=name)
        out.append(text[last:m.start()])
        size += m.start() - last
        value = str(variables[name])
        spans.append((size, size + len(value), m.start(), m.end()))
        out.append(value)
        size += len(value)
        last = m.end()
    out.append(text[last:])

    def back(pos: int) -> int:
        shift = 0
        for s, e, o, oe in spans:
            if pos < s:
                break
            if pos < e:
                return o
            shift += (oe - o) - (e - s)
        return pos + shift

    return "".join(out), back


# --- query ----------------------------------------------------------------------------

def tokenize(text: str) -> list[Tok]:
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
                    raise QueryError("unclosed_quote", i)
                i, quoted = j + 1, True
            else:
                i += 1
        toks.append(Tok(text[start:i], start, i, quoted))
    return toks


def parse(source: str, variables: dict[str, str] | None = None, now: datetime | None = None) -> Query:
    """Parse one query. `now` is the portal's local time (periods like 90d count from it)."""
    if len(source) > MAX_QUERY:
        raise QueryError("too_long", MAX_QUERY, max=MAX_QUERY)
    text, back = expand(source, variables or {})
    try:
        return _parse(text, now or datetime.now())
    except QueryError as e:
        e.pos = back(e.pos)
        raise


def _parse(text: str, now: datetime) -> Query:
    toks = tokenize(text)
    if not toks:
        raise QueryError("empty", 0)
    is_clause = lambda t: not t.quoted and t.text in CLAUSES  # noqa: E731

    first = toks[0]
    if first.text == "count":
        measure, i = ("count",), 1
    elif first.text in AGGS or re.fullmatch(r"p([1-9][0-9])", first.text):
        if len(toks) < 3 or toks[1].text != "days":
            raise QueryError("need_days", toks[1].start if len(toks) > 1 else len(text), agg=first.text)
        a, sep, b = toks[2].text.partition("..")
        if not sep:
            raise QueryError("need_range", toks[2].start)
        for k in (a, b):
            if k not in DATE_KEYS:
                raise QueryError("bad_date", toks[2].start, got=k, dates=", ".join(DATE_KEYS))
        if a == b:
            raise QueryError("same_dates", toks[2].start)
        measure, i = ("duration", first.text, a, b), 3
    else:
        raise QueryError("bad_start", first.start, got=first.text)

    q = Query(measure)
    seen: set[str] = set()
    chart = None
    while i < len(toks):
        kw = toks[i]
        if not is_clause(kw):
            raise QueryError("expected_clause", kw.start, got=kw.text, clauses=", ".join(CLAUSES))
        if kw.text in seen:
            raise QueryError("repeated", kw.start, kw=kw.text)
        seen.add(kw.text)
        i += 1
        args = []
        while i < len(toks) and not is_clause(toks[i]):
            args.append(toks[i])
            i += 1
        if not args:
            raise QueryError("no_value", kw.end, kw=kw.text)
        a0 = args[0]

        if kw.text == "by":
            dims = "".join(a.text for a in args).split(",")
            for d in dims:
                if d not in DIMS:
                    raise QueryError("bad_dim", a0.start, got=d, dims=", ".join(DIMS))
            if len(dims) > 2 or len(set(dims)) != len(dims):
                raise QueryError("two_dims", a0.start)
            q.by = dims
        elif kw.text == "over":
            if len(args) != 3 or args[1].text != "per":
                raise QueryError("bad_over", a0.start)
            if args[0].text not in DATE_KEYS:
                raise QueryError("bad_date", a0.start, got=args[0].text, dates=", ".join(DATE_KEYS))
            if args[2].text not in UNITS:
                raise QueryError("bad_unit", args[2].start, got=args[2].text, units=", ".join(UNITS))
            q.over = (args[0].text, args[2].text)
        elif kw.text == "where":
            q.where = parse_filter(text[a0.start:args[-1].end], now, strict=True, offset=a0.start)
        elif kw.text == "top":
            if len(args) != 1 or not a0.text.isdigit() or not 1 <= int(a0.text) <= MAX_TOP:
                raise QueryError("bad_top", a0.start, max=MAX_TOP)
            q.top = int(a0.text)
        elif kw.text == "as":
            if len(args) != 1 or a0.text not in CHARTS:
                raise QueryError("bad_chart", a0.start, charts="|".join(CHARTS))
            chart = a0.text
        elif kw.text == "title":
            if len(args) != 1 or not (a0.quoted and a0.text.startswith('"') and a0.text.endswith('"')):
                raise QueryError("title_quotes", a0.start)
            q.title = a0.text[1:-1]

    if chart is None:
        if q.over:
            chart = "line"
        elif not q.by:
            chart = "number"
        else:
            chart = "hbar" if q.by[0] in ("source", "report", "operator") else "bar"
    if chart == "number" and (q.by or q.over):
        raise QueryError("number_no_group", 0)
    if chart == "line" and not q.over:
        raise QueryError("line_needs_over", 0)
    if chart == "hbar" and (q.over or not q.by):
        raise QueryError("hbar_needs_by", 0)
    if chart == "bar" and not (q.by or q.over):
        raise QueryError("bar_needs_group", 0)
    if q.over and len(q.by) > 1:
        raise QueryError("over_one_dim", 0)
    if q.top and not q.by:
        raise QueryError("top_needs_by", 0)
    q.chart = chart
    return q


# --- the Hub filter (a port of frontend/src/filterQuery.js) -------------------------------

def add_months(d: datetime, n: int) -> datetime:
    y, m = divmod(d.month - 1 + n, 12)
    y += d.year
    leap = y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)
    last = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m]
    return d.replace(year=y, month=m + 1, day=min(d.day, last))


def _calendar_span(text: str):
    if m := re.fullmatch(r"(\d{1,2})-(\d{1,2})-(\d{4})", text):
        try:
            start = datetime(int(m[3]), int(m[2]), int(m[1]))
        except ValueError:
            return None
        return start, start + timedelta(days=1)
    if m := re.fullmatch(r"(\d{1,2})-(\d{4})", text):
        if not 1 <= int(m[1]) <= 12:
            return None
        start = datetime(int(m[2]), int(m[1]), 1)
        return start, add_months(start, 1)
    if m := re.fullmatch(r"(\d{4})", text):
        if int(m[1]) < 1:
            return None
        return datetime(int(m[1]), 1, 1), datetime(int(m[1]) + 1, 1, 1)
    # A semester or a quarter: 26s1 / 2026s1, 26q3 / 26t3 (trimestre). Two digits mean 20xx.
    if m := re.fullmatch(r"(\d{2}|\d{4})([sqt])(\d)", text):
        year = int(m[1]) + (2000 if len(m[1]) == 2 else 0)
        n, size = int(m[3]), (6 if m[2] == "s" else 3)
        if not 1 <= n <= 12 // size:
            return None
        start = datetime(year, (n - 1) * size + 1, 1)
        return start, add_months(start, size)
    return None


def parse_period(text: str, now: datetime):
    """(from, to) local datetimes, either None, `to` exclusive; None when invalid.
    7d = today and the 6 days before; 3m, 2y count back from today."""
    v = text.strip().lower()
    today = datetime(now.year, now.month, now.day)
    if m := re.fullmatch(r"(\d{1,4})([dmy])", v):
        n = int(m[1])
        if n < 1:
            return None
        if m[2] == "d":
            return today - timedelta(days=n - 1), None
        try:
            return add_months(today, -n if m[2] == "m" else -12 * n), None
        except ValueError:
            return None
    parts = v.split(".")
    if len(parts) == 1:
        parts = ["", parts[0], ""]
    if len(parts) != 3:
        return None
    spans = [_calendar_span(p) if p else False for p in parts]
    if None in spans:
        return None
    d1, d2, d3 = spans
    if d1 or d3:
        if d1 and d3 and d3[1] <= d1[0]:
            return None
        return (d1[0] if d1 else None), (d3[1] if d3 else None)
    return (d2[0], d2[1]) if d2 else None


CVSS_RE = re.compile(r"(?:10(?:\.0)?|[0-9](?:\.[0-9])?)")


@dataclass
class FilterTok:
    negate: bool
    key: str          # "text", "status", "cvss", "report", "operator", "source" or a date key
    value: object     # str, float, list of statuses, or (from, to)
    raw: str


def filter_tokens(text: str) -> list[tuple[str, int]]:
    """Split on spaces, except inside quotes (like filterQuery.js). (raw, start) pairs."""
    out, i, n = [], 0, len(text)
    while i < n:
        while i < n and text[i].isspace():
            i += 1
        start = i
        while i < n and not text[i].isspace():
            if text[i] == '"':
                j = text.find('"', i + 1)
                i = n if j < 0 else j + 1
            else:
                i += 1
        if i > start:
            out.append((text[start:i], start))
    return out


def parse_filter(text: str, now: datetime, strict: bool = False, offset: int = 0) -> list[FilterTok]:
    """The Hub filter's tokens. Not strict (the Hub while typing), unreadable tokens are left out;
    strict (a chart), they are errors."""
    out = []
    for raw, start in filter_tokens(text):
        def bad(code, raw=raw, start=start, **p):
            if strict:
                raise QueryError(code, offset + start, raw=raw, **p)

        negate = raw.startswith("-") and len(raw) > 1
        body = raw[1:] if negate else raw
        colon, quote = body.find(":"), body.find('"')
        if colon == -1 or (quote != -1 and quote < colon):
            value = body.replace('"', "")
            if not value:
                bad("bad_text")
                continue
            out.append(FilterTok(negate, "text", value, raw))
            continue
        key, value = body[:colon].lower(), body[colon + 1:].replace('"', "")
        if key not in FILTER_KEYS:
            bad("bad_key", keys=", ".join(sorted(FILTER_KEYS - set(DATE_KEYS))) + ", " + ", ".join(DATE_KEYS))
            continue
        if key == "status":
            wanted = value.split(",")
            if not value or any(s not in STATUSES for s in wanted):
                bad("bad_status", statuses=", ".join(STATUSES))
                continue
            out.append(FilterTok(negate, key, wanted, raw))
        elif key == "cvss":
            if not CVSS_RE.fullmatch(value):
                bad("bad_cvss")
                continue
            out.append(FilterTok(negate, key, float(value), raw))
        elif key in DATE_KEYS:
            period = parse_period(value, now)
            if period is None:
                bad("bad_period")
                continue
            out.append(FilterTok(negate, key, period, raw))
        else:
            if not value:
                bad("bad_text")
                continue
            out.append(FilterTok(negate, key, value, raw))
    return out


def match(row: dict, tokens: list[FilterTok]) -> bool:
    """Does a finding pass every token? `row` has the fields engine.load_rows gives."""
    for t in tokens:
        if t.key == "text":
            ok = t.value.lower() in (row["identifier"] or "").lower()
        elif t.key == "status":
            ok = row["status"] in t.value
        elif t.key == "cvss":
            ok = row["cvss"] is not None and row["cvss"] >= t.value
        elif t.key == "report":
            if t.value.lower() == "none":
                ok = row["report_id"] is None
            else:
                ok = row["report_id"] is not None and t.value.lower() in row["report_text"].lower()
        elif t.key == "operator":
            ok = any(t.value.lower() in o.lower() for o in row["operators"])
        elif t.key == "source":
            ok = t.value.lower() in (row["source"] or "").lower()
        else:
            d, (lo, hi) = row[DATE_KEYS[t.key]], t.value
            ok = d is not None and (lo is None or d >= lo) and (hi is None or d < hi)
        if ok == t.negate:
            return False
    return True


def check_tv(q: Query) -> None:
    """TV links show only groupings without names of reports or people."""
    for d in q.by:
        if d not in TV_DIMS:
            raise QueryError("tv_dim", 0, dim=d, dims=", ".join(sorted(TV_DIMS)))


def clean_variables(items: list[dict]) -> dict[str, str]:
    out = {}
    for v in items or []:
        name, value = str(v.get("name", "")), str(v.get("value", ""))
        if not VAR_NAME_RE.fullmatch(name):
            raise ValueError(f"Invalid variable name: {name!r}")
        if name in out:
            raise ValueError(f"Variable defined twice: {name}")
        if len(value) > 200 or "\n" in value:
            raise ValueError(f"Variable {name}: at most 200 characters, one line")
        out[name] = value
    return out
