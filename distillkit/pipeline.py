"""蒸馏编排：五阶流水线。"""

from __future__ import annotations

import json
import re

from . import prompts
from .ingest import chunk_text


def extract_json(text: str) -> dict:
    """从模型输出中稳健地解析 JSON（容忍 ```json 围栏与前后废话）。"""
    if not text:
        raise RuntimeError("模型返回为空，无法解析 JSON。")
    s = text.strip()
    # 去掉 markdown 代码围栏
    s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*```$", "", s)
    # 截取第一个 { 到最后一个 }
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        s = s[start : end + 1]
        try:
            return json.loads(s)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"JSON 解析失败：{e}\n片段：{s[:300]}") from e
    raise RuntimeError(f"未找到 JSON 对象：{text[:300]}")


def run(text: str, cfg, client, kind: str, source_name: str) -> dict:
    lang = cfg.distill.get("language", "zh")
    top_k = int(cfg.distill.get("top_k", 12))
    chunk_chars = int(cfg.distill.get("chunk_chars", 6000))

    # 阶段一：通读（map-reduce）
    chunks = chunk_text(text, chunk_chars)
    if not chunks:
        raise RuntimeError("输入文本为空。")
    summaries = []
    for i, ch in enumerate(chunks, 1):
        out = client.chat(prompts.survey_map_messages(ch, lang))
        summaries.append(f"【片段 {i}】\n{out}")
    summaries_text = "\n\n".join(summaries)
    survey = extract_json(client.chat(prompts.survey_reduce_messages(summaries_text, lang)))

    # 阶段二：萃取候选
    candidates = extract_json(
        client.chat(prompts.extract_messages(survey, summaries_text, lang, top_k))
    )
    cand_list = candidates.get("candidates", []) if isinstance(candidates, dict) else candidates
    if not isinstance(cand_list, list) or not cand_list:
        raise RuntimeError("未提取到任何候选知识单元。")

    # 阶段三：筛滤
    filt = extract_json(client.chat(prompts.filter_messages(candidates, survey, lang, top_k)))
    kept_ids = set(filt.get("kept", [])) if isinstance(filt, dict) else set()
    rejected = filt.get("rejected", []) if isinstance(filt, dict) else []
    kept = [c for c in cand_list if c.get("id") in kept_ids]
    if not kept:
        # 兜底：若筛选异常，保留前 top_k
        kept = cand_list[:top_k]

    # 阶段四：逐单元结晶
    skills = []
    for c in kept:
        md = client.chat(prompts.crystallize_messages(c, survey, summaries_text, lang))
        skills.append({"meta": c, "md": md})

    # 阶段五：汇编
    index = client.chat(prompts.compile_index_messages(skills, survey, lang))
    cards = client.chat(prompts.compile_cards_messages(skills, survey, lang))
    checklist = client.chat(prompts.compile_checklist_messages(skills, survey, lang))

    return {
        "source_name": source_name,
        "kind": kind,
        "language": lang,
        "survey": survey,
        "candidates": cand_list,
        "kept_ids": sorted(kept_ids),
        "rejected": rejected,
        "skills": skills,
        "index": index,
        "cards": cards,
        "checklist": checklist,
    }
