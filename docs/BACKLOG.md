# Backlog

Features and decisions that were discussed and deliberately parked. Newest first.
When one is picked up, move its outcome to `DECISIONS.md` and delete it here.

---

## Report template management (next)

First version built (D11): save from a report, pick on creation, private + admin-shared.
Still to decide/build:
- Rename, edit the content, delete (reports keep their copy either way).
- Admin UI to share / unshare an existing template (the API already has `PATCH /report-templates/{id}`).
- A dedicated "Templates" page, or management inside the picker menu?
- Placeholders such as `{cliente}`, `{inicio}`, `{fim}` filled in on creation.
- Images in templates (logo, diagrams) — needs template-owned attachments.
- Related idea: a *vulnerability library* (reusable findings) sharing the same management page.

---

## Other parked items

- **Permission / state constraints catalogue** (~45 items: delete rules by status,
  ownership, who may dispatch, login throttling, session revocation, API-key role limits…).
  Waiting on the owner's decisions.
- **Operators limited to users who can edit?** Today a read-only user can be made an
  operator (the ingest API already refuses this). Recommended: operators = admin / editors
  only; readers get access through "Compartilhado com".
- **Date filters in the Hub** (`created:`, `updated:`, relative `7d`, status dates).
  Waiting on the team.
- **Real email dispatch:** SMTP details and recipients (or Azure ACS).
- **UI theme refinement** (the e2e suite protects against regressions).
- **Ultrawide screens:** optionally cap the page width above ~2560px.
- **Test hygiene:** a browser test leaves one untitled draft vulnerability per run.
