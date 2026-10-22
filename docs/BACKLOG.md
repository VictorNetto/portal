# Backlog

Features and decisions that were discussed and deliberately parked. Newest first.
When one is picked up, move its outcome to `DECISIONS.md` and delete it here.

---

## Report template management — what is left

Built (D11): save from a report, pick on creation, Templates page with preview, edit, delete, and
reviewed sharing (owner requests → admin approves; admin unshares / reshares).
Still open:
- **Duplicar**: copy a shared template into my own list (the owner's way to keep working on a
  template once it is shared — today they would recreate it by hand).
- A reason when an admin rejects or unshares, shown to the owner; a notification for new requests.
- **Novo template** from scratch on the page.
- Placeholders such as `{cliente}`, `{inicio}`, `{fim}` filled in on creation.
- Images in templates: today an embedded image still points to the source report's attachment,
  so people without access to that report see it broken. Needs template-owned attachments.
- Related idea: a *vulnerability library* (reusable findings).

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
