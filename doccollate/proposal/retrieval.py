from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from .chunking import Chunk


@dataclass(frozen=True)
class FieldSpec:
    field: str
    filter_keywords: list[str]
    bm25_query: str
    topk: int


FIELD_SPECS: dict[str, FieldSpec] = {
    "{{ purpose }}": FieldSpec(
        field="{{ purpose }}",
        filter_keywords=["目的", "编写目的", "背景", "概述", "简介", "目标", "本文档", "用于", "面向", "解决"],
        bm25_query="编写目的 背景 目标 本文档 用于 解决什么问题",
        topk=6,
    ),
    "{{ scope }}": FieldSpec(
        field="{{ scope }}",
        filter_keywords=["范围", "适用范围", "适用对象", "本项目", "功能范围", "边界", "不包括", "约束", "限制"],
        bm25_query="范围 边界 包含 不包含 适用对象 交付内容",
        topk=8,
    ),
    "{{ references }}": FieldSpec(
        field="{{ references }}",
        filter_keywords=["参考", "引用", "依据", "标准", "规范", "链接", "文档", "附录"],
        bm25_query="参考 规范 标准 引用 链接 文档",
        topk=4,
    ),
    "{{ project_source }}": FieldSpec(
        field="{{ project_source }}",
        filter_keywords=["项目来源", "来源", "背景", "需求来源", "客户", "业务", "痛点", "现状"],
        bm25_query="项目来源 背景 需求 痛点 现状",
        topk=8,
    ),
    "{{ project_scope_objectives }}": FieldSpec(
        field="{{ project_scope_objectives }}",
        filter_keywords=["目标", "目的", "范围", "交付", "里程碑", "功能", "实现", "支持", "提升"],
        bm25_query="项目目标 交付 里程碑 范围 功能 提升",
        topk=10,
    ),
    "{{ potential_customers }}": FieldSpec(
        field="{{ potential_customers }}",
        filter_keywords=["适用", "用户", "客户", "场景", "行业", "角色", "使用者"],
        bm25_query="目标用户 适用对象 客户 场景 行业 角色",
        topk=6,
    ),
    "{{ product_features }}": FieldSpec(
        field="{{ product_features }}",
        filter_keywords=["建设", "内容", "范围", "核心", "能力", "目标", "交付", "价值", "收益", "提升", "改造", "优化"],
        bm25_query="建设内容 核心能力 建设范围 目标 交付 价值 收益 提升 优化",
        topk=10,
    ),
    "{{ product_goals }}": FieldSpec(
        field="{{ product_goals }}",
        filter_keywords=["目标", "规划", "路线图", "未来", "迭代", "二期", "三期", "优化", "扩展", "多租户", "性能", "安全"],
        bm25_query="发展目标 规划 迭代 路线图 未来 优化 扩展",
        topk=6,
    ),
    "{{ architecture }}": FieldSpec(
        field="{{ architecture }}",
        filter_keywords=["架构", "架构图", "体系", "模块", "组件", "服务", "前端", "后端", "数据", "部署", "接口", "网关", "鉴权"],
        bm25_query="体系架构 模块 组件 服务 数据流 部署 鉴权",
        topk=10,
    ),
    "{{ technical_feasibility }}": FieldSpec(
        field="{{ technical_feasibility }}",
        filter_keywords=["可行性", "技术方案", "实现", "兼容", "性能", "安全", "风险", "约束", "部署", "数据", "权限", "日志"],
        bm25_query="技术可行性 实现 风险 约束 部署 性能 安全 兼容",
        topk=8,
    ),
    "{{ market_feasibility }}": FieldSpec(
        field="{{ market_feasibility }}",
        filter_keywords=["场景", "业务", "价值", "痛点", "效率", "合规", "审计", "成本", "客户", "用户"],
        bm25_query="业务场景 价值 痛点 效率 合规 审计 成本",
        topk=6,
    ),
    "{{ ip_analysis }}": FieldSpec(
        field="{{ ip_analysis }}",
        filter_keywords=["知识产权", "版权", "软著", "开源", "许可证", "依赖", "第三方"],
        bm25_query="开源 许可证 依赖 第三方 软著 知识产权",
        topk=4,
    ),
    "{{ conclusion }}": FieldSpec(
        field="{{ conclusion }}",
        filter_keywords=["总结", "结论", "建议", "立项", "可行性", "风险", "收益"],
        bm25_query="结论 建议 立项 可行性 风险 收益",
        topk=6,
    ),
    "terms": FieldSpec(
        field="terms",
        filter_keywords=["术语", "缩写", "acronym", "定义", "名词解释"],
        bm25_query="术语 缩写 定义 表",
        topk=6,
    ),
    "resources": FieldSpec(
        field="resources",
        filter_keywords=["资源", "环境", "部署", "服务器", "数据库", "网络", "账号", "权限", "存储", "配置"],
        bm25_query="部署环境 服务器 配置 数据库 存储 访问 网络 资源",
        topk=6,
    ),
    "costs": FieldSpec(
        field="costs",
        filter_keywords=["成本", "费用", "预算", "人力", "服务器", "采购"],
        bm25_query="预算 成本 费用 人力 服务器",
        topk=4,
    ),
    "milestones": FieldSpec(
        field="milestones",
        filter_keywords=["计划", "进度", "里程碑", "周期", "阶段", "交付", "验收", "测试", "部署"],
        bm25_query="项目计划 里程碑 阶段 交付 验收 测试 部署",
        topk=6,
    ),
}


MULTI_QUERY_FIELDS: dict[str, list[str]] = {
    "{{ product_features }}": [
        "建设 内容 范围 目标 交付",
        "核心 能力 平台 服务 集成 数据",
        "价值 收益 效率 提升 风险 合规",
    ],
    "{{ architecture }}": [
        "架构 体系 组件 服务 部署 接口",
        "技术栈 前端 后端 数据库 中间件 环境",
    ],
}


def filter_chunks(chunks: list[Chunk], keywords: list[str]) -> list[Chunk]:
    cleaned = [kw.strip() for kw in keywords if kw and kw.strip() and kw != "—"]
    if not cleaned:
        return chunks
    result: list[Chunk] = []
    for chunk in chunks:
        if any(kw in chunk["text"] for kw in cleaned):
            result.append(chunk)
    return result


def tokenize(text: str) -> list[str]:
    try:
        import jieba

        tokens = [tok.strip() for tok in jieba.lcut(text) if tok.strip()]
        return tokens
    except Exception:
        tokens = []
        buff = ""
        for ch in text:
            if ch.isspace():
                if buff:
                    tokens.append(buff)
                    buff = ""
                continue
            if ord(ch) < 128:
                buff += ch
            else:
                if buff:
                    tokens.append(buff)
                    buff = ""
                tokens.append(ch)
        if buff:
            tokens.append(buff)
        return tokens


class BM25:
    def __init__(self, corpus: list[list[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.corpus = corpus
        self.k1 = k1
        self.b = b
        self.doc_lens = [len(doc) for doc in corpus]
        self.avgdl = sum(self.doc_lens) / len(self.doc_lens) if self.doc_lens else 0
        self.df: dict[str, int] = {}
        for doc in corpus:
            seen = set(doc)
            for token in seen:
                self.df[token] = self.df.get(token, 0) + 1
        self.N = len(corpus)

    def score(self, query_tokens: list[str]) -> list[float]:
        scores = [0.0 for _ in self.corpus]
        if not self.corpus:
            return scores
        for i, doc in enumerate(self.corpus):
            freq: dict[str, int] = {}
            for token in doc:
                freq[token] = freq.get(token, 0) + 1
            dl = self.doc_lens[i]
            for q in query_tokens:
                if q not in self.df:
                    continue
                df = self.df[q]
                idf = math.log(1 + (self.N - df + 0.5) / (df + 0.5))
                tf = freq.get(q, 0)
                denom = tf + self.k1 * (1 - self.b + self.b * (dl / (self.avgdl or 1)))
                if denom != 0:
                    scores[i] += idf * (tf * (self.k1 + 1) / denom)
        return scores


def _rank_with_bm25(chunks: list[Chunk], query: str, topk: int) -> list[Chunk]:
    tokenized = [tokenize(chunk["text"]) for chunk in chunks]
    query_tokens = tokenize(query)
    try:
        from rank_bm25 import BM25Okapi

        bm25 = BM25Okapi(tokenized)
        scores = bm25.get_scores(query_tokens)
    except Exception:
        bm25 = BM25(tokenized)
        scores = bm25.score(query_tokens)
    ranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
    return [chunk for chunk, _ in ranked[:topk]]


def bm25_rank(chunks: list[Chunk], query: str, topk: int) -> list[Chunk]:
    if not chunks:
        return []
    return _rank_with_bm25(chunks, query, topk)


def multi_query_rank(
    chunks: list[Chunk], queries: list[str], per_query_topk: int, max_total: int
) -> list[Chunk]:
    merged: list[Chunk] = []
    seen_ids: set[str] = set()
    for query in queries:
        ranked = bm25_rank(chunks, query, per_query_topk)
        for chunk in ranked:
            if chunk["id"] in seen_ids:
                continue
            merged.append(chunk)
            seen_ids.add(chunk["id"])
            if len(merged) >= max_total:
                return merged
    return merged


def build_field_evidence(
    chunks: list[Chunk],
    field: str,
    topk: int,
    filter_keywords_list: list[str],
    query: str,
) -> list[Chunk]:
    filtered = filter_chunks(chunks, filter_keywords_list)
    if not filtered:
        filtered = chunks
    return bm25_rank(filtered, query, topk)


def retrieve_all_fields(chunks: list[Chunk], topk_default: int) -> dict[str, list[Chunk]]:
    evidence: dict[str, list[Chunk]] = {}
    for field, spec in FIELD_SPECS.items():
        if field in MULTI_QUERY_FIELDS:
            filtered = filter_chunks(chunks, spec.filter_keywords)
            if not filtered:
                filtered = chunks
            merged = multi_query_rank(
                filtered,
                MULTI_QUERY_FIELDS[field],
                per_query_topk=6,
                max_total=12,
            )
            evidence[field] = merged
            continue
        topk = spec.topk or topk_default
        evidence[field] = build_field_evidence(
            chunks,
            field,
            topk,
            spec.filter_keywords,
            spec.bm25_query,
        )
    return evidence
