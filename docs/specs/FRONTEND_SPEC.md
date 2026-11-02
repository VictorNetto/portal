# Red Team Operations Platform — Frontend Specification (MVP Draft)

> **Status names:** this document predates **D14** (`docs/DECISIONS.md`). Read `saved_local` as `ready`,
> `dispatched` as `sent`, `acknowledged`/`waiting_fix` as `fixing`, `pending_retest` as `retesting`;
> `dispatching` is no longer a status (now the `reports.sending` flag).

## Overview

Frontend specification for the Red Team Operations Platform MVP, aligned with the system specification. The frontend is a Vue SPA with Tailwind CSS and an API-driven shell. This document defines the current visual language, routes, pages, components, interaction rules, state rules, and API calls for the currently prototyped screens.

**Frontend stack:** Vue SPA · Tailwind CSS · REST API integration · JWT-authenticated requests.

**Current scope:** authenticated shell, Operations Hub, vulnerability/report list switching, row actions, batch actions, bottom details panel, create vulnerability page, and reusable Markdown Editor component.

---

## 0. Terminology

- **Operations Hub** — first page shown after login; main workspace for vulnerabilities and reports.
- **Collapsed menu** — default left navigation rail with icons only.
- **Expanded menu** — transient overlay state of the same left navigation component.
- **Bottom details panel** — docked preview panel opened from a list row click or row `Visualizar` action.
- **Batch actions** — actions applied to one or more selected list rows.
- **Row actions** — actions opened from the three-dots button in the `Ações` column for a single row.
- **Markdown Editor** — standardized multiline Markdown input with edition and visualization modes.
- **Edition mode** — Markdown Editor mode where the user edits raw Markdown text.
- **Visualization mode** — Markdown Editor mode where Markdown is rendered as read-only preview.

---

## 1. Scope

This frontend draft covers:
- application shell;
- console-like visual system;
- authenticated SPA routes;
- Operations Hub page;
- vulnerabilities / reports list switching;
- left navigation behavior;
- fixed-width list columns;
- checkbox selection and select-all behavior;
- batch actions;
- row-level three-dots actions;
- pagination;
- bottom details panel behavior;
- create vulnerability page;
- Markdown Editor component;
- minimal API contract required by these screens.

This draft does **not** yet define:
- full report creation UI;
- full vulnerability detail page;
- full report detail page;
- report editor;
- RVS queue page;
- audit log page;
- user management page;
- API key management page;
- responsive/mobile rules.

---

## 2. Application Shell

### 2.1 Global Regions

The authenticated SPA uses these persistent regions:
1. **Top header** — fixed, full width.
2. **Left navigation rail** — fixed below the header.
3. **Main content area** — fills remaining space.
4. **Transient overlays** — expanded menu, dropdowns, action menus, bottom details panel.

### 2.2 Top Header

The top header is persistent on all authenticated routes.

**Contents:**
- hamburger button;
- shield/system icon;
- system brand;
- language selector;
- notification icon;
- current user menu.

**Brand text:**
- PT-BR: `Portal Red Team`
- EN: `Red Team Portal`

**Visual rule:**
- header uses an opaque background color;
- header shall not use transparency or backdrop blur.

### 2.3 Left Navigation

The left navigation starts immediately below the header and extends to the bottom edge of the viewport.

#### Collapsed state
- default state;
- icon-only rail;
- fixed width;
- no text labels visible;
- delayed tooltip on hover;
- no left margin;
- no bottom margin;
- explicit visual separation from page content through a subtle right separator and side shadow.

#### Expanded state
- same component widened horizontally;
- icon positions do not move between collapsed and expanded states;
- labels are revealed to the right of the fixed icon rail;
- overlays all page content instead of resizing or pushing content;
- usable over the central panel and bottom details panel;
- soft shadow indicates elevation;
- closes when user clicks elsewhere in the page.

#### Navigation items
- Central Operacional / Operations Hub
- Criar Vulnerabilidade / Create Vulnerability
- Criar Relatório / Create Report
- Fila RVS / RVS Queue
- Logs de Auditoria / Audit Logs
- Usuários / Users
- Chaves de API / API Keys
- Configurações / Settings

Role-based filtering is deferred.

---

## 3. Visual System

### 3.1 Theme

The MVP theme is **console-like / terminal-like**.

**Visual goals:**
- premium modern terminal look;
- dark graphite / green-black background;
- restrained phosphor-green accents;
- subtle cyan support accents;
- off-white and pale green-gray text;
- thin typography;
- thin borders;
- compact operational density.

### 3.2 Color Principles

#### Base surfaces
- app background: very dark graphite / green-black;
- panels: slightly lighter dark surface;
- header and left rail: darkest surface tier;
- overlays: dark surface with shadow.

#### Accent colors
- primary accent: terminal green;
- secondary accent: muted cyan;
- warning: amber/orange;
- danger/high severity: restrained red-orange;
- success/resolved: muted green;
- neutral text: off-white / pale gray-green.

#### Unified value color rule
These fields use one shared accent color everywhere:
- identifier;
- operators;
- source.

They must not use separate colors.

### 3.3 Borders and Separators

- all borders are thin;
- left menu has an explicit but subtle separation from the page content;
- expanded sidebar uses shadow as primary elevation cue;
- panels use subtle contrast, not heavy outlines;
- bottom details panel uses subtle top shadow only;
- unnecessary separator lines are avoided.

### 3.4 Typography

- monospaced or monospaced-inspired text is preferred for operational content;
- fonts remain thin and compact;
- headings use medium emphasis;
- labels use low-to-medium emphasis;
- values use medium emphasis.

### 3.5 Spacing

- compact toolbar spacing;
- compact table rows;
- moderate panel padding;
- no excessive vertical whitespace;
- column separation may use whitespace instead of separators.

### 3.6 Radius

- subtle rounded corners for panels, buttons, inputs, pills, menus, and editor surfaces;
- no large rounded-card visual style.

### 3.7 Transitions

- menu expand/collapse: 150–220 ms;
- hover states: 120–180 ms;
- table row highlight: 120–180 ms;
- bottom panel open/close: 160–220 ms;
- no spring or bouncy motion.

### 3.8 Scrollbars

Scrollbars use the same console-like style as the rest of the page:
- thin scrollbar width;
- dark track;
- green-accent thumb;
- rounded thumb;
- hover state slightly increases accent intensity.

---

## 4. SPA Routes

### 4.1 Authenticated Routes

```text
/                         -> redirect to /hub after login
/hub                      -> Operations Hub
/vulnerabilities/new      -> Create Vulnerability page
/reports/new              -> Create Report page
/vulnerabilities/:id      -> Vulnerability details page
/reports/:id              -> Report details page
/vulnerabilities/:id/edit -> Edit Vulnerability page or create page in edit mode
/reports/:id/edit         -> Edit Report page
```

### 4.2 Route Rules

- successful login redirects to `/hub`;
- `Criar Vulnerabilidade` navigates to `/vulnerabilities/new`;
- `Criar Relatório` navigates to `/reports/new`;
- `Detalhar` in the bottom panel navigates to the selected item detail route;
- row-level `Editar` navigates to the selected item edit route;
- list mode switching may be state-only for MVP.

### 4.3 Recommended Query State

```text
/hub?entity=vulnerabilities
/hub?entity=reports
```

Filter state may later be encoded in the query string.

---

## 5. Operations Hub Page

### 5.1 Purpose

`/hub` is the first page after login and the main operational workspace for switching between vulnerabilities and reports.

### 5.2 Main Regions

- page title;
- entity switcher;
- contextual toolbar;
- create button;
- central list panel;
- pagination controls;
- optional bottom details panel.

### 5.3 Page Title

**PT-BR:** `Central Operacional`

### 5.4 Entity Switcher

Text buttons at the top-left of the central workspace:
- `Vulnerabilidades`
- `Relatórios`

Rules:
- buttons are visually close together;
- active item is highlighted;
- switching changes the central list, current create button label, pagination dataset, and contextual behavior.

### 5.5 Contextual Toolbar

Controls shown to the right of the entity switcher:
- `Filtros`;
- batch `Ações`, visible only when one or more rows are selected;
- contextual create button.

Create button labels:
- `Criar Vulnerabilidade`
- `Criar Relatório`

Visual rule:
- create button has fixed width so switching between vulnerability and report modes does not shift the toolbar.

### 5.6 Vulnerabilities List

Columns:
- selection checkbox;
- Identificador;
- Status;
- CVSS;
- Operadores;
- Fonte;
- Ações.

The internal ID is not displayed in this current UI iteration.

### 5.7 Reports List

The reports list follows the same structural behavior and same fixed column widths as the vulnerabilities list.

Minimum columns:
- selection checkbox;
- report name or identifier;
- status;
- risk/severity placeholder or equivalent field;
- operators;
- source/client/origin;
- actions.

### 5.8 Fixed Column Widths

The list table uses fixed column widths. Switching between vulnerabilities and reports must not resize columns or shift layout.

Rules:
- table layout is fixed;
- long values are truncated with ellipsis;
- identifier, operators, and source/client columns preserve their widths between modes.

### 5.9 Row Click Zones

#### Checkbox zone
- toggles checkbox selection only;
- does not open the bottom details panel.

#### Row body zone
- opens the bottom details panel for the clicked item.

#### Three-dots zone
- opens the single-row action menu;
- does not open the bottom details panel unless the user chooses `Visualizar`.

### 5.10 Selection State

- checkbox selection and preview state are independent;
- selected rows receive a subtle selected-state background;
- previewed row receives a subtle preview-state background;
- selecting checkboxes does not open the bottom panel.

### 5.11 Select All

The checkbox in the table header selects or deselects all visible rows on the current page.

Rules:
- when all visible rows are selected, the header checkbox is checked;
- when some visible rows are selected, the header checkbox is indeterminate;
- selection persists when moving between pages in the current entity mode;
- switching between `Vulnerabilidades` and `Relatórios` clears current selection.

### 5.12 Pagination

The list includes pagination controls below the table.

Controls:
- current range label, e.g. `Mostrando 1-5 de 12`;
- page size selector;
- previous button;
- numbered page buttons;
- next button.

Rules:
- page size changes reset to page 1;
- previous/next buttons are disabled at boundaries;
- pagination does not resize the central list columns.

---

## 6. Actions

### 6.1 Batch Actions

Batch `Ações` appears only when one or more rows are selected.

Current batch actions:
- `Exportar`;
- `Disparar`;
- `Excluir`.

Rules:
- batch actions apply to selected rows only;
- `Visualizar` and `Editar` are not batch actions;
- `Excluir` must require confirmation before destructive execution.

### 6.2 Row Actions

Each row has a vertical three-dots button in the `Ações` column.

The row action menu contains:
- `Editar`;
- `Visualizar`;
- `Exportar`;
- `Disparar`;
- `Excluir`.

Rules:
- row actions apply only to the row that owns the clicked three-dots button;
- `Visualizar` opens the bottom details panel for that row;
- `Editar` opens the edit flow for that row;
- `Exportar` exports that single item;
- `Disparar` dispatches that single item, subject to lifecycle permissions;
- `Excluir` requires confirmation before destructive execution.

### 6.3 Row Action Menu Placement

The row action menu is positioned dynamically near the pointer.

Rules:
- menu appears side-by-side with the mouse cursor where possible;
- menu opens to the right of the cursor unless there is not enough viewport space;
- if there is not enough room on the right, menu opens to the left;
- menu is vertically centered around the pointer as much as possible;
- menu is clamped inside the viewport;
- clicking outside the menu closes it;
- clicking another three-dots button closes any open row menu and opens the new row menu.

---

## 7. Bottom Details Panel

### 7.1 Purpose

Docked preview surface for the currently clicked or visualized list item.

### 7.2 Open Behavior

The panel opens when:
- user clicks a row outside the checkbox and row action areas;
- user chooses `Visualizar` from a row action menu.

### 7.3 Position and Size

- docked to the bottom edge of the viewport;
- height: approximately 30% of the page height;
- starts immediately after the collapsed left menu rail;
- extends to the right edge;
- overlays the main list panel;
- does not resize, shrink, or reflow the main list panel.

If the left menu is expanded, it overlays the bottom details panel as well.

### 7.4 Top Area

The panel uses a single uniform background. There is no separate header color and no horizontal separator line.

Top-area contents:
- left: selected item identifier value;
- right: `Detalhar` button with eye icon;
- far right: close `X` button.

### 7.5 Content Layout

Three columns separated by whitespace only.

#### Column 1 — Activity
Shows lifecycle activity and status transitions.

Examples:
- Criado
- Salvo Localmente
- Despachado
- Reconhecido
- Aguardando Correção

Each entry may show timestamp, actor, and supplemental note.

#### Column 2 — Core details
Shows:
- Status;
- CVSS;
- Descrição.

#### Column 3 — Origin / ownership
Shows:
- Fonte;
- Operadores.

### 7.6 Closing Rules

The panel closes when:
- user clicks `X`;
- route changes;
- optionally user presses `Esc`.

### 7.7 Navigation Rule

`Detalhar` opens the full detail route for the selected item.

---

## 8. Create Vulnerability Page

### 8.1 Route

```text
/vulnerabilities/new
```

### 8.2 Entry Point

Opened when the user clicks `Criar Vulnerabilidade` from the Operations Hub toolbar or left navigation.

### 8.3 Shell Behavior

The app shell remains unchanged:
- same top header;
- same collapsed left rail by default;
- same console-like theme;
- central panel changes from list mode to form mode.

### 8.4 Page Header

Recommended structure:
- breadcrumb: `Central Operacional > Vulnerabilidades > Criar Vulnerabilidade`;
- page title: `Criar Vulnerabilidade`;
- helper text;
- top-right page actions.

### 8.5 Page Actions

- `Cancelar`
- `Enviar`
- `Salvar rascunho`

### 8.6 Form Structure

#### Section: Informações Gerais
Fields:
- Identificador;
- CWE;
- CVSS;
- Fonte;
- Operador.

#### Section: Descrição
Uses the Markdown Editor component.

#### Section: Detalhes do Achado
Uses the Markdown Editor component.

#### Section: Mitigação / Solução
Uses the Markdown Editor component.

#### Section: Referências
- repeatable URL input rows;
- add/remove controls;
- does not use the Markdown Editor.

#### Section: Anexos
- drag-and-drop upload area;
- file picker behavior;
- empty-state list;
- supports image and non-image files.

#### Section: Notas Internas
Uses the Markdown Editor component.

### 8.7 Layout

The current desktop layout uses:
- top full-width general information panel;
- main left column for narrative Markdown fields and references;
- right column for attachments and internal notes.

### 8.8 Validation

- required fields validate on interaction or submit attempt;
- CVSS validates numeric range;
- save draft permits incomplete records;
- send requires mandatory dispatch-ready fields;
- submit buttons show loading state while request is pending.

---

## 9. Create Report Page

### 9.1 Route

```text
/reports/new
```

### 9.2 Current Scope

This route is defined as the target for `Criar Relatório`, but the detailed page design is deferred.

### 9.3 Requirement

The page must follow the same shell, visual language, route conventions, and component patterns used in the create vulnerability page.

---

## 10. Markdown Editor Component

### 10.1 Purpose

The Markdown Editor is the standard multiline text component for fields that store Markdown content.

### 10.2 Usage Locations

Current vulnerability creation usage:
- Descrição;
- Detalhes do Achado;
- Mitigação / Solução;
- Notas Internas.

Future usage:
- report narrative sections;
- report internal notes;
- other Markdown-based fields.

### 10.3 Modes

#### Edition mode
- activated by pencil icon;
- shows editable textarea/code-editor surface;
- line numbers are visible;
- Markdown formatting buttons are enabled.

#### Visualization mode
- activated by eye icon;
- swaps the textarea for a rendered Markdown preview;
- line numbers are hidden;
- Markdown formatting buttons are disabled;
- content is read-only.

### 10.4 Header / Toolbar

The editor header is a single integrated toolbar.

#### Mode group
The left side contains two grouped buttons:
- pencil icon;
- eye icon.

The active mode button uses the primary green accent.

#### Separator
After the mode group, add spacing and a subtle `|` separator.

#### Markdown buttons
After the separator, show:
- bold;
- italic;
- heading;
- bullet list;
- numbered list;
- code;
- link;
- image;
- quote.

Markdown buttons are disabled in visualization mode.

### 10.5 Editable Surface

Rules:
- fixed width inherited from parent layout;
- user cannot manually resize;
- no resize handle;
- height changes only through text insertion/removal;
- compact line height;
- left gutter with muted line numbers;
- line numbers represent logical lines only;
- visual wrap does not create a new line number.

### 10.6 Logical Line Counting

A logical line is created only by a newline character.

A long logical line that visually wraps at the right border remains one logical line. The wrapped continuation aligns to the text area, not to the line-number gutter.

### 10.7 Dynamic Height Rule

Let:

```text
n = number of logical text lines
```

For `n = 0` to `10`:

```text
visible_lines = n + 2
```

For `n >= 11`:

```text
visible_lines = 12
```

If content exceeds the visible area, a vertical scrollbar appears.

Examples:

```text
0 logical lines  -> 2 visible lines
1 logical line   -> 3 visible lines
5 logical lines  -> 7 visible lines
10 logical lines -> 12 visible lines
11+ lines        -> 12 visible lines + scrollbar as needed
```

### 10.8 Preview Surface

Visualization mode renders Markdown in a read-only preview surface.

Minimum supported render features:
- headings;
- paragraphs;
- bullet lists;
- numbered lists;
- inline code;
- code blocks;
- links;
- images;
- blockquotes.

### 10.9 Visual Rules

- toolbar and body are visually part of one component;
- surface background is uniform and dark;
- borders are thin;
- line-number gutter is muted;
- active mode uses green accent;
- disabled buttons are muted but recognizable;
- component remains compact and avoids excessive empty space.

---

## 11. API Calls

### 11.1 General Rules

- authenticated calls use bearer JWT tokens;
- API failures show inline errors where possible;
- toolbar refresh re-fetches the current dataset;
- preview panel calls are decoupled from list calls.

### 11.2 Vulnerabilities List

```http
GET /api/v1/vulnerabilities?view=hub&status=...&operator_id=...&source=...&page=...&page_size=...
```

Minimum response fields:
- id;
- identifier;
- status;
- cvss_score;
- operators[];
- source;
- selectable/actionable flags.

### 11.3 Reports List

```http
GET /api/v1/reports?view=hub&status=...&operator_id=...&page=...&page_size=...
```

Minimum response fields:
- id;
- name;
- status;
- operators[];
- client_name;
- start_date;
- end_date.

### 11.4 Vulnerability Preview

```http
GET /api/v1/vulnerabilities/{id}
```

Minimum preview fields:
- id;
- identifier;
- status;
- cvss_score;
- description;
- source;
- operators[];
- lifecycle timestamps;
- rvs_id when applicable.

Optional future endpoint:

```http
GET /api/v1/vulnerabilities/{id}/preview
```

### 11.5 Report Preview

```http
GET /api/v1/reports/{id}
```

Optional future endpoint:

```http
GET /api/v1/reports/{id}/preview
```

### 11.6 Create Vulnerability

```http
POST /api/v1/vulnerabilities
Content-Type: application/json
```

Minimum request body:
- identifier;
- cwe;
- cvss_score;
- source;
- operator_ids[];
- description;
- finding_detail;
- mitigation;
- references[];
- internal_notes;
- status = `draft` or `saved_local`.

### 11.7 Create Report

```http
POST /api/v1/reports
Content-Type: application/json
```

### 11.8 Attachment Upload

Recommended MVP contract:

```http
POST /api/v1/uploads
```

Alternative presigned pattern:

```http
POST /api/v1/uploads/presign
POST file directly to returned URL
POST /api/v1/attachments/commit
```

Attachment binding rule:
1. save draft;
2. receive entity ID;
3. upload files;
4. associate files to entity.

### 11.9 Action Endpoints

```http
POST /api/v1/vulnerabilities/{id}/dispatch
POST /api/v1/reports/{id}/dispatch
GET  /api/v1/vulnerabilities/{id}/export?format=pdf|docx
GET  /api/v1/reports/{id}/export?format=pdf|docx
DELETE /api/v1/vulnerabilities/{id}
DELETE /api/v1/reports/{id}
```

Batch forms of export, dispatch, and delete may be added later.

---

## 12. Frontend State Rules

### 12.1 Hub State

Local SPA state:
- active entity tab;
- filters;
- selected checkboxes;
- active preview item;
- bottom panel open/closed;
- pagination;
- row action menu open/closed;
- batch action menu open/closed.

### 12.2 Navigation State

- left menu collapsed by default;
- expanded menu is transient;
- outside click collapses expanded menu.

### 12.3 List / Preview Independence

- checkbox selection does not open preview;
- row preview does not select checkbox;
- action menu does not open preview unless `Visualizar` is selected.

### 12.4 Form Draft State

- create pages keep unsaved local state;
- route-leave warning is recommended for dirty forms;
- submit buttons lock during request;
- attachment upload may be disabled until first draft save returns an entity ID.

### 12.5 Markdown Editor State

Each Markdown Editor instance maintains:
- current mode (`edition` or `visualization`);
- current raw Markdown value;
- current logical line count;
- current visible line count;
- scroll position, when content exceeds 12 visible lines.

---

## 13. Internationalization

### 13.1 Supported Languages

- PT-BR
- EN

### 13.2 Current Visual Draft Language

The current visual drafts are PT-BR-first.

Header brand localization:
- PT-BR: `Portal Red Team`
- EN: `Red Team Portal`

---

## 14. Accessibility and UX Notes

- icon-only controls require accessible labels;
- collapsed sidebar icons require tooltips and keyboard labels;
- Markdown toolbar buttons require accessible names;
- row action menus must be keyboard reachable in the implementation phase;
- row menus must close on outside click;
- destructive actions must require confirmation;
- line numbers must not be read as editable content;
- visualization mode must expose rendered content semantically;
- disabled toolbar actions must be visually and programmatically disabled;
- contrast must remain strong in the dark theme;
- status pills must remain readable.

---

## 15. Deferred Items

Deferred from this draft:
- full report creation page;
- full vulnerability detail page;
- full report detail page;
- report lock UI;
- RVS queue page;
- audit logs page;
- user management page;
- API key page;
- responsive/mobile rules;
- full design-token sheet.

---

## 16. Change Log — Latest Prototype Update

### Added

- Opaque top header requirement.
- Console-style scrollbar requirements.
- Explicit sidebar/page separation requirement.
- Left navigation entries for `Criar Vulnerabilidade` and `Criar Relatório`.
- Fixed-width create button rule to avoid toolbar shift.
- Fixed-width table column rules.
- Pagination requirements.
- Select-all behavior for the list header checkbox.
- Batch `Ações` visibility rule: only visible when one or more rows are selected.
- Batch actions: `Exportar`, `Disparar`, `Excluir`.
- Row-level three-dots action menu with: `Editar`, `Visualizar`, `Exportar`, `Disparar`, `Excluir`.
- Row action menu dynamic placement rules near the mouse cursor.
- Row action outside-click close rule.
- Details panel overlay rule: the main list does not resize when the panel is open.

### Removed / Changed

- Removed standalone `Exportar` toolbar button.
- Removed `Editar` and `Visualizar` from batch actions.
- Changed `Operador` column to `Operadores`.
- Changed sidebar `Vulnerabilidades` / `Relatórios` entries to `Criar Vulnerabilidade` / `Criar Relatório`.
- Changed row action menu from static below-button positioning to dynamic side-by-side pointer positioning.
- Changed header from translucent to opaque.

---

## 17. Summary

The current frontend MVP draft consists of:
- persistent authenticated shell;
- console-like visual system;
- Operations Hub for vulnerabilities and reports;
- transient overlay left menu;
- paginated fixed-width lists;
- independent checkbox selection and preview behavior;
- separate batch and row action models;
- row action menu with dynamic pointer-based placement;
- bottom details panel from row clicks or `Visualizar`;
- create vulnerability page;
- reusable Markdown Editor with edition and visualization modes;
- route and API expectations for the current UI scope.
