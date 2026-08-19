"""五阶蒸馏法的提示词（原创）。

阶段：SURVEY_MAP -> SURRVEY_REDUCE -> EXTRACT -> FILTER
      -> CRYSTALLIZE(逐单元) -> COMPILE_INDEX / CARDS / CHECKLIST

每个函数返回 OpenAI 格式的 messages 列表；system 中以 [STAGE:xxx]
标记阶段，供 --mock 模式识别。
"""

from __future__ import annotations


def _lang_hint(lang: str) -> str:
    return "中文" if lang == "zh" else "English"


# 阶段一：通读（map）——逐片段提取要点
def survey_map_messages(chunk: str, lang: str) -> list[dict]:
    lh = _lang_hint(lang)
    system = (
        "[STAGE:SURVEY_MAP] 你是一位严谨的阅读笔记专家。用户会给你一段书稿/文稿的"
        "一个片段，请提取其中可复用的方法论、原则、框架、思维模型或技巧，"
        "给出 3-5 条要点。不要复述，只要「能拿走用的东西」。用" + lh + "回答。"
    )
    user = f"以下是文稿的一个片段，请提取要点：\n\n{chunk}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# 阶段一：通读（reduce）——汇总为整书全局理解（JSON）
def survey_reduce_messages(summaries_text: str, lang: str) -> list[dict]:
    lh = _lang_hint(lang)
    system = (
        "[STAGE:SURVEY_REDUCE] 你是一位图书蒸馏专家。基于各片段摘要，输出关于整本书/"
        "文稿的全局理解，必须只返回 JSON（不要解释、不要代码块围栏）。字段用" + lh + "："
        "title(书名/标题), one_liner(一句话总结), core_thesis(核心论点), "
        "target_audience(适合谁), structure(结构列表), key_topics(关键主题列表)。"
    )
    user = f"各片段摘要如下：\n\n{summaries_text}\n\n请输出 JSON。"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# 阶段二：萃取——候选知识单元（JSON）
def extract_messages(survey_json: dict, summaries_text: str, lang: str, top_k: int) -> list[dict]:
    lh = _lang_hint(lang)
    system = (
        "[STAGE:EXTRACT] 你是知识萃取专家。基于整书理解与摘要，列出值得蒸馏成"
        "「可执行知识单元」的候选方法论/框架/原则/技巧。只返回 JSON："
        "candidates 列表，每项含 id(简短英文slug), name(名称), type(method/framework/"
        "principle/mental-model/technique), why_valuable(为什么值得蒸馏), source_hint(出处提示)。"
        f"最多列出 {top_k * 2} 条。用{lh}。"
    )
    survey_str = _dump(survey_json)
    user = (
        f"整书理解：\n{survey_str}\n\n摘要：\n{summaries_text}\n\n"
        "请输出候选 JSON（字段用" + lh + "）。"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# 阶段三：筛滤——保留 top_k，其余给淘汰理由（JSON）
def filter_messages(candidates_json: dict, survey_json: dict, lang: str, top_k: int) -> list[dict]:
    lh = _lang_hint(lang)
    system = (
        f"[STAGE:FILTER] 你是筛选专家。从候选中保留最值得蒸馏的 {top_k} 条"
        "（优先选可独立复用、普适、高杠杆的），其余给出淘汰理由。只返回 JSON："
        "kept(保留的 id 列表), rejected(列表，每项 {{id, reason}})。用" + lh + "。"
    )
    user = (
        f"候选：\n{_dump(candidates_json)}\n\n整书理解：\n{_dump(survey_json)}\n\n"
        "请输出筛选 JSON。"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# 阶段四：结晶——把单个知识单元写成技能卡（Markdown）
def crystallize_messages(candidate: dict, survey_json: dict, summaries_text: str, lang: str) -> list[dict]:
    lh = _lang_hint(lang)
    system = (
        "[STAGE:CRYSTALLIZE] 你要把一个知识单元写成一份可被 AI / 人直接调用的"
        "「技能卡」(SKILL)。用 Markdown 输出，且只输出正文（不要 YAML 头），包含以下小节："
        "# 标题\n> 一句话（核心主张）\n## 适用场景（触发条件）\n## 核心步骤\n"
        "## 关键判断 / 原则\n## 案例\n## 常见误区 / 反模式\n## 来源\n用" + lh + "。"
    )
    user = (
        f"待蒸馏的知识单元：\n{_dump(candidate)}\n\n整书理解：\n{_dump(survey_json)}\n\n"
        f"相关摘要：\n{summaries_text}\n\n请写出这份技能卡。"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# 阶段五：汇编——索引 / 卡片 / 清单
def compile_index_messages(skills: list[dict], survey_json: dict, lang: str) -> list[dict]:
    lh = _lang_hint(lang)
    system = (
        "[STAGE:COMPILE_INDEX] 生成 INDEX.md：所有技能的全景图（名称 + 一句话），"
        "推荐学习顺序，以及「怎么用」说明。只用 Markdown。用" + lh + "。"
    )
    body = "\n\n---\n\n".join(s["md"] for s in skills)
    user = f"整书理解：\n{_dump(survey_json)}\n\n技能卡合集：\n{body}\n\n请生成 INDEX.md。"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def compile_cards_messages(skills: list[dict], survey_json: dict, lang: str) -> list[dict]:
    lh = _lang_hint(lang)
    system = (
        "[STAGE:COMPILE_CARDS] 基于所有技能生成 10-20 张复习卡片，每卡用 "
        "「- Q：…\n  A：…」格式。只用 Markdown。用" + lh + "。"
    )
    body = "\n\n---\n\n".join(s["md"] for s in skills)
    user = f"技能卡合集：\n{body}\n\n请生成复习卡片 flashcards.md。"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def compile_checklist_messages(skills: list[dict], survey_json: dict, lang: str) -> list[dict]:
    lh = _lang_hint(lang)
    system = (
        "[STAGE:COMPILE_CHECKLIST] 基于所有技能生成可立即执行的行动清单，"
        "用 Markdown 勾选列表（- [ ] …）。只用 Markdown。用" + lh + "。"
    )
    body = "\n\n---\n\n".join(s["md"] for s in skills)
    user = f"技能卡合集：\n{body}\n\n请生成 action-checklist.md。"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _dump(obj) -> str:
    import json

    if isinstance(obj, str):
        return obj
    return json.dumps(obj, ensure_ascii=False, indent=2)
