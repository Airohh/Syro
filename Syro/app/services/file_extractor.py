from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Iterator, Optional

from docx import Document  # type: ignore
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader

logger = logging.getLogger(__name__)

TEXT_TYPES = {
    "text/plain",
    "text/markdown",
    "text/csv",
}


def _escape_md_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _rows_to_markdown_table(rows: list[list[str]]) -> str:
    """Convertit des lignes de cellules en tableau Markdown."""
    cleaned = [[c.strip() for c in row] for row in rows if any(c.strip() for c in row)]
    if not cleaned:
        return ""
    width = max(len(r) for r in cleaned)
    normalized = [r + [""] * (width - len(r)) for r in cleaned]
    header = normalized[0]
    lines = [
        "| " + " | ".join(_escape_md_cell(c) for c in header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in normalized[1:]:
        lines.append("| " + " | ".join(_escape_md_cell(c) for c in row) + " |")
    return "\n".join(lines)


def _iter_docx_blocks(document: Document) -> Iterator[Paragraph | Table]:
    """Parcourt paragraphes et tableaux dans l'ordre du document."""
    for child in document.element.body:
        if child.tag == qn("w:p"):
            yield Paragraph(child, document)
        elif child.tag == qn("w:tbl"):
            yield Table(child, document)


def _extract_pdf(content: bytes) -> str:
    parts: list[str] = []

    try:
        import pdfplumber
    except ImportError:
        pdfplumber = None  # type: ignore[assignment]

    if pdfplumber is not None:
        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    page_text = (page.extract_text() or "").strip()
                    if page_text:
                        parts.append(page_text)
                    for table in page.extract_tables() or []:
                        rows = [
                            [(cell or "").strip() for cell in row]
                            for row in table
                            if row and any((cell or "").strip() for cell in row)
                        ]
                        md = _rows_to_markdown_table(rows)
                        if md:
                            parts.append(md)
            return "\n\n".join(parts)
        except Exception as exc:
            logger.warning(
                "pdfplumber extraction failed, falling back to pypdf: %s", exc
            )
            parts = []

    reader = PdfReader(io.BytesIO(content))
    for page in reader.pages:
        text = (page.extract_text() or "").strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def _extract_docx(content: bytes) -> str:
    doc = Document(io.BytesIO(content))
    parts: list[str] = []
    for block in _iter_docx_blocks(doc):
        if isinstance(block, Paragraph):
            text = block.text.strip()
            if text:
                parts.append(text)
        else:
            rows = [[cell.text.strip() for cell in row.cells] for row in block.rows]
            md = _rows_to_markdown_table(rows)
            if md:
                parts.append(md)
    return "\n\n".join(parts)


def extract_text_from_bytes(
    content: bytes, filename: str, content_type: Optional[str]
) -> str:
    ext = Path(filename).suffix.lower()
    if content_type in TEXT_TYPES or ext in {".txt", ".md", ".csv"}:
        return content.decode("utf-8", errors="ignore")
    if content_type == "application/pdf" or ext == ".pdf":
        return _extract_pdf(content)
    if content_type in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    } or ext in {".docx", ".doc"}:
        return _extract_docx(content)
    return content.decode("utf-8", errors="ignore")


def detect_source_type(filename: str, content_type: Optional[str]) -> str:
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext:
        return ext
    if content_type:
        return content_type.split("/")[-1]
    return "unknown"
