import json
import pytest
import tempfile
from pathlib import Path
from backend.ingestion.pipeline import IngestionPipeline


@pytest.mark.asyncio
async def test_ingestion_pipeline_run():
    with tempfile.TemporaryDirectory() as temp_dir:
        src_repo = Path(temp_dir) / "mini-service"
        src_repo.mkdir()
        (src_repo / "main.py").write_text("def run(): pass", encoding="utf-8")

        content_dir = Path(temp_dir) / "content"
        work_dir = Path(temp_dir) / "work"

        pipeline = IngestionPipeline(
            content_dir=content_dir,
            temp_dir=work_dir,
        )

        events = []
        async for ev in pipeline.run(source=str(src_repo)):
            events.append(ev)

        event_names = [e.event for e in events]
        assert "step" in event_names
        assert "done" in event_names

        steps = [e.data.get("step") for e in events if e.event == "step"]
        assert "clone" in steps
        assert "bundle" in steps
        assert "toc" in steps
        assert "doc_gen" in steps
        assert "pageindex" in steps

        done_event = next(e for e in events if e.event == "done")
        assert done_event.data["repo"] == "mini-service"
        assert done_event.data["redirect"] == "/wiki/mini-service/overview"

        # Check output artifacts
        repo_content = content_dir / "mini-service"
        assert (repo_content / "toc.json").exists()
        assert (repo_content / "overview.md").exists()
        assert (repo_content / "architecture.md").exists()
        assert (repo_content / "setup.md").exists()
        assert (repo_content / "api-reference.md").exists()
        assert (repo_content / "pageindex_tree.json").exists()

        tree_data = json.loads((repo_content / "pageindex_tree.json").read_text(encoding="utf-8"))
        assert tree_data["repo"] == "mini-service"
        assert len(tree_data["nodes"]) >= 4
