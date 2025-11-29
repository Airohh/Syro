from __future__ import annotations

import io
from pathlib import Path
from typing import Optional

from pypdf import PdfReader
from docx import Document  # type: ignore

TEXT_TYPES = {
    "text/plain",
    "text/markdown",
    "text/csv",
}

def _extract_pdf(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)

def _extract_docx(content: bytes) -> str:
    doc = Document(io.BytesIO(content))
    return "\n".join(p.text for p in doc.paragraphs)

def extract_text_from_bytes(content: bytes, filename: str, content_type: Optional[str]) -> str:
    ext = Path(filename).suffix.lower()
    if content_type in TEXT_TYPES or ext in {".txt", ".md", ".csv"}:
        return content.decode("utf-8", errors="ignore")
    if content_type == "application/pdf" or ext == ".pdf":
        return _extract_pdf(content)
    if content_type in {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"} or ext in {".docx", ".doc"}:
        return _extract_docx(content)
    return content.decode("utf-8", errors="ignore")

def detect_source_type(filename: str, content_type: Optional[str]) -> str:
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext:
        return ext
    if content_type:
        return content_type.split("/")[-1]
    return "unknown"
