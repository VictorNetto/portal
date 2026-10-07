"""Document rendering: report / vulnerability PDF and the vulnerabilities Excel
(SPEC §7 Export Formats, §9 dispatch).

Pure functions over plain objects: callers pass the report/vuln ORM rows and a
`load_image(attachment_id)` callback, so this module never touches the database.
Internal notes are never rendered (excluded from all exports).
"""

from __future__ import annotations

import io
import os
import re
from collections.abc import Callable
from datetime import datetime
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    CondPageBreak,
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

# (bytes, mime) for an attachment id, or None when it can't be used.
ImageLoader = Callable[[str], "tuple[bytes, str] | None"]

PAGE_W, PAGE_H = A4
MARGIN = 20 * mm
FRAME_W = PAGE_W - 2 * MARGIN
ACCENT = colors.HexColor("#4f46e5")
MUTED = colors.HexColor("#5f6d7e")
LINE = colors.HexColor("#d8dde4")

# --- fonts ------------------------------------------------------------------
_FONTS_READY = False
BASE, BOLD, ITALIC, MONO = "Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Courier"


def _fonts() -> None:
    """Use the Vera family bundled with ReportLab (Latin-1 + common punctuation,
    so Portuguese renders correctly); fall back to the built-in Helvetica."""
    global _FONTS_READY, BASE, BOLD, ITALIC
    if _FONTS_READY:
        return
    import reportlab

    folder = os.path.join(os.path.dirname(reportlab.__file__), "fonts")
    try:
        for name, file in (("Vera", "Vera.ttf"), ("Vera-Bold", "VeraBd.ttf"),
                           ("Vera-Italic", "VeraIt.ttf"), ("Vera-BoldItalic", "VeraBI.ttf")):
            pdfmetrics.registerFont(TTFont(name, os.path.join(folder, file)))
        pdfmetrics.registerFontFamily(
            "Vera", normal="Vera", bold="Vera-Bold", italic="Vera-Italic", boldItalic="Vera-BoldItalic"
        )
        BASE, BOLD, ITALIC = "Vera", "Vera-Bold", "Vera-Italic"
    except Exception:  # pragma: no cover - font files missing
        pass
    _FONTS_READY = True


def _styles() -> dict[str, ParagraphStyle]:
    _fonts()
    s: dict[str, ParagraphStyle] = {}
    s["body"] = ParagraphStyle("body", fontName=BASE, fontSize=9.5, leading=14, alignment=TA_LEFT,
                               spaceAfter=6, textColor=colors.HexColor("#27323f"))
    s["small"] = ParagraphStyle("small", parent=s["body"], fontSize=8.5, leading=12, textColor=MUTED)
    s["H1"] = ParagraphStyle("H1", fontName=BOLD, fontSize=17, leading=22, spaceBefore=4, spaceAfter=10,
                             textColor=ACCENT)
    s["H2"] = ParagraphStyle("H2", fontName=BOLD, fontSize=13, leading=18, spaceBefore=10, spaceAfter=6,
                             textColor=colors.HexColor("#0f1b2a"))
    s["H3"] = ParagraphStyle("H3", fontName=BOLD, fontSize=10.5, leading=15, spaceBefore=8, spaceAfter=3,
                             textColor=ACCENT)
    # Markdown headings inside user content (kept out of the TOC, smaller than H1/H2).
    s["md1"] = ParagraphStyle("md1", fontName=BOLD, fontSize=12, leading=16, spaceBefore=8, spaceAfter=4)
    s["md2"] = ParagraphStyle("md2", fontName=BOLD, fontSize=10.5, leading=15, spaceBefore=6, spaceAfter=3)
    s["md3"] = ParagraphStyle("md3", fontName=BOLD, fontSize=9.5, leading=14, spaceBefore=4, spaceAfter=2)
    s["quote"] = ParagraphStyle("quote", parent=s["body"], leftIndent=10, textColor=MUTED,
                                borderPadding=(2, 0, 2, 6))
    s["code"] = ParagraphStyle("code", fontName=MONO, fontSize=8.2, leading=11, backColor=colors.HexColor("#f4f6f8"),
                               borderPadding=5, spaceBefore=2, spaceAfter=8, leftIndent=4)
    s["title"] = ParagraphStyle("title", fontName=BOLD, fontSize=26, leading=32, textColor=colors.HexColor("#0f1b2a"))
    s["subtitle"] = ParagraphStyle("subtitle", fontName=BASE, fontSize=13, leading=18, textColor=MUTED)
    s["cell"] = ParagraphStyle("cell", parent=s["body"], fontSize=9, leading=12, spaceAfter=0)
    s["cellh"] = ParagraphStyle("cellh", parent=s["cell"], fontName=BOLD, textColor=MUTED)
    return s


# --- markdown -> flowables ------------------------------------------------------
_IMG = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
_ATT_URL = re.compile(r"^/api/attachments/([0-9a-f-]{36})/content$", re.I)


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline(text: str) -> str:
    """Inline markdown -> ReportLab mini-markup. Escapes first, so author text can
    never inject tags; only http(s)/mailto links are made clickable."""
    stash: list[str] = []

    def keep(markup: str) -> str:
        stash.append(markup)
        return f"\x00{len(stash) - 1}\x00"

    out = _esc(text)
    out = re.sub(r"`([^`]+)`", lambda m: keep(f'<font name="{MONO}" size="8.6">{m.group(1)}</font>'), out)

    def link(m: re.Match) -> str:
        url = m.group(2).replace("&amp;", "&")
        if re.match(r"^(https?://|mailto:)", url, re.I):
            safe = url.replace('"', "%22").replace("&", "&amp;")
            return keep(f'<a href="{safe}" color="#4f46e5">{m.group(1)}</a>')
        return m.group(0)

    out = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", out)
    out = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", out)
    return re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m.group(1))], out)


def _image_flowable(url: str, alt: str, load_image: ImageLoader, st: dict) -> Any | None:
    m = _ATT_URL.match(url)
    if not m:
        return None
    loaded = load_image(m.group(1))
    if not loaded:
        return Paragraph(f"[{_esc(alt) or 'imagem'} — indisponível]", st["small"])
    data, _mime = loaded
    try:
        from PIL import Image as PILImage

        pil = PILImage.open(io.BytesIO(data))
        pil.load()
        if pil.format not in ("PNG", "JPEG"):  # GIF / WebP -> PNG for ReportLab
            buf = io.BytesIO()
            pil.convert("RGBA" if pil.mode in ("RGBA", "LA", "P") else "RGB").save(buf, "PNG")
            data = buf.getvalue()
        w, h = ImageReader(io.BytesIO(data)).getSize()
    except Exception:
        return Paragraph(f"[{_esc(alt) or 'imagem'} — formato não suportado]", st["small"])
    scale = min(FRAME_W / w, (PAGE_H * 0.5) / h, 1.0)
    img = Image(io.BytesIO(data), width=w * scale, height=h * scale)
    img.hAlign = "LEFT"
    parts: list[Any] = [img]
    if alt.strip():
        parts.append(Paragraph(_esc(alt), st["small"]))
    return KeepTogether(parts)


def md_flowables(text: str | None, st: dict, load_image: ImageLoader) -> list[Any]:
    if not (text or "").strip():
        return []
    src = text.replace("\r\n", "\n").replace("\r", "\n")
    flow: list[Any] = []

    # fenced code blocks are lifted out first
    blocks: list[str] = []

    def fence(m: re.Match) -> str:
        blocks.append(m.group(1).rstrip("\n"))
        return f"\n\x01{len(blocks) - 1}\x01\n"

    src = re.sub(r"```[^\n]*\n?(.*?)```", fence, src, flags=re.S)

    para: list[str] = []
    items: list[str] = []
    ordered = False
    quote: list[str] = []

    def flush_para() -> None:
        nonlocal para
        if not para:
            return
        joined = "\n".join(para)
        para = []
        # split around images so each becomes its own flowable
        pos = 0
        for m in _IMG.finditer(joined):
            before = joined[pos:m.start()].strip()
            if before:
                flow.append(Paragraph(_inline(before).replace("\n", "<br/>"), st["body"]))
            img = _image_flowable(m.group(2), m.group(1), load_image, st)
            if img is not None:
                flow.append(img)
                flow.append(Spacer(1, 4))
            pos = m.end()
        rest = joined[pos:].strip()
        if rest:
            flow.append(Paragraph(_inline(rest).replace("\n", "<br/>"), st["body"]))

    def flush_list() -> None:
        nonlocal items
        if not items:
            return
        for i, item in enumerate(items, start=1):
            bullet = f"{i}." if ordered else "•"
            flow.append(Paragraph(f"{bullet}&nbsp;&nbsp;{_inline(item)}",
                                  ParagraphStyle("li", parent=st["body"], leftIndent=14, firstLineIndent=-10,
                                                 spaceAfter=2)))
        flow.append(Spacer(1, 4))
        items = []

    def flush_quote() -> None:
        nonlocal quote
        if quote:
            flow.append(Paragraph(_inline("\n".join(quote)).replace("\n", "<br/>"), st["quote"]))
            quote = []

    def flush_all() -> None:
        flush_para(); flush_list(); flush_quote()

    for line in src.split("\n"):
        if not line.strip():
            flush_all()
            continue
        if (m := re.fullmatch(r"\x01(\d+)\x01", line)):
            flush_all()
            code = _esc(blocks[int(m.group(1))]).replace("\n", "<br/>").replace(" ", "&nbsp;")
            flow.append(Paragraph(code, st["code"]))
            continue
        if (m := re.match(r"^(#{1,3}) (.*)$", line)):
            flush_all()
            flow.append(Paragraph(_inline(m.group(2)), st[f"md{len(m.group(1))}"]))
            continue
        if (m := re.match(r"^> ?(.*)$", line)):
            flush_para(); flush_list()
            quote.append(m.group(1))
            continue
        if (m := re.match(r"^[-*] (.*)$", line)):
            flush_para(); flush_quote()
            if items and ordered:
                flush_list()
            ordered = False
            items.append(m.group(1))
            continue
        if (m := re.match(r"^\d+\. (.*)$", line)):
            flush_para(); flush_quote()
            if items and not ordered:
                flush_list()
            ordered = True
            items.append(m.group(1))
            continue
        flush_list(); flush_quote()
        para.append(line)
    flush_all()
    return flow


# --- document skeleton --------------------------------------------------------------
class _Doc(BaseDocTemplate):
    """Feeds headings (H1/H2) to the table of contents."""

    def __init__(self, buf, footer: str, **kw):
        super().__init__(buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                         topMargin=MARGIN, bottomMargin=MARGIN + 6 * mm, **kw)
        self._footer = footer
        frame = Frame(MARGIN, MARGIN + 6 * mm, FRAME_W, PAGE_H - 2 * MARGIN - 6 * mm, id="f")
        self.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=self._decorate)])

    def _decorate(self, canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont(BASE, 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN, 12 * mm, self._footer)
        canvas.drawRightString(PAGE_W - MARGIN, 12 * mm, f"Página {doc.page}")
        canvas.restoreState()

    def afterFlowable(self, flowable) -> None:
        if isinstance(flowable, Paragraph) and flowable.style.name in ("H1", "H2"):
            # The built-in sequencer is reset on every build pass; a counter of our
            # own would give new keys each pass and the TOC would never settle.
            key = f"toc{self.seq.nextf('toc')}"
            self.canv.bookmarkPage(key)
            self.notify("TOCEntry", (0 if flowable.style.name == "H1" else 1,
                                     flowable.getPlainText(), self.page, key))


def _kv_table(rows: list[tuple[str, str]], st: dict) -> Table:
    data = [[Paragraph(_esc(k), st["cellh"]), Paragraph(_inline(v) if v else "—", st["cell"])]
            for k, v in rows]
    t = Table(data, colWidths=[38 * mm, FRAME_W - 38 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _fmt_date(d) -> str:
    return d.strftime("%d/%m/%Y") if d else "—"


def _score(v) -> str:
    return f"{float(v):.1f}" if v is not None else "—"


def _vuln_story(v, st: dict, load_image: ImageLoader, *, title_style: str = "H2") -> list[Any]:
    """One vulnerability, all structured fields (internal notes excluded)."""
    story: list[Any] = []
    title = v.identifier or v.internal_id or "Vulnerabilidade"
    story.append(Paragraph(_esc(title), st[title_style]))
    cvss = _score(v.cvss_score) + (f"  ({_esc(v.cvss_vector)})" if v.cvss_vector else "")
    ops = ", ".join(sorted(o.username for o in v.operators)) or "—"
    story.append(_kv_table([
        ("ID interno", v.internal_id or "—"),
        ("CWE", v.cwe or "—"),
        ("CVSS", cvss),
        ("Fonte", v.source or "—"),
        ("Operadores", ops),
    ], st))
    story.append(Spacer(1, 6))
    for heading, text in (("Descrição", v.description), ("Detalhes do achado", v.finding_detail),
                          ("Mitigação / Solução", v.mitigation)):
        body = md_flowables(text, st, load_image)
        if body:
            story.append(Paragraph(heading, st["H3"]))
            story.extend(body)
    refs = [r for r in (v.references or []) if r]
    if refs:
        story.append(Paragraph("Referências", st["H3"]))
        for r in refs:
            story.append(Paragraph("•&nbsp;&nbsp;" + _inline(f"[{r}]({r})"),
                                   ParagraphStyle("ref", parent=st["body"], leftIndent=14, firstLineIndent=-10,
                                                  spaceAfter=2)))
    return story


# --- public: vulnerability PDF -------------------------------------------------------------
def vulnerability_pdf(v, load_image: ImageLoader) -> bytes:
    st = _styles()
    buf = io.BytesIO()
    doc = _Doc(buf, footer=f"{v.internal_id or 'Vulnerabilidade'} — documento gerado em "
                           f"{datetime.now():%d/%m/%Y %H:%M}")
    story = _vuln_story(v, st, load_image, title_style="H1")
    doc.build(story)
    return buf.getvalue()


# --- public: report PDF ------------------------------------------------------------------------
def report_pdf(report, vulns: list, load_image: ImageLoader) -> bytes:
    """Cover, TOC, executive summary, introduction, report data, free-form
    sections, then every vulnerability by CVSS descending (SPEC §7)."""
    st = _styles()
    buf = io.BytesIO()
    doc = _Doc(buf, footer=f"{report.internal_id or ''} — {report.name}")
    story: list[Any] = []

    # 1. Cover (auto-rendered from report fields)
    story.append(Spacer(1, 55 * mm))
    story.append(Paragraph(_esc(report.name), st["title"]))
    story.append(Spacer(1, 6))
    if report.client_name:
        story.append(Paragraph(_esc(report.client_name), st["subtitle"]))
    story.append(Spacer(1, 18))
    ops = ", ".join(sorted(o.username for o in report.operators)) or "—"
    story.append(_kv_table([
        ("Relatório", report.internal_id or "—"),
        ("Período", f"{_fmt_date(report.start_date)} – {_fmt_date(report.end_date)}"),
        ("Operadores", ops),
        ("Gerado em", datetime.now().strftime("%d/%m/%Y %H:%M")),
    ], st))
    story.append(PageBreak())

    # 3. TOC (generated; never stored)
    story.append(Paragraph("Sumário", st["H1"]))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("toc0", fontName=BOLD, fontSize=10.5, leading=16, leftIndent=0, spaceBefore=4),
        ParagraphStyle("toc1", fontName=BASE, fontSize=9.5, leading=14, leftIndent=14),
    ]
    story.append(toc)
    story.append(PageBreak())

    # 2. Executive summary
    story.append(Paragraph("Sumário Executivo", st["H1"]))
    story.extend(md_flowables(report.executive_summary_md, st, load_image)
                 or [Paragraph("—", st["body"])])

    # 4. Introduction
    story.append(PageBreak())
    story.append(Paragraph("Introdução", st["H1"]))
    story.extend(md_flowables(report.introduction_md, st, load_image) or [Paragraph("—", st["body"])])

    # 5. Report data
    story.append(Paragraph("Dados do Relatório", st["H1"]))
    story.append(_kv_table([
        ("Tipo de teste", report.test_type or ""),
        ("Modelo de teste", report.test_model or ""),
        ("Ambiente", report.environment or ""),
        ("Origem da demanda", report.demand_origin or ""),
        ("Escopo", (report.scope or "").replace("\n", "  ")),
    ], st))

    # 6. Free-form extras, in operator order
    story.append(CondPageBreak(60 * mm))
    for section in sorted(report.sections, key=lambda x: x.position):
        story.append(CondPageBreak(60 * mm))  # start a new page only when little room is left
        story.append(Paragraph(_esc(section.title), st["H1"]))
        story.extend(md_flowables(section.content_markdown, st, load_image))

    # 7. Vulnerabilities, CVSS descending
    story.append(PageBreak())
    story.append(Paragraph("Vulnerabilidades", st["H1"]))
    if not vulns:
        story.append(Paragraph("Nenhuma vulnerabilidade registrada neste relatório.", st["body"]))
    for i, v in enumerate(vulns):
        if i:
            story.append(Spacer(1, 10))
        story.extend(_vuln_story(v, st, load_image))

    doc.multiBuild(story)
    return buf.getvalue()


# --- public: Excel ---------------------------------------------------------------------------------
def vulnerabilities_xlsx(report, vulns: list) -> bytes:
    """All the report's vulnerabilities as rows (SPEC §9 step 4). No internal notes."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Vulnerabilidades"
    headers = ["ID interno", "Identificador", "CWE", "CVSS", "Vetor CVSS", "Fonte", "Operadores",
               "Status", "Descrição", "Detalhes do achado", "Mitigação / Solução", "Referências"]
    ws.append(headers)
    for v in vulns:
        ws.append([
            v.internal_id or "", v.identifier or "", v.cwe or "",
            float(v.cvss_score) if v.cvss_score is not None else None,
            v.cvss_vector or "", v.source or "",
            ", ".join(sorted(o.username for o in v.operators)),
            v.status.value if hasattr(v.status, "value") else str(v.status),
            v.description or "", v.finding_detail or "", v.mitigation or "",
            "\n".join(r for r in (v.references or []) if r),
        ])
    header_fill = PatternFill("solid", fgColor="4F46E5")
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(vertical="center")
    widths = [12, 34, 10, 7, 38, 14, 20, 14, 60, 60, 60, 40]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"

    info = wb.create_sheet("Relatório")
    for k, val in (
        ("Relatório", report.internal_id or ""), ("Nome", report.name),
        ("Cliente", report.client_name or ""),
        ("Início", _fmt_date(report.start_date)), ("Fim", _fmt_date(report.end_date)),
        ("Operadores", ", ".join(sorted(o.username for o in report.operators))),
        ("Vulnerabilidades", len(vulns)),
    ):
        info.append([k, val])
    info.column_dimensions["A"].width = 18
    info.column_dimensions["B"].width = 50
    for row in info.iter_rows():
        row[0].font = Font(bold=True)

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
