import io

import docx
import pytest
from reportlab.pdfgen import canvas

from config import settings
from tests.conftest import setup


def make_pdf(text):
    b = io.BytesIO()
    c = canvas.Canvas(b)
    c.drawString(72, 720, text)
    c.save()
    return b.getvalue()


def make_docx(text):
    b = io.BytesIO()
    d = docx.Document()
    d.add_paragraph(text)
    d.save(b)
    return b.getvalue()


async def up(client, eid, name, data, ctype):
    return await client.post(f"/api/experiments/{eid}/documents", files={"file": (name, data, ctype)})


async def test_accepts_supported_types_and_feeds_context(client, fake):
    eid, personas, sc = await setup(client, "food_delivery", 1)
    cases = [("a.txt", b"Users hate surprise delivery fees.", "text/plain"),
             ("b.csv", b"segment,pain\nstudents,fees\n", "text/csv"),
             ("c.pdf", make_pdf("Competitor pricing study"), "application/pdf"),
             ("d.docx", make_docx("Interview notes: trust matters"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")]
    for name, data, ct in cases:
        r = await up(client, eid, name, data, ct)
        assert r.status_code == 201 and r.json()["extractedChars"] > 5, (name, r.text)
    assert len((await client.get(f"/api/experiments/{eid}/documents")).json()) == 4
    iid = (await client.post("/api/interviews", json={"experimentId": eid, "personaId": personas[0]["id"]})).json()["id"]
    await client.post(f"/api/interviews/{iid}/messages", json={"content": "hello"})
    ctx = next(c[1]["context"] for c in fake.calls if c[0] == "PersonaAnswer")
    assert "surprise delivery fees" in ctx and "Competitor pricing study" in ctx and "trust matters" in ctx   # extracted text reaches the LLM context


async def test_rejects_bad_files(client, monkeypatch):
    eid, _, _ = await setup(client, "food_delivery", 1)
    assert (await up(client, eid, "evil.exe", b"MZ\x90", "application/octet-stream")).status_code == 422
    assert (await up(client, eid, "fake.pdf", b"not a pdf", "application/pdf")).status_code == 422          # magic bytes
    assert (await up(client, eid, "fake.docx", b"plain text", "application/octet-stream")).status_code == 422
    assert (await up(client, eid, "a.txt", b"hello", "application/pdf")).status_code == 422                  # MIME mismatch
    assert (await up(client, eid, "bin.txt", b"ab\x00cd", "text/plain")).status_code == 422
    assert (await up(client, eid, "empty.txt", b"", "text/plain")).status_code == 422
    monkeypatch.setattr(settings, "MAX_UPLOAD_MB", 1)
    assert (await up(client, eid, "big.txt", b"a" * (1024 * 1024 + 10), "text/plain")).status_code == 422
    assert (await up(client, "ghost", "a.txt", b"hi there", "text/plain")).status_code == 404
    ok = await up(client, eid, "../../etc/passwd.txt", b"harmless", "text/plain")                           # path traversal in name
    assert ok.status_code == 201 and "/" not in ok.json()["filename"]
    assert (await up(client, eid, "again.txt", b"harmless", "text/plain")).status_code == 409                # duplicate content
