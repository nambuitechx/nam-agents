"""Document text extraction from common file formats."""

from __future__ import annotations

import asyncio
import io
import shutil
import subprocess
from pathlib import Path

import aiofiles
from docx import Document
from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ".pdf", ".docx", ".doc"}


def _load_text_sync(content: bytes, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Unsupported file type '{suffix}'. Supported: {supported}")

    if suffix in {".txt", ".md", ".markdown"}:
        return content.decode("utf-8")

    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(content))
        parts = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(parts).strip()
        if not text:
            raise ValueError(f"No extractable text found in PDF '{filename}'")
        return text

    if suffix == ".docx":
        document = Document(io.BytesIO(content))
        parts = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
        text = "\n".join(parts).strip()
        if not text:
            raise ValueError(f"No extractable text found in DOCX '{filename}'")
        return text

    if suffix == ".doc":
        return _load_doc_legacy(content, filename)

    raise ValueError(f"Unsupported file type '{suffix}'")


def _load_doc_legacy(content: bytes, filename: str) -> str:
    antiword = shutil.which("antiword")
    if antiword is None:
        raise ValueError(
            f"Cannot read legacy .doc file '{filename}'. "
            "Install antiword or convert to .docx/.pdf first."
        )

    result = subprocess.run(
        [antiword, "-"],
        input=content,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"Failed to read .doc file '{filename}': {stderr or 'antiword error'}")

    text = result.stdout.decode("utf-8", errors="replace").strip()
    if not text:
        raise ValueError(f"No extractable text found in DOC '{filename}'")
    return text


async def load_text(content: bytes, filename: str) -> str:
    """Extract plain text from file bytes based on filename extension."""
    return await asyncio.to_thread(_load_text_sync, content, filename)


async def load_text_from_path(path: Path) -> tuple[str, str]:
    """Read a file from disk and extract plain text. Returns (text, filename)."""
    async with aiofiles.open(path, "rb") as handle:
        content = await handle.read()
    text = await load_text(content, path.name)
    return text, path.name
