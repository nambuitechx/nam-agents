"""Text chunking for embedding."""

from __future__ import annotations


def chunk_text(text: str, *, max_chars: int) -> list[str]:
    """Split text into chunks that respect Cohere's per-text character limit."""
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return []

    paragraphs = [part.strip() for part in normalized.split("\n\n") if part.strip()]
    if not paragraphs:
        paragraphs = [normalized]

    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_long_paragraph(paragraph, max_chars=max_chars))
            continue

        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = paragraph

    if current:
        chunks.append(current)

    return chunks


def _split_long_paragraph(paragraph: str, *, max_chars: int) -> list[str]:
    parts: list[str] = []
    start = 0
    while start < len(paragraph):
        end = min(start + max_chars, len(paragraph))
        if end < len(paragraph):
            split_at = paragraph.rfind(" ", start, end)
            if split_at > start:
                end = split_at
        piece = paragraph[start:end].strip()
        if piece:
            parts.append(piece)
        start = max(end, start + 1)
    return parts
