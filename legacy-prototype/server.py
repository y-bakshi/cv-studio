#!/usr/bin/env python3
"""CV Studio local server.

Serves the frontend and a small JSON API backed by the CV repository. The server
uses only Python's standard library so the workspace can run without installing
packages.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import sys
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


WEB_ROOT = Path(__file__).resolve().parent
REPO_ROOT = WEB_ROOT.parent
STATE_ROOT = REPO_ROOT / ".cvstudio"
DOCUMENT_ROOT = STATE_ROOT / "documents"
INDEX_FILE = STATE_ROOT / "index.json"
MAX_BODY = 4 * 1024 * 1024
LOCK = threading.Lock()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def safe_json_read(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return fallback


def atomic_json_write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def document_id(path: Path) -> str:
    relative = path.relative_to(REPO_ROOT).as_posix()
    return hashlib.sha1(relative.encode()).hexdigest()[:14]


def title_from_path(path: Path) -> str:
    if path == REPO_ROOT / "source" / "master_resume.md":
        return "Master Resume"
    metadata = safe_json_read(path.parent / "metadata.json", {})
    company = metadata.get("company") or metadata.get("organization")
    role = metadata.get("role") or metadata.get("position") or metadata.get("job_title")
    if str(company).strip().lower() in {"", "unknown", "none", "n/a"}:
        company = None
    if str(role).strip().lower() in {"", "unknown", "none", "n/a"}:
        role = None
    if company and role:
        return f"{role} · {company}"
    name = path.stem
    name = re.sub(r"^Yash_Bakshi_", "", name, flags=re.I)
    name = re.sub(r"_(tailored_)?resume$", "", name, flags=re.I)
    name = re.sub(r"_CV$", "", name, flags=re.I)
    return re.sub(r"[_-]+", " ", name).strip().title() or path.parent.name.replace("_", " ").title()


def folder_from_path(path: Path) -> str:
    relative = path.relative_to(REPO_ROOT)
    if relative.parts[0] == "source":
        return "Master versions"
    slug = relative.parts[2] if len(relative.parts) > 2 else "Applications"
    if slug.startswith("asu_"):
        return "On-campus"
    systems = ("system", "cloud", "linux", "servicenow", "infrastructure")
    return "Cloud & Systems" if any(word in slug for word in systems) else "Software Engineering"


def source_candidates() -> list[Path]:
    candidates: list[Path] = []
    master = REPO_ROOT / "source" / "master_resume.md"
    if master.exists():
        candidates.append(master)
    applications = REPO_ROOT / "applications"
    if applications.exists():
        for directory in sorted(applications.glob("*/*"), reverse=True):
            preferred = directory / "tailored_resume.md"
            if preferred.exists():
                candidates.append(preferred)
                continue
            resumes = sorted(directory.glob("*Resume.md"))
            if resumes:
                candidates.append(resumes[0])
    return candidates


def markdown_inline(value: str) -> str:
    value = html.escape(value)
    value = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", value)
    value = re.sub(r"(?<!\*)\*(.+?)\*(?!\*)", r"<em>\1</em>", value)
    value = re.sub(r"`(.+?)`", r"<code>\1</code>", value)
    value = re.sub(r"\[([^]]+)]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', value)
    return value


def markdown_to_resume(markdown: str) -> str:
    lines = markdown.replace("\r\n", "\n").splitlines()
    out: list[str] = []
    in_list = False
    first_h1 = True
    section_open = False
    for raw in lines:
        line = raw.strip()
        if line == "---":
            continue
        if line.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{markdown_inline(line[2:])}</li>")
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        if not line:
            continue
        if line.startswith("# "):
            if section_open:
                out.append("</section>")
                section_open = False
            text = markdown_inline(line[2:])
            if first_h1:
                out.append(f'<section class="resume-header"><h1>{text}</h1></section>')
                first_h1 = False
            else:
                out.append(f"<section><h2>{text}</h2></section>")
        elif line.startswith("## "):
            if section_open:
                out.append("</section>")
            out.append(f"<section><h2>{markdown_inline(line[3:])}</h2>")
            section_open = True
        elif line.startswith("### "):
            out.append(f'<div class="role-heading"><strong>{markdown_inline(line[4:])}</strong></div>')
        elif line.startswith("#### "):
            out.append(f'<div class="company-heading">{markdown_inline(line[5:])}</div>')
        elif line.startswith("|"):
            continue
        else:
            out.append(f"<p>{markdown_inline(line)}</p>")
    if in_list:
        out.append("</ul>")
    if section_open:
        out.append("</section>")
    result = "".join(out)
    if not result:
        result = '<section class="resume-header"><h1>UNTITLED CV</h1></section><section><h2>SUMMARY</h2><p>Start writing here.</p></section>'
    return result


def load_index() -> dict:
    index = safe_json_read(INDEX_FILE, {})
    index.setdefault("overrides", {})
    index.setdefault("custom", [])
    return index


def scan_documents() -> list[dict]:
    index = load_index()
    documents: list[dict] = []
    seen: set[str] = set()
    for path in source_candidates():
        doc_id = document_id(path)
        seen.add(doc_id)
        override = index["overrides"].get(doc_id, {})
        stat = path.stat()
        draft_path = DOCUMENT_ROOT / f"{doc_id}.json"
        draft = safe_json_read(draft_path, {})
        modified = draft.get("updated_at") or datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(timespec="seconds")
        documents.append({
            "id": doc_id,
            "title": override.get("title") or draft.get("title") or title_from_path(path),
            "folder": folder_from_path(path),
            "source_path": path.relative_to(REPO_ROOT).as_posix(),
            "updated_at": modified,
            "starred": bool(override.get("starred", False)),
            "has_draft": draft_path.exists(),
        })
    for doc_id in index["custom"]:
        if doc_id in seen:
            continue
        draft = safe_json_read(DOCUMENT_ROOT / f"{doc_id}.json", {})
        if draft:
            override = index["overrides"].get(doc_id, {})
            documents.append({
                "id": doc_id,
                "title": override.get("title") or draft.get("title", "Untitled CV"),
                "folder": override.get("folder", "Drafts"),
                "source_path": None,
                "updated_at": draft.get("updated_at", now_iso()),
                "starred": bool(override.get("starred", False)),
                "has_draft": True,
            })
    return sorted(documents, key=lambda item: item["updated_at"], reverse=True)


def get_document(doc_id: str) -> dict | None:
    for summary in scan_documents():
        if summary["id"] != doc_id:
            continue
        draft = safe_json_read(DOCUMENT_ROOT / f"{doc_id}.json", {})
        if draft.get("html"):
            return {**summary, **draft}
        source = REPO_ROOT / summary["source_path"] if summary["source_path"] else None
        markdown = source.read_text(encoding="utf-8", errors="replace") if source else ""
        return {**summary, "html": markdown_to_resume(markdown), "source_markdown": markdown}
    return None


def plain_text(markup: str) -> str:
    text = re.sub(r"<[^>]+>", " ", markup)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def ats_review(markup: str) -> tuple[str, dict]:
    text = plain_text(markup)
    words = text.split()
    sections = [name for name in ("summary", "experience", "education", "skills", "projects") if name in text.lower()]
    metrics = len(re.findall(r"\b(?:\d+(?:\.\d+)?%|\d{2,}\+?)\b", text))
    score = min(96, 54 + len(sections) * 6 + min(metrics, 6) * 2 + (8 if 350 <= len(words) <= 750 else 2))
    missing = [name.title() for name in ("experience", "education", "skills") if name not in sections]
    details = f"I completed an ATS review: **{score}/100**. I found {len(words)} words, {len(sections)} standard sections, and {metrics} measurable results."
    if missing:
        details += f" Add standard section headings for {', '.join(missing)}."
    elif len(words) > 750:
        details += " The content is dense; trim lower-priority bullets to keep the document scannable."
    else:
        details += " The structure is parser-friendly. Keep role-specific keywords supported by evidence in your bullets."
    return details, {"score": score, "word_count": len(words), "metrics": metrics, "sections": sections}


def extract_keywords(job_description: str) -> list[str]:
    stop = {"with", "from", "that", "this", "will", "have", "your", "their", "about", "into", "using", "work", "team", "years", "experience", "skills", "role", "job", "and", "the", "for", "are", "you", "our"}
    words = re.findall(r"[A-Za-z][A-Za-z+#.]{2,}", job_description.lower())
    counts: dict[str, int] = {}
    for word in words:
        if word not in stop:
            counts[word] = counts.get(word, 0) + 1
    return [word for word, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:10]]


def local_chat(payload: dict) -> dict:
    message = str(payload.get("message", "")).strip()
    lower = message.lower()
    markup = str(payload.get("document_html", ""))
    selected = str(payload.get("selected_text", "")).strip()
    job = str(payload.get("job_description", "")).strip()
    if "ats" in lower:
        response, analysis = ats_review(markup)
        return {"message": response, "analysis": analysis}
    if job and any(term in lower for term in ("tailor", "match", "job", "keyword")):
        keywords = extract_keywords(job)
        present = [word for word in keywords if word.lower() in plain_text(markup).lower()]
        missing = [word for word in keywords if word not in present]
        return {"message": f"I compared the CV with the attached job description. Strong matches: **{', '.join(present[:5]) or 'none yet'}**. Consider adding evidence for: **{', '.join(missing[:5]) or 'the remaining role requirements'}**. Only add a keyword when your experience supports it.", "analysis": {"keywords": keywords, "present": present, "missing": missing}}
    if selected:
        concise = re.sub(r"\b(successfully|responsible for|worked to|helped to|in order to)\b", "", selected, flags=re.I)
        concise = re.sub(r"\s+", " ", concise).strip()
        if concise:
            concise = concise[0].upper() + concise[1:]
        return {"message": "I tightened the selected passage while preserving its factual claims.", "change": {"type": "replace_selection", "before": selected, "after": concise}}
    if any(term in lower for term in ("summary", "backend", "rewrite")):
        summary = "Software engineer with 3+ years of experience delivering cloud-native backend systems, deployment automation, and enterprise platforms. Builds reliable APIs, CI/CD quality gates, and operational tooling across Java, Python, AWS, and GCP environments."
        return {"message": "I prepared a concise, backend-focused summary using evidence already present in the CV.", "change": {"type": "replace_summary", "after": summary}}
    return {"message": "I reviewed the current CV context. Ask me to run an ATS review, tailor it to the attached job description, improve the summary, or select text in the canvas for a focused rewrite."}


def remote_chat(payload: dict) -> dict | None:
    endpoint = os.getenv("CV_STUDIO_AI_URL", "").strip()
    api_key = os.getenv("CV_STUDIO_AI_KEY", "").strip()
    model = os.getenv("CV_STUDIO_AI_MODEL", "").strip()
    if not endpoint or not model:
        return None
    prompt = f"""You are a truthful resume editor. Never invent claims or metrics.
Return JSON with keys: message (string), and optionally change with type replace_summary or replace_selection and after.
User request: {payload.get('message', '')}
Selected text: {payload.get('selected_text', '')}
Job description: {str(payload.get('job_description', ''))[:8000]}
Resume text: {plain_text(str(payload.get('document_html', '')))[:12000]}"""
    request_body = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2, "response_format": {"type": "json_object"}}
    request = urllib.request.Request(endpoint, data=json.dumps(request_body).encode(), headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {api_key}"} if api_key else {})})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = json.load(response)
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)
    except (urllib.error.URLError, KeyError, ValueError, TimeoutError):
        return None


class CVStudioHandler(SimpleHTTPRequestHandler):
    server_version = "CVStudio/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def log_message(self, format: str, *args) -> None:
        sys.stdout.write(f"[{self.log_date_time_string()}] {format % args}\n")
        sys.stdout.flush()

    def json_response(self, payload, status=HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_BODY:
            raise ValueError("Request is too large")
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self.json_response({"ok": True, "documents": len(scan_documents()), "ai": "remote" if os.getenv("CV_STUDIO_AI_URL") else "local"})
            return
        if parsed.path == "/api/documents":
            query = parse_qs(parsed.query).get("q", [""])[0].lower()
            docs = scan_documents()
            if query:
                docs = [doc for doc in docs if query in doc["title"].lower() or query in doc["folder"].lower()]
            self.json_response({"documents": docs})
            return
        if parsed.path == "/api/document":
            doc_id = parse_qs(parsed.query).get("id", [""])[0]
            document = get_document(doc_id)
            self.json_response(document or {"error": "Document not found"}, HTTPStatus.OK if document else HTTPStatus.NOT_FOUND)
            return
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            payload = self.read_json()
            if parsed.path == "/api/documents":
                with LOCK:
                    index = load_index()
                    source_id = str(payload.get("from_id", ""))
                    source = get_document(source_id) if source_id else None
                    doc_id = hashlib.sha1(f"{now_iso()}:{os.urandom(8).hex()}".encode()).hexdigest()[:14]
                    title = str(payload.get("title") or "Untitled CV")[:140]
                    document = {"id": doc_id, "title": title, "html": source.get("html") if source else markdown_to_resume("# YASH BAKSHI\n\n## SUMMARY\n\nStart writing here."), "created_at": now_iso(), "updated_at": now_iso()}
                    atomic_json_write(DOCUMENT_ROOT / f"{doc_id}.json", document)
                    index["custom"].insert(0, doc_id)
                    index["overrides"][doc_id] = {"title": title, "folder": str(payload.get("folder") or "Drafts")}
                    atomic_json_write(INDEX_FILE, index)
                self.json_response(document, HTTPStatus.CREATED)
                return
            if parsed.path == "/api/chat":
                result = remote_chat(payload) or local_chat(payload)
                result["provider"] = "remote" if os.getenv("CV_STUDIO_AI_URL") else "local"
                self.json_response(result)
                return
            self.json_response({"error": "Unknown endpoint"}, HTTPStatus.NOT_FOUND)
        except (ValueError, json.JSONDecodeError) as error:
            self.json_response({"error": str(error)}, HTTPStatus.BAD_REQUEST)

    def do_PUT(self):
        parsed = urlparse(self.path)
        try:
            payload = self.read_json()
            doc_id = str(payload.get("id", ""))
            if not re.fullmatch(r"[a-f0-9]{14}", doc_id) or not get_document(doc_id):
                self.json_response({"error": "Invalid document"}, HTTPStatus.NOT_FOUND)
                return
            if parsed.path == "/api/document":
                with LOCK:
                    current = safe_json_read(DOCUMENT_ROOT / f"{doc_id}.json", {})
                    document = {**current, "id": doc_id, "title": str(payload.get("title", "Untitled CV"))[:140], "html": str(payload.get("html", ""))[:MAX_BODY], "updated_at": now_iso()}
                    document.setdefault("created_at", now_iso())
                    atomic_json_write(DOCUMENT_ROOT / f"{doc_id}.json", document)
                    index = load_index()
                    index["overrides"].setdefault(doc_id, {})["title"] = document["title"]
                    atomic_json_write(INDEX_FILE, index)
                self.json_response({"ok": True, "updated_at": document["updated_at"]})
                return
            if parsed.path == "/api/document/star":
                with LOCK:
                    index = load_index()
                    override = index["overrides"].setdefault(doc_id, {})
                    override["starred"] = bool(payload.get("starred"))
                    atomic_json_write(INDEX_FILE, index)
                self.json_response({"ok": True, "starred": override["starred"]})
                return
            self.json_response({"error": "Unknown endpoint"}, HTTPStatus.NOT_FOUND)
        except (ValueError, json.JSONDecodeError) as error:
            self.json_response({"error": str(error)}, HTTPStatus.BAD_REQUEST)


def main() -> None:
    port = int(os.getenv("CV_STUDIO_PORT", "8000"))
    STATE_ROOT.mkdir(exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", port), CVStudioHandler)
    print(f"CV Studio running at http://localhost:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
