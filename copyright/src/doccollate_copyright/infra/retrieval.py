from __future__ import annotations

import re
from dataclasses import dataclass

import jieba
from rank_bm25 import BM25Okapi


@dataclass(frozen=True)
class RetrievalChunk:
    chunk_id: int
    text: str


def _tokenize(text: str) -> list[str]:
    raw = text.strip()
    if not raw:
        return []
    zh_tokens = [t.strip() for t in jieba.cut(raw) if t.strip()]
    en_tokens = re.findall(r"[A-Za-z0-9_]+", raw.lower())
    return zh_tokens + en_tokens


def _split_chunks(text: str, max_chars: int = 480) -> list[RetrievalChunk]:
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]

    segments: list[str] = []
    buf = ""
    for ln in lines:
        if len(buf) + len(ln) + 1 > max_chars:
            if buf:
                segments.append(buf)
            buf = ln
        else:
            buf = f"{buf}\n{ln}" if buf else ln
    if buf:
        segments.append(buf)

    if not segments and text.strip():
        segments = [text.strip()[:max_chars]]
    return [RetrievalChunk(chunk_id=i, text=s) for i, s in enumerate(segments, start=1)]


def _char_ngrams(text: str, n: int = 3) -> set[str]:
    s = re.sub(r"\s+", "", text.lower())
    if len(s) < n:
        return {s} if s else set()
    return {s[i : i + n] for i in range(len(s) - n + 1)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _normalize_scores(values: list[float]) -> list[float]:
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    if hi - lo < 1e-9:
        return [1.0 if hi > 0 else 0.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def _field_queries() -> dict[str, list[str]]:
    return {
        "tech__dev_purpose": ["开发目的", "建设目标", "目标", "purpose"],
        "tech__main_functions": ["主要功能", "功能模块", "系统功能", "功能"],
        "tech__features": ["技术特点", "创新点", "特色", "优势"],
        "tech__hardware_dev": [
            "软件开发硬件环境",
            "最低配置",
            "推荐配置",
            "CPU",
            "内存",
            "存储",
            "网络",
        ],
        "tech__hardware_run": [
            "软件运行硬件环境",
            "客户端",
            "服务器端",
            "数据库",
            "中间件",
            "最低配置",
            "推荐配置",
            "CPU",
            "内存",
            "存储",
            "网络",
        ],
        "tech__os_dev": ["开发该软件的操作系统", "Windows", "Linux", "macOS", "版本", "64位"],
        "tech__os_run": ["运行平台", "客户端运行平台", "服务器运行平台", "操作系统", "版本范围"],
        "tech__dev_tools": [
            "软件开发环境",
            "开发工具",
            "IDE",
            "编辑器",
            "版本管理",
            "语言",
            "SDK",
            "运行时",
            "构建",
            "依赖管理",
        ],
        "tech__run_support": [
            "软件运行支撑环境",
            "支持软件",
            "运行时",
            "应用环境",
            "Web服务",
            "反向代理",
            "数据库",
            "缓存",
            "消息队列",
            "容器",
        ],
        "tech__language": ["编程语言", "开发语言", "language"],
        "tech__source_lines": ["源程序量", "代码行数", "行数", "LOC"],
        "copyright__development_method": ["开发方式", "独立开发", "合作开发", "委托开发"],
        "copyright__status_published": ["发表状态", "是否发表", "发布情况", "公开"],
        "copyright__publish_date": ["首次发表日期", "发布时间", "发布日期"],
        "copyright__publish_location": ["首次发表地点", "发布地点", "发表地点"],
        "rights__acquire_method": ["权利取得方式", "原始取得", "继受取得", "受让", "承受", "继承"],
        "rights__scope": ["权利范围", "全部权利", "部分权利"],
    }


def retrieve_field_contexts(source_text: str, top_k: int = 3) -> dict[str, list[dict[str, object]]]:
    chunks = _split_chunks(source_text)
    if not chunks:
        return {}

    corpus_tokens = [_tokenize(c.text) for c in chunks]
    bm25 = BM25Okapi(corpus_tokens)
    chunk_ngrams = [_char_ngrams(c.text) for c in chunks]
    queries = _field_queries()

    results: dict[str, list[dict[str, object]]] = {}
    for field, q_terms in queries.items():
        query_text = " ".join(q_terms)
        query_tokens = _tokenize(query_text)
        bm25_scores = bm25.get_scores(query_tokens).tolist()
        bm25_norm = _normalize_scores(bm25_scores)

        q_ngrams = _char_ngrams(query_text)
        dense_scores = [_jaccard(q_ngrams, cng) for cng in chunk_ngrams]
        dense_norm = _normalize_scores(dense_scores)

        hybrid = [0.7 * b + 0.3 * d for b, d in zip(bm25_norm, dense_norm)]
        ranked = sorted(enumerate(hybrid), key=lambda x: x[1], reverse=True)[:top_k]

        picks: list[dict[str, object]] = []
        for idx, score in ranked:
            if score <= 0:
                continue
            chunk = chunks[idx]
            picks.append({"chunk_id": chunk.chunk_id, "score": round(score, 4), "text": chunk.text})
        if picks:
            results[field] = picks

    return results
