# Backlog

Features and decisions that were discussed and deliberately parked. Newest first.
When one is picked up, move its outcome to `DECISIONS.md` and delete it here.

---

## Report templates (parked 2026-10-08)

Let a user start a report with pre-filled text instead of empty inputs.

**Proposed design**
- A template holds: executive summary, introduction, scope, test type, test model,
  environment, demand origin, and free-form sections (title + text, ordered).
  Not included: client, dates, operators, sharing, vulnerabilities, internal notes.
- Chosen in the "Criar Relatório" card (a default one pre-selected).
- **Copied, not linked:** editing or deleting a template never changes existing reports.
  The report keeps a reference to the template it came from.
- A "Modelos" page to list / create / edit / deactivate / duplicate templates,
  reusing the Markdown and section editors.
- The executive-summary text currently hard-coded in `backend/app/services/report.py`
  (`DEFAULT_EXECUTIVE_SUMMARY`) becomes a seeded "Padrão" template.

**To build:** one table (sections stored inside it) + a template reference on reports;
CRUD API (audited, server-enforced permissions); report creation accepts a template;
the "Modelos" page and nav item; picker on the create card; i18n; API + browser tests.

**Impact:** none on the lock, dispatch, exports, restricted roles, vulnerability list or
RVS queue. A report made from a template is an ordinary report.

**Open decisions**
1. Who manages templates: admins only (recommended) or `write_all` too?
2. Placeholders such as `{cliente}`, `{inicio}`, `{fim}` filled in on creation? (cheap, useful)
3. Images in templates (logo, diagrams)? Recommended: text-only first.
4. Apply only on creation (recommended), or also "load template" on an existing draft?

**Related follow-up:** a *vulnerability library*: reusable findings (title, CWE,
description, mitigation, references) to create vulnerabilities from. Often more valuable
than report templates; would share the management page.

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
