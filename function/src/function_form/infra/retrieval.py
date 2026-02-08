from __future__ import annotations

from dataclasses import dataclass

KEYWORDS = [
    "软件主要功能",
    "功能架构",
    "模块",
    "工作台",
    "订单池",
    "网络概览",
    "任务详情",
    "冲突",
    "推荐路线",
    "菜单",
]


@dataclass(frozen=True)
class TextChunk:
    title: str
    content: str


def chunk_text(source_text: str, max_chars: int = 1200) -> list[TextChunk]:
    lines = (source_text or "").splitlines()
    chunks: list[TextChunk] = []
    cur_title = "未命名段落"
    cur_lines: list[str] = []
    cur_len = 0

    def flush() -> None:
        nonlocal cur_lines, cur_len
        text = "\n".join(x for x in cur_lines if x.strip()).strip()
        if text:
            chunks.append(TextChunk(title=cur_title, content=text))
        cur_lines = []
        cur_len = 0

    for raw in lines:
        line = raw.rstrip()
        if line.startswith("#"):
            flush()
            cur_title = line.lstrip("#").strip() or "未命名段落"
            continue

        if not line.strip():
            continue

        if cur_len + len(line) > max_chars and cur_lines:
            flush()
        cur_lines.append(line)
        cur_len += len(line)

    flush()
    return chunks


def retrieve_function_chunks(chunks: list[TextChunk], top_k: int = 10) -> list[TextChunk]:
    scored: list[tuple[float, TextChunk]] = []
    for c in chunks:
        text = f"{c.title}\n{c.content}".lower()
        score = 0.0
        for kw in KEYWORDS:
            if kw.lower() in text:
                score += 1.0
        if c.title.startswith("4."):
            score += 1.2
        if "4.2" in c.title:
            score += 2.0
        if score > 0:
            scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]
