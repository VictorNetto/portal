# Red Team Operations Platform — Frontend Specification (MVP Draft)

## Overview

Frontend specification for the Red Team Operations Platform MVP. The frontend is an authenticated SPA with a console-like visual language, operational list management, vulnerability/report workflows, and reusable Markdown editing components.

**Frontend stack:** Vue SPA · Tailwind CSS · REST API integration · JWT-authenticated requests.

**Current scope:** authenticated shell, Operations Hub, vulnerability/report list switching, row actions, batch actions, bottom details panel, create vulnerability page, Markdown Editor component, dynamic general information inputs, dynamic references, and related API expectations.

---

## 0. Terminology

- **Operations Hub** — first page shown after login; main workspace for vulnerabilities and reports.
- **Collapsed menu** — default left navigation rail with icons only.
- **Expanded menu** — transient overlay state of the same left navigation component.
- **Bottom details panel** — docked preview panel opened from a list row click or row `Visualizar` action.
- **Batch actions** — actions applied to one or more selected list rows.
- **Row actions** — actions opened from the three-dots button in the `Ações` column for a single row.
- **Markdown Editor** — standardized Markdown input consisting of a textarea for editing and a div for rendered preview.
- **Edition mode** — Markdown Editor mode where the user edits raw Markdown text.
- **Visualization mode** — Markdown Editor mode where Markdown is rendered as read-only preview.
- **Auxiliary multi-line view** — read-only hover view used by multi-value inputs such as Fontes and Operadores.

---

## 1. Application Shell

### 1.1 Global Regions

The authenticated SPA uses:

1. fixed top header;
2. fixed left navigation rail;
3. main content area;
4. transient overlays, including dropdowns, expanded menu, bottom details panel, row action menu, and auxiliary hover views.

### 1.2 Top Header

The top header is persistent on authenticated routes.

Contents:

- hamburger button;
- shield/system icon;
- system brand;
- language selector;
- notification icon;
- current user menu.

Rules:

- header uses an opaque dark background;
- header does not use transparency or backdrop blur;
- brand text is `Portal Red Team` in PT-BR and `Red Team Portal` in EN.

### 1.3 Left Navigation

Collapsed state:

- icon-only rail;
- fixed width;
- no labels visible;
- delayed tooltips on hover;
- explicit right separator and subtle side shadow.

Expanded state:

- overlays page content;
- does not resize main content;
- icon positions remain stable;
- labels show to the right of the icon column;
- closes when user clicks elsewhere.

Navigation items:

- Central Operacional / Operations Hub
- Criar Vulnerabilidade / Create Vulnerability
- Criar Relatório / Create Report
- Fila RVS / RVS Queue
- Logs de Auditoria / Audit Logs
- Usuários / Users
- Chaves de API / API Keys
- Configurações / Settings

---

## 2. Visual System

### 2.1 Theme

The MVP uses a terminal-like visual language:

- dark graphite / green-black background;
- thin borders;
- compact operational density;
- monospaced or monospaced-inspired typography for operational content;
- restrained phosphor-green accents;
- muted support colors.

### 2.2 Color Principles

Base surfaces:

- app background: very dark graphite / green-black;
- panels: slightly lighter dark surfaces;
- header and left rail: darkest surface tier;
- overlays: dark surface with elevated shadow.

Accent rules:

- primary accent: terminal green;
- secondary accent: muted cyan;
- danger: restrained red-orange;
- identifier, operators, and source values use the same shared accent color.

### 2.3 Scrollbars

Scrollbars use the same console-like style:

- thin scrollbar width;
- dark track;
- green-accent thumb;
- rounded thumb;
- hover state slightly increases accent intensity.

---

## 3. SPA Routes

Authenticated routes:

```text
/                         -> redirect to /hub after login
/hub                      -> Operations Hub
/vulnerabilities/new      -> Create Vulnerability page
/reports/new              -> Create Report page
/vulnerabilities/:id      -> Vulnerability details page
/reports/:id              -> Report details page
/vulnerabilities/:id/edit -> Edit Vulnerability page
/reports/:id/edit         -> Edit Report page
```

Route rules:

- successful login redirects to `/hub`;
- `Criar Vulnerabilidade` navigates to `/vulnerabilities/new`;
- `Criar Relatório` navigates to `/reports/new`;
- `Detalhar` in the bottom panel navigates to the selected item detail route;
- row-level `Editar` navigates to the selected item edit route.

---

## 4. Operations Hub Page

### 4.1 Purpose

`/hub` is the first page after login and the main operational workspace for vulnerabilities and reports.

### 4.2 Main Regions

- page title;
- entity switcher;
- contextual toolbar;
- create button;
- central list panel;
- pagination controls;
- optional bottom details panel.

### 4.3 Entity Switcher

Switcher buttons:

- `Vulnerabilidades`
- `Relatórios`

Rules:

- active item is highlighted;
- switching changes the central list, create button label, pagination dataset, and contextual behavior.

### 4.4 Contextual Toolbar

Controls:

- `Filtros`;
- batch `Ações`, visible only when one or more rows are selected;
- contextual create button.

Create button labels:

- `Criar Vulnerabilidade`
- `Criar Relatório`

Rules:

- create button has fixed width to avoid toolbar shift when switching modes.

### 4.5 Vulnerability List Columns

- selection checkbox;
- Identificador;
- Status;
- CVSS;
- Operadores;
- Fonte;
- Ações.

### 4.6 Report List Columns

Reports follow the same structural and fixed-width behavior as vulnerabilities.

Minimum columns:

- selection checkbox;
- report name or identifier;
- status;
- risk/severity placeholder or equivalent field;
- operators;
- source/client/origin;
- actions.

### 4.7 Fixed Column Widths

Rules:

- table layout is fixed;
- switching between vulnerabilities and reports must not resize columns;
- long values use ellipsis truncation.

### 4.8 Row Click Zones

- checkbox zone toggles selection only;
- row body opens bottom details panel;
- three-dots zone opens row action menu only.

### 4.9 Selection and Pagination

Selection rules:

- checkbox selection and preview state are independent;
- select-all checkbox selects/deselects visible rows;
- header checkbox supports checked and indeterminate states;
- switching entity mode clears current selection.

Pagination controls:

- range label;
- page size selector;
- previous/next;
- numbered page buttons.

---

## 5. Actions

### 5.1 Batch Actions

Batch `Ações` appears only when one or more rows are selected.

Current batch actions:

- `Exportar`;
- `Disparar`;
- `Excluir`.

Rules:

- batch actions apply to selected rows only;
- `Editar` and `Visualizar` are not batch actions;
- `Excluir` requires confirmation.

### 5.2 Row Actions

Each row has a vertical three-dots button in the `Ações` column.

The row action menu contains:

- `Editar`;
- `Visualizar`;
- `Exportar`;
- `Disparar`;
- `Excluir`.

Rules:

- row actions apply only to the clicked row;
- `Visualizar` opens the bottom details panel;
- `Editar` opens the edit flow;
- `Excluir` requires confirmation.

### 5.3 Row Action Menu Placement

Rules:

- menu appears side-by-side with the mouse cursor where possible;
- menu opens right unless there is not enough viewport space;
- if needed, menu opens left;
- menu is vertically centered around the pointer as much as possible;
- menu is clamped inside viewport;
- clicking outside closes the menu;
- clicking another three-dots button closes the current menu and opens the new one.

---

## 6. Bottom Details Panel

The bottom details panel is a docked preview surface.

Open behavior:

- row body click;
- row menu `Visualizar` action.

Rules:

- docked to the bottom edge;
- height is approximately 30% of viewport;
- starts after collapsed left menu rail;
- overlays the main list;
- does not resize or shrink the central list panel;
- expanded sidebar overlays it.

Content layout:

- top area with selected item identifier, `Detalhar` button, and close `X`;
- activity column;
- core details column;
- origin/ownership column.

---

## 7. Create Vulnerability Page

### 7.1 Route

```text
/vulnerabilities/new
```

### 7.2 Page Structure

The page includes:

- breadcrumbs;
- page title;
- page actions: `Cancelar`, `Enviar`, `Salvar rascunho`;
- Informações Gerais section;
- Markdown-driven narrative sections;
- dynamic Referências section;
- Anexos section;
- internal notes.

### 7.3 Section: Informações Gerais

Fields:

- Identificador;
- CWE;
- CVSS;
- Vetor CVSS;
- Fontes;
- Operadores.

Layout rules:

- first row contains Identificador, CWE, CVSS, and Vetor CVSS;
- second row contains Fontes and Operadores;
- placeholders show only examples and do not include `Ex.:`.

CWE behavior:

- accepts numeric characters only;
- displays value as `CWE-123456`;
- current prototype limits numeric section to six digits.

CVSS behavior:

- when not focused, displays real CVSS scale `0.0–10.0`;
- when focused/clicked, converts to editable `0–100` scale;
- losing focus converts value back to `0.0–10.0`;
- focused mouse wheel changes value by `1` on the `0–100` scale;
- unfocused mouse wheel changes value by `0.1` on the real `0.0–10.0` scale;
- values are clamped between `0` and `100` internally and `0.0` and `10.0` when displayed as real CVSS.

Vetor CVSS behavior:

- accepts free-form string input;
- intended for values like `CVSS:3.1/AV:N/AC:L/...`.

Fontes behavior:

- accepts multiple comma-separated values;
- auxiliary hover view displays one source per line;
- auxiliary view appears only when input is not focused and mouse remains over the input for the hover delay;
- auxiliary view closes immediately when mouse leaves;
- auxiliary view closes when input receives focus.

Operadores behavior:

- accepts multiple comma-separated user names;
- auxiliary hover view displays one operator per line;
- auxiliary view follows the same focus and mouse-leave rules as Fontes.

General input behavior:

- clicking or focusing standard inputs selects their current content;
- pressing `Enter` inside inputs clears focus with `blur()`.

### 7.4 Markdown Narrative Sections

Sections using the Markdown Editor:

- Descrição;
- Detalhes do Achado;
- Mitigação / Solução;
- Notas Internas.

### 7.5 Section: Referências

Reference behavior:

- reference rows are repeatable URL inputs;
- clicking `Adicionar referência` creates a new empty reference row;
- new reference input receives focus automatically;
- row delete button removes that reference row;
- existing reference rows can be deleted;
- if the last reference row is removed, the UI automatically creates one empty row so the section remains usable;
- reference inputs support auto-select on click/focus;
- pressing `Enter` inside a reference input clears focus.

### 7.6 Section: Anexos

Rules:

- drag-and-drop upload area;
- file picker behavior;
- empty-state file list;
- supports common evidence formats such as PDF, PNG, JPG, GIF, TXT, CSV, ZIP.

---

## 8. Markdown Editor Component

The Markdown Editor uses:

- textarea for raw Markdown editing;
- div for rendered Markdown preview;
- mode buttons for edit and preview;
- formatting toolbar;
- line-number gutter.

Line numbering rules:

- line numbers are based only on logical lines separated by actual `
` characters;
- visual wrapping caused by long text must not create extra line numbers;
- line number height expands to match wrapped visual height of its logical line;
- gutter scrolls in sync with textarea;
- line numbers continue increasing correctly beyond 12 lines.

Dynamic height rules:

- if `n = 0..10`, visible lines = `n + 2`;
- if `n >= 11`, visible lines are capped at 12 and the textarea scrolls vertically.

Preview mode:

- hides the textarea/gutter surface;
- renders Markdown into the preview div;
- disables formatting buttons;
- content is read-only.

---

## 9. API Expectations

### 9.1 Vulnerabilities List

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

### 9.2 Reports List

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

### 9.3 Create Vulnerability

```http
POST /api/v1/vulnerabilities
Content-Type: application/json
```

Minimum request body:

- identifier;
- cwe;
- cvss_score;
- cvss_vector;
- sources[];
- operators[] or operator_ids[], depending on backend identity resolution;
- description;
- finding_detail;
- mitigation;
- references[];
- internal_notes;
- status = `draft` or `saved_local`.

### 9.4 Action Endpoints

```http
POST /api/v1/vulnerabilities/{id}/dispatch
POST /api/v1/reports/{id}/dispatch
GET  /api/v1/vulnerabilities/{id}/export?format=pdf|docx
GET  /api/v1/reports/{id}/export?format=pdf|docx
DELETE /api/v1/vulnerabilities/{id}
DELETE /api/v1/reports/{id}
```

---

## 10. State Rules

Hub state:

- active entity tab;
- filters;
- selected rows;
- active preview item;
- bottom panel open/closed;
- pagination;
- row action menu open/closed;
- batch action menu open/closed.

Form state:

- create pages keep unsaved local state;
- route-leave warning is recommended for dirty forms;
- submit buttons lock during request;
- dynamic references are part of local form state;
- multi-value fields are stored as comma-separated UI values and should be normalized before API submission.

---

## 11. Internationalization

Supported languages:

- PT-BR;
- EN.

Current visual drafts are PT-BR-first.

---

## 12. Accessibility and UX Notes

- icon-only controls require accessible labels;
- collapsed sidebar icons require tooltips and keyboard labels;
- Markdown toolbar buttons require accessible names;
- row action menus must be keyboard reachable in implementation;
- row menus must close on outside click;
- destructive actions must require confirmation;
- line numbers must not be read as editable content;
- disabled toolbar actions must be visually and programmatically disabled;
- auxiliary multi-line views are read-only and should not trap focus.

---

## 13. Deferred Items

Deferred:

- full report creation page;
- vulnerability detail page;
- report detail page;
- report lock UI;
- RVS queue page;
- audit logs page;
- user management page;
- API key page;
- responsive/mobile rules;
- full design-token sheet.

---

## 14. Change Log — Latest Prototype Updates

### Added

- Opaque top header requirement.
- Console-style scrollbar requirements.
- Explicit sidebar/page separation requirement.
- Left navigation entries for `Criar Vulnerabilidade` and `Criar Relatório`.
- Fixed-width create button rule.
- Fixed-width table column rules.
- Pagination requirements.
- Select-all behavior for list header checkbox.
- Batch actions: `Exportar`, `Disparar`, `Excluir`.
- Row-level three-dots action menu with `Editar`, `Visualizar`, `Exportar`, `Disparar`, and `Excluir`.
- Dynamic row menu placement near the mouse cursor.
- Markdown Editor with textarea + rendered div preview.
- Markdown Editor logical line numbering and synchronized gutter scrolling.
- New `Vetor CVSS` input in the vulnerability creation page.
- Numeric-only CWE behavior with displayed `CWE-123456` format.
- CVSS dual-scale behavior with focus-based `0–100` editing and blurred `0.0–10.0` display.
- Multi-value `Fontes` field with comma-separated input and auxiliary multi-line hover view.
- Multi-value `Operadores` field with comma-separated user names and auxiliary multi-line hover view.
- Dynamic reference row creation via `Adicionar referência`.
- Dynamic reference row deletion via row delete button.
- Automatic creation of one empty reference row when the last row is deleted.
- Auto-select-on-click/focus behavior for standard and reference inputs.
- `Enter` key handling to blur standard and reference inputs.

### Removed / Changed

- Removed standalone `Exportar` toolbar button.
- Removed `Editar` and `Visualizar` from batch actions.
- Changed `Operador` column to `Operadores`.
- Changed sidebar `Vulnerabilidades` / `Relatórios` entries to `Criar Vulnerabilidade` / `Criar Relatório`.
- Changed row action menu from static below-button positioning to dynamic side-by-side pointer positioning.
- Changed header from translucent to opaque.
- Replaced single `Fonte` input semantics with multi-value `Fontes` semantics.
- Replaced single `Operador` form semantics with multi-value `Operadores` semantics.
- Removed `Ex.:` from placeholders.
- Changed CVSS input from direct real-score entry to focus-based scale conversion.
- Changed reference rows from static examples to fully addable/removable rows.

---

## 15. Summary

The current frontend MVP draft consists of:

- authenticated shell;
- console-like visual system;
- Operations Hub for vulnerabilities and reports;
- fixed-width list layout;
- independent selection and preview behavior;
- separate batch and row action models;
- dynamic row action menu placement;
- bottom details preview panel;
- create vulnerability page with dynamic general-info inputs and references;
- reusable Markdown Editor with textarea + preview div;
- route and API expectations for current UI scope.
