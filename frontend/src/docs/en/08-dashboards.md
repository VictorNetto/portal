<!-- page: dashboards -->
# Dashboards

A dashboard answers questions about the vulnerabilities as a whole: how many are open, how many were fixed each month, how long the defense team takes to accept a finding. It is made of charts, and each chart is described by **one line of text**, the query, which says what to count, how to group it and how to draw it.

A dashboard's numbers are always **counts and durations**. No chart shows a vulnerability, an identifier or a host, which is why a dashboard can be seen by people who don't have access to the vulnerabilities themselves, such as Dashboards accounts, or be put up on a TV.

## The list and the editor

Dashboards live in the menu under **Dashboards**. The list is shared between administrators and Dashboards accounts: everyone sees and edits the same dashboards. **Edit** opens the editor, with the dashboard's name, its [variables](#dash-variaveis) and the queries. Each query has a preview next to it, which updates as you type, so you see the chart take shape before saving. A dashboard with a wrong query isn't saved: the message says what is wrong and where in the line.

## Screens

A dashboard can have several **screens**, each with its own charts and an optional title, to keep subjects apart: one screen for what is open, another for fix times. On the dashboard's page, **Previous** and **Next**, or the ← and → keys, move between screens, and the address keeps the screen you are on, as in `?tela=2`.

## Refreshing

The numbers are recomputed from time to time. In the editor, **Refresh the numbers every** sets that interval, from 30 seconds to 1 hour, for the page and the TV, and **On a TV, change screens every** sets how long the TV shows each screen, from 5 seconds to 10 minutes. On the page, **Refresh** recomputes at once.

<!-- page: dash-consultas -->
# Writing queries

A query is a short sentence with a fixed shape:

```
<measure> [by <group>[, <group>]] [over <date> per <unit>] [where <filter>] [top N] [as <chart>] [title "…"]
```

Only the measure is required. The other parts can come in any order, each at most once. Let's build a query bit by bit, to see what each part does.

## The measure

The simplest query is `count`: a number, with how many vulnerabilities there are. Instead of counting, the measure can also be a duration between two dates of the same vulnerability. `median days sent..fixed` is the median, in days, between sending and fixing. Besides `median`, there are `avg`, `min`, `max` and percentiles such as `p90`. A duration computed from fewer than three vulnerabilities shows as "—", because a number like that would say little.

The dates a duration can use are the same as the filters': `created`, `updated`, `sent`, `accepted`, `fixing`, `retesting`, `fixed` and `risk`.

## Filtering with where

`where` limits what is counted, with the **same filter as the Operations page**. `count where status:sent,fixing,retesting` counts the open vulnerabilities; the comma in `status:` means "one or the other". There is one difference from Operations: there, a filter that can't be read is ignored, and here it is an error, because a chart computed over the wrong filter would show a wrong number without warning.

## Grouping with by

`by` splits the count into groups. `count by severity where status:sent,fixing,retesting` shows the open ones by severity. The possible groups are `status`, `severity`, `source`, `report` and `operator`. Severity comes from the CVSS: critical from 9, high from 7, medium from 4 and low above 0. With two groups, as in `by report, severity`, the bars are stacked, or the result becomes a cross table.

When there are many groups, `top 6` shows the six largest of the first `by` and adds up the rest as "Other".

## Over time with over

`over` creates a time axis: `count over fixed per month` counts the vulnerabilities fixed in each month. The units are `day`, `week`, `month`, `quarter`, `semester` and `year`. The axis's period is the filter's on the same date, so `count over fixed per month where fixed:12m` shows the last twelve months. The axis always starts on a whole unit, such as a full month, week, quarter or semester.

## The look

`as` chooses the kind of chart: `number`, `bar`, `hbar` (horizontal bars), `line` or `table`. Without `as`, the portal picks what fits the query. Finally, `title "Open"` gives the chart a title.

<!-- page: dash-exemplos -->
# Examples

Looking at ready-made queries is the quickest way to pick up the language. The examples on this page go from the simplest to the most elaborate, and all of them can be pasted into the editor and adjusted.

A big number with the total of open vulnerabilities is a good start for any dashboard:

```
count where status:sent,fixing,retesting title "Open"
```

Combining a status with an inverted date filter, the number starts watching a problem: the vulnerabilities sent more than fifteen days ago that the defense team hasn't accepted yet.

```
count where status:sent -sent:15d title "Awaiting acceptance for over 15 days"
```

To see how the open ones are spread, group by severity. To see which reports hold the most problems, group by report and severity, showing the six largest as horizontal bars:

```
count by severity where status:sent,fixing,retesting
count by report, severity top 6 where status:sent,fixing,retesting as hbar
```

With `over`, the question becomes one of pace. The first chart below shows how many vulnerabilities were fixed in each of the last twelve months, by severity, and the second compares semesters by the number sent:

```
count by severity over fixed per month where fixed:12m as bar title "Fixed per month"
count by severity over sent per semester where sent:25S2..26S2 as bar title "Sent per semester"
```

Durations answer how long things take. The first query below shows, in a table, the median days between sending and fixing for each severity, over the last year. The second shows within how many days nine in ten sent vulnerabilities were accepted, quarter by quarter:

```
median days sent..fixed by severity where fixed:1y as table
p90 days sent..accepted over sent per quarter
```

Finally, a number fixed to a period, useful for a semester review:

```
count where sent:26S1 title "Sent in 26S1"
```

<!-- page: dash-variaveis -->
# Variables

Some parts of a query repeat across several charts, or change often. The list of statuses that counts as "open" appears in almost every dashboard, and the period of interest may be the last quarter today and the last year tomorrow. A **variable** holds a piece like that, so it is written only once.

Create the variable in the editor, with a name and a value, such as `open` with the value `sent,fixing,retesting`, or `period` with the value `3m`. Then write `$name` in the query:

```
count where status:$open fixed:$period
```

The value replaces `$name` before the query is read, titles included. On the dashboard's page, viewers can change the values and click **Apply**, and the change applies to that view only. To change a value for good, edit the dashboard.

<!-- page: dash-tv -->
# TV links

A dashboard can be put up on a TV in the room without anyone signing in on it. On the dashboard's page, **New TV link** creates an address that shows the dashboard full screen, dark and without signing in. Open that address in the TV's browser: it goes through the screens in turn and recomputes the numbers at the intervals set on the dashboard. A change made to the dashboard reaches the TV at its next refresh.

The link is shown once only, right after it is created, so copy it at once. If you lose it, create another and revoke the old one.

## What the TV can show

A TV sits where people pass who don't necessarily have access to the portal, so a TV link is stricter than the dashboard. It only accepts groupings by **status**, **severity** and **source**: no report or person name reaches the TV. The editor says which queries are left out, and a chart that stops being accepted after the link exists shows as unavailable on the TV. The TV also receives neither the queries nor the variables, only the numbers and the titles.

## Turning a link off

**Revoke** turns the link off at once. It also stops working if the dashboard is deleted or its creator loses access. Creating and revoking links is kept in the audit logs, and the list of links shows when each one was last opened.
