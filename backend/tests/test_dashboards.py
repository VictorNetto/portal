"""Dashboards (D18): the query language, the dashboard role, and TV links."""

from datetime import datetime

import httpx
import pytest

from app.services.dashboard_engine import evaluate
from app.services.dashboard_query import QueryError, parse, parse_filter
from tests.conftest import BASE_URL, make_user, saved_vuln, tag

NOW = datetime(2026, 11, 13, 14, 0)


def err(text, variables=None):
    with pytest.raises(QueryError) as e:
        parse(text, variables, NOW)
    return e.value


# --- the language -------------------------------------------------------------------------

def test_defaults_pick_the_chart():
    assert parse("count", now=NOW).chart == "number"
    assert parse("count by severity", now=NOW).chart == "bar"
    assert parse("count by report", now=NOW).chart == "hbar"
    assert parse("count over fixed per month", now=NOW).chart == "line"
    q = parse('median days sent..fixed by severity where fixed:90d as table title "T"', now=NOW)
    assert (q.measure, q.by, q.chart, q.title) == (("duration", "median", "sent", "fixed"), ["severity"], "table", "T")


@pytest.mark.parametrize("text,code,pos", [
    ("count by host", "bad_dim", 9),
    ("count where status:sent as pie", "bad_chart", 27),
    ("median days sent fixed", "need_range", 12),
    ("count by report title Abertas", "title_quotes", 22),
    ("count over fixed per month as number", "number_no_group", 0),
    ("count by severity over fixed per week where fixed:12w", "bad_period", 44),
    ("count where status:open", "bad_status", 12),
    ("count where host:x", "bad_key", 12),
    ("count by severity by status", "repeated", 18),
    ("count top 3", "top_needs_by", 0),
    ('count title "x', "unclosed_quote", 12),
])
def test_errors_say_what_and_where(text, code, pos):
    e = err(text)
    assert (e.code, e.pos) == (code, pos)


def test_variables_are_replaced_and_errors_point_at_them():
    q = parse("count where status:$open fixed:$p", {"open": "sent,fixing", "p": "90d"}, NOW)
    assert q.where[0].value == ["sent", "fixing"]
    e = err("count by severity where $bad", {"bad": "fixed:12w"})
    assert e.code == "bad_period" and e.pos == 24          # the $bad the user typed
    assert err("count where $nope").code == "undefined_var"
    # a value is not expanded again, so variables can't loop
    assert parse("count where $a", {"a": "$a"}, NOW).where[0].value == "$a"


def test_filter_matches_the_hub():
    """The same cases as e2e/tests/dashboards.spec.js runs on frontend/src/filterQuery.js."""
    toks = parse_filter('status:sent,fixing -cvss:9 report:"Rede X" fixed:01-2026.. "a b"', NOW)
    assert [(t.negate, t.key) for t in toks] == [
        (False, "status"), (True, "cvss"), (False, "report"), (False, "fixed"), (False, "text")]
    assert toks[2].value == "Rede X" and toks[4].value == "a b"
    assert toks[3].value == (datetime(2026, 1, 1), None)
    # Not strict (the Hub while typing), an unreadable token is left out.
    assert parse_filter("fixed:12w status:open cvss:11", NOW) == []


def row(**kw):
    base = {"identifier": "x", "status": "fixing", "cvss": 7.5, "source": "Burp", "report_id": None,
            "report_text": "", "report_name": "", "operators": []}
    base.update({c: None for c in ("created_at", "updated_at", "sent_at", "accepted_at", "fixing_at",
                                   "retesting_at", "fixed_at", "risk_accepted_at")})
    base.update(kw)
    return base


def test_engine_counts_groups_and_windows():
    rows = [row(cvss=9.8), row(), row(status="fixed", fixed_at=datetime(2026, 11, 2), sent_at=datetime(2026, 10, 1)),
            row(status="fixed", fixed_at=datetime(2026, 9, 5), sent_at=datetime(2026, 9, 1)),
            row(status="fixed", fixed_at=datetime(2026, 9, 9), sent_at=datetime(2026, 9, 1), cvss=None)]
    r = evaluate(parse("count by severity where status:fixing,retesting", now=NOW), rows, NOW)
    assert [x["key"] for x in r["x"]] == ["critical", "high"] and r["values"] == [[1], [1]]
    r = evaluate(parse("count over fixed per month where fixed:3m", now=NOW), rows, NOW)
    # 3 months back from 13-11 is 13-08: the window starts on the whole month of August
    assert [x["key"] for x in r["x"]] == ["2026-08-01", "2026-09-01", "2026-10-01", "2026-11-01"]
    assert r["values"] == [[0], [2], [0], [1]]
    r = evaluate(parse("median days sent..fixed", now=NOW), rows, NOW)
    assert (r["value"], r["n"]) == (8.0, 3)
    r = evaluate(parse("median days sent..fixed where cvss:7", now=NOW), rows, NOW)
    assert r["value"] is None and r["n"] == 2              # fewer than 3: shown as a dash


def test_operators_count_once_each():
    rows = [row(operators=["ana", "bia"]), row(operators=["ana"]), row()]
    r = evaluate(parse("count by operator", now=NOW), rows, NOW)
    assert [(x["key"], v[0]) for x, v in zip(r["x"], r["values"], strict=True)] == [("ana", 2), ("bia", 1), ("__none__", 1)]


# --- the API ------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def painel(admin):
    return make_user(admin, "dashboard")


def board(c, **kw):
    body = {"name": f"pytest-{tag()}", "variables": [{"name": "open", "value": "sent,fixing,retesting"}],
            "charts": [{"query": 'count where status:$open title "Abertas"'},
                       {"query": "count by severity where status:$open", "width": 2}], **kw}
    r = c.post("/dashboards", body)
    assert r.status_code == 201, r.text
    return r.json()


def test_only_admins_and_dashboard_accounts(admin, painel, writer, reader):
    for c in (writer, reader):
        assert c.get("/dashboards").status_code == 403
    assert admin.get("/dashboards").status_code == 200
    d = board(painel)
    assert any(x["id"] == d["id"] for x in admin.get("/dashboards").json())


def test_dashboard_accounts_reach_nothing_else(painel):
    for path in ("/vulnerabilities", "/reports", "/users", "/report-templates", "/defense/vulnerabilities"):
        assert painel.get(path).status_code == 403, path
    assert painel.get("/auth/me").status_code == 200


def test_saving_refuses_a_chart_that_cannot_run(painel):
    r = painel.post("/dashboards", {"name": f"pytest-{tag()}", "charts": [{"query": "count"}, {"query": "count by host"}]})
    assert r.status_code == 422
    assert r.json()["detail"]["errors"] == [{"chart": 1, "code": "bad_dim", "pos": 9,
                                             "params": {"got": "host", "dims": "status, severity, source, report, operator"}}]
    d = board(painel)
    assert painel.patch(f"/dashboards/{d['id']}", {"variables": []}).status_code == 422  # $open now undefined


def test_run_and_preview_return_aggregates_only(painel, writer):
    saved_vuln(writer, cvss_score=9.1)
    d = board(painel)
    out = painel.post(f"/dashboards/{d['id']}/run", {}).json()
    assert [c["width"] for c in out["charts"]] == [1, 2]
    assert out["charts"][0]["result"]["chart"] == "number"
    ready = painel.post(f"/dashboards/{d['id']}/run", {"variables": [{"name": "open", "value": "ready"}]}).json()
    assert ready["charts"][0]["result"]["value"] >= 1
    p = painel.post("/dashboards/preview", {"query": "count by report where status:ready"}).json()
    assert p["tv_error"]["code"] == "tv_dim" and "identifier" not in str(p)
    r = painel.post("/dashboards/preview", {"query": "count by host"})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "bad_dim"


def test_edit_and_delete_are_audited(admin, painel):
    d = board(painel)
    r = painel.patch(f"/dashboards/{d['id']}", {"name": d["name"] + "-x"})
    assert r.status_code == 200 and r.json()["updated_by"] == painel.user["username"]
    assert painel.delete(f"/dashboards/{d['id']}").status_code == 204
    assert painel.get(f"/dashboards/{d['id']}").status_code == 404
    items = admin.get("/audit-logs", params={"entity_type": "dashboard", "page_size": 50}).json()["items"]
    assert {e["action"] for e in items if e["entity_id"] == d["id"]} == {"create", "update", "delete"}


def tv_get(token):
    return httpx.get(f"{BASE_URL}/tv/{token}", timeout=30)


def test_tv_link_shows_the_board_without_signing_in(painel):
    d = board(painel)
    link = painel.post(f"/dashboards/{d['id']}/links", {"label": "Sala"}).json()
    r = tv_get(link["token"])
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == d["name"] and len(body["charts"]) == 2
    assert "query" not in str(body) and "open" not in str(body)          # no query text, no variables
    listed = painel.get(f"/dashboards/{d['id']}/links").json()
    assert "token" not in listed[0] and listed[0]["last_used_at"]
    assert painel.post(f"/dashboards/{d['id']}/links/{link['id']}/revoke").status_code == 200
    assert tv_get(link["token"]).status_code == 404
    assert tv_get("nope").status_code == 404


def test_tv_refuses_names_of_reports_and_people(painel):
    d = board(painel, charts=[{"query": "count by operator"}])
    r = painel.post(f"/dashboards/{d['id']}/links", {"label": "Sala"})
    assert r.status_code == 422 and r.json()["detail"]["errors"][0]["code"] == "tv_dim"
    # a chart added after the link is hidden on the TV, not shown
    ok = board(painel)
    link = painel.post(f"/dashboards/{ok['id']}/links", {"label": "Sala"}).json()
    painel.patch(f"/dashboards/{ok['id']}", {"charts": [{"query": "count by report"}]})
    chart = tv_get(link["token"]).json()["charts"][0]
    assert "result" not in chart and chart["error"]["code"] == "unavailable"


def test_tv_stops_when_its_maker_loses_access(admin):
    maker = make_user(admin, "dashboard")
    d = board(maker)
    link = maker.post(f"/dashboards/{d['id']}/links", {"label": "Sala"}).json()
    assert tv_get(link["token"]).status_code == 200
    admin.patch(f"/users/{maker.user['id']}", {"is_active": False})
    assert tv_get(link["token"]).status_code == 404
