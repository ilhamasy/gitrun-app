"""
Test isolation.

`backend/main.py` resolves CONTENT_DIR/TEMP_DIR from the environment (seeded by
`backend/.env`), so an unguarded test run would write generated wikis into the
real `content/` board. Every test therefore runs against a throwaway content
directory seeded from `backend/tests/fixtures/content`.

The LLM is switched off as well: `backend/.env` carries a live ROUTER_API_KEY,
and letting the suite call it would make results non-deterministic, slow, and
dependent on the network. `load_dotenv()` does not override variables that are
already set, so assigning these before `backend.main` is imported wins.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import pytest

FIXTURE_CONTENT_DIR = Path(__file__).parent / "fixtures" / "content"

# Repo sandbox root: created once, removed when the interpreter exits.
_SANDBOX = Path(tempfile.mkdtemp(prefix="gowiki-tests-"))


def _seed_content_dir() -> Path:
    """Reset the sandbox to exactly the fixture wikis."""
    content_dir = _SANDBOX / "content"
    if content_dir.exists():
        shutil.rmtree(content_dir)
    content_dir.mkdir(parents=True, exist_ok=True)
    for repo_dir in FIXTURE_CONTENT_DIR.iterdir():
        if repo_dir.is_dir():
            shutil.copytree(repo_dir, content_dir / repo_dir.name, dirs_exist_ok=True)
    return content_dir


TEST_CONTENT_DIR = _seed_content_dir()
TEST_TEMP_DIR = _SANDBOX / "temp"
TEST_TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Must precede any `backend.main` import.
os.environ["CONTENT_DIR"] = str(TEST_CONTENT_DIR)
os.environ["TEMP_DIR"] = str(TEST_TEMP_DIR)
for _key in ("ROUTER_API_KEY", "OPENAI_API_KEY"):
    os.environ[_key] = ""


@pytest.fixture(autouse=True)
def _prune_generated_repos():
    """Drop wikis a test generated, so each test sees only the fixtures."""
    yield
    for repo_dir in TEST_CONTENT_DIR.iterdir():
        shutil.rmtree(repo_dir, ignore_errors=True)
        fixture = FIXTURE_CONTENT_DIR / repo_dir.name
        if fixture.exists():
            shutil.copytree(fixture, repo_dir)


@pytest.fixture(scope="session")
def content_dir() -> Path:
    """The throwaway content directory every test reads and writes."""
    return TEST_CONTENT_DIR


@pytest.fixture(scope="session")
def temp_dir() -> Path:
    """The throwaway working directory for clones and bundles."""
    return TEST_TEMP_DIR


@pytest.fixture(scope="session")
def repo_content_dir() -> Path:
    """The real `content/` board shipped with the app, for isolation checks."""
    return Path(__file__).resolve().parents[2] / "content"
