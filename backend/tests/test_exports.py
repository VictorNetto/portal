"""PDF / Excel / Word exports and the batch export."""

import io
import zipfile

import openpyxl
import pytest
from conftest import new_report, new_vuln, png_bytes, report_vuln, saved_vuln, tag, upload
from docx import Document
from pypdf import PdfReader

SECRET = "SEGREDO-INTERNO"


def pdf_text(data: bytes) -> str:
    return "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(data)).pages)


def make_report(c):
    rid = new_report(c, client_name="ACME")["id"]
    c.patch(f"/reports/{rid}", {"internal_notes": SECRET, "introduction_md": "Introdução com ação e coração."})
    c.post(f"/reports/{rid}/sections", {"title": "Metodologia", "content_markdown": "OWASP **ASVS**."})
    v = report_vuln(c, rid, cvss_score=9.1, description="Descrição **forte**", internal_notes=SECRET)
    att = upload(c, f"/vulnerabilities/{v['id']}/attachments", "shot.png", png_bytes(), "Captura").json()
    c.patch(f"/vulnerabilities/{v['id']}", {"version": v["version"], "finding_detail": f"![Captura](/api/attachments/{att['id']}/content)"})
    return rid, v


def test_report_pdf(writer):
    rid, v = make_report(writer)
    r = writer.get(f"/reports/{rid}/export", params={"format": "pdf"})
    assert r.status_code == 200 and r.content[:5] == b"%PDF-"
    assert "attachment" in r.headers["content-disposition"]
    text = pdf_text(r.content)
    assert "Introdução" in text and "ação" in text and "Metodologia" in text    # accents + sections
    assert SECRET not in text                                                   # internal notes never exported
    assert any(p.images for p in PdfReader(io.BytesIO(r.content)).pages)         # the embedded evidence image


def test_report_excel(writer):
    rid, v = make_report(writer)
    r = writer.get(f"/reports/{rid}/export", params={"format": "xlsx"})
    wb = openpyxl.load_workbook(io.BytesIO(r.content))
    rows = list(wb["Vulnerabilidades"].iter_rows(values_only=True))
    assert len(rows) == 2 and rows[1][1] == v["identifier"] and isinstance(rows[1][3], float)
    assert SECRET not in str(rows) and wb["Relatório"]["B2"].value


def test_report_word(writer):
    rid, v = make_report(writer)
    r = writer.get(f"/reports/{rid}/export", params={"format": "docx"})
    assert r.status_code == 200 and "wordprocessingml" in r.headers["content-type"]
    doc = Document(io.BytesIO(r.content))
    headings = [p.text for p in doc.paragraphs if p.style.name == "Heading 1"]
    assert headings == ["Sumário", "Sumário Executivo", "Introdução", "Dados do Relatório", "Metodologia", "Vulnerabilidades"]
    assert len(doc.inline_shapes) == 1
    assert SECRET not in "\n".join(p.text for p in doc.paragraphs)


def test_single_vulnerability_exports(writer):
    v = saved_vuln(writer, cwe="CWE-89", cvss_score=8.8, references=["https://owasp.org"])
    pdf = writer.get(f"/vulnerabilities/{v['id']}/export", params={"format": "pdf"})
    assert pdf.content[:5] == b"%PDF-" and v["internal_id"] in pdf.headers["content-disposition"]
    assert "CWE-89" in pdf_text(pdf.content)
    docx = writer.get(f"/vulnerabilities/{v['id']}/export", params={"format": "docx"})
    assert Document(io.BytesIO(docx.content)).paragraphs[0].text == v["identifier"]
    assert writer.get(f"/vulnerabilities/{v['id']}/export", params={"format": "xlsx"}).status_code == 422


def test_unknown_formats_are_rejected(writer):
    rid = new_report(writer)["id"]
    assert writer.get(f"/reports/{rid}/export", params={"format": "odt"}).status_code == 422


def test_anyone_can_export_and_exports_are_audited(admin, reader, writer):
    v = saved_vuln(writer)
    assert reader.get(f"/vulnerabilities/{v['id']}/export").status_code == 200
    items = admin.get("/audit-logs", params={"action": "export", "page_size": 200}).json()["items"]
    assert any(e["entity_id"] == v["id"] and e["actor"] == reader.user["username"] for e in items)


def test_batch_export_of_vulnerabilities(writer):
    ids = [saved_vuln(writer)["id"] for _ in range(3)]
    z = writer.post("/vulnerabilities/export", {"ids": ids, "format": "pdf"})
    assert z.status_code == 200 and z.headers["content-type"] == "application/zip"
    names = zipfile.ZipFile(io.BytesIO(z.content)).namelist()
    assert len(names) == 3 and all(n.endswith(".pdf") for n in names)

    x = writer.post("/vulnerabilities/export", {"ids": ids + ids, "format": "xlsx"})   # duplicates collapse
    wb = openpyxl.load_workbook(io.BytesIO(x.content))
    assert wb.sheetnames == ["Vulnerabilidades"] and wb["Vulnerabilidades"].max_row == 4


def test_batch_export_validation(writer):
    assert writer.post("/vulnerabilities/export", {"ids": [], "format": "pdf"}).status_code == 422
    assert writer.post("/vulnerabilities/export", {"ids": ["00000000-0000-0000-0000-000000000000"], "format": "pdf"}).status_code == 404
    assert writer.post("/vulnerabilities/export", {"ids": [new_vuln(writer)["id"]], "format": "docx"}).status_code == 422


def test_batch_export_of_reports(writer):
    ids = [new_report(writer)["id"] for _ in range(2)]
    z = writer.post("/reports/export", {"ids": ids})
    assert z.status_code == 200
    assert len(zipfile.ZipFile(io.BytesIO(z.content)).namelist()) == 2


@pytest.mark.parametrize("text", ["XSS em <script>", "R&D <b>x", "\x010\x01", "x\n\x015\x01\ny", "a\x0bb"])
def test_awkward_text_never_breaks_an_export(writer, text):
    rep = new_report(writer, name="pytest-text " + text)
    report_vuln(writer, rep["id"], identifier=text, description=text)
    for fmt in ("pdf", "docx", "xlsx"):
        assert writer.get(f"/reports/{rep['id']}/export", params={"format": fmt}).status_code == 200


def test_a_title_is_never_a_formula_in_the_spreadsheet(writer):
    import io

    from openpyxl import load_workbook

    rep = new_report(writer, name="pytest-formula-" + tag(), client_name="=2+2")
    report_vuln(writer, rep["id"], identifier="=1+1")
    data = writer.get(f"/reports/{rep['id']}/export", params={"format": "xlsx"}).content
    book = load_workbook(io.BytesIO(data))
    cell = book.active["B2"]
    assert cell.value == "=1+1" and cell.data_type == "s"
    assert book["Relatório"]["B3"].data_type == "s"
