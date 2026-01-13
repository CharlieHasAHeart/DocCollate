from __future__ import annotations

from typing import TypedDict


class Chunk(TypedDict):
    id: str
    text: str
    start: int
    end: int


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 120) -> list[Chunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0:
        raise ValueError("overlap must be non-negative")
    chunks: list[Chunk] = []
    start = 0
    idx = 1
    text_len = len(text)
    while start < text_len:
        end = min(text_len, start + chunk_size)
        chunk = text[start:end]
        chunks.append(
            {
                "id": f"chunk_{idx:04d}",
                "text": chunk,
                "start": start,
                "end": end,
            }
        )
        idx += 1
        if end == text_len:
            break
        start = max(0, end - overlap)
    return chunks
