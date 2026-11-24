<!-- page: operacoes -->
# Operations: finding and exporting

Over time, the portal gathers hundreds of vulnerabilities and dozens of reports. The **Operations** page is where you find them. It has two tabs, one for vulnerabilities and one for reports, and each tab is a list with one row per record.

The list shows only the essentials. Clicking a row opens the details panel just below the list, with all the information and the timeline; the **Open** button goes to the record's page. To act on several records at once, tick the rows in the boxes on the left and use the **Actions** menu, which lets you export, send or delete. Records the chosen action can't apply to, such as a report already sent when deleting, are skipped, and the portal says which ones.

This chapter shows how to filter the list to find what you are looking for, by date too, and how to get documents out of the portal.

<!-- page: filtros -->
# Filtering the list

The **Filter** box at the top of the list takes free text and keyed filters. Free text searches the identifier: typing `sql` shows the vulnerabilities with "sql" in their name. To filter by something else, write a key, a colon and a value, such as `status:draft`. You don't need to remember the keys: type `/` and the portal shows the list.

| Filter | Shows |
|---|---|
| `status:draft` | Vulnerabilities in that status; `status:sent,fixing` takes more than one |
| `cvss:7` | Those with a CVSS of 7 or more |
| `report:name` | Those in a report whose name contains the text; `report:none`, those in no report |
| `operator:name` | Those with that person as an operator, by name or by username |
| `batch:BATCH-0001` | Those that came in that batch through the API; `batch:none`, those in no batch |

Terms combine, and all of them must hold at once: `status:sent cvss:7` shows the sent ones with a CVSS of 7 or more. A `-` before the key inverts the filter, and `-status:fixed` shows everything not fixed.

A filter's value runs up to the first space. If it has spaces, like a report's name, use quotes: `report:"Data Center Network"`.

At the end of the `/` menu, **More filters…** shows the less common filters, such as `source:nuclei`, which searches the finding's source, and the date filters, which have a page of their own.

<!-- page: filtros-datas -->
# Filtering by date

A vulnerability gathers dates along its path: when it was created, sent, accepted, fixed. Date filters use any of them and answer questions like "what was fixed in September?" or "what was sent more than fifteen days ago and still has no answer?".

A date filter has a key, which says which date to look at, and a value, which says the period.

| Key | The date |
|---|---|
| `created` | Creation |
| `updated` | Last change |
| `sent` | Sending |
| `accepted` | Acceptance by the defense team |
| `fixing` | Start of the fix |
| `retesting` | Retest request |
| `fixed` | Fix confirmed |
| `risk` | Risk accepted |

## Relative periods

The simplest way to give a period is to count back from today. `created:7d` shows what was created in the last seven days, today included (`1d` is just today). In the same way, `m` counts months and `y` counts years: `fixed:3m` is what was fixed in the last three months.

## Dates and ranges

For a fixed period, write dates. A date can be a day (`05-10-2026`), a month (`10-2026`), a year (`2026`), a semester (`26S1` or `2026S1`) or a quarter (`26T3`, or `26Q3`). A date on its own means that whole period: `fixed:10-2026` is everything fixed in October 2026.

For a range, put two dots between the start and the end. `fixed:01-09-2026..30-09-2026` runs from 1 to 30 September, both days included, and `fixed:09-2026..10-2026` covers all of September and October. Leaving one side empty opens the range: `sent:01-10-2026..` is from 1 October on, and `sent:..31-12-2025` is up to the end of 2025.

## Inverting the period

With a `-` in front, the period is inverted: `-updated:30d` shows what has *not* changed in the last thirty days. One detail: a vulnerability that doesn't have that date at all is included too, since it isn't inside the period. So inverted filters work best combined with a status. This filter shows the vulnerabilities sent more than fifteen days ago that are still waiting for an answer from the defense team:

```
status:sent -sent:15d
```

And this one, the drafts forgotten for a month:

```
status:draft -updated:30d
```

For reports, `created`, `updated` and `sent` apply. All dates follow your browser's time zone.

<!-- page: exportar -->
# Exporting documents

Sooner or later, what is in the portal has to become a file: to attach to an email, for a meeting, to archive. The **Export** button, on vulnerability and report pages, gathers the available formats. A vulnerability can be exported as PDF or Word. A report can be exported as PDF or Word, and also as Excel, with the spreadsheet of its vulnerabilities.

To export many records at once, use Operations: tick the rows and choose the export in the **Actions** menu. The result is a ZIP with one PDF per record, or one Excel spreadsheet with all of them.

Exported documents are the same ones the team responsible receives when something is sent, with the evidence images in place and without the sections marked as left out of the document (see [What a report contains](#rel-conteudo)). Internal notes never go into an exported file.
