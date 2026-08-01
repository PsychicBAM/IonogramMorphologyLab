"""Regression tests for git ls-files -z path handling in hygiene scanner."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_repository_hygiene.py"


def _load_hygiene():
    spec = importlib.util.spec_from_file_location("check_repository_hygiene", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def git_repo(tmp_path: Path):
    """Initialize a tiny git repository for path-handling tests."""
    subprocess.check_call(["git", "init"], cwd=tmp_path, stdout=subprocess.DEVNULL)
    subprocess.check_call(
        ["git", "config", "user.email", "hygiene-test@example.com"],
        cwd=tmp_path,
        stdout=subprocess.DEVNULL,
    )
    subprocess.check_call(
        ["git", "config", "user.name", "Hygiene Test"],
        cwd=tmp_path,
        stdout=subprocess.DEVNULL,
    )
    # Avoid global hooks interfering
    subprocess.check_call(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=tmp_path,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return tmp_path


def _git_add_commit(repo: Path, rel: str, content: str = "ok\n") -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    subprocess.check_call(["git", "add", "--", rel], cwd=repo, stdout=subprocess.DEVNULL)
    subprocess.check_call(
        ["git", "commit", "-m", f"add {rel}"],
        cwd=repo,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def test_unicode_tracked_filename(git_repo: Path):
    hyg = _load_hygiene()
    rel = "docs/пример_файла.md"
    _git_add_commit(git_repo, rel, "# пример\n")
    paths = list(hyg.tracked_files(git_repo))
    assert any(p.name == "пример_файла.md" for p in paths)
    code, errors, _ = hyg.scan_repository(git_repo)
    assert code == 0
    assert errors == []


def test_filename_containing_spaces(git_repo: Path):
    hyg = _load_hygiene()
    rel = "docs/my spaced file.md"
    _git_add_commit(git_repo, rel, "# spaced\n")
    paths = [p.relative_to(git_repo).as_posix() for p in hyg.tracked_files(git_repo)]
    assert "docs/my spaced file.md" in paths
    code, errors, _ = hyg.scan_repository(git_repo)
    assert code == 0
    assert errors == []


def test_git_path_non_ascii_text(git_repo: Path):
    hyg = _load_hygiene()
    rel = "src/данные/модуль.py"
    _git_add_commit(git_repo, rel, "VALUE = 1\n")
    rels = [os.fsdecode(os.fsencode(p.relative_to(git_repo).as_posix())) for p in hyg.tracked_files(git_repo)]
    assert any("данные" in r and "модуль.py" in r for r in rels)
    # Ensure NUL-split decode did not produce quoted garbage paths
    for p in hyg.tracked_files(git_repo):
        assert '"' not in p.name
        assert p.exists()


def test_missing_tracked_file_is_controlled_violation(git_repo: Path):
    hyg = _load_hygiene()
    rel = "docs/will_vanish.md"
    _git_add_commit(git_repo, rel, "# temp\n")
    (git_repo / rel).unlink()
    # Index still lists the path; working tree file is gone
    code, errors, counts = hyg.scan_repository(git_repo)
    assert code == 1
    assert counts["missing_tracked"] >= 1
    assert any(e.startswith("missing tracked path:") and "will_vanish.md" in e for e in errors)


def test_hygiene_scan_returns_controlled_violation_not_crash(git_repo: Path):
    hyg = _load_hygiene()
    # Build the detectable secret pattern at runtime so this tracked test source
    # never contains the complete literal that the hygiene SECRET regex matches.
    credential_name = "".join(("api", "_", "key"))
    credential_value = "x" * 32
    payload = f"{credential_name} = '{credential_value}'\n"
    _git_add_commit(git_repo, "docs/leak.md", payload)
    try:
        code, errors, counts = hyg.scan_repository(git_repo)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"hygiene scan crashed: {exc}")
    assert code == 1
    assert counts["possible_secret"] >= 1
    # Avoid writing the contiguous scanner match (word + ':' + quote) in this file.
    marker = "possible " + "secret" + ":"
    assert any(marker in e and "leak.md" in e for e in errors)
