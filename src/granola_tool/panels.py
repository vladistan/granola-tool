"""Fetch and render Granola document panels (AI-generated meeting notes)."""

from typing import Any

import structlog

from granola_tool.api import api_request
from granola_tool.errors import ApiError


def get_panels(doc_id: str) -> list[dict[str, Any]]:
    """Fetch panels for a document from the API."""
    log = structlog.get_logger()
    try:
        result = api_request("/v1/get-document-panels", {"document_id": doc_id})
        if isinstance(result, list):
            return result
    except ApiError as e:
        log.warning("panels_fetch_failed", doc_id=doc_id, error=str(e))
    return []


def panels_to_markdown(panels: list[dict[str, Any]]) -> str:
    """Convert panels to markdown text."""
    sections: list[str] = []
    for panel in panels:
        title = panel.get("title", "")
        content = panel.get("content")
        if not content:
            continue
        lines: list[str] = []
        if title:
            lines.append(f"## {title}")
            lines.append("")
        _render_nodes(content.get("content", []), lines, depth=0)
        sections.append("\n".join(lines))
    return "\n\n".join(sections)


def _render_nodes(nodes: list[dict[str, Any]], lines: list[str], depth: int) -> None:
    """Recursively render ProseMirror nodes to markdown lines."""
    for node in nodes:
        node_type = node.get("type", "")
        if node_type == "heading":
            level = node.get("attrs", {}).get("level", 3)
            text = _extract_text(node.get("content", []))
            prefix = "#" * min(level + 1, 6)
            lines.append(f"{prefix} {text}")
            lines.append("")
        elif node_type == "paragraph":
            text = _extract_text(node.get("content", []))
            if depth > 0:
                indent = "  " * (depth - 1)
                lines.append(f"{indent}- {text}")
            elif text:
                lines.append(text)
                lines.append("")
        elif node_type == "bulletList":
            _render_list(node.get("content", []), lines, depth)
        elif node_type == "orderedList":
            _render_list(node.get("content", []), lines, depth, ordered=True)
        elif node_type == "blockquote":
            inner_lines: list[str] = []
            _render_nodes(node.get("content", []), inner_lines, depth=0)
            for line in inner_lines:
                lines.append(f"> {line}")
            lines.append("")
        elif node_type == "horizontalRule":
            lines.append("---")
            lines.append("")


def _render_list(
    items: list[dict[str, Any]], lines: list[str], depth: int, *, ordered: bool = False
) -> None:
    """Render list items with proper indentation."""
    for i, item in enumerate(items):
        sub_nodes = item.get("content", [])
        for j, sub_node in enumerate(sub_nodes):
            if sub_node.get("type") == "paragraph":
                text = _extract_text(sub_node.get("content", []))
                indent = "  " * depth
                if j == 0:
                    marker = f"{i + 1}." if ordered else "-"
                    lines.append(f"{indent}{marker} {text}")
                else:
                    lines.append(f"{indent}  {text}")
            elif sub_node.get("type") in ("bulletList", "orderedList"):
                _render_list(
                    sub_node.get("content", []),
                    lines,
                    depth + 1,
                    ordered=sub_node.get("type") == "orderedList",
                )
    if depth == 0:
        lines.append("")


def _extract_text(content: list[dict[str, Any]]) -> str:
    """Extract plain text from inline content nodes, applying marks."""
    parts: list[str] = []
    for node in content:
        if node.get("type") == "text":
            text = node.get("text", "")
            marks = node.get("marks", [])
            for mark in marks:
                mark_type = mark.get("type", "")
                if mark_type == "bold":
                    text = f"**{text}**"
                elif mark_type == "italic":
                    text = f"*{text}*"
                elif mark_type == "code":
                    text = f"`{text}`"
                elif mark_type == "link":
                    href = mark.get("attrs", {}).get("href", "")
                    text = f"[{text}]({href})"
            parts.append(text)
        elif node.get("type") == "hardBreak":
            parts.append("\n")
    return "".join(parts)
