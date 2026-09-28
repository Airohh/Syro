"""Advanced hierarchical chunking for documents."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

import tiktoken


@lru_cache(maxsize=1)
def _get_encoding():
    """Tokenizer cl100k (tiktoken). None si indisponible (hors-ligne sans cache) :
    l'échec est mémorisé pour ne pas retenter un téléchargement à chaque appel."""
    try:
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return None


def _estimate_tokens(text: str) -> int:
    # Repli prudent (~3 caractères/token en français) : surestime plutôt que l'inverse.
    return max(1, len(text) // 3)


def count_tokens(text: str) -> int:
    encoding = _get_encoding()
    if encoding is None:
        return _estimate_tokens(text)
    return len(encoding.encode_ordinary(text))


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
                    chunks.append(
                        {
                            "text": current_chunk.strip(),
                            "index": chunk_index,
                            "header": current_header,
                            "level": current_level,
                        }
                    )
                    chunk_index += 1

                if section_tokens <= chunk_size:
                    current_chunk = section_text
                    current_tokens = section_tokens
                    current_header = section_header
                    current_level = section_level
                else:
                    sub_chunks = _split_large_section(section_text, chunk_size, overlap)
                    for i, sub_chunk in enumerate(sub_chunks):
                        text = sub_chunk.strip()
                        if i > 0 and section_header:
                            # Suite d'une longue section : on rappelle son titre.
                            text = f"{section_header} (suite)\n{text}"
                        chunks.append(
                            {
                                "text": text,
                                "index": chunk_index,
                                "header": section_header,
                                "level": section_level,
                            }
                        )
                        chunk_index += 1
                    current_chunk = ""
                    current_tokens = 0
                    current_header = ""
                    current_level = 0

        if current_chunk.strip():
            chunks.append(
                {
                    "text": current_chunk.strip(),
                    "index": chunk_index,
                    "header": current_header,
                    "level": current_level,
                }
            )
    else:
        chunks = _chunk_simple(text, chunk_size, overlap)

    return chunks


def _split_by_headers(text: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []

    markdown_pattern = r"^(#{1,6})\s+(.+)$"
    html_pattern = r"<(h[1-6])[^>]*>(.*?)</\1>"

    lines = text.split("\n")
    buffer: list[str] = []
    header = ""
    level = 0

    def flush() -> None:
        body = "\n".join(buffer)
        content = (
            buffer[1:]
            if header and buffer and buffer[0].lstrip().startswith("#")
            else buffer
        )
        if "\n".join(content).strip():
            sections.append({"text": body, "header": header, "level": level})

    for line in lines:
        # La ligne de titre est gardée dans la section : le titre fait partie
        # du texte embeddé et indexé BM25 (contexte « de quoi parle ce chunk »).
        md_match = re.match(markdown_pattern, line.strip())
        if md_match:
            flush()
            buffer = [line]
            level = len(md_match.group(1))
            header = md_match.group(2).strip()
            continue

        html_match = re.search(html_pattern, line, re.IGNORECASE)
        if html_match:
            flush()
            buffer = [
                f"{'#' * int(html_match.group(1)[1])} {html_match.group(2).strip()}"
            ]
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


def _split_markdown_table(text: str, chunk_size: int) -> list[str]:
    """Découpe un tableau Markdown en blocs avec en-tête répété."""
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if len(lines) < 2:
        return [text]

    header, separator = lines[0], lines[1]
    data_rows = lines[2:]
    if not data_rows:
        return [text]

    chunks: list[str] = []
    current = [header, separator]
    current_tokens = count_tokens("\n".join(current))

    for row in data_rows:
        row_tokens = count_tokens(row)
        if len(current) > 2 and current_tokens + row_tokens > chunk_size:
            chunks.append("\n".join(current))
            current = [header, separator, row]
            current_tokens = count_tokens("\n".join(current))
        else:
            current.append(row)
            current_tokens += row_tokens

    if len(current) > 2:
        chunks.append("\n".join(current))
    return chunks or [text]


def _split_large_section(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Découpe une section longue en préservant les blocs tableau Markdown."""
    if _is_markdown_table_block(text):
        if count_tokens(text) <= chunk_size:
            return [text]
        return _split_markdown_table(text, chunk_size)
    if "|" in text and "---" in text:
        blocks = re.split(r"\n\n+", text)
        chunks: list[str] = []
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            if _is_markdown_table_block(block):
                if count_tokens(block) <= chunk_size:
                    chunks.append(block)
                else:
                    chunks.extend(_split_markdown_table(block, chunk_size))
            else:
                chunks.extend(_split_by_tokens(block, chunk_size, overlap))
        return chunks or [text]
    return _split_by_tokens(text, chunk_size, overlap)


def _split_by_tokens(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Fenêtres glissantes de `chunk_size` tokens (overlap en tokens).

    On découpe sur les mots (jamais au milieu d'un mot) mais on compte en
    tokens, pour que la taille réelle respecte la limite du reranker
    (512 tokens question + passage) et du modèle d'embedding.
    """
    words = text.split()
    if not words:
        return []
    encoding = _get_encoding()
    if encoding is None:
        word_tokens = [_estimate_tokens(f" {w}") for w in words]
    else:
        word_tokens = [
            len(t) for t in encoding.encode_ordinary_batch([f" {w}" for w in words])
        ]

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end, total = start, 0
        while end < len(words) and (
            total + word_tokens[end] <= chunk_size or end == start
        ):
            total += word_tokens[end]
            end += 1
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        # Recul de `overlap` tokens pour le chevauchement (au moins 1 mot d'avance).
        back, new_start = 0, end
        while new_start - 1 > start and back + word_tokens[new_start - 1] <= overlap:
            new_start -= 1
            back += word_tokens[new_start]
        start = new_start
    return chunks


def _chunk_simple(text: str, chunk_size: int, overlap: int) -> list[dict[str, Any]]:
    return [
        {"text": chunk, "index": i, "header": "", "level": 0}
        for i, chunk in enumerate(_split_by_tokens(text, chunk_size, overlap))
    ]
