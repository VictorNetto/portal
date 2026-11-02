"""File uploads: validation, access rules, locking."""

from conftest import new_report, new_vuln, png_bytes, report_vuln, saved_vuln, upload


def path(v):
    return f"/vulnerabilities/{v['id']}/attachments"


def test_upload_list_download_delete_roundtrip(writer):
    v = new_vuln(writer)
    data = png_bytes()
    r = upload(writer, path(v), "shot.png", data, "Captura")
    assert r.status_code == 201
    att = r.json()
    assert att["is_image"] and att["mime_type"] == "image/png" and att["display_name"] == "Captura"

    assert [a["id"] for a in writer.get(path(v)).json()] == [att["id"]]
    got = writer.get(f"/attachments/{att['id']}/content")
    assert got.status_code == 200 and got.content == data
    assert got.headers["content-type"] == "image/png"
    assert got.headers["x-content-type-options"] == "nosniff"
    assert got.headers["content-disposition"].startswith("inline")

    assert writer.delete(f"/attachments/{att['id']}").status_code == 204
    assert writer.get(f"/attachments/{att['id']}/content").status_code == 404


def test_non_images_download_as_attachments(writer):
    v = new_vuln(writer)
    att = upload(writer, path(v), "report.pdf", b"%PDF-1.4 evidence").json()
    r = writer.get(f"/attachments/{att['id']}/content")
    assert r.headers["content-disposition"].startswith("attachment") and not att["is_image"]


def test_types_are_checked_by_content_not_by_name(writer):
    v = new_vuln(writer)
    assert upload(writer, path(v), "evil.png", b"MZ\x90\x00 an executable").status_code == 415   # not a PNG
    assert upload(writer, path(v), "bin.txt", b"abc\x00\x01\x02").status_code == 415            # binary as text
    assert upload(writer, path(v), "fake.pdf", b"not a pdf").status_code == 415


def test_dangerous_or_unknown_types_are_refused(writer):
    v = new_vuln(writer)
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    assert upload(writer, path(v), "x.svg", svg).status_code == 415
    assert upload(writer, path(v), "run.exe", b"MZ").status_code == 415
    assert upload(writer, path(v), "page.html", b"<html></html>").status_code == 415
    assert upload(writer, path(v), "noext", b"data").status_code == 415


def test_empty_and_oversized_files(writer):
    v = new_vuln(writer)
    assert upload(writer, path(v), "empty.txt", b"").status_code == 422
    assert upload(writer, path(v), "big.txt", b"a" * (51 * 1024 * 1024)).status_code == 413


def test_path_tricks_in_filenames_are_neutralised(writer):
    v = new_vuln(writer)
    att = upload(writer, path(v), "../../etc/evil.png", png_bytes()).json()
    assert att["original_filename"] == "evil.png"
    att2 = upload(writer, path(v), "C:\\Windows\\system.png", png_bytes()).json()
    assert att2["original_filename"] == "system.png"


def test_readers_can_read_but_not_upload(writer, reader):
    v = new_vuln(writer)
    att = upload(writer, path(v), "a.txt", b"hello").json()
    assert reader.get(path(v)).status_code == 200
    assert reader.get(f"/attachments/{att['id']}/content").status_code == 200
    assert upload(reader, path(v), "b.txt", b"x").status_code == 403
    assert reader.delete(f"/attachments/{att['id']}").status_code == 403


def test_content_requires_authentication(writer):
    import httpx
    from conftest import BASE_URL

    v = new_vuln(writer)
    att = upload(writer, path(v), "a.txt", b"hello").json()
    assert httpx.get(f"{BASE_URL}/attachments/{att['id']}/content").status_code == 401


def test_attachments_lock_once_the_vuln_is_sent_vuln(writer):
    v = saved_vuln(writer)                                            # ready: still attachable
    att = upload(writer, path(v), "a.txt", b"hello").json()
    writer.post(f"/vulnerabilities/{v['id']}/send")
    assert upload(writer, path(v), "b.txt", b"x").status_code == 409
    assert writer.delete(f"/attachments/{att['id']}").status_code == 409
    assert writer.get(f"/attachments/{att['id']}/content").status_code == 200   # reading stays possible


def test_files_of_a_deleted_vuln_become_unreadable(writer):
    v = new_vuln(writer)
    att = upload(writer, path(v), "a.txt", b"secret").json()
    writer.delete(f"/vulnerabilities/{v['id']}")
    assert writer.get(f"/attachments/{att['id']}/content").status_code == 404


def test_reads_and_changes_are_audited(admin, writer):
    v = new_vuln(writer)
    att = upload(writer, path(v), "a.txt", b"x").json()
    writer.get(f"/attachments/{att['id']}/content")
    writer.delete(f"/attachments/{att['id']}")
    items = admin.get("/audit-logs", params={"page_size": 200}).json()["items"]
    mine = {e["action"] for e in items if e["entity_id"] == att["id"]}
    assert {"create", "read", "delete"} <= mine


def test_report_vuln_attachments_need_the_report_lock(writer, writer2):
    rep = new_report(writer)
    rv = report_vuln(writer, rep["id"])
    assert upload(writer, path(rv), "a.txt", b"x").status_code == 201            # lock holder
    assert upload(writer2, path(rv), "b.txt", b"x").status_code == 409           # someone else


def test_report_evidence_follows_the_report_lock(writer, writer2):
    rep = new_report(writer)
    p = f"/reports/{rep['id']}/attachments"
    ev = upload(writer, p, "evidence.pdf", b"%PDF-1.4 e", "Geral")
    assert ev.status_code == 201 and ev.json()["report_id"] == rep["id"]
    assert upload(writer2, p, "x.pdf", b"%PDF-1.4 x").status_code == 409
    assert [a["id"] for a in writer2.get(p).json()] == [ev.json()["id"]]          # anyone can list
    assert writer2.delete(f"/attachments/{ev.json()['id']}").status_code == 409   # but not remove
    assert writer.delete(f"/attachments/{ev.json()['id']}").status_code == 204
