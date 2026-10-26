"""
PageIndex Tree Search & Reasoning Engine.
"""

from backend.pageindex.parser import (
    SectionNode,
    extract_section_by_node_id,
    parse_markdown_sections,
    plain_heading_text,
    slugify_heading,
    split_document_numeral,
)
from backend.pageindex.indexer import TreeIndexer
from backend.pageindex.llm import LLMClient, fallback_summarize

__all__ = [
    "SectionNode",
    "extract_section_by_node_id",
    "parse_markdown_sections",
    "plain_heading_text",
    "slugify_heading",
    "split_document_numeral",
    "TreeIndexer",
    "LLMClient",
    "fallback_summarize",
]
