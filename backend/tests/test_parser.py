import pytest
from backend.pageindex.parser import (
    slugify_heading,
    plain_heading_text,
    split_document_numeral,
    parse_markdown_sections,
    extract_section_by_node_id,
)


def test_slugify_heading():
    assert slugify_heading("Core Capabilities") == "core-capabilities"
    assert slugify_heading("Response `201 Created`") == "response-201-created"
    assert slugify_heading("1. Create Payment Intent") == "1-create-payment-intent"
    assert slugify_heading("Database Schema & Partitioning") == "database-schema-partitioning"
    assert slugify_heading("  Extra   Spaces  ") == "extra-spaces"


def test_plain_heading_text():
    assert plain_heading_text("Response `201 Created`") == "Response 201 Created"
    assert plain_heading_text("**Bold** and _italic_") == "Bold and italic"


def test_split_document_numeral():
    code, text = split_document_numeral("1. Create Payment Intent")
    assert code == "1"
    assert text == "Create Payment Intent"

    code, text = split_document_numeral("2.4.5 Nested Section")
    assert code == "2.4.5"
    assert text == "Nested Section"

    code, text = split_document_numeral("No Numeral Here")
    assert code is None
    assert text == "No Numeral Here"


def test_parse_markdown_sections():
    sample_md = """# Document Title

Introductory paragraphs before any H2 section.

## Core Capabilities

- High availability
- Distributed locks

### Sub Details

Inner details that should belong to Core Capabilities.

## Second Section

Information about the second section.
"""

    sections = parse_markdown_sections(sample_md, slug="overview", target_levels=(2,))
    assert len(sections) == 2

    assert sections[0].node_id == "overview#core-capabilities"
    assert sections[0].title == "Core Capabilities"
    assert sections[0].level == 2
    assert "High availability" in sections[0].content
    assert "Inner details that should belong to Core Capabilities" in sections[0].content

    assert sections[1].node_id == "overview#second-section"
    assert sections[1].title == "Second Section"
    assert "Information about the second section" in sections[1].content


def test_extract_section_by_node_id():
    sample_md = """## First Block
Content A

## Second Block
Content B
"""
    node = extract_section_by_node_id(sample_md, slug="test", target_node_id="test#second-block")
    assert node is not None
    assert node.title == "Second Block"
    assert "Content B" in node.content
