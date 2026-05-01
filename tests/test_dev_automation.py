"""Regression tests for local developer automation scripts."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _copy_dev_script_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / "web-dashboard").mkdir()
    (root / "browser-extension").mkdir()
    shutil.copy2(REPO_ROOT / "scripts" / "run-stack.sh", root / "scripts" / "run-stack.sh")
    return root


def test_run_stack_setup_creates_complete_local_env_without_installing(tmp_path: Path) -> None:
    root = _copy_dev_script_fixture(tmp_path)

    result = subprocess.run(
        ["bash", "scripts/run-stack.sh", "setup", "--skip-install"],
        cwd=root,
        env={**os.environ, "BRIEFLY_ROOT_DIR": str(root)},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout

    root_env = (root / ".env").read_text(encoding="utf-8")
    web_env = (root / "web-dashboard" / ".env").read_text(encoding="utf-8")
    extension_env = (root / "browser-extension" / ".env").read_text(encoding="utf-8")

    assert "JWT_SECRET_KEY=" in root_env
    assert "ENCRYPTION_KEY=" in root_env
    assert "EMAIL_LOOKUP_KEY=" in root_env
    assert "SMTP_HOST=localhost" in root_env
    assert "SMTP_PORT=1025" in root_env
    assert "APP_BASE_URL=http://localhost:3001" in root_env
    assert "ALLOWED_ORIGINS=http://localhost:3001" in root_env
    assert "DATABASE_URL=sqlite+aiosqlite:///./briefly.db" in root_env
    assert "VITE_API_BASE_URL=/api" in web_env
    assert "VITE_API_BASE_URL=http://localhost:8000" in extension_env


def test_start_dev_entrypoint_delegates_to_run_stack() -> None:
    entrypoint = REPO_ROOT / "start-dev.sh"

    assert entrypoint.exists()
    assert entrypoint.stat().st_mode & stat.S_IXUSR
    assert 'exec "$ROOT_DIR/scripts/run-stack.sh" "$@"' in entrypoint.read_text(encoding="utf-8")


def test_create_test_user_uses_env_backed_email_lookup_key() -> None:
    script = (REPO_ROOT / "scripts" / "create_test_user.py").read_text(encoding="utf-8")

    assert "EMAIL_LOOKUP_KEY" in script
    assert "LOOKUP_KEY = b" not in script
