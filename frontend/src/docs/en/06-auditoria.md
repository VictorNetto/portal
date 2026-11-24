<!-- page: auditoria -->
# Audit logs

The portal records almost everything that happens in it: sign-ins, creations, changes, status changes, sendings, exports, attachment reads and reservation releases. Each entry says who acted (a person, an API key, shown as `api:<prefix>`, or the system itself), when, from which IP address and what exactly changed. That record is what lets you answer, months later, who sent a report, who opened a piece of evidence or why a status changed.

The logs live in the menu under **Audit Logs**, and only administrators and auditors see them. The page is a list, from the newest entry to the oldest. Clicking a row shows the entry's full detail and a shortcut to open the record it is about.

<!-- page: auditoria-filtros -->
# Filtering the logs

The logs' filter box works like the one in Operations: free text and keyed filters, which combine, and `/` to see the list of keys. The difference is that here free text searches everything: the actor, the action, the record, the detail and the IP.

| Filter | Shows |
|---|---|
| `action:update,delete` | Entries for one of those actions |
| `actor:maria` | What a person did, by username, display name or full name |
| `actor:api:<prefix>` | What an API key did; `actor:system`, what the portal itself did |
| `entity:report` | Entries about one kind of record; `entity:none`, those about no record |
| `record:VULN-0012` | Everything about one record, by internal ID or UUID, its attachments included |
| `date:7d` | When it happened, with the same periods as Operations, such as `date:10-2026` |

**More filters…** holds `role:admin`, the role of whoever acted, `ip:10.0.`, the source address, and `detail:password`, which searches the entry's detail.

As in Operations, a `-` before the key excludes what matches, and quotes allow values with spaces. There is also a shortcut: clicking a value in the list, such as an actor, an action, a kind, a record or an IP, filters by it.

The search is kept in the page's address. To show someone exactly what you are looking at, copy the link.
