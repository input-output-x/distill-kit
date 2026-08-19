"""用 --mock 模式对整条流水线做冒烟测试（不调用真实模型）。"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from distillkit.config import Config
from distillkit.llm import LLMClient
from distillkit import pipeline
from distillkit.ingest import chunk_text


def test_chunk_text():
    chunks = chunk_text("段落一\n段落二\n段落三", chunk_chars=10)
    assert len(chunks) >= 1


def test_mock_pipeline():
    cfg = Config.load(None)
    cfg.distill["top_k"] = 3
    client = LLMClient(cfg, mock=True)
    text = (ROOT / "tests" / "fixtures" / "sample.txt").read_text(encoding="utf-8")
    result = pipeline.run(text, cfg, client, "book", "sample.txt")
    assert result["survey"]["title"]
    assert result["skills"], "应产出至少一张技能卡"
    assert len(result["skills"]) <= 3


if __name__ == "__main__":
    test_chunk_text()
    test_mock_pipeline()
    print("OK: 冒烟测试通过（mock 模式）")
