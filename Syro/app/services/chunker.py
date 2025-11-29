"""Advanced hierarchical chunking for documents."""

from __future__ import annotations

import re
from typing import Any

import tiktoken

def count_tokens(text: str, model: str = "gpt-4") -> int:
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
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
    current_section = {"text": "", "header": "", "level": 0}
    
    for line in lines:
        md_match = re.match(markdown_pattern, line.strip())
        if md_match:
            if current_section["text"].strip():
                sections.append(current_section)
            level = len(md_match.group(1))
            header = md_match.group(2).strip()
            current_section = {
                "text": "",
                "header": header,
                "level": level,
            }
            continue
        
        html_match = re.search(html_pattern, line, re.IGNORECASE)
        if html_match:
            if current_section["text"].strip():
                sections.append(current_section)
            level = int(html_match.group(1)[1])  # h1 -> 1, h2 -> 2, etc.
            header = html_match.group(2).strip()
            current_section = {
                "text": "",
                "header": header,
                "level": level,
            }
            continue
        
        if current_section["text"]:
            current_section["text"] += "\n" + line
        else:
            current_section["text"] = line
    
    if current_section["text"].strip():
        sections.append(current_section)
    
    if not sections:
        return [{"text": text, "header": "", "level": 0}]
    
    return sections

def _split_large_section(text: str, chunk_size: int, overlap: int) -> list[str]:
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

