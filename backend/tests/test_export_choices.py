"""Sections left out of a vulnerability's / report's documents (export and send)."""

import io

import openpyxl
from conftest import new_report, new_vuln, report_vuln
from docx import Document
from pypdf import PdfReader


def docx_text(data: bytes) -> str:
    return "\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs)


def pdf_text(data: bytes) -> str:
    return "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(data)).pages)


def test_a_vuln_section_can_be_left_out_of_its_documents(writer):
    v = new_vuln(writer, description="DESC-VISIVEL", mitigation="MITIG-OCULTA",
                 references=["https://owasp.org/oculta"], export_hidden=["mitigation", "references"])
    assert v["export_hidden"] == ["mitigation", "references"]
    for fmt, text in (("pdf", pdf_text), ("docx", docx_text)):
        body = text(writer.get(f"/vulnerabilities/{v['id']}/export", params={"format": fmt}).content)
        assert "DESC-VISIVEL" in body and "MITIG-OCULTA" not in body and "owasp.org/oculta" not in body
    # The portal still has it all.
    got = writer.get(f"/vulnerabilities/{v['id']}").json()
    assert got["mitigation"] == "MITIG-OCULTA" and got["references"] == ["https://owasp.org/oculta"]
    # Put back in.
    r = writer.patch(f"/vulnerabilities/{v['id']}", {"version": got["version"], "export_hidden": []})
    assert r.status_code == 200 and r.json()["export_hidden"] == []
    body = docx_text(writer.get(f"/vulnerabilities/{v['id']}/export", params={"format": "docx"}).content)
    assert "MITIG-OCULTA" in body


def test_only_known_sections_and_not_after_sending(writer):
    v = new_vuln(writer)
    assert writer.patch(f"/vulnerabilities/{v['id']}", {"version": v["version"], "export_hidden": ["identifier"]}).status_code == 422
    sent = new_vuln(writer)
    writer.post(f"/vulnerabilities/{sent['id']}/complete")
    cur = writer.post(f"/vulnerabilities/{sent['id']}/send").json()
    # Like the content, what went out is fixed once sent.
    r = writer.patch(f"/vulnerabilities/{sent['id']}", {"version": cur["version"], "export_hidden": ["mitigation"]})
    assert r.status_code == 422


def test_report_sections_can_be_left_out(writer):
    rid = new_report(writer)["id"]
    writer.patch(f"/reports/{rid}", {"executive_summary_md": "RESUMO-OCULTO", "introduction_md": "INTRO-VISIVEL",
                                     "test_type": "TIPO-OCULTO", "export_hidden": ["executive_summary", "report_data"]})
    writer.post(f"/reports/{rid}/sections", {"title": "Metodologia", "content_markdown": "SECAO-VISIVEL"})
    r = writer.post(f"/reports/{rid}/sections", {"title": "Rascunhos", "content_markdown": "SECAO-OCULTA", "exported": False})
    out = r.json()
    assert out["export_hidden"] == ["executive_summary", "report_data"]
    assert [s["exported"] for s in out["sections"]] == [True, False]
    report_vuln(writer, rid, description="VULN-DESC", mitigation="VULN-MITIG", export_hidden=["mitigation"])

    for fmt, text in (("pdf", pdf_text), ("docx", docx_text)):
        body = text(writer.get(f"/reports/{rid}/export", params={"format": fmt}).content)
        assert "INTRO-VISIVEL" in body and "SECAO-VISIVEL" in body and "VULN-DESC" in body, fmt
        for hidden in ("RESUMO-OCULTO", "TIPO-OCULTO", "SECAO-OCULTA", "VULN-MITIG", "Rascunhos"):
            assert hidden not in body, (fmt, hidden)

    # Excel: a hidden vuln section is an empty cell.
    ws = openpyxl.load_workbook(io.BytesIO(writer.get(f"/reports/{rid}/export", params={"format": "xlsx"}).content)).active
    row = [c.value for c in ws[2]]
    assert "VULN-DESC" in row and "VULN-MITIG" not in row

    # A section put back in.
    sid = out["sections"][1]["id"]
    r = writer.patch(f"/reports/{rid}/sections/{sid}", {"exported": True})
    assert r.json()["sections"][1]["exported"] is True
    assert "SECAO-OCULTA" in docx_text(writer.get(f"/reports/{rid}/export", params={"format": "docx"}).content)
