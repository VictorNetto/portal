# Red Team Operations Platform — Frontend Specification (MVP Draft)

## Overview

A frontend specification for the Red Team Operations Platform MVP, aligned with the entity model and workflows defined in `SPEC 2.md`. The frontend is a Vue SPA with Tailwind CSS and an API-driven shell. This document defines the routes, pages, visual system, interaction rules, and API calls for the pages and components discussed in the design iteration. The scope of this draft is limited to the app shell, the main post-login workspace, the bottom details panel, and the vulnerability creation page. citeturn1search1

**Frontend stack:** Vue SPA · Tailwind CSS · REST API integration · JWT-authenticated requests. citeturn1search1

**Primary entities surfaced in the UI:** vulnerabilities and reports. citeturn1search1

---

## 0. Terminology

- **Operations Hub** — the first page shown after login; the main workspace for listing and switching between vulnerabilities and reports.
- **Bottom details panel** — the docked preview panel opened from a list row click.
- **Collapsed menu** — the default left navigation state showing icons only.
- **Expanded menu** — the transient overlay state of the same left navigation component.
- **Create Vulnerability page** — the page shown after clicking `Criar Vulnerabilidade`.
- **Create Report page** — the page shown after clicking `Criar Relatório`.

---

## 1. Scope

This frontend draft covers:
- app shell and global layout;
- Operations Hub page;
- vulnerabilities / reports list switching;
- left navigation behavior;
- row selection and bottom details panel behavior;
- create vulnerability page;
- SPA routes;
- minimal API contract required by these screens;
- visual system and interaction rules.

This draft does **not** yet define:
- full report editor;
- full vulnerability detail page contents;
- audit pages;
- user management pages;
- API key pages;
- lock-state UI beyond route placeholders.

---

## 2. Application Shell

### 2.1 Global Regions

The authenticated SPA uses four fixed layout regions:
1. **Top header** — fixed, full width.
2. **Left navigation rail** — fixed below the header.
3. **Main content area** — fills all remaining horizontal and vertical space.
4. **Transient overlays** — expanded left menu and future dropdowns / action menus.

### 2.2 Top Header

The top header is persistent across authenticated routes.

**Contents:**
- system brand;
- hamburger button;
- language selector;
- notification icon;
- current user indicator / menu.

**Brand text:**
- PT-BR: `Portal Red Team`
- EN: `Red Team Portal`

### 2.3 Left Navigation

The left navigation starts **below** the header and extends to the bottom edge of the viewport.

#### Collapsed state (default)
- icon-only rail;
- fixed width;
- no text labels visible;
- labels appear as delayed hover tooltips;
- no outer border.

#### Expanded state (overlay)
- the **same** navigation component widens horizontally;
- it overlays the content instead of pushing or resizing the content;
- it has no right border;
- it uses shadow only to indicate hierarchy above content;
- clicking outside the menu collapses it back to the icon-only state.

#### Navigation items (current shell)
- Operations Hub
- Vulnerabilities
- Reports
- RVS Queue
- Audit Logs
- Users
- API Keys
- Settings

These entries may be role-filtered later.

---

## 3. Visual System

### 3.1 Theme

The current MVP theme is **console-like / terminal-like**.

**Style goals:**
- premium modern terminal aesthetic;
- not retro neon;
- dark graphite / green-black surfaces;
- restrained phosphor-green accents;
- subtle cyan support accents;
- high legibility;
- thin and lightweight visual rhythm.

### 3.2 Color Principles

#### Base surfaces
- application background: very dark graphite / green-black;
- panel background: slightly lighter than page background;
- header and rail: darkest surface tier;
- overlays: same family as shell background with slightly elevated opacity and shadow.

#### Accent colors
- primary accent: terminal green;
- secondary accent: muted cyan;
- danger / high-severity values: restrained red-orange;
- warning values: restrained amber;
- success states: muted green;
- neutral text: off-white / pale green-gray.

#### Unified field color rule
The following fields use **one single shared accent color** across list rows and preview panels:
- identifier;
- operator;
- source.

These three fields must not use separate colors.

### 3.3 Borders

- all borders are thin;
- no heavy outlines;
- panels use subtle contrast rather than strong framing;
- the expanded left menu uses **shadow instead of border** to indicate overlay;
- the bottom details panel uses a subtle top shadow only.

### 3.4 Typography

- monospaced or monospaced-inspired headings are allowed;
- body text remains highly legible and compact;
- typography should appear thinner than the earlier light-theme mockups;
- headings: medium emphasis;
- labels: low-to-medium emphasis;
- values: medium emphasis.

### 3.5 Spacing

- compact toolbar rhythm;
- compact list rows;
- moderate inner panel padding;
- wider whitespace between content groups than between label/value pairs;
- the bottom details panel uses three columns separated by blank space only.

### 3.6 Radius

- subtle rounded corners on inputs, buttons, pills, and panels;
- no exaggerated radius.

### 3.7 Transitions

- menu expand / collapse: short fade-width transition, ~150–220 ms;
- hover states: short opacity / background transition, ~120–180 ms;
- table row highlight: short background transition, ~120–180 ms;
- bottom panel open / close: vertical slide + fade, ~160–220 ms;
- no spring or bouncy motion.

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
```

### 4.2 Route Rules

- after successful login, the user lands on `/hub`;
- `Criar Vulnerabilidade` navigates to `/vulnerabilities/new`;
- `Criar Relatório` navigates to `/reports/new`;
- `Detalhar` in the bottom panel navigates to the respective details route;
- changes of list mode on `/hub` do not require route changes in MVP; they are view-state changes inside the page.

### 4.3 Recommended Query State for `/hub`

```text
/hub?entity=vulnerabilities
/hub?entity=reports
```

Optional filter state may also be encoded in the query string when implemented.

---

## 5. Operations Hub Page

### 5.1 Purpose

`/hub` is the first page after login and the main operational workspace for switching between vulnerabilities and reports.

### 5.2 Main Regions

- page heading;
- entity switcher;
- contextual toolbar;
- create button;
- central list panel;
- optional bottom details panel.

### 5.3 Page Heading

**PT-BR:** `Central Operacional`

**Use:** the page title remains stable while the central panel content changes.

### 5.4 Entity Switcher

Text-buttons at the top-left of the central workspace:
- `Vulnerabilidades`
- `Relatórios`

Rules:
- the buttons are visually close together;
- the active item is highlighted;
- changing tabs swaps the list content and contextual toolbar behavior.

### 5.5 Contextual Toolbar

Shown on the same row as the entity switcher, aligned to the right.

Current controls:
- `Filtros`
- `Ações`
- `Exportar`
- `Criar Vulnerabilidade` or `Criar Relatório`

`Ações` is represented by a compact button; row-level actions use a vertical three-dots icon.

### 5.6 Central List Panel

The central panel fills the remaining page space under the page heading and toolbar.

#### Vulnerabilities mode
Columns:
- selection checkbox;
- Identificador;
- Status;
- CVSS;
- Operador;
- Fonte;
- Ações.

#### Reports mode
Columns are not yet visually detailed in this draft, but the structural behavior matches vulnerabilities mode:
- selection checkbox;
- report-identifying fields;
- status;
- operators;
- actions.

#### Current omission
The internal backend ID is intentionally **not displayed** in the current UI iteration.

### 5.7 Row Click Zones

#### Checkbox zone
- clicking the checkbox only toggles selection;
- it does **not** open the bottom details panel.

#### Row body zone
- clicking any row area outside the checkbox and outside row actions opens the bottom details panel for that item.

#### Three-dots zone
- clicking the row action icon opens row actions;
- it does **not** open the bottom details panel.

### 5.8 Selected Row State

- the selected row gets a subtle background highlight;
- selection state and preview state are independent;
- a row may be previewed without its checkbox selected.

---

## 6. Bottom Details Panel

### 6.1 Purpose

A docked preview surface for the currently clicked list item.

### 6.2 Open Behavior

The panel opens when the user clicks a row outside the checkbox area.

### 6.3 Position and Size

- docked to the bottom edge of the viewport;
- height: approximately 30% of the page height;
- horizontal start: immediately after the collapsed left menu rail;
- width: all remaining horizontal space.

If the left menu is expanded as an overlay, the menu floats above the bottom panel just like it floats above the central list panel.

### 6.4 Panel Top Area

The panel top area uses the **same background color** as the rest of the panel. There is:
- no separate header strip;
- no horizontal separator line;
- no visual division between header and content.

Top-area contents:
- left: selected item identifier value;
- right: `Detalhar` button with eye icon;
- far right: close `X` button.

### 6.5 Content Layout

The panel content is split into **three columns** separated only by whitespace.

#### Column 1 — Lifecycle activity
Compact timeline / activity list showing the item lifecycle transitions, for example:
- Criado
- Despachado
- Reconhecido
- Aguardando Correção

Each entry may show:
- timestamp;
- actor;
- supplemental note (for example, RVS ID when relevant).

#### Column 2 — Core details
Shows:
- Status;
- CVSS;
- Descrição.

#### Column 3 — Ownership / origin
Shows:
- Fonte;
- Operador.

### 6.6 Closing Rules

The panel closes when:
- the user clicks `X`;
- the route changes;
- optionally the user presses `Esc`.

### 6.7 Navigation Rule

`Detalhar` navigates to the full details route of the selected item.

---

## 7. Create Vulnerability Page

### 7.1 Route

```text
/vulnerabilities/new
```

### 7.2 Entry Point

Opened when the user clicks `Criar Vulnerabilidade` from the Operations Hub.

### 7.3 Shell Behavior

The app shell is unchanged:
- same top header;
- same collapsed left rail by default;
- same theme;
- central panel content changes from list mode to form mode.

### 7.4 Page Header

Recommended top structure:
- breadcrumb or contextual path;
- page title `Criar Vulnerabilidade`;
- short helper subtitle;
- top-right page actions.

### 7.5 Header Actions

Current actions:
- `Cancelar`
- `Salvar rascunho`
- optional `Enviar`

### 7.6 Form Structure

#### Section: Informações Gerais
Fields:
- Identificador
- CWE
- CVSS
- Fonte
- Operador

#### Section: Descrição
- large markdown-like textarea with toolbar.

#### Section: Detalhes do Achado
- large markdown-like textarea with toolbar.

#### Section: Mitigação / Solução
- large markdown-like textarea with toolbar.

#### Section: Referências
- repeatable URL rows;
- add and remove controls.

#### Section: Anexos
- upload surface for files;
- empty-state list;
- supports images and non-image files.

#### Section: Notas Internas
- markdown-like textarea;
- excluded from exports, but visibly editable in the page.

### 7.7 Form Layout

The current visual draft uses a central form with compact vertical sections and a secondary area for attachments / internal notes.

### 7.8 Validation

- required fields show validation only after interaction or submit attempt;
- numeric and format validation is inline;
- save-draft allows partially complete records;
- send requires all mandatory dispatch fields.

---

## 8. Create Report Page

### 8.1 Route

```text
/reports/new
```

### 8.2 Current Scope

This page exists as a route target from `Criar Relatório`, but the detailed visual definition is deferred in this draft.

### 8.3 Current Requirement

The page shall follow the same shell, theme, and route conventions as the create vulnerability page.

---

## 9. API Calls

### 9.1 General Rules

- all authenticated calls use bearer JWT tokens;
- API failures return non-blocking inline error states where possible;
- toolbar refresh and page reload must re-fetch the current dataset;
- list and preview calls should be decoupled so the preview panel can be loaded on demand.

### 9.2 Operations Hub — vulnerabilities list

#### Initial list load / refresh
```http
GET /api/v1/vulnerabilities?view=hub&status=...&operator_id=...&source=...&page=...&page_size=...
```

**Expected response fields (minimum):**
- id
- identifier
- status
- cvss_score
- operators[]
- source
- selectable / actionable flags

### 9.3 Operations Hub — reports list

```http
GET /api/v1/reports?view=hub&status=...&operator_id=...&page=...&page_size=...
```

**Expected response fields (minimum):**
- id
- name
- status
- operators[]
- client_name
- start_date
- end_date

### 9.4 Bottom details panel — vulnerability preview

```http
GET /api/v1/vulnerabilities/{id}
```

**Minimum fields needed by the panel:**
- id
- identifier
- status
- cvss_score
- description
- source
- operators[]
- lifecycle timestamps
- rvs_id when applicable

A dedicated preview endpoint may be introduced later if payload size becomes an issue:

```http
GET /api/v1/vulnerabilities/{id}/preview
```

### 9.5 Bottom details panel — report preview

```http
GET /api/v1/reports/{id}
```

A dedicated preview endpoint is also acceptable later:

```http
GET /api/v1/reports/{id}/preview
```

### 9.6 Create vulnerability — save draft

```http
POST /api/v1/vulnerabilities
Content-Type: application/json
```

**Minimum request body:**
- identifier
- cwe
- cvss_score
- source
- operator_ids[]
- description
- finding_detail
- mitigation
- references[]
- internal_notes
- status = `draft` or `saved_local`

### 9.7 Create report — create draft

```http
POST /api/v1/reports
Content-Type: application/json
```

### 9.8 Attachment upload

Since files are stored in MinIO behind backend-controlled URLs, the frontend should use a backend-mediated upload flow. citeturn1search1

Recommended MVP contract:

```http
POST /api/v1/uploads
```

or a two-step presigned pattern:

```http
POST /api/v1/uploads/presign
POST file directly to returned URL
POST /api/v1/attachments/commit
```

#### Attachment rule for create pages
For simplicity, attachments should bind to the entity **after** the first successful draft save returns an entity ID.

Recommended sequence:
1. user fills form;
2. frontend saves draft;
3. backend returns vulnerability ID;
4. frontend uploads files and associates them to the saved entity.

### 9.9 Toolbar actions (future-ready)

```http
POST /api/v1/vulnerabilities/{id}/dispatch
POST /api/v1/reports/{id}/dispatch
GET  /api/v1/vulnerabilities/{id}/export?format=pdf|docx
GET  /api/v1/reports/{id}/export?format=pdf|docx
```

These endpoints align with the dispatch and export flows already defined for the platform. citeturn1search1

---

## 10. Frontend State Rules

### 10.1 Hub View State

State managed locally by the SPA:
- active entity tab (`vulnerabilities` | `reports`);
- applied filters;
- selected checkboxes;
- active preview item;
- bottom panel open / closed;
- current page and page size.

### 10.2 Navigation State

- left menu collapsed by default;
- expanded state is transient;
- expanded state closes on outside click.

### 10.3 List / Preview Independence

- checkbox selection does not drive preview;
- preview does not imply checkbox selection;
- row action menus do not open preview.

### 10.4 Form Draft State

Create pages maintain unsaved local state until draft save succeeds.

Recommended protection:
- dirty-form warning on route leave;
- save lock while submit is in progress;
- attachment upload disabled until first successful draft save if files require an entity ID.

---

## 11. Internationalization

### 11.1 Supported Languages

Current shell strings shall support:
- PT-BR
- EN

### 11.2 Current UX Convention

The approved visual drafts are PT-BR-first. Header brand text localizes as:
- PT-BR: `Portal Red Team`
- EN: `Red Team Portal`

The language selector remains visible in the header on all authenticated routes.

---

## 12. Accessibility and UX Notes

- all icon-only controls require accessible labels;
- collapsed left rail icons require tooltip text on hover and keyboard focus labels;
- row click areas must remain clearly distinguishable from checkboxes;
- the bottom panel must not trap the user unexpectedly;
- contrast must remain strong even in the console-like theme;
- status pills must preserve readability in dark surfaces.

---

## 13. Deferred Items

Deferred from this draft:
- full report creation UI;
- full details pages for vulnerabilities and reports;
- report lock UI;
- RVS queue page UI;
- admin pages;
- responsive and mobile rules;
- keyboard shortcut map;
- full design token sheet.

---

## 14. Summary

The current frontend MVP draft consists of:
- a persistent authenticated shell;
- an Operations Hub listing vulnerabilities and reports;
- a transient overlay left menu;
- a bottom details panel opened from row clicks;
- a full create vulnerability page using the same shell and theme;
- formal route and API expectations for these screens.

This draft intentionally keeps the frontend surface small while staying aligned with the entity model, lifecycle-driven UI, file-upload flow, exports, and dispatch behaviors already defined in the platform specification. citeturn1search1
