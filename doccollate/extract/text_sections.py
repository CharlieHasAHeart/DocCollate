from __future__ import annotations

import re
from dataclasses import dataclass


def _chinese_numeral_to_int(value: str) -> int | None:
    mapping = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    if value in mapping:
        return mapping[value]
    if len(value) == 2 and value.startswith("十"):
        return 10 + mapping.get(value[1], 0)
    if len(value) == 2 and value.endswith("十"):
        return mapping.get(value[0], 0) * 10
    if len(value) == 3 and value[1] == "十":
        return mapping.get(value[0], 0) * 10 + mapping.get(value[2], 0)
    return None


def build_section_map(text: str) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}
    current_id = None
    current_title = None
    for line in text.splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            if current_id is not None:
                sections[current_id]["content"] += line + "\n"
            continue
        heading = re.sub(r"^#+\s*", "", line_stripped)
        is_heading = line_stripped.startswith("#") or re.match(r"^\d+(\.\d+)*\s+", heading)
        if is_heading:
            if re.match(r"^\d+(\.\d+)*\s+", heading):
                current_id = heading.split()[0]
                current_title = " ".join(heading.split()[1:])
                sections.setdefault(current_id, {"title": current_title, "content": ""})
                continue
            chapter_match = re.match(r"^第([一二三四五六七八九十]+)章\s+(.+)$", heading)
            if chapter_match:
                num = _chinese_numeral_to_int(chapter_match.group(1))
                current_id = str(num) if num else chapter_match.group(1)
                current_title = chapter_match.group(2).strip()
                sections.setdefault(current_id, {"title": current_title, "content": ""})
                continue
            current_id = f"title:{heading}"
            current_title = heading
            sections.setdefault(current_id, {"title": current_title, "content": ""})
            continue
        if current_id is not None:
            sections[current_id]["content"] += line + "\n"
    return {
        key: {"title": value.get("title", ""), "content": value.get("content", "").strip()}
        for key, value in sections.items()
        if value.get("content", "").strip()
    }


@dataclass
class Chunk:
    text: str
    section_id: str | None = None
    section_title: str | None = None


def split_into_chunks(full_text: str, max_chars: int = 600, overlap: int = 80) -> list[Chunk]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", full_text) if p.strip()]
    chunks: list[Chunk] = []
    buf = ""
    for paragraph in paragraphs:
        if len(buf) + len(paragraph) + 2 <= max_chars:
            buf += ("\n\n" + paragraph) if buf else paragraph
        else:
            if buf:
                chunks.append(Chunk(text=buf))
            buf = (buf[-overlap:] + "\n\n" + paragraph) if overlap > 0 else paragraph
    if buf:
        chunks.append(Chunk(text=buf))
    return chunks


def build_section_chunks(section_map: dict[str, dict[str, str]], max_chars: int = 900) -> list[Chunk]:
    chunks: list[Chunk] = []
    for section_id, section in section_map.items():
        title = section.get("title", "")
        content = section.get("content", "").strip()
        if not content:
            continue
        if len(content) <= max_chars:
            chunks.append(Chunk(text=content, section_id=section_id, section_title=title))
        else:
            for sub in split_into_chunks(content, max_chars=max_chars, overlap=120):
                sub.section_id = section_id
                sub.section_title = title
                chunks.append(sub)
    return chunks
