"""Runs chart queries (D18) over the findings and returns aggregates only.

The query is never turned into SQL: the findings' few chart fields are loaded once per
request (`load_rows`), in the portal's time zone, and every chart of a dashboard is computed
from them in Python. No result carries an identifier, a description or a host.
"""

from __future__ import annotations

import math
import statistics
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.report import Report
from app.models.user import User
from app.models.vulnerability import Vulnerability, vulnerability_operators
from app.services.dashboard_query import DATE_KEYS, STATUSES, Query, add_months, match

MIN_SAMPLE = 3  # a duration from fewer findings is shown as a dash
SEVERITIES = ["critical", "high", "medium", "low", "none"]
OTHERS, NONE = "__others__", "__none__"


def local_now() -> datetime:
    return datetime.now(ZoneInfo(settings.portal_timezone)).replace(tzinfo=None)


def _local(d: datetime | None, tz: ZoneInfo) -> datetime | None:
    # The database keeps naive UTC.
    return None if d is None else d.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)


def load_rows(session: Session) -> list[dict]:
    """Every live finding, with what a chart can filter or group by."""
    tz = ZoneInfo(settings.portal_timezone)
    V = Vulnerability
    cols = [V.id, V.identifier, V.status, V.cvss_score, V.source, V.report_id, Report.internal_id, Report.name,
            *(getattr(V, c) for c in DATE_KEYS.values())]
    q = (select(*cols).outerjoin(Report, Report.id == V.report_id).where(V.deleted_at.is_(None)))
    ops: dict = {}
    for vid, name in session.execute(
            select(vulnerability_operators.c.vulnerability_id, User.username)
            .join(User, User.id == vulnerability_operators.c.user_id)):
        ops.setdefault(vid, []).append(name)
    rows = []
    for r in session.execute(q):
        row = {
            "identifier": r.identifier, "status": r.status.value,
            "cvss": float(r.cvss_score) if r.cvss_score is not None else None,
            "source": r.source, "report_id": r.report_id,
            "report_text": f"{r.internal_id or ''} {r.name or ''}",
            "report_name": r.name or r.internal_id or "",
            "operators": sorted(ops.get(r.id, [])),
        }
        for c in DATE_KEYS.values():
            row[c] = _local(getattr(r, c), tz)
        rows.append(row)
    return rows


def severity(cvss: float | None) -> str:
    if not cvss:
        return "none"
    return "low" if cvss < 4 else "medium" if cvss < 7 else "high" if cvss < 9 else "critical"


def bucket(d: datetime, unit: str) -> datetime:
    day = datetime(d.year, d.month, d.day)
    if unit == "day":
        return day
    if unit == "week":
        return day - timedelta(days=d.weekday())  # weeks start on Monday
    if unit == "month":
        return datetime(d.year, d.month, 1)
    if unit == "quarter":
        return datetime(d.year, 3 * ((d.month - 1) // 3) + 1, 1)
    return datetime(d.year, 1, 1)


def next_bucket(b: datetime, unit: str) -> datetime:
    if unit == "day":
        return b + timedelta(days=1)
    if unit == "week":
        return b + timedelta(days=7)
    if unit == "month":
        return add_months(b, 1)
    if unit == "quarter":
        return add_months(b, 3)
    return b.replace(year=b.year + 1)


def dim_values(row: dict, dim: str) -> list:
    """A finding's group(s) for a dimension: (key, label). Several operators = several groups."""
    if dim == "severity":
        return [(severity(row["cvss"]), None)]
    if dim == "status":
        return [(row["status"], None)]
    if dim == "report":
        return [(str(row["report_id"]), row["report_name"])] if row["report_id"] else [(NONE, None)]
    if dim == "source":
        return [(row["source"], row["source"])] if row["source"] else [(NONE, None)]
    return [(o, o) for o in row["operators"]] or [(NONE, None)]


def _days(row: dict, a: str, b: str) -> float | None:
    x, y = row[DATE_KEYS[a]], row[DATE_KEYS[b]]
    if x is None or y is None or y < x:
        return None
    return (y - x).total_seconds() / 86400


def aggregate(measure: tuple, rows: list[dict]) -> tuple[float | None, int]:
    """(value, how many findings it comes from)."""
    if measure[0] == "count":
        return len(rows), len(rows)
    _, agg, a, b = measure
    days = sorted(d for d in (_days(r, a, b) for r in rows) if d is not None)
    if len(days) < MIN_SAMPLE:
        return None, len(days)
    if agg == "avg":
        v = statistics.fmean(days)
    elif agg == "median":
        v = statistics.median(days)
    elif agg == "min":
        v = days[0]
    elif agg == "max":
        v = days[-1]
    else:  # pNN, linear interpolation
        k = (len(days) - 1) * int(agg[1:]) / 100
        lo, hi = math.floor(k), math.ceil(k)
        v = days[lo] + (days[hi] - days[lo]) * (k - lo)
    return round(v, 1), len(days)


def _order(dim: str, keys: set, weight: dict) -> list:
    if dim == "status":
        return [s for s in STATUSES if s in keys]
    if dim == "severity":
        return [s for s in SEVERITIES if s in keys]
    rest = sorted((k for k in keys if k not in (OTHERS, NONE)), key=lambda k: (-weight.get(k, 0), str(k)))
    return rest + [k for k in (NONE, OTHERS) if k in keys]


def evaluate(q: Query, all_rows: list[dict], now: datetime) -> dict:
    tokens = list(q.where)
    buckets = None
    rows = all_rows
    if q.over:
        key, unit = DATE_KEYS[q.over[0]], q.over[1]
        # The window is the where filter's period on the over date (else from the first such
        # date), and starts on a whole bucket: fixed:12m per month = 12 whole months + this one.
        window = [t for t in tokens if t.key == q.over[0] and not t.negate]
        tokens = [t for t in tokens if t not in window]
        rows = [r for r in rows if r[key] is not None and match(r, tokens)]
        lo, hi = window[-1].value if window else (None, None)
        end = now + timedelta(seconds=1)
        lo = bucket(lo or min((r[key] for r in rows), default=now), unit)
        hi = min(hi or end, end)
        rows = [r for r in rows if lo <= r[key] < hi]
        buckets, b = [], lo
        while b < hi and len(buckets) < 400:
            buckets.append(b)
            b = next_bucket(b, unit)
    else:
        rows = [r for r in rows if match(r, tokens)]

    dims = q.by
    labels: dict = {}
    keep = None
    if q.top and dims:
        weight: dict = {}
        for r in rows:
            for k, _ in dim_values(r, dims[0]):
                weight[k] = weight.get(k, 0) + 1
        keep = set(sorted(weight, key=lambda k: (-weight[k], str(k)))[:q.top])

    # Group: (bucket, x-group, series) -> rows. With over, by[0] is the series.
    grouped: dict = {}
    for r in rows:
        gs = dim_values(r, dims[0]) if dims else [(None, None)]
        ss = dim_values(r, dims[1]) if len(dims) > 1 else [(None, None)]
        for g, gl in gs:
            if keep is not None and g not in keep:
                g, gl = OTHERS, None
            labels[g] = gl
            for s, sl in ss:
                labels[s] = sl
                k = (bucket(r[DATE_KEYS[q.over[0]]], q.over[1]), None, g) if q.over else (None, g, s)
                grouped.setdefault(k, {})[id(r)] = r  # a finding counts once per group
    cells = {k: aggregate(q.measure, list(v.values())) for k, v in grouped.items()}

    weight = {}
    for (_, g, s), (_, n) in cells.items():
        weight[g] = weight.get(g, 0) + n
        weight[s] = weight.get(s, 0) + n
    item = lambda k: {"key": k, "label": labels.get(k)}  # noqa: E731
    empty = (0 if q.measure[0] == "count" else None, 0)

    if q.over:
        series = _order(dims[0], {k[2] for k in cells}, weight) if dims else [None]
        x = [{"key": b.date().isoformat(), "label": None} for b in buckets]
        cell = lambda b, s: cells.get((b, None, s), empty)  # noqa: E731
        grid = [[cell(b, s) for s in series] for b in buckets]
    elif dims:
        groups = _order(dims[0], {k[1] for k in cells}, weight)
        series = _order(dims[1], {k[2] for k in cells}, weight) if len(dims) > 1 else [None]
        x = [item(g) for g in groups]
        grid = [[cells.get((None, g, s), empty) for s in series] for g in groups]
    else:
        series, x = [None], []
        value, n = cells.get((None, None, None), aggregate(q.measure, []))
        return {**_head(q), "value": value, "n": n}

    return {
        **_head(q),
        "x": x,
        "series": [] if series == [None] else [item(s) for s in series],
        "values": [[v for v, _ in row] for row in grid],
        "sizes": [[n for _, n in row] for row in grid],
    }


def _head(q: Query) -> dict:
    return {
        "chart": q.chart, "title": q.title,
        "measure": q.measure[0], "agg": q.measure[1] if q.measure[0] == "duration" else None,
        "range": [q.measure[2], q.measure[3]] if q.measure[0] == "duration" else None,
        "by": q.by, "over": {"date": q.over[0], "unit": q.over[1]} if q.over else None,
    }
