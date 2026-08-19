"""OpenAI 兼容的 LLM 客户端（含 --mock 演示模式）。

支持任意 OpenAI Chat Completions 兼容端点：
OpenAI / DeepSeek / 通义 / 智谱 / 本地 llama.cpp / vLLM 等。
"""

from __future__ import annotations

import json

import requests

from .config import Config

_MOCK_SURVEY = {
    "title": "示例书（MOCK 演示）",
    "one_liner": "这是一本关于「如何把知识变成行动」的书（本段由 --mock 生成，未调用真实模型）。",
    "core_thesis": "真正的成长来自把方法论落成可复用的动作，而不是收藏更多资料。",
    "target_audience": "想把读过的书真正用起来的自学者。",
    "structure": ["第一篇：认知", "第二篇：方法", "第三篇：实践"],
    "key_topics": ["知识内化", "行动闭环", "复盘迭代"],
}


class LLMClient:
    def __init__(self, cfg: Config, mock: bool = False):
        self.llm = cfg.llm
        self.mock = mock

    def chat(self, messages, temperature=None, max_tokens=None) -> str:
        if self.mock:
            return self._mock(messages)
        temperature = temperature if temperature is not None else self.llm.get("temperature", 0.3)
        max_tokens = max_tokens or self.llm.get("max_tokens", 4096)
        url = self.llm["base_url"].rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.llm['api_key']}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.llm["model"],
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            r = requests.post(url, headers=headers, json=body, timeout=self.llm.get("timeout", 120))
        except requests.RequestException as e:
            raise RuntimeError(f"调用 LLM 失败（{url}）：{e}") from e
        if r.status_code != 200:
            raise RuntimeError(f"LLM 返回错误 {r.status_code}：{r.text[:500]}")
        data = r.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"LLM 返回格式异常：{data}") from e

    # ------------------------------------------------------------------
    # --mock 演示：根据 system prompt 中的阶段标签返回合法占位内容 -------
    # ------------------------------------------------------------------
    def _mock(self, messages) -> str:
        system = messages[0]["content"] if messages else ""
        if "SURVEY_MAP" in system:
            return "本片段提出了「把知识变成动作」的核心主张，并给了两个小例子。"
        if "SURVEY_REDUCE" in system:
            return json.dumps(_MOCK_SURVEY, ensure_ascii=False, indent=2)
        if "EXTRACT" in system:
            cands = [
                {"id": "c1", "name": "行动闭环法", "type": "method",
                 "why_valuable": "把模糊的目标变成可执行的步骤", "source_hint": "第二篇"},
                {"id": "c2", "name": "每日复盘框架", "type": "framework",
                 "why_valuable": "用固定问题清单做低成本复盘", "source_hint": "第三篇"},
                {"id": "c3", "name": "知识卡片法", "type": "technique",
                 "why_valuable": "把书摘变成可检索的卡片", "source_hint": "第一篇"},
            ]
            return json.dumps({"candidates": cands}, ensure_ascii=False, indent=2)
        if "FILTER" in system:
            return json.dumps(
                {"kept": ["c1", "c2", "c3"], "rejected": []},
                ensure_ascii=False, indent=2,
            )
        if "CRYSTALLIZE" in system:
            return (
                "# 行动闭环法\n\n"
                "> 一句话：把模糊目标拆成「触发—动作—检验」三步并立刻执行。\n\n"
                "## 适用场景（触发条件）\n- 想做一件事却一直没开始。\n\n"
                "## 核心步骤\n1. 写下最小可行动作。\n2. 设定触发条件。\n3. 完成后自检。\n\n"
                "## 关键判断 / 原则\n- 动作用动词开头。\n\n"
                "## 案例\n- 想读书 → 「每天通勤读 5 页」。\n\n"
                "## 常见误区 / 反模式\n- 目标过大导致无从下手。\n\n"
                "## 来源\n- 《示例书》第二篇（MOCK 演示内容）。\n"
            )
        if "COMPILE_INDEX" in system:
            return (
                "# 技能全景图（MOCK）\n\n"
                "1. 行动闭环法 — 把目标变动作\n2. 每日复盘框架 — 低成本复盘\n"
                "3. 知识卡片法 — 书摘变卡片\n\n"
                "**推荐学习顺序**：先学行动闭环法，再复盘，最后沉淀卡片。\n"
            )
        if "COMPILE_CARDS" in system:
            return (
                "# 复习卡片（MOCK）\n\n"
                "- Q：行动闭环法的三步是什么？\n  A：触发—动作—检验。\n"
                "- Q：复盘框架为什么低成本？\n  A：用固定问题清单，不需写长文。\n"
            )
        if "COMPILE_CHECKLIST" in system:
            return (
                "# 行动清单（MOCK）\n\n"
                "- [ ] 选一本正在读的书，挑一个方法论今天就用一次\n"
                "- [ ] 建一个每日复盘的问题清单\n"
                "- [ ] 把三条书摘写成知识卡片\n"
            )
        return "（MOCK 占位回复）"
