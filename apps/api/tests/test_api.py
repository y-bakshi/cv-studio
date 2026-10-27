from __future__ import annotations

import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test-cv-studio.db"
os.environ["ARTIFACT_ROOT"] = "./test-artifacts"

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import Base, engine
from app.main import app
from app.latex import document_to_tex


def setup_module():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def test_formatted_heading_preserves_latex_command_case():
    document = {
        "type": "doc",
        "content": [{
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": "Summary", "marks": [{"type": "bold"}]}],
        }],
    }
    source = document_to_tex(document)
    assert r"\section{\textbf{Summary}}" in source
    assert r"\TEXTBF" not in source


@pytest.mark.anyio
async def test_authenticated_cv_revision_annotation_and_job_flow():
  async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
    registered = await client.post("/api/auth/register", json={"email": "test@example.com", "password": "correct-horse"})
    assert registered.status_code == 201

    created = await client.post("/api/cvs", json={"title": "Backend CV"})
    assert created.status_code == 201
    cv = created.json()
    assert "\\documentclass" in cv["tex_source"]

    cv["document"]["content"][2]["content"][0]["text"] = "Professional Summary"
    updated = await client.patch(
        f"/api/cvs/{cv['id']}",
        json={"document": cv["document"], "expected_version": cv["version"]},
    )
    assert updated.status_code == 200
    assert updated.json()["version"] == 2

    conflict = await client.patch(
        f"/api/cvs/{cv['id']}",
        json={"title": "Stale title", "expected_version": 1},
    )
    assert conflict.status_code == 409

    annotation = await client.post(
        f"/api/cvs/{cv['id']}/annotations",
        json={"quoted_text": "Professional Summary", "note": "Shorten this"},
    )
    assert annotation.status_code == 201

    job = await client.post(
        f"/api/cvs/{cv['id']}/job-descriptions",
        json={"title": "Example role", "content": "Build reliable Python APIs."},
    )
    assert job.status_code == 201

    revisions = await client.get(f"/api/cvs/{cv['id']}/revisions")
    assert [item["version"] for item in revisions.json()] == [2, 1]


@pytest.mark.anyio
async def test_user_isolation():
  async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
    first = await client.post("/api/auth/register", json={"email": "first@example.com", "password": "password-one"})
    assert first.status_code == 201
    cv_id = (await client.post("/api/cvs", json={"title": "Private CV"})).json()["id"]
    await client.post("/api/auth/logout")
    second = await client.post("/api/auth/register", json={"email": "second@example.com", "password": "password-two"})
    assert second.status_code == 201
    assert (await client.get(f"/api/cvs/{cv_id}")).status_code == 404


@pytest.mark.anyio
async def test_resume_sections_are_stored_separately_and_loaded_whole():
  async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
    await client.post("/api/auth/register", json={"email": "resume@example.com", "password": "correct-horse"})
    cv = (await client.post("/api/cvs", json={"title": "Structured"})).json()

    empty = (await client.get(f"/api/cvs/{cv['id']}/resume")).json()
    assert set(empty["resume"]) == {"contact", "skills", "experience", "projects", "education", "section_order"}

    skills = [{"name": "Languages", "skills": ["Python", "Rust"]}]
    saved = await client.put(
        f"/api/cvs/{cv['id']}/resume/sections/skills",
        json={"data": skills, "expected_version": empty["version"]},
    )
    assert saved.status_code == 200
    assert saved.json()["resume"]["skills"][0]["skills"] == ["Python", "Rust"]
    assert saved.json()["version"] == empty["version"] + 1

    stale = await client.put(
        f"/api/cvs/{cv['id']}/resume/sections/contact",
        json={"data": {"name": "Ada"}, "expected_version": empty["version"]},
    )
    assert stale.status_code == 409

    invalid = await client.put(
        f"/api/cvs/{cv['id']}/resume/sections/contact",
        json={"data": {"nope": 1}, "expected_version": saved.json()["version"]},
    )
    assert invalid.status_code == 422
    missing = await client.put(
        f"/api/cvs/{cv['id']}/resume/sections/unknown",
        json={"data": {}, "expected_version": saved.json()["version"]},
    )
    assert missing.status_code == 404

    whole = (await client.get(f"/api/cvs/{cv['id']}/resume")).json()
    assert whole["resume"]["skills"][0]["name"] == "Languages"


@pytest.mark.anyio
async def test_all_edit_modes_stay_in_sync_and_compile():
  async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
    await client.post("/api/auth/register", json={"email": "sync@example.com", "password": "correct-horse"})
    cv = (await client.post("/api/cvs", json={"title": "Sync"})).json()
    base = f"/api/cvs/{cv['id']}/resume"

    version = (await client.get(base)).json()["version"]
    contact = {"name": "Ada Lovelace", "email": "ada@example.com"}
    saved = (await client.put(f"{base}/sections/contact", json={"data": contact, "expected_version": version})).json()

    tex = (await client.get(f"{base}/tex")).json()
    assert r"\resumecontact{Ada Lovelace}" in tex["tex_source"]

    edited = tex["tex_source"].replace("Ada Lovelace", "Ada King")
    ok = await client.put(f"{base}/tex", json={"tex_source": edited, "expected_version": saved["version"]})
    assert ok.status_code == 200
    assert (await client.get(base)).json()["resume"]["contact"]["name"] == "Ada King"

    bad = await client.put(
        f"{base}/tex",
        json={"tex_source": edited.replace(r"\end{document}", "\\textbf{x}\n\\end{document}"),
              "expected_version": ok.json()["version"]},
    )
    assert bad.status_code == 422 and bad.json()["detail"]["line"]

    queued = (await client.post(f"/api/cvs/{cv['id']}/compile")).json()
    assert queued["status"] in {"queued", "compiling", "success"}


@pytest.mark.anyio
async def test_exports_and_real_pdf_compile():
  import io, json, shutil, zipfile
  from app.latex import compile_tex
  from app.resume import Resume
  from app.resume_latex import resume_to_tex
  async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
    await client.post("/api/auth/register", json={"email": "export@example.com", "password": "correct-horse"})
    cv = (await client.post("/api/cvs", json={"title": "My Résumé"})).json()
    base = f"/api/cvs/{cv['id']}/resume"
    version = (await client.get(base)).json()["version"]
    await client.put(f"{base}/sections/experience", json={"expected_version": version, "data": [
        {"company": "Thryv", "role": "Intern", "bullets": ["Cut costs 30% & latency"]}]})

    as_json = await client.get(f"{base}/export/json")
    assert json.loads(as_json.text)["experience"][0]["company"] == "Thryv"
    assert "attachment" in as_json.headers["content-disposition"]
    assert r"\resumeentry" in (await client.get(f"{base}/export/tex")).text
    docx = await client.get(f"{base}/export/docx")
    assert docx.status_code == 200
    assert "word/document.xml" in zipfile.ZipFile(io.BytesIO(docx.content)).namelist()
    assert (await client.get(f"{base}/export/pdf")).status_code == 404

    if shutil.which("pdflatex"):
        tex = (await client.get(f"{base}/tex")).json()["tex_source"]
        ok, log = compile_tex(tex, Path("./test-artifacts/export.pdf"))
        assert ok, log[-2000:]
