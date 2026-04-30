from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
E2E_DIR = REPO_ROOT / "web-dashboard" / "tests" / "e2e"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_playwright_suite_has_no_ad_hoc_debug_specs() -> None:
    debug_specs = sorted(path.name for path in E2E_DIR.glob("debug-*.spec.ts"))

    assert debug_specs == []


def test_playwright_suite_has_no_machine_local_paths_or_obsolete_test_accounts() -> None:
    stale_tokens = [
        "/media/younghwan/",
        "testtest@test.com",
        "3644@3644",
        "debug-infinite-loading-signing-in-during-login",
        "--get-latest",
    ]
    offenders: list[str] = []

    for path in sorted(E2E_DIR.glob("*.spec.ts")):
        text = _read(path)
        for token in stale_tokens:
            if token in text:
                offenders.append(f"{path.relative_to(REPO_ROOT)} contains {token!r}")

    assert offenders == []


def test_circle_e2e_mocks_match_paginated_content_contract() -> None:
    circle1 = _read(E2E_DIR / "circle1.frontend-frontend.spec.ts")
    circle3 = _read(E2E_DIR / "circle3.db-backend-frontend.spec.ts")

    assert "items: [" in circle1
    assert "has_more: false" in circle1
    assert "const backendItems = backendPayload.items" in circle3
