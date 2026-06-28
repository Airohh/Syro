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


def _extract_pdf(content: bytes) -> str:
    parts: list[str] = []
    reader = PdfReader(io.BytesIO(content))
    for page in reader.pages:
        parts.append(page.extract_text() or "")

    # Tableaux via pdfplumber si disponible (T5.1)
    try:
        import pdfplumber

        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables() or []:
                    rows = [
                        [(cell or "").strip() for cell in row]
                        for row in table
                        if row and any((cell or "").strip() for cell in row)
                    ]
                    md = _rows_to_markdown_table(rows)
                    if md:
                        parts.append(md)
    except ImportError:
        pass

    return "\n\n".join(p for p in parts if p.strip())


def _extract_docx(content: bytes) -> str:
    doc = Document(io.BytesIO(content))
    parts: list[str] = []
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if text:
            parts.append(text)
    for table in doc.tables:
        rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]
        md = _rows_to_markdown_table(rows)
        if md:
            parts.append(md)
    return "\n\n".join(parts)

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
