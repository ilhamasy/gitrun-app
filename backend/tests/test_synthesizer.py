import json
import pytest
import tempfile
from pathlib import Path
from backend.ingestion.synthesizer import DocSynthesizer


@pytest.mark.asyncio
async def test_synthesizer_pass1_and_pass2():
    with tempfile.TemporaryDirectory() as temp_dir:
        content_dir = Path(temp_dir) / "content"
        bundle_file = Path(temp_dir) / "test-repo-bundle.xml"
        bundle_file.write_text(
            """<repository name="test-repo">
<file path="main.go">package main; func main() {}</file>
<file path="handler.go">package main; func Handle() {}</file>
</repository>""",
            encoding="utf-8",
        )

        synthesizer = DocSynthesizer(content_dir=content_dir)

        # Pass 1: TOC Generation
        toc = await synthesizer.pass1_generate_toc("test-repo", bundle_file)
        assert toc["repo_name"] == "test-repo"
        assert len(toc["pages"]) == 4
        assert (content_dir / "test-repo" / "toc.json").exists()

        # Pass 2: Parallel Page Generation
        pages = await synthesizer.pass2_generate_pages("test-repo", bundle_file, toc)
        assert len(pages) == 4

        for slug in ["overview", "architecture", "setup", "api-reference"]:
            md_path = content_dir / "test-repo" / f"{slug}.md"
            assert md_path.exists()
            text = md_path.read_text(encoding="utf-8")
            # Must contain top level heading and at least one secondary section
            assert text.startswith("# ")
            assert "## " in text
