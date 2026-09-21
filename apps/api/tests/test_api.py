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
