"""Two-way conversion between ``Resume`` JSON and a structured LaTeX dialect.

The generated document is built from a fixed set of ``\\resume...`` macros so
that it can be parsed back into JSON exactly. Anything the parser does not
understand raises ``DialectError`` instead of being guessed at, which is how
callers know a hand-edited ``.tex`` has left the dialect.

Layout of a generated file::

    %%% BEGIN PREAMBLE   <- free-form; stored as-is, never parsed
    %%% END PREAMBLE
    %%% BEGIN MACROS     <- managed; defines the \\resume... macros
    %%% END MACROS
    \\begin{document}
    ...dialect body (parsed)...
    \\end{document}
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .resume import Contact, Resume

PREAMBLE_BEGIN = "%%% BEGIN PREAMBLE (free-form: packages, fonts, margins)"
PREAMBLE_END = "%%% END PREAMBLE"
MACROS_BEGIN = "%%% BEGIN MACROS (managed by CV Studio)"
MACROS_END = "%%% END MACROS"

DEFAULT_PREAMBLE = r"""\documentclass[10pt,letterpaper]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[margin=0.55in]{geometry}
\usepackage{xcolor}
\usepackage{titlesec}
\usepackage[hidelinks]{hyperref}
\usepackage[scaled=0.92]{helvet}
\renewcommand{\familydefault}{\sfdefault}
\setlength{\parindent}{0pt}
\titleformat{\section}{\bfseries\large\MakeUppercase}{}{0pt}{}[\titlerule]
\titlespacing{\section}{0pt}{7pt}{3pt}
\input{glyphtounicode}
\pdfgentounicode=1"""

MACROS = r"""\newif\ifskillfirst
\newif\ifcoursefirst
\newcommand{\resumecontact}[5]{\begin{center}{\LARGE\bfseries #1}\\ #2\\ #3 \textbar\ #4 \textbar\ #5\end{center}}
\newcommand{\resumetag}[1]{{\small #1}\quad}
\newcommand{\resumelink}[3][]{\href{#3}{#2}\quad}
\newcommand{\resumesection}[2][]{\section{#2}}
\newcommand{\skillgroup}[2][]{\par\noindent\textbf{#2:}\ \skillfirsttrue}
\newcommand{\resumeskill}[1]{\ifskillfirst\skillfirstfalse\else, \fi #1}
\newcommand{\resumeentry}[7][]{\par\medskip\noindent\textbf{#2}\par\noindent\textit{#3}\hfill #4\ $\cdot$\ #5 -- #6\par #7\par}
\newcommand{\resumeproject}[7][]{\par\medskip\noindent\textbf{#2} #3\hfill #6 -- #7\par\noindent\textit{#4}\hfill #5\par}
\newcommand{\resumeeducation}[7][]{\par\medskip\noindent\textbf{#2}\hfill #5 -- #6\par\noindent\textit{#3}\hfill #4\par\ifx\relax#7\relax\else GPA: #7\par\fi\coursefirsttrue}
\newcommand{\resumeachievement}[1]{\par\noindent #1}
\newcommand{\resumecourse}[1]{\ifcoursefirst\par\noindent\textit{Coursework:} \coursefirstfalse\else, \fi #1}
\newcommand{\resumebullet}[1]{\par\noindent\hangindent=1.2em\hangafter=1 \textbullet\ #1\par}"""


class DialectError(ValueError):
    """Raised when LaTeX falls outside the structured dialect."""

    def __init__(self, message: str, line: int | None = None):
        super().__init__(f"line {line}: {message}" if line else message)
        self.line = line


# ---------------------------------------------------------------- escaping

_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
    "{": r"\{", "}": r"\}",
    "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
}
_UNESCAPE = re.compile(
    r"\\textbackslash\{\}|\\textasciitilde\{\}|\\textasciicircum\{\}|\\([&%$#_{}])"
)
_UNESCAPED = {
    r"\textbackslash{}": "\\",
    r"\textasciitilde{}": "~",
    r"\textasciicircum{}": "^",
}


def escape(text: str) -> str:
    return "".join(_ESCAPES.get(char, char) for char in text)


def unescape(text: str) -> str:
    return _UNESCAPE.sub(lambda m: m.group(1) or _UNESCAPED[m.group(0)], text)


# -------------------------------------------------------------- generation

def _m(name: str, *args: str, ident: str | None = None) -> str:
    opt = f"[{ident}]" if ident else ""
    return f"\\{name}{opt}" + "".join("{" + escape(a) + "}" for a in args)


def _bullets(items: list[str]) -> list[str]:
    return [_m("resumebullet", item) for item in items]


def resume_to_tex(resume: Resume, preamble: str | None = None) -> str:
    c = resume.contact
    body: list[str] = [_m("resumecontact", c.name, c.subtitle, c.email, c.phone, c.location)]
    body += [_m("resumetag", tag) for tag in c.tags]
    body += [_m("resumelink", link.label, link.url, ident=link.id) for link in c.links]

    def skills() -> list[str]:
        lines = []
        for group in resume.skills:
            lines.append(_m("skillgroup", group.name, ident=group.id))
            lines += [_m("resumeskill", skill) for skill in group.skills]
        return lines

    def experience() -> list[str]:
        lines = []
        for e in resume.experience:
            lines.append(_m("resumeentry", e.company, e.role, e.location, e.start, e.end, e.summary, ident=e.id))
            lines += _bullets(e.bullets)
        return lines

    def projects() -> list[str]:
        lines = []
        for p in resume.projects:
            lines.append(_m("resumeproject", p.name, p.link_text, p.organization, p.location, p.start, p.end, ident=p.id))
            lines += _bullets(p.bullets)
        return lines

    def education() -> list[str]:
        lines = []
        for e in resume.education:
            lines.append(_m("resumeeducation", e.school, e.degree, e.location, e.start, e.end, e.gpa, ident=e.id))
            lines += [_m("resumeachievement", a) for a in e.achievements]
            lines += [_m("resumecourse", course) for course in e.coursework]
            lines += _bullets(e.bullets)
        return lines

    builders = {
        "skills": ("Skills", skills),
        "experience": ("Professional Experience", experience),
        "projects": ("Projects", projects),
        "education": ("Education", education),
    }
    order = [n for n in resume.section_order if n in builders]
    order += [n for n in builders if n not in order]
    for name in order:
        title, build = builders[name]
        lines = build()
        if lines:
            body.append("")
            body.append(_m("resumesection", title, ident=name))
            body += lines

    return "\n".join([
        PREAMBLE_BEGIN, (preamble or DEFAULT_PREAMBLE).strip("\n"), PREAMBLE_END,
        MACROS_BEGIN, MACROS, MACROS_END,
        r"\begin{document}", r"\pagenumbering{gobble}", "",
        *body, "", r"\end{document}", "",
    ])


# ------------------------------------------------------------------ parsing

# macro name -> (number of mandatory args, accepts optional [id])
_MACROS: dict[str, tuple[int, bool]] = {
    "resumecontact": (5, False),
    "resumetag": (1, False),
    "resumelink": (2, True),
    "resumesection": (1, True),
    "skillgroup": (1, True),
    "resumeskill": (1, False),
    "resumeentry": (6, True),
    "resumeproject": (6, True),
    "resumeeducation": (6, True),
    "resumeachievement": (1, False),
    "resumecourse": (1, False),
    "resumebullet": (1, False),
    "pagenumbering": (1, False),  # emitted by the generator; ignored
}


@dataclass
class ParsedTex:
    resume: Resume
    preamble: str


class _Reader:
    def __init__(self, text: str, line_offset: int):
        self.text, self.pos, self.line_offset = text, 0, line_offset

    def line(self) -> int:
        return self.line_offset + self.text.count("\n", 0, self.pos) + 1

    def skip_space(self) -> None:
        while self.pos < len(self.text) and self.text[self.pos].isspace():
            self.pos += 1

    def group(self, open_: str, close: str) -> str:
        self.skip_space()
        if self.text[self.pos : self.pos + 1] != open_:
            raise DialectError(f"expected {open_!r}", self.line())
        start, depth = self.pos + 1, 0
        i = self.pos
        while i < len(self.text):
            char = self.text[i]
            if char == "\\":
                i += 2
                continue
            if char == open_:
                depth += 1
            elif char == close:
                depth -= 1
                if depth == 0:
                    self.pos = i + 1
                    return self.text[start:i]
            i += 1
        raise DialectError(f"unclosed {open_!r}", self.line())


def _tokens(body: str, line_offset: int):
    reader = _Reader(body, line_offset)
    while True:
        reader.skip_space()
        if reader.pos >= len(body):
            return
        char = body[reader.pos]
        if char == "%":
            newline = body.find("\n", reader.pos)
            reader.pos = len(body) if newline < 0 else newline + 1
            continue
        if char != "\\":
            raise DialectError("text outside a \\resume... command", reader.line())
        line = reader.line()
        match = re.compile(r"\\([A-Za-z]+)").match(body, reader.pos)
        name = match.group(1) if match else ""
        if name not in _MACROS:
            raise DialectError(f"unsupported command \\{name}" if name else "stray backslash", line)
        reader.pos = match.end()
        count, allows_id = _MACROS[name]
        ident = None
        if allows_id:
            save = reader.pos
            reader.skip_space()
            if body[reader.pos : reader.pos + 1] == "[":
                ident = reader.group("[", "]").strip()
            else:
                reader.pos = save
        args = [unescape(reader.group("{", "}")).strip() for _ in range(count)]
        yield line, name, ident, args


def tex_to_resume(tex: str) -> ParsedTex:
    """Parse dialect LaTeX back into a ``Resume`` (raises ``DialectError``)."""
    pre = re.search(
        re.escape(PREAMBLE_BEGIN) + r"\n(.*?)\n?" + re.escape(PREAMBLE_END), tex, re.S
    )
    begin, end = tex.find(r"\begin{document}"), tex.rfind(r"\end{document}")
    if not pre or begin < 0 or end < begin:
        raise DialectError("missing preamble markers or document environment")
    body_start = begin + len(r"\begin{document}")
    line_offset = tex.count("\n", 0, body_start)

    contact: Contact | None = None
    tags: list[str] = []
    links: list[dict] = []
    data: dict[str, list] = {"skills": [], "experience": [], "projects": [], "education": []}
    order: list[str] = []
    entry: dict | None = None

    def need(target: dict | None, line: int, what: str) -> dict:
        if target is None:
            raise DialectError(f"{what} must follow an entry it belongs to", line)
        return target

    group: dict | None = None
    for line, name, ident, a in _tokens(tex[body_start:end], line_offset):
        with_id = {"id": ident} if ident else {}
        if name == "pagenumbering":
            continue
        elif name == "resumecontact":
            contact = Contact(name=a[0], subtitle=a[1], email=a[2], phone=a[3], location=a[4])
        elif name == "resumetag":
            tags.append(a[0])
        elif name == "resumelink":
            links.append({**with_id, "label": a[0], "url": a[1]})
        elif name == "resumesection":
            if ident not in data:
                raise DialectError(f"unknown section [{ident}]", line)
            if ident not in order:
                order.append(ident)
        elif name == "skillgroup":
            group = {**with_id, "name": a[0], "skills": []}
            data["skills"].append(group)
        elif name == "resumeskill":
            need(group, line, r"\resumeskill")["skills"].append(a[0])
        elif name == "resumeentry":
            entry = {**with_id, "company": a[0], "role": a[1], "location": a[2],
                     "start": a[3], "end": a[4], "summary": a[5], "bullets": []}
            data["experience"].append(entry)
        elif name == "resumeproject":
            entry = {**with_id, "name": a[0], "link_text": a[1], "organization": a[2],
                     "location": a[3], "start": a[4], "end": a[5], "bullets": []}
            data["projects"].append(entry)
        elif name == "resumeeducation":
            entry = {**with_id, "school": a[0], "degree": a[1], "location": a[2],
                     "start": a[3], "end": a[4], "gpa": a[5],
                     "achievements": [], "coursework": [], "bullets": []}
            data["education"].append(entry)
        elif name == "resumebullet":
            need(entry, line, r"\resumebullet")["bullets"].append(a[0])
        elif name in ("resumeachievement", "resumecourse"):
            key = "achievements" if name == "resumeachievement" else "coursework"
            target = need(entry, line, "\\" + name)
            if key not in target:
                raise DialectError(f"\\{name} is only valid in education", line)
            target[key].append(a[0])

    if contact is None:
        raise DialectError(r"missing \resumecontact")
    order += [n for n in Resume.DEFAULT_ORDER if n not in order]
    resume = Resume.model_validate({
        "contact": {**contact.model_dump(), "tags": tags, "links": links},
        **data,
        "section_order": order,
    })
    return ParsedTex(resume=resume, preamble=pre.group(1).strip("\n"))
