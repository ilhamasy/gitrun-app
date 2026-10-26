"""
Markdown AST and section parser for PageIndex tree engine.
Maintains exact slugification and heading parity with lib/stations.ts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

DOCUMENT_NUMERAL = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+")
HEADING_LINE = re.compile(r"^(#{1,6})\s+(.+)$")

def slugify_heading(text: str) -> str:
    r"""
    Match lib/stations.ts slugifyHeading:
    text.toLowerCase().replace(/[`*_~]/g, "").replace(/[^\w\s-]/g, "").trim().replace(/\s+/g, "-").replace(/-+/g, "-")
    """
    s = text.lower()
    s = re.sub(r"[`*_~]", "", s)
    s = re.sub(r"[^\w\s-]", "", s)
    s = s.strip()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s

def plain_heading_text(text: str) -> str:
    r"""
    Match lib/stations.ts plainHeadingText:
    text.replace(/[`*_~]/g, "").replace(/\s+/g, " ").trim()
    """
    s = re.sub(r"[`*_~]", "", text)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def split_document_numeral(text: str) -> Tuple[Optional[str], str]:
    """
    Match lib/stations.ts splitDocumentNumeral:
    Separates leading numerals (e.g. '1. Create Payment Intent') from display text.
    """
    match = DOCUMENT_NUMERAL.match(text)
    if not match:
        return None, text
    return match.group(1), text[match.end() :]


@dataclass
class SectionNode:
    node_id: str
    file: str
    slug: str
    anchor: str
    title: str
    level: int
    content: str
    raw_heading: str


def parse_markdown_sections(
    markdown: str,
    slug: str,
    target_levels: Tuple[int, ...] = (2,),
) -> List[SectionNode]:
    """
    Parses a markdown document into distinct sections.
    Each section starts with a heading in target_levels (e.g. H2)
    and captures all text up to the next heading of equal or higher level.
    """
    lines = markdown.split("\n")
    sections: List[SectionNode] = []

    current_raw: Optional[str] = None
    current_level: int = 0
    current_lines: List[str] = []

    def flush_current():
        nonlocal current_raw, current_level, current_lines
        if current_raw is not None and current_level in target_levels:
            raw_title = current_raw.strip()
            anchor = slugify_heading(raw_title)
            _, display_text = split_document_numeral(raw_title)
            title = plain_heading_text(display_text)
            content = "\n".join(current_lines).strip()
            node_id = f"{slug}#{anchor}"

            sections.append(
                SectionNode(
                    node_id=node_id,
                    file=f"{slug}.md",
                    slug=slug,
                    anchor=anchor,
                    title=title,
                    level=current_level,
                    content=content,
                    raw_heading=current_raw,
                )
            )

    for line in lines:
        match = HEADING_LINE.match(line)
        if match:
            level = len(match.group(1))
            raw_heading = match.group(2).strip()

            # If this heading is at or above the current section level, close previous section
            if current_raw is not None:
                if level <= current_level:
                    flush_current()
                    if level in target_levels:
                        current_raw = raw_heading
                        current_level = level
                        current_lines = [line]
                    else:
                        current_raw = None
                        current_level = 0
                        current_lines = []
                    continue
                else:
                    # Subheading (e.g. H3 inside H2), append to current section
                    current_lines.append(line)
                    continue

            # No current active section, start one if it matches target_levels
            if level in target_levels:
                current_raw = raw_heading
                current_level = level
                current_lines = [line]
        else:
            if current_raw is not None:
                current_lines.append(line)

    flush_current()
    return sections


def extract_section_by_node_id(
    markdown: str,
    slug: str,
    target_node_id: str,
    target_levels: Tuple[int, ...] = (2, 3),
) -> Optional[SectionNode]:
    """
    Extracts the exact section text for a given node_id from the markdown document.
    """
    # Accept both full node_id ('slug#anchor') or bare anchor ('anchor')
    target_anchor = target_node_id.split("#")[-1] if "#" in target_node_id else target_node_id

    sections = parse_markdown_sections(markdown, slug, target_levels=(2, 3))
    for s in sections:
        if s.anchor == target_anchor or s.node_id == target_node_id:
            return s

    return None
