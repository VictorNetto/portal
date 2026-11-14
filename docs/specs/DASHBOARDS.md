# Dashboards: the chart query language

Status: **built** (D18 in [DECISIONS.md](../DECISIONS.md)), except reports (§4). In the portal: menu ➝ *Dashboards*, for admins and the **dashboard** role. The language runs in the API ([dashboard_query.py](../../backend/app/services/dashboard_query.py), [dashboard_engine.py](../../backend/app/services/dashboard_engine.py)); the browser draws the results ([DashChart.vue](../../frontend/src/components/DashChart.vue)).

The images below come from the first prototype, [dashboards/prototype.py](dashboards/prototype.py), over **mock data** (about 420 invented findings over 15 months). The portal draws the same charts in its own style.

## 1. Idea

One line of text describes one chart. The same line works in a dashboard (on screen or on a TV) and in a report, where it sits in the Markdown as a `chart` block.

```
count by severity where status:sent,fixing,retesting title "Abertas por severidade"
└─┬─┘ └────┬────┘ └───────────────┬────────────────┘ └───────────┬────────────┘
measure  grouping      which findings (Hub filter)            the chart's title
```

The `where` part is **the Hub's filter**, so whoever already filters the Hub knows half the language. The rest says what to count, how to group it and how to draw it.

## 2. Grammar

```ebnf
query    = measure , { clause } ;                 (* each clause at most once, in any order *)

measure  = "count"
         | agg , "days" , date , ".." , date ;    (* time between two dates of the same finding *)
agg      = "avg" | "median" | "min" | "max" | percentile ;
percentile = "p" , digit , digit ;                (* p50, p90, p95 … *)

clause   = by | over | where | top | as | title ;
by       = "by" , dim , [ "," , dim ] ;
over     = "over" , date , "per" , unit ;
where    = "where" , filter ;                     (* the Hub filter, up to the next clause word *)
top      = "top" , integer ;
as       = "as" , chart ;
title    = "title" , quoted-string ;

dim      = "status" | "severity" | "source" | "report" | "operator" ;
date     = "created" | "updated" | "sent" | "accepted" | "fixing" | "retesting" | "fixed" | "risk" ;
unit     = "day" | "week" | "month" | "quarter" | "year" ;
chart    = "number" | "bar" | "hbar" | "line" | "table" ;
```

Clause words (`by`, `over`, `where`, `top`, `as`, `title`) end the clause before them. To search the Hub's free text for one of these words, quote it: `where "by"`.

### Variables

A dashboard has variables, `name = value`. `$name` anywhere in a query (titles included) is replaced by the value before the query is read; values are not expanded again. An error inside a value points at the `$name` that brought it.

```
aberta  = sent,fixing,retesting
periodo = 3m

count where status:$aberta fixed:$periodo title "Corrigidas ($periodo)"
```

On the dashboard page, viewers may change the values for their own view (*Aplicar* / *Restaurar*); editing the dashboard changes them for everyone. A report would set `$periodo` to its own period (§4).

### Vocabulary

| Part | Meaning |
|---|---|
| `count` | How many findings |
| `median days sent..fixed` | Median of the days between the two dates, over the findings that have both (and the second after the first). Also `avg`, `min`, `max`, `p90`… A value from fewer than **3** findings is shown as "—" |
| `by status` | One bar, row or line per status. Statuses in lifecycle order |
| `by severity` | From the CVSS: critical ≥ 9, high ≥ 7, medium ≥ 4, low > 0, none. Shown critical first |
| `by source`, `by report`, `by operator` | Largest first; "Sem relatório" and "Outros" last |
| `by a, b` | Two groupings: a stacked bar or a cross table. With `over`, only one (it becomes the series) |
| `over fixed per month` | A time axis: each finding falls in the bucket of its `fixed` date. Findings without that date are left out |
| `top 6` | The 6 largest groups of the first `by`; the rest add up to "Outros" |
| `as …` | How to draw it (below). Optional |
| `title "…"` | The title shown above the chart |

### Charts

| `as` | Needs | Default when |
|---|---|---|
| `number` | No `by`, no `over` | Neither `by` nor `over` |
| `bar` | `by` or `over` | `by status` or `by severity`; with `over`, stacked columns |
| `hbar` | `by`, no `over` | `by source`, `by report`, `by operator` (long names) |
| `line` | `over` | `over` |
| `table` | Anything | Never (always chosen) |

Pie charts are left out on purpose: bars compare the same numbers more precisely.

### The time window

With `over`, the window is the period that the `where` filter gives the same date (`over fixed … where fixed:12m`). Without one, the window runs from the first such date in the data until now.

The window **starts on a whole bucket**: `fixed:12m per month` is 12 whole months plus the current one, never a cut-off first month. Buckets without findings show 0 (`count`) or a gap (durations). Weeks start on Monday. All dates are in the portal's time zone.

### Two differences from the Hub filter

1. **`status:a,b` means either.** `status:sent,fixing,retesting` reads as "sent or fixing or retesting". The Hub accepts it too, so the two stay the same language. There is no `status:open` shortcut on purpose: the statuses are written out (or kept in a variable).
2. **An invalid filter is an error.** While you type, the Hub ignores a token it can't read (`fixed:12w`). A saved chart must not, because it would silently count something else. The prototype found exactly this mistake in one of its own examples.

## 3. Examples

All titles and numbers are from the mock data. "Open" below means `status:sent,fixing,retesting`.

### Numbers

| | |
|---|---|
| `count where status:sent,fixing,retesting title "Abertas"` | ![](dashboards/examples/01-abertas.png) |
| `count where status:sent,fixing,retesting cvss:9 title "Críticas abertas"` | ![](dashboards/examples/02-criticas-abertas.png) |
| `count where status:sent -sent:15d title "Aguardando aceite há mais de 15 dias"`. Sent, and not in the last 15 days | ![](dashboards/examples/03-aguardando-aceite.png) |
| `median days sent..fixed where fixed:90d title "Tempo até a correção (90 dias)"` | ![](dashboards/examples/04-mediana-correcao.png) |

### Bars

`count by severity where status:sent,fixing,retesting title "Abertas por severidade"`

![](dashboards/examples/05-abertas-por-severidade.png)

`count by status where -status:draft -status:ready title "Depois do envio"`

![](dashboards/examples/06-funil-por-status.png)

`count by report, severity top 6 where status:sent,fixing,retesting as hbar title "Abertas por relatório"`

![](dashboards/examples/07-abertas-por-relatorio.png)

`count by source where created:90d title "Encontradas nos últimos 90 dias, por fonte"`

![](dashboards/examples/08-novas-por-fonte.png)

### Over time

`count over sent per month where sent:12m title "Enviadas por mês"`

![](dashboards/examples/09-enviadas-por-mes.png)

`count by severity over fixed per month where fixed:12m as bar title "Corrigidas por mês"`

![](dashboards/examples/10-corrigidas-por-mes.png)

`p90 days sent..accepted by severity over sent per quarter where sent:01-2026.. title "Tempo até o aceite (p90), por trimestre"`. Nine in ten findings sent in each quarter were accepted within this many days. ("Nenhuma" has too few findings, so no line.)

![](dashboards/examples/11-tempo-ate-aceite.png)

### Tables

`median days sent..fixed by severity where fixed:$periodo as table title "Mediana de dias até a correção"`. `$periodo` is a variable (here `01-08-2026..31-10-2026`). Duration tables also show how many findings each value comes from.

![](dashboards/examples/12-tabela-tempo-correcao.png)

`count by severity, status where -status:draft -status:ready as table title "Severidade × status"`

![](dashboards/examples/13-tabela-severidade-status.png)

### A TV board

Six queries in a dark, full-screen layout (1920 × 1080). TV links accept only the groupings `status`, `severity` and `source` (section 5), so no report name or person appears.

```
count where status:sent,fixing,retesting title "Abertas"
count where status:sent,fixing,retesting cvss:9 title "Críticas abertas"
count where status:sent -sent:15d title "Aguardando aceite > 15 dias"
count by severity where status:sent,fixing,retesting title "Abertas por severidade"
count by severity over fixed per week where fixed:3m as bar title "Corrigidas por semana"
count by status where status:sent,fixing,retesting title "Em andamento"
```

![](dashboards/examples/tv-remediacao.png)

### Errors

Errors give the position and the fix, in the user's language:

| Query | Message |
|---|---|
| `count by host` | não dá para agrupar por "host"; use status, severity, source, report, operator (posição 10) |
| `count where status:sent as pie` | as number\|bar\|hbar\|line\|table (posição 28) |
| `median days sent fixed` | o intervalo é \<data\>..\<data\>, por exemplo sent..fixed (posição 13) |
| `count by report title Abertas` | o título vai entre aspas: title "Abertas" (posição 23) |
| `count over fixed per month as number` | as number mostra um único valor: sem by nem over (posição 1) |
| `count by severity over fixed per week where fixed:12w` | período inválido; use 7d, 3m, 1y ou d1.d2.d3 (dd-mm-aaaa, mm-aaaa, aaaa): "fixed:12w" (posição 45) |
| `count where status:open` | status desconhecido; use draft, ready, sent, fixing, retesting, fixed, risk_accepted: "status:open" (posição 13) |

## 4. In reports (not built yet)

A report is Markdown with `chart` blocks. When the report is generated for a period, `$periodo` becomes that period (`01-08-2026..31-10-2026`), and the numbers are **frozen** in the report: editing a finding later does not change a report already issued.

````markdown
## Remediação no trimestre

```chart
count by severity over fixed per week where fixed:$periodo as bar title "Corrigidas por semana"
```

```chart
median days sent..fixed by severity where fixed:$periodo as table title "Mediana de dias até a correção"
```
````

## 5. Rules

- **Computed in the API**, never in the browser, and never turned into SQL text: the API loads the few chart fields of every live finding once per request and computes each chart from them. Periods and buckets use the portal's time zone (`PORTAL_TIMEZONE`, default `America/Sao_Paulo`).
- **Who:** admins and the **dashboard** role. A dashboard account reaches nothing else in the portal. Every dashboard is shared by those accounts, and the counts cover every finding.
- **Aggregates only.** No query lists findings or shows an identifier, host or description.
- **Screens.** A dashboard is a list of screens, each with an optional title and its charts (up to 10 screens, 24 charts in all). The portal shows one at a time with *Anterior* / *Próxima*; a TV loops over them, one every `rotate_seconds` (5 s to 10 min). Both recompute every `refresh_seconds` (30 s to 1 h), set per dashboard.
- **A chart that can't run is not saved.** The editor previews each query as it is typed (`POST /dashboards/preview`) and says whether it can go on a TV.
- **TV links** (read-only, no sign-in, revocable, recorded in the audit log, last use shown) accept only `status`, `severity` and `source` groupings, checked when the link is made and again at every refresh; a chart that fails shows as *unavailable*. The token is shown once and stored as a hash. A board computes with the access of the person who made the link and stops when that account is deactivated or loses the role. The TV receives titles and numbers, never the queries or the variables.
- **One filter grammar.** The Hub filter runs in the browser (`frontend/src/filterQuery.js`); the API has the same rules in Python. `backend/tests/test_dashboards.py` and `e2e/tests/dashboards.spec.js` check the same cases on each side.
- **No code from users.** Running user-written Python on the server would hand its author the API's database access, past the role and TV rules. More control over charts would come as more clauses, not code.

## 6. Open questions

Decided: who writes queries (admins and the dashboard role), no `status:open` shortcut, no SLA for now.

3. **Comparisons:** "87 open, 5 more than last week" is a common TV need. A later `vs previous` clause could compare a period with the one before it.
4. **Backlog over time:** "how many were open at the end of each week" is not a count of one date, so the grammar can't say it yet. A later `open … per week` measure could.
5. **Several series from different dates** ("found vs fixed per month") would need two queries in one chart.
6. **SLA targets** (none for now). With remediation deadlines per severity, a `within sla` measure (share fixed on time) would be the most useful chart of all.
7. **Reports** (§4): chart blocks with frozen numbers.
