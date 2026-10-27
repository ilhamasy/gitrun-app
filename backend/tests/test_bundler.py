import pytest
import tempfile
from pathlib import Path
from backend.ingestion.bundler import RepomixBundler


def test_bundler_creates_xml():
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = Path(temp_dir) / "sample-app"
        repo_dir.mkdir()
        (repo_dir / "index.ts").write_text("export const answer = 42;", encoding="utf-8")
        (repo_dir / "config.json").write_text('{"env": "test"}', encoding="utf-8")
        (repo_dir / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")  # Binary to ignore

        work_dir = Path(temp_dir) / "work"
        bundler = RepomixBundler(temp_dir=work_dir)

        bundle_path = bundler.bundle(repo_dir=repo_dir, repo_name="sample-app")

        assert bundle_path.exists()
        assert bundle_path.is_file()
        content = bundle_path.read_text(encoding="utf-8")

        assert 'path="index.ts"' in content
        assert "export const answer = 42;" in content
        assert 'path="config.json"' in content
        # Binary file must be excluded
        assert "image.png" not in content
