from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings:
    database_url = os.getenv(
        "DATABASE_URL", f"sqlite:///{PROJECT_ROOT / 'cv-studio.db'}"
    )
    artifact_root = Path(
        os.getenv("ARTIFACT_ROOT", str(PROJECT_ROOT / "artifacts"))
    ).resolve()
    session_cookie = "cvstudio_session"
    session_days = int(os.getenv("SESSION_DAYS", "30"))
    frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    secure_cookies = os.getenv("SECURE_COOKIES", "false").lower() == "true"
    compile_timeout_seconds = int(os.getenv("COMPILE_TIMEOUT_SECONDS", "20"))


settings = Settings()
settings.artifact_root.mkdir(parents=True, exist_ok=True)

