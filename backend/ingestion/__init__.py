"""
GoWiki Backend Ingestion Engine.
Clones repositories, bundles with Repomix, synthesizes documentation via LLM,
and indexes headings into PageIndex trees.
"""

from backend.ingestion.cloner import RepoCloner
from backend.ingestion.bundler import RepomixBundler
from backend.ingestion.synthesizer import DocSynthesizer
from backend.ingestion.pipeline import IngestionPipeline
from backend.ingestion.system_pipeline import SystemIngestionPipeline
from backend.ingestion.mesh import SystemSynthesizer, CrossRepoMeshExtractor

__all__ = [
    "RepoCloner",
    "RepomixBundler",
    "DocSynthesizer",
    "IngestionPipeline",
    "SystemIngestionPipeline",
    "SystemSynthesizer",
    "CrossRepoMeshExtractor",
]
