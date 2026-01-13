from __future__ import annotations

import re

from ..core.constants import FIELD_QUERIES, FIELD_TITLE_KEYWORDS
from .text_sections import Chunk


def tokenize(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text)
    tokens = re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9]+", text)
    return [token.lower() for token in tokens if token.strip()]


class BM25Retriever:
    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        self.corpus_tokens = [tokenize(chunk.text) for chunk in chunks]
        try:
            from rank_bm25 import BM25Okapi

            self.bm25 = BM25Okapi(self.corpus_tokens)
            self.use_bm25 = True
        except Exception:
            self.bm25 = None
            self.use_bm25 = False

    def retrieve(self, query: str, top_k: int = 4) -> list[tuple[Chunk, float]]:
        if not self.chunks:
            return []
        query_tokens = tokenize(query)
        if self.use_bm25 and self.bm25 is not None:
            scores = self.bm25.get_scores(query_tokens)
        else:
            scores = []
            for tokens in self.corpus_tokens:
                score = sum(tokens.count(token) for token in query_tokens)
                scores.append(float(score))
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
        return [(self.chunks[i], float(score)) for i, score in ranked]


def filter_chunks_by_title_keywords(field: str, chunks: list[Chunk], min_keep: int = 6) -> list[Chunk]:
    keywords = FIELD_TITLE_KEYWORDS.get(field)
    if not keywords:
        return chunks
    filtered = []
    for chunk in chunks:
        title = chunk.section_title or ""
        if any(keyword in title for keyword in keywords):
            filtered.append(chunk)
    return filtered if len(filtered) >= min_keep else chunks


def build_module_query(title: str) -> str:
    return f"{title} 功能 模块 作用 描述"


def retrieve_evidence_for_module(title: str, retriever: BM25Retriever, top_k: int = 2) -> str:
    results = retriever.retrieve(build_module_query(title), top_k=top_k)
    parts = []
    for chunk, _score in results:
        header = chunk.section_title or ""
        parts.append(f"{header}\n{chunk.text}".strip())
    return "\n\n---\n\n".join(parts)


def get_context_for_field(
    field: str,
    section_chunks: list[Chunk],
    full_chunks: list[Chunk],
    top_k: int = 6,
) -> str:
    base_chunks = section_chunks if section_chunks else full_chunks
    candidate_chunks = filter_chunks_by_title_keywords(field, base_chunks)
    if not candidate_chunks:
        candidate_chunks = full_chunks or base_chunks
    query = FIELD_QUERIES.get(field, field.replace("__", " "))
    retriever = BM25Retriever(candidate_chunks)
    results = retriever.retrieve(query, top_k=top_k)
    parts = []
    for chunk, _score in results:
        header = ""
        if chunk.section_id or chunk.section_title:
            header = f"[{chunk.section_id or ''} {chunk.section_title or ''}]".strip()
        parts.append(f"{header}\n{chunk.text}".strip())
    context = "\n\n---\n\n".join(parts).strip()
    return context
