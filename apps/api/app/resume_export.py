"""Word (.docx) and JSON exports built directly from the ``Resume`` model."""

from __future__ import annotations

import io

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

from .resume import Resume

SECTION_TITLES = {
    "skills": "Skills",
    "experience": "Professional Experience",
    "projects": "Projects",
    "education": "Education",
}


def _dates(start: str, end: str) -> str:
    return " – ".join(part for part in (start, end) if part)


def _rule(paragraph) -> None:
    border = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    for key, value in (("val", "single"), ("sz", "6"), ("space", "1"), ("color", "000000")):
        bottom.set(qn(f"w:{key}"), value)
    border.append(bottom)
    paragraph._p.get_or_add_pPr().append(border)


def resume_to_docx(resume: Resume) -> bytes:
    """ATS-friendly single-column document: real headings, no tables or text boxes."""
    doc = Document()
    for section in doc.sections:
        section.left_margin = section.right_margin = Inches(0.6)
        section.top_margin = section.bottom_margin = Inches(0.55)
        width = section.page_width - section.left_margin - section.right_margin
    normal = doc.styles["Normal"]
    normal.font.name, normal.font.size = "Calibri", Pt(10)
    normal.paragraph_format.space_after = Pt(0)

    def line(left: str = "", right: str = "", bold=False, italic=False, size=None):
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.tab_stops.add_tab_stop(width, WD_TAB_ALIGNMENT.RIGHT)
        run = paragraph.add_run(left)
        run.bold, run.italic = bold, italic
        if size:
            run.font.size = Pt(size)
        if right:
            paragraph.add_run("\t" + right).italic = italic
        return paragraph

    def bullets(items: list[str]) -> None:
        for text in items:
            doc.add_paragraph(text, style="List Bullet").paragraph_format.space_after = Pt(0)

    c = resume.contact
    if c.name:
        heading = doc.add_paragraph()
        heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = heading.add_run(c.name)
        run.bold, run.font.size = True, Pt(20)
    info = [c.subtitle] if c.subtitle else []
    contact_line = " | ".join(p for p in (c.location, c.phone, c.email, *(l.url for l in c.links)) if p)
    for text in (*info, contact_line, " · ".join(c.tags)):
        if text:
            paragraph = doc.add_paragraph(text)
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

    order = [n for n in resume.section_order if n in SECTION_TITLES]
    order += [n for n in SECTION_TITLES if n not in order]
    for name in order:
        if not getattr(resume, name):
            continue
        title = doc.add_paragraph()
        title.paragraph_format.space_before = Pt(8)
        title.paragraph_format.keep_with_next = True
        title.add_run(SECTION_TITLES[name].upper()).bold = True
        _rule(title)
        if name == "skills":
            for group in resume.skills:
                paragraph = doc.add_paragraph()
                paragraph.add_run(f"{group.name}: ").bold = True
                paragraph.add_run(", ".join(group.skills))
        elif name == "experience":
            for e in resume.experience:
                line(e.company, bold=True).paragraph_format.space_before = Pt(4)
                line(e.role, " · ".join(p for p in (e.location, _dates(e.start, e.end)) if p), italic=True)
                if e.summary:
                    doc.add_paragraph(e.summary)
                bullets(e.bullets)
        elif name == "projects":
            for p in resume.projects:
                line(" ".join(x for x in (p.name, p.link_text) if x), _dates(p.start, p.end), bold=True).paragraph_format.space_before = Pt(4)
                if p.organization or p.location:
                    line(p.organization, p.location, italic=True)
                bullets(p.bullets)
        elif name == "education":
            for e in resume.education:
                line(e.school, _dates(e.start, e.end), bold=True).paragraph_format.space_before = Pt(4)
                line(e.degree, e.location, italic=True)
                if e.gpa:
                    doc.add_paragraph(f"GPA: {e.gpa}")
                bullets(e.achievements)
                if e.coursework:
                    doc.add_paragraph("Coursework: " + ", ".join(e.coursework))
                bullets(e.bullets)

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()
