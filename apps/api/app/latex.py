from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .config import settings


def compile_tex(source: str, output_path: Path) -> tuple[bool, str]:
    """Compile source in an isolated temporary directory and copy the PDF out."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cvstudio-") as temporary:
        work = Path(temporary)
        tex = work / "resume.tex"
        tex.write_text(source, encoding="utf-8")
        env = {**os.environ, "openin_any": "p", "openout_any": "p", "TEXMFOUTPUT": str(work)}
        command = [
            "pdflatex",
            "-no-shell-escape",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-synctex=1",
            "resume.tex",
        ]
        logs: list[str] = []
        try:
            for _ in range(2):
                result = subprocess.run(command, cwd=work, env=env, capture_output=True, text=True, timeout=settings.compile_timeout_seconds)
                logs.append(result.stdout[-30000:] + result.stderr[-5000:])
                if result.returncode != 0:
                    return False, "\n".join(logs)
            shutil.copy2(work / "resume.pdf", output_path)
            return True, "\n".join(logs)
        except (subprocess.TimeoutExpired, FileNotFoundError) as error:
            return False, f"Compilation failed: {error}"
