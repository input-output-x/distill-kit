"""把蒸馏结果写入磁盘。"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


# Windows 保留设备名：用作文件名会在 mkdir 时直接报错，需要兜底
_RESERVED_NAMES = {
    "con", "prn", "aux", "nul",
    "com1", "com2", "com3", "com4", "com5", "com6", "com7", "com8", "com9",
    "lpt1", "lpt2", "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9",
}


def slugify(text: str) -> str:
    text = (text or "untitled").strip().lower()
    text = re.sub(r"[\s]+", "-", text)
    # 去掉 Windows 不允许出现在文件名里的字符（\:*?"<>| 等）；
    # 中文（\u4e00-\u9fff）与连字符保留，其余一律剔除。
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff\-]", "", text)
    text = re.sub(r"-+", "-", text).strip("-").strip(".")
    text = text or "untitled"
    if text in _RESERVED_NAMES:
        text = f"{text}-distilled"
    return text


def write(result: dict, out_dir: str, cfg) -> Path:
    base = Path(out_dir)
    title = result["survey"].get("title") or result["source_name"]
    folder = base / slugify(title)
    folder.mkdir(parents=True, exist_ok=True)

    # README
    (folder / "README.md").write_text(_readme(result), encoding="utf-8")
    # 全局理解
    (folder / "BOOK_OVERVIEW.md").write_text(_overview(result), encoding="utf-8")
    # 索引
    (folder / "INDEX.md").write_text(result["index"], encoding="utf-8")
    # 卡片
    (folder / "flashcards.md").write_text(result["cards"], encoding="utf-8")
    # 行动清单
    (folder / "action-checklist.md").write_text(result["checklist"], encoding="utf-8")
    # 被淘汰候选
    if result["rejected"]:
        (folder / "rejected.md").write_text(_rejected(result), encoding="utf-8")

    # 技能卡
    skills_dir = folder / "skills"
    skills_dir.mkdir(exist_ok=True)
    for s in result["skills"]:
        name = slugify(s["meta"].get("name") or s["meta"].get("id") or "skill")
        one_liner = _first_line(s["md"])
        front = (
            "---\n"
            f"name: {name}\n"
            f"description: {one_liner}\n"
            "---\n\n"
        )
        (skills_dir / f"{name}.md").write_text(front + s["md"].lstrip(), encoding="utf-8")

    # 元信息
    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": result["source_name"],
        "kind": result["kind"],
        "language": result["language"],
        "model": cfg.llm.get("model"),
        "title": title,
        "skill_count": len(result["skills"]),
        "kept_ids": result["kept_ids"],
    }
    (folder / "distill.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return folder


def _first_line(md: str) -> str:
    # 优先取「一句话」摘要（> 开头的引用块），其次取首个标题文本
    quote = None
    first_heading = None
    for line in md.splitlines():
        s = line.strip()
        if s.startswith(">") and quote is None:
            quote = s.lstrip(">").strip()
        elif s.startswith("#") and first_heading is None:
            first_heading = s.lstrip("#").strip()
        if quote and first_heading:
            break
    return (quote or first_heading or "")[:120]


def _readme(result: dict) -> str:
    title = result["survey"].get("title", "")
    one_liner = result["survey"].get("one_liner", "")
    n = len(result["skills"])
    lines = [
        f"# {title} · 蒸馏产物",
        "",
        f"> {one_liner}",
        "",
        f"本目录由 **distillkit** 自动生成，来源类型：`{result['kind']}`。",
        "",
        "## 目录结构",
        "",
        "- `BOOK_OVERVIEW.md` — 整书/文稿全局理解（一句话、核心论点、结构、主题）",
        "- `INDEX.md` — 技能全景图 + 推荐学习顺序 + 使用说明",
        f"- `skills/*.md` — {n} 张可执行「技能卡」（Agent Skill 兼容）",
        "- `flashcards.md` — 复习卡片（Q&A）",
        "- `action-checklist.md` — 可立即执行的行动清单",
        "- `rejected.md` — 被淘汰的候选及原因（如有）",
        "- `distill.meta.json` — 生成元信息",
        "",
        "## 怎么用",
        "",
        "1. 先读 `INDEX.md` 建立全景认知。",
        "2. 遇到具体问题，翻对应的 `skills/<name>.md` 直接照做。",
        "3. 把 `skills/` 接入你的 Agent 框架（Claude Code / Codex / WorkBuddy 等），",
        "   让 AI 带着这本书的方法论回答问题。",
        "4. 用 `flashcards.md` 复习，`action-checklist.md` 落地。",
    ]
    return "\n".join(lines) + "\n"


def _overview(result: dict) -> str:
    s = result["survey"]
    lines = ["# 整书理解", ""]
    lines.append(f"> {s.get('one_liner','')}")
    lines += [
        "",
        "## 核心论点",
        s.get("core_thesis", ""),
        "",
        "## 适合谁",
        s.get("target_audience", ""),
        "",
        "## 结构",
    ]
    for x in s.get("structure", []):
        lines.append(f"- {x}")
    lines.append("")
    lines.append("## 关键主题")
    for x in s.get("key_topics", []):
        lines.append(f"- {x}")
    return "\n".join(lines) + "\n"


def _rejected(result: dict) -> str:
    lines = ["# 被淘汰的候选", ""]
    for r in result["rejected"]:
        lines.append(f"- **{r.get('id','')}**：{r.get('reason','')}")
    return "\n".join(lines) + "\n"
