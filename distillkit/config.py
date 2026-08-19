"""配置加载：文件 + 环境变量覆盖。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from pathlib import Path

import yaml

DEFAULT_CONFIG: dict = {
    "llm": {
        "base_url": "https://api.openai.com/v1",
        "api_key": "",
        "model": "gpt-4o-mini",
        "temperature": 0.3,
        "max_tokens": 4096,
        "timeout": 120,
    },
    "distill": {
        "top_k": 12,
        "chunk_chars": 6000,
        "language": "zh",
        "output_dir": "./distilled",
    },
}

# 环境变量 -> (section, key)
ENV_MAP = {
    "DISTILL_API_KEY": ("llm", "api_key"),
    "DISTILL_BASE_URL": ("llm", "base_url"),
    "DISTILL_MODEL": ("llm", "model"),
    "DISTILL_TOP_K": ("distill", "top_k"),
    "DISTILL_LANGUAGE": ("distill", "language"),
    "DISTILL_OUTPUT_DIR": ("distill", "output_dir"),
}


@dataclass
class Config:
    llm: dict = field(default_factory=dict)
    distill: dict = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | None = None) -> "Config":
        cfg = {k: dict(v) for k, v in DEFAULT_CONFIG.items()}
        # 环境变量覆盖（最低优先级，但高于默认值）
        for env, (sec, key) in ENV_MAP.items():
            val = os.environ.get(env)
            if val is not None:
                # 尝试把数字解析成 int
                if key in ("top_k",):
                    try:
                        val = int(val)
                    except ValueError:
                        pass
                cfg[sec][key] = val
        # 配置文件覆盖（高于环境变量）
        if path and Path(path).exists():
            with open(path, "r", encoding="utf-8") as f:
                user = yaml.safe_load(f) or {}
            for sec in ("llm", "distill"):
                if sec in user and isinstance(user[sec], dict):
                    cfg[sec].update(user[sec])
        return cls(**cfg)

    def apply_cli(self, args) -> None:
        """命令行参数覆盖（最高优先级）。"""
        mapping = {
            "model": ("llm", "model"),
            "api_key": ("llm", "api_key"),
            "base_url": ("llm", "base_url"),
            "top_k": ("distill", "top_k"),
            "language": ("distill", "language"),
            "output_dir": ("distill", "output_dir"),
        }
        for attr, (sec, key) in mapping.items():
            val = getattr(args, attr, None)
            if val is not None:
                if key == "top_k":
                    val = int(val)
                self.__dict__[sec][key] = val

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(asdict(self), f, allow_unicode=True, sort_keys=False)

    def validate(self) -> None:
        if not self.llm.get("api_key"):
            raise RuntimeError(
                "未配置 LLM API Key。请设置环境变量 DISTILL_API_KEY，"
                "或在配置文件中填写 llm.api_key，或使用 --api-key 参数。"
            )
