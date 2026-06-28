"""Advanced hierarchical chunking for documents."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

import tiktoken


@lru_cache(maxsize=8)
def _get_encoding(model: str):
    return tiktoken.encoding_for_model(model)


def count_tokens(text: str, model: str = "gpt-4") -> int:
    try:
        return len(_get_encoding(model).encode(text))
    except Exception:
        return len(text) // 4

def chunk_text_hierarchical(
    text: str,
    chunk_size: int = 400,
    overlap: int = 60,
    respect_headers: bool = True,
) -> list[dict[str, Any]]:
    if not text.strip():
        return []
    
    chunks: list[dict[str, Any]] = []
    
    if respect_headers:
        sections = _split_by_headers(text)
        
        current_chunk = ""
        current_tokens = 0
        current_header = ""
        current_level = 0
        chunk_index = 0
        
        for section in sections:
            section_text = section["text"]
            section_header = section.get("header", "")
            section_level = section.get("level", 0)
            section_tokens = count_tokens(section_text)
            
            if current_tokens + section_tokens <= chunk_size and current_chunk:
                current_chunk += "\n\n" + section_text
                current_tokens += section_tokens
                if section_header and not current_header:
                    current_header = section_header
                    current_level = section_level
            else:
                if current_chunk.strip():
                    chunks.append({
                        "text": current_chunk.strip(),
                        "index": chunk_index,
                        "header": current_header,
                        "level": current_level,
                    })
                    chunk_index += 1
                
                if section_tokens <= chunk_size:
                    current_chunk = section_text
                    current_tokens = section_tokens
                    current_header = section_header
                    current_level = section_level
                else:
                    sub_chunks = _split_large_section(section_text, chunk_size, overlap)
                    for sub_chunk in sub_chunks:
                        chunks.append({
                            "text": sub_chunk.strip(),
                            "index": chunk_index,
                            "header": section_header,
                            "level": section_level,
                        })
                        chunk_index += 1
                    current_chunk = ""
                    current_tokens = 0
                    current_header = ""
                    current_level = 0
        
        if current_chunk.strip():
            chunks.append({
                "text": current_chunk.strip(),
                "index": chunk_index,
                "header": current_header,
                "level": current_level,
            })
    else:
        chunks = _chunk_simple(text, chunk_size, overlap)
    
    return chunks

def _split_by_headers(text: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    
    markdown_pattern = r'^(#{1,6})\s+(.+)$'
    html_pattern = r'<(h[1-6])[^>]*>(.*?)</\1>'
    
    lines = text.split('\n')
    buffer: list[str] = []
    header = ""
    level = 0

    def flush() -> None:
        body = "\n".join(buffer)
        if body.strip():
            sections.append({"text": body, "header": header, "level": level})

    for line in lines:
        md_match = re.match(markdown_pattern, line.strip())
        if md_match:
            flush()
            buffer = []
            level = len(md_match.group(1))
            header = md_match.group(2).strip()
            continue

        html_match = re.search(html_pattern, line, re.IGNORECASE)
        if html_match:
            flush()
            buffer = []
            level = int(html_match.group(1)[1])  # h1 -> 1, h2 -> 2, etc.
            header = html_match.group(2).strip()
            continue

        buffer.append(line)

    flush()

    if not sections:
        return [{"text": text, "header": "", "level": 0}]

    return sections

def _is_markdown_table_block(text: str) -> bool:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if len(lines) < 2:
        return False
    return all(ln.startswith("|") and ln.endswith("|") for ln in lines[:2])


def _split_large_section(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Découpe une section longue en préservant les blocs tableau Markdown."""
    if _is_markdown_table_block(text):
        if count_tokens(text) <= chunk_size:
            return [text]
    if "|" in text and "---" in text:
        blocks = re.split(r"\n\n+", text)
        chunks: list[str] = []
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            if _is_markdown_table_block(block):
                chunks.append(block)
            else:
                chunks.extend(_split_large_section_words(block, chunk_size, overlap))
        return chunks or [text]
    return _split_large_section_words(text, chunk_size, overlap)


def _split_large_section_words(text: str, chunk_size: int, overlap: int) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    start = 0
    
    while start < len(words):
        end = min(len(words), start + chunk_size)
        chunk_text = " ".join(words[start:end])
        chunks.append(chunk_text)
        start = end - overlap
        if start < 0:
            start = 0
        if start >= len(words):
            break
    
    return chunks

def _chunk_simple(text: str, chunk_size: int, overlap: int) -> list[dict[str, Any]]:
    words = text.split()
    chunks: list[dict[str, Any]] = []
    start = 0
    index = 0
    
    while start < len(words):
        end = min(len(words), start + chunk_size)
        chunk_text = " ".join(words[start:end])
        chunks.append({
            "text": chunk_text,
            "index": index,
            "header": "",
            "level": 0,
        })
        index += 1
        start = end - overlap
        if start < 0:
            start = 0
        if start >= len(words):
            break
    
    return chunks

