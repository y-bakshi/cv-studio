from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .config import settings


LATEX_ESCAPES = {
    "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
    "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
}


def escape_tex(text: str) -> str:
    return "".join(LATEX_ESCAPES.get(char, char) for char in text)


def inline_tex(node: dict) -> str:
    text = escape_tex(node.get("text", ""))
    for mark in node.get("marks", []):
        if mark.get("type") == "bold": text = rf"\textbf{{{text}}}"
        elif mark.get("type") == "italic": text = rf"\textit{{{text}}}"
        elif mark.get("type") == "highlight": text = rf"\colorbox{{yellow}}{{{text}}}"
    return text


def content_text(node: dict) -> str:
    return "".join(inline_tex(child) if child.get("type") == "text" else content_text(child) for child in node.get("content", []))


def document_to_tex(document: dict) -> str:
    body: list[str] = []
    for node in document.get("content", []):
        kind = node.get("type")
        text = content_text(node)
        if kind == "heading":
            level = node.get("attrs", {}).get("level", 2)
            body.append(rf"\begin{{center}}{{\Huge\textbf{{{text}}}}}\end{{center}}" if level == 1 else rf"\section{{{text}}}")
        elif kind == "paragraph":
            body.append(text + r"\par")
        elif kind in {"bulletList", "orderedList"}:
            environment = "enumerate" if kind == "orderedList" else "itemize"
            items = []
            for item in node.get("content", []):
                items.append(r"\item " + content_text(item))
            body.append(rf"\begin{{{environment}}}" + "\n" + "\n".join(items) + "\n" + rf"\end{{{environment}}}")
        elif kind == "horizontalRule":
            body.append(r"\hrule")
    return """\\documentclass[10pt,letterpaper]{article}
\\usepackage[T1]{fontenc}
\\usepackage[utf8]{inputenc}
\\usepackage[margin=0.55in]{geometry}
\\usepackage{enumitem}
\\usepackage{xcolor}
\\usepackage{titlesec}
\\usepackage[hidelinks]{hyperref}
\\usepackage[scaled=0.92]{helvet}
\\renewcommand{\\familydefault}{\\sfdefault}
\\setlist[itemize]{noitemsep,topsep=2pt,leftmargin=*}
\\titleformat{\\section}{\\bfseries\\large}{}{0pt}{}[\\titlerule]
\\titlespacing{\\section}{0pt}{7pt}{3pt}
\\input{glyphtounicode}
\\pdfgentounicode=1
\\begin{document}
\\pagenumbering{gobble}
""" + "\n".join(body) + "\n\\end{document}\n"


def initial_document(name: str = "YOUR NAME") -> dict:
    def text(value): return {"type": "text", "text": value}
    def paragraph(value): return {"type": "paragraph", "attrs": {"id": os.urandom(5).hex()}, "content": [text(value)]}
    def heading(value, level=2): return {"type": "heading", "attrs": {"level": level, "id": os.urandom(5).hex()}, "content": [text(value)]}
    return {"type": "doc", "content": [
        heading(name.upper(), 1), paragraph("City, State • email@example.com • linkedin.com/in/username"),
        heading("Summary"), paragraph("Write a concise professional summary grounded in your experience."),
        heading("Experience"), paragraph("Role — Company | Dates"),
        {"type":"bulletList","attrs":{"id":os.urandom(5).hex()},"content":[{"type":"listItem","content":[paragraph("Describe an achievement with evidence and measurable impact.")]}]},
        heading("Education"), paragraph("Degree — University | Graduation date"),
        heading("Technical Skills"), paragraph("Languages: • Frameworks: • Cloud:")
    ]}


def compile_tex(source: str, output_path: Path) -> tuple[bool, str]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cvstudio-") as temporary:
        work = Path(temporary)
        tex = work / "resume.tex"
        tex.write_text(source, encoding="utf-8")
        env = {**os.environ, "openin_any": "p", "openout_any": "p", "TEXMFOUTPUT": str(work)}
        command = ["pdflatex", "-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error", "-synctex=1", "resume.tex"]
        logs: list[str] = []
        try:
            for _ in range(2):
                result = subprocess.run(command, cwd=work, env=env, capture_output=True, text=True, timeout=settings.compile_timeout_seconds)
                logs.append(result.stdout[-30000:] + result.stderr[-5000:])
                if result.returncode != 0: return False, "\n".join(logs)
            shutil.copy2(work / "resume.pdf", output_path)
            return True, "\n".join(logs)
        except (subprocess.TimeoutExpired, FileNotFoundError) as error:
            return False, f"Compilation failed: {error}"
