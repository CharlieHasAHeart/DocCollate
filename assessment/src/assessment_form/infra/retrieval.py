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


def _split_chunks(text: str, max_chars: int = 560) -> list[RetrievalChunk]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
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
    if not s:
        return set()
    if len(s) < n:
        return {s}
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
        "product__service_object": ["服务对象", "适用对象", "用户角色", "业务场景", "应用对象"],
        "product__main_functions": ["主要功能", "功能模块", "子系统", "业务流程", "功能清单"],
        "product__tech_specs": ["技术指标", "并发", "响应", "可用性", "稳定性", "安全", "兼容性", "扩展性"],
        "app__product_type_text": ["产品类型", "软件类型", "类别", "应用软件", "系统软件", "嵌入式"],
        "env__memory_req": ["内存", "内存要求", "内存配置", "MB", "GB"],
        "env__hardware_model": ["机型", "硬件平台", "终端", "服务器", "x86", "ARM"],
        "env__os": ["操作系统", "Windows", "Linux", "macOS", "客户端", "服务器"],
        "env__language": ["编程语言", "开发语言", "Java", "Python", "TypeScript", "Go", "C++"],
        "env__database": ["数据库", "MySQL", "PostgreSQL", "Oracle", "SQL Server", "Redis"],
        "env__soft_scale": ["软件规模", "规模", "大中小", "模块数量", "子系统"],
        "env__os_version": ["操作系统版本", "Ubuntu", "CentOS", "Kylin", "Windows Server", "LTS"],
        "env__hw_dev_platform": ["开发硬件环境", "开发机", "CPU", "内存", "存储", "网络"],
        "env__sw_dev_platform": ["开发环境", "IDE", "版本管理", "SDK", "运行时", "构建", "依赖管理"],
        "app__category_assess": ["软件产品类别", "分类编码", "计算机应用软件", "信息服务"],
        "assess__product_mode_val": ["产品方式", "纯软件", "嵌入式", "交付方式"],
        "assess__support_floppy": ["软驱"],
        "assess__support_sound": ["声卡", "音频硬件"],
        "assess__support_cdrom": ["光驱"],
        "assess__support_gpu": ["显卡", "GPU"],
        "assess__support_other": ["其他外设", "其他硬件要求"],
        "assess__is_self_dev": ["自主开发", "自研"],
        "assess__has_docs": ["技术文档", "说明文档", "设计文档"],
        "assess__has_source": ["源代码", "源码"],
    }


def retrieve_field_contexts(source_text: str, top_k: int = 3) -> dict[str, list[dict[str, object]]]:
    chunks = _split_chunks(source_text)
    if not chunks:
        return {}

    corpus_tokens = [_tokenize(c.text) for c in chunks]
    bm25 = BM25Okapi(corpus_tokens)
    chunk_ngrams = [_char_ngrams(c.text) for c in chunks]

    out: dict[str, list[dict[str, object]]] = {}
    for field, terms in _field_queries().items():
        query_text = " ".join(terms)
        query_tokens = _tokenize(query_text)
        bm25_scores = bm25.get_scores(query_tokens).tolist()
        bm25_norm = _normalize_scores(bm25_scores)
        query_ngrams = _char_ngrams(query_text)
        dense_scores = [_jaccard(query_ngrams, item) for item in chunk_ngrams]
        dense_norm = _normalize_scores(dense_scores)

        hybrid = [0.7 * b + 0.3 * d for b, d in zip(bm25_norm, dense_norm)]
        ranked = sorted(enumerate(hybrid), key=lambda x: x[1], reverse=True)[:top_k]
        picks: list[dict[str, object]] = []
        for idx, score in ranked:
            if score <= 0:
                continue
            chunk = chunks[idx]
            picks.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "score": round(score, 4),
                    "text": chunk.text,
                }
            )
        if picks:
            out[field] = picks
    return out

