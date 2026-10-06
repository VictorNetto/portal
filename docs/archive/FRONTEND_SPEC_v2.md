# Red Team Operations Platform — Frontend Specification (MVP Draft)

## Overview

A frontend specification for the Red Team Operations Platform MVP, aligned with the system specification. The frontend is a Vue SPA with Tailwind CSS and an API-driven shell. This document defines the current visual language, routes, pages, core components, state rules, interactions, and API calls for the pages currently designed.

**Frontend stack:** Vue SPA · Tailwind CSS · REST API integration · JWT-authenticated requests.

**Current scope:** authenticated shell, Operations Hub, vulnerability/report list switching, bottom details panel, create vulnerability page, and reusable Markdown Editor component.

---

## 0. Terminology

- **Operations Hub** — first page shown after login; main workspace for vulnerabilities and reports.
- **Collapsed menu** — default left navigation rail with icons only.
- **Expanded menu** — transient overlay state of the same left navigation component.
- **Bottom details panel** — docked preview panel opened from a list row click.
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
- row selection and bottom details panel behavior;
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
4. **Transient overlays** — expanded menu, dropdowns, action menus.

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
- no borders.

#### Expanded state
- same component widened horizontally;
- overlays all page content instead of resizing or pushing content;
- usable over the central panel and bottom details panel;
- no right border;
- soft shadow indicates elevation;
- closes when user clicks elsewhere in the page.

#### Navigation items
- Central Operacional / Operations Hub
- Vulnerabilidades / Vulnerabilities
- Relatórios / Reports
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
- overlays: dark translucent surface with shadow.

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
- operator;
- source.

They must not use separate colors.

### 3.3 Borders

- all borders are thin;
- sidebar expanded state uses shadow instead of border;
- panels use subtle contrast, not heavy outlines;
- bottom details panel uses subtle top shadow only;
- no unnecessary separator lines.

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

- subtle rounded corners for panels, buttons, inputs, pills, and editor surfaces;
- no large rounded-card visual style.

### 3.7 Transitions

- menu expand/collapse: 150–220 ms;
- hover states: 120–180 ms;
- table row highlight: 120–180 ms;
- bottom panel open/close: 160–220 ms;
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

- successful login redirects to `/hub`;
- `Criar Vulnerabilidade` navigates to `/vulnerabilities/new`;
- `Criar Relatório` navigates to `/reports/new`;
- `Detalhar` in the bottom panel navigates to the selected item detail route;
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
- switching changes the central list and contextual actions.

### 5.5 Contextual Toolbar

Controls shown to the right of the entity switcher:
- `Filtros`
- `Ações`
- `Exportar`
- contextual create button.

Create button labels:
- `Criar Vulnerabilidade`
- `Criar Relatório`

### 5.6 Vulnerabilities List

Columns:
- selection checkbox;
- Identificador;
- Status;
- CVSS;
- Operador;
- Fonte;
- Ações.

The internal ID is not displayed in this current UI iteration.

### 5.7 Reports List

The reports list follows the same structural behavior.

Minimum columns:
- selection checkbox;
- report name or identifier;
- status;
- operators;
- client;
- actions.

### 5.8 Row Click Zones

#### Checkbox zone
- toggles checkbox selection only;
- does not open the bottom details panel.

#### Row body zone
- opens the bottom details panel for the clicked item.

#### Three-dots zone
- opens contextual row actions;
- does not open the bottom details panel.

### 5.9 Selected Row State

- previewed row is subtly highlighted;
- checkbox selection and preview state are independent.

---

## 6. Bottom Details Panel

### 6.1 Purpose

Docked preview surface for the currently clicked list item.

### 6.2 Open Behavior

The panel opens when a user clicks a row outside the checkbox and row action areas.

### 6.3 Position and Size

- docked to the bottom edge of the viewport;
- height: approximately 30% of the page height;
- starts immediately after the collapsed left menu rail;
- extends to the right edge.

If the left menu is expanded, it overlays the bottom details panel as well.

### 6.4 Top Area

The panel uses a single uniform background. There is no separate header color and no horizontal separator line.

Top-area contents:
- left: selected item identifier value;
- right: `Detalhar` button with eye icon;
- far right: close `X` button.

### 6.5 Content Layout

Three columns separated by whitespace only.

#### Column 1 — Activity
Shows lifecycle activity and status transitions.

Examples:
- Criado
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
- Operador.

### 6.6 Closing Rules

The panel closes when:
- user clicks `X`;
- route changes;
- optionally user presses `Esc`.

### 6.7 Navigation Rule

`Detalhar` opens the full detail route for the selected item.

---

## 7. Create Vulnerability Page

### 7.1 Route

```text
/vulnerabilities/new
```

### 7.2 Entry Point

Opened when the user clicks `Criar Vulnerabilidade` from the Operations Hub.

### 7.3 Shell Behavior

The app shell remains unchanged:
- same top header;
- same collapsed left rail by default;
- same console-like theme;
- central panel changes from list mode to form mode.

### 7.4 Page Header

Recommended structure:
- breadcrumb: `Central Operacional > Vulnerabilidades > Criar Vulnerabilidade`;
- page title: `Criar Vulnerabilidade`;
- helper text;
- top-right page actions.

### 7.5 Page Actions

- `Cancelar`
- `Enviar`
- `Salvar rascunho`

### 7.6 Form Structure

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

### 7.7 Layout

The current desktop layout uses:
- top full-width general information panel;
- main left column for narrative Markdown fields and references;
- right column for attachments and internal notes.

### 7.8 Validation

- required fields validate on interaction or submit attempt;
- CVSS validates numeric range;
- save draft permits incomplete records;
- send requires mandatory dispatch-ready fields;
- submit buttons show loading state while request is pending.

---

## 8. Create Report Page

### 8.1 Route

```text
/reports/new
```

### 8.2 Current Scope

This route is defined as the target for `Criar Relatório`, but the detailed page design is deferred.

### 8.3 Requirement

The page must follow the same shell, visual language, route conventions, and component patterns used in the create vulnerability page.

---

## 9. Markdown Editor Component

### 9.1 Purpose

The Markdown Editor is the standard multiline text component for fields that store Markdown content.

### 9.2 Usage Locations

Current vulnerability creation usage:
- Descrição;
- Detalhes do Achado;
- Mitigação / Solução;
- Notas Internas.

Future usage:
- report narrative sections;
- report internal notes;
- other Markdown-based fields.

### 9.3 Modes

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

### 9.4 Header / Toolbar

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

### 9.5 Editable Surface

Rules:
- fixed width inherited from parent layout;
- user cannot manually resize;
- no resize handle;
- height changes only through text insertion/removal;
- compact line height;
- left gutter with muted line numbers;
- line numbers represent logical lines only;
- visual wrap does not create a new line number.

### 9.6 Logical Line Counting

A logical line is created only by a newline character.

A long logical line that visually wraps at the right border remains one logical line. The wrapped continuation aligns to the text area, not to the line-number gutter.

### 9.7 Dynamic Height Rule

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

### 9.8 Preview Surface

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

### 9.9 Visual Rules

- toolbar and body are visually part of one component;
- surface background is uniform and dark;
- borders are thin;
- line-number gutter is muted;
- active mode uses green accent;
- disabled buttons are muted but recognizable;
- component remains compact and avoids excessive empty space.

---

## 10. API Calls

### 10.1 General Rules

- authenticated calls use bearer JWT tokens;
- API failures show inline errors where possible;
- toolbar refresh re-fetches the current dataset;
- preview panel calls are decoupled from list calls.

### 10.2 Vulnerabilities List

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

### 10.3 Reports List

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

### 10.4 Vulnerability Preview

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

### 10.5 Report Preview

```http
GET /api/v1/reports/{id}
```

Optional future endpoint:

```http
GET /api/v1/reports/{id}/preview
```

### 10.6 Create Vulnerability

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

### 10.7 Create Report

```http
POST /api/v1/reports
Content-Type: application/json
```

### 10.8 Attachment Upload

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

### 10.9 Toolbar Actions

```http
POST /api/v1/vulnerabilities/{id}/dispatch
POST /api/v1/reports/{id}/dispatch
GET  /api/v1/vulnerabilities/{id}/export?format=pdf|docx
GET  /api/v1/reports/{id}/export?format=pdf|docx
```

---

## 11. Frontend State Rules

### 11.1 Hub State

Local SPA state:
- active entity tab;
- filters;
- selected checkboxes;
- active preview item;
- bottom panel open/closed;
- pagination.

### 11.2 Navigation State

- left menu collapsed by default;
- expanded menu is transient;
- outside click collapses expanded menu.

### 11.3 List / Preview Independence

- checkbox selection does not open preview;
- row preview does not select checkbox;
- action menu does not open preview.

### 11.4 Form Draft State

- create pages keep unsaved local state;
- route-leave warning is recommended for dirty forms;
- submit buttons lock during request;
- attachment upload may be disabled until first draft save returns an entity ID.

### 11.5 Markdown Editor State

Each Markdown Editor instance maintains:
- current mode (`edition` or `visualization`);
- current raw Markdown value;
- current logical line count;
- current visible line count;
- scroll position, when content exceeds 12 visible lines.

---

## 12. Internationalization

### 12.1 Supported Languages

- PT-BR
- EN

### 12.2 Current Visual Draft Language

The current visual drafts are PT-BR-first.

Header brand localization:
- PT-BR: `Portal Red Team`
- EN: `Red Team Portal`

---

## 13. Accessibility and UX Notes

- icon-only controls require accessible labels;
- collapsed sidebar icons require tooltips and keyboard labels;
- Markdown toolbar buttons require accessible names;
- line numbers must not be read as editable content;
- visualization mode must expose rendered content semantically;
- disabled toolbar actions must be visually and programmatically disabled;
- contrast must remain strong in the dark theme;
- status pills must remain readable.

---

## 14. Deferred Items

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

## 15. Summary

The current frontend MVP draft consists of:
- persistent authenticated shell;
- console-like visual system;
- Operations Hub for vulnerabilities and reports;
- transient overlay left menu;
- bottom details panel from row clicks;
- create vulnerability page;
- reusable Markdown Editor with edition and visualization modes;
- route and API expectations for the current UI scope.
