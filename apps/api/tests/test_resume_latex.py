import pytest

from app.resume import Resume
from app.resume_latex import DialectError, resume_to_tex, tex_to_resume


def sample() -> Resume:
    return Resume.model_validate({
        "contact": {
            "name": "Yash Bakshi", "subtitle": "Backend Engineer", "email": "y@asu.edu",
            "phone": "623-275-5694", "location": "Tempe, AZ", "tags": ["Open to work"],
            "links": [{"label": "GitHub", "url": "https://github.com/y-bakshi/a_b?x=1&y=2#top"}],
        },
        "skills": [{"name": "Languages", "skills": ["Java", "C/C++17", "Pub/Sub"]}],
        "experience": [{
            "company": "Thryv", "role": "Intern", "location": "Tempe, AZ",
            "start": "May 2026", "end": "Aug 2026", "summary": "",
            "bullets": ["Cut costs 30% & latency {p99} by ~5x", r"Used C:\temp and $HOME_DIR ^caret #1"],
        }],
        "projects": [{"name": "CV Studio", "link_text": "repo", "organization": "", "location": "",
                      "start": "", "end": "", "bullets": ["Built a LaTeX editor"]}],
        "education": [{
            "school": "ASU", "degree": "M.S.", "location": "", "start": "Jan 2025", "end": "Dec 2026",
            "gpa": "4.0", "achievements": ["Dean's list"], "coursework": ["Cloud Computing", "DSA"],
            "bullets": [],
        }],
        "section_order": ["education", "skills", "experience", "projects"],
    })


def test_json_to_latex_to_json_round_trips_exactly():
    resume = sample()
    parsed = tex_to_resume(resume_to_tex(resume))
    assert parsed.resume == resume


def test_ids_survive_and_are_optional():
    resume = sample()
    tex = resume_to_tex(resume)
    assert f"[{resume.experience[0].id}]" in tex
    stripped = tex.replace(f"[{resume.experience[0].id}]", "")
    assert tex_to_resume(stripped).resume.experience[0].company == "Thryv"


def test_editing_inside_the_dialect_updates_json():
    tex = resume_to_tex(sample()).replace("{Thryv}", "{Thryv Inc}")
    tex += ""
    assert tex_to_resume(tex).resume.experience[0].company == "Thryv Inc"


def test_custom_preamble_is_preserved_not_parsed():
    tex = resume_to_tex(sample(), preamble="\\documentclass{article}\n\\usepackage{mathpazo}")
    assert tex_to_resume(tex).preamble.endswith(r"\usepackage{mathpazo}")


def test_raw_tex_outside_dialect_is_rejected_with_line_number():
    tex = resume_to_tex(sample()).replace(r"\end{document}", "\\textbf{custom}\n\\end{document}")
    with pytest.raises(DialectError, match="unsupported command"):
        tex_to_resume(tex)
    tex = resume_to_tex(sample()).replace(r"\end{document}", "loose text\n\\end{document}")
    with pytest.raises(DialectError, match="outside"):
        tex_to_resume(tex)


def test_orphan_bullet_is_rejected():
    tex = resume_to_tex(Resume()).replace(
        r"\end{document}", "\\resumebullet{x}\n\\end{document}")
    with pytest.raises(DialectError, match="must follow"):
        tex_to_resume(tex)


def test_empty_sections_are_omitted_but_order_is_restored():
    resume = Resume.model_validate({"contact": {"name": "A"}})
    tex = resume_to_tex(resume)
    assert "\\resumesection[" not in tex
    assert tex_to_resume(tex).resume == resume
