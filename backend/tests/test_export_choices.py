"""Sections left out of a vulnerability's / report's documents (export and send).

The choice is a presentation one, not content: it is saved on its own (PUT .../export-sections),
in any status, without the report lock and without a new version."""

import io

import openpyxl
from conftest import fixing_vuln, new_report, new_vuln, report_vuln
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
    # Put back in, on its own: no new version, so an open editor stays valid.
    r = writer.put(f"/vulnerabilities/{v['id']}/export-sections", {"hidden": []})
    assert r.status_code == 200 and r.json() == {"hidden": []}
    after = writer.get(f"/vulnerabilities/{v['id']}").json()
    assert after["export_hidden"] == [] and after["version"] == got["version"]
    assert "MITIG-OCULTA" in docx_text(writer.get(f"/vulnerabilities/{v['id']}/export", params={"format": "docx"}).content)


def test_the_choice_works_after_sending_and_only_for_writers(writer, reader):
    sent = fixing_vuln(writer, mitigation="MITIG-ENVIADA")
    r = writer.put(f"/vulnerabilities/{sent['id']}/export-sections", {"hidden": ["mitigation"]})
    assert r.status_code == 200
    assert "MITIG-ENVIADA" not in docx_text(writer.get(f"/vulnerabilities/{sent['id']}/export", params={"format": "docx"}).content)
    assert writer.put(f"/vulnerabilities/{sent['id']}/export-sections", {"hidden": ["identifier"]}).status_code == 422
    assert reader.put(f"/vulnerabilities/{sent['id']}/export-sections", {"hidden": []}).status_code == 403
    # Not through the content PATCH any more.
    cur = writer.get(f"/vulnerabilities/{sent['id']}").json()
    writer.patch(f"/vulnerabilities/{sent['id']}", {"version": cur["version"], "export_hidden": []})
    assert writer.get(f"/vulnerabilities/{sent['id']}").json()["export_hidden"] == ["mitigation"]


def test_report_sections_can_be_left_out(writer, writer2):
    rid = new_report(writer)["id"]
    writer.patch(f"/reports/{rid}", {"executive_summary_md": "RESUMO-OCULTO", "introduction_md": "INTRO-VISIVEL",
                                     "test_type": "TIPO-OCULTO"})
    writer.post(f"/reports/{rid}/sections", {"title": "Metodologia", "content_markdown": "SECAO-VISIVEL"})
    out = writer.post(f"/reports/{rid}/sections", {"title": "Rascunhos", "content_markdown": "SECAO-OCULTA", "exported": False}).json()
    assert [s["exported"] for s in out["sections"]] == [True, False]
    # Another writer (no lock) may change the choice while the first one edits.
    r = writer2.put(f"/reports/{rid}/export-sections", {"hidden": ["executive_summary", "report_data"]})
    assert r.status_code == 200 and r.json()["export_hidden"] == ["executive_summary", "report_data"]
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

    # A free-form section put back in, after the report is sent.
    sid = out["sections"][1]["id"]
    assert writer.post(f"/reports/{rid}/send").status_code == 200
    r = writer.put(f"/reports/{rid}/export-sections", {"sections": {sid: True}})
    assert r.status_code == 200 and r.json()["sections"][sid] is True
    assert r.json()["export_hidden"] == ["executive_summary", "report_data"]       # untouched
    assert "SECAO-OCULTA" in docx_text(writer.get(f"/reports/{rid}/export", params={"format": "docx"}).content)
    assert writer.put(f"/reports/{rid}/export-sections", {"sections": {rid: True}}).status_code == 404
