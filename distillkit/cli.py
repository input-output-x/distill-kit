"""命令行入口。"""

from __future__ import annotations

import argparse
import sys

from .config import Config
from . import ingest
from .llm import LLMClient
from . import pipeline
from .output import write


def build_parser() -> argparse.ArgumentParser:
    # 公共参数：既能在子命令前，也能在子命令后（通过 parents 共享）
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", default="distill.yaml", help="配置文件路径")
    common.add_argument("--output-dir", default=None, help="输出目录（覆盖配置）")
    common.add_argument("--model", default=None, help="模型名（覆盖配置）")
    common.add_argument("--api-key", default=None, help="LLM API Key（覆盖配置）")
    common.add_argument("--base-url", default=None, help="OpenAI 兼容端点（覆盖配置）")
    common.add_argument("--top-k", default=None, help="保留的技能数量")
    common.add_argument("--language", default=None, choices=["zh", "en"], help="输出语言")
    common.add_argument("--mock", action="store_true", help="不调用真实模型，生成演示产物")
    common.add_argument("--init", action="store_true", help="生成示例配置文件并退出")

    p = argparse.ArgumentParser(
        prog="distill",
        parents=[common],
        description="把书 / 视频 / 文本蒸馏成结构化知识包（技能卡 + 索引 + 卡片 + 清单）。",
    )
    sub = p.add_subparsers(dest="kind")
    pb = sub.add_parser("book", parents=[common], help="蒸馏一本书（txt/md/pdf/epub）")
    pb.add_argument("path", help="书本文件路径")
    pv = sub.add_parser("video", parents=[common], help="蒸馏一段视频（传入转录/字幕文本）")
    pv.add_argument("path", help="转录/字幕文本路径（txt/srt/vtt/md）")
    pt = sub.add_parser("text", parents=[common], help="蒸馏一段文本")
    pt.add_argument("content", nargs="?", default="-", help="文本内容，或用 - 从 stdin 读取")
    pu = sub.add_parser("url", parents=[common], help="（预留）视频/文章链接")
    pu.add_argument("url", help="链接")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.init:
        cfg = Config.load(args.config)
        cfg.save(args.config)
        print(f"已生成示例配置：{args.config}")
        return 0

    if not args.kind:
        build_parser().print_help()
        return 1

    cfg = Config.load(args.config)
    cfg.apply_cli(args)

    if args.kind == "url":
        print(
            "「url」模式需要先把链接转成文本/字幕：\n"
            "  视频：用 yt-dlp 下载字幕，或用 whisper 转写，再 `distill video 字幕.txt`\n"
            "  文章：用浏览器另存为 .md / .txt，再 `distill book 文件`\n"
            "本工具专注于「文本 -> 知识包」，摄取由你掌控，便于处理带图/付费内容。"
        )
        return 0

    # 读取输入
    try:
        if args.kind == "text":
            content = args.content
            if content == "-":
                # Windows 下 sys.stdin 默认用控制台代码页（如 cp936），管道传入
                # 的 UTF-8 文本会乱码；统一重配置为 utf-8 以保证跨平台一致。
                try:
                    sys.stdin.reconfigure(encoding="utf-8")
                except (AttributeError, ValueError):
                    pass
                content = sys.stdin.read()
            text = content
            source_name = "stdin-text"
        else:
            text = ingest.load_source(args.kind, args.path)
            source_name = args.path
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"读取输入失败：{e}", file=sys.stderr)
        return 1

    if not args.mock:
        try:
            cfg.validate()
        except RuntimeError as e:
            print(f"配置错误：{e}", file=sys.stderr)
            return 1

    client = LLMClient(cfg, mock=args.mock)
    print(f"开始蒸馏：{source_name}（kind={args.kind}, mock={args.mock}）")
    try:
        result = pipeline.run(text, cfg, client, args.kind, source_name)
    except RuntimeError as e:
        print(f"蒸馏失败：{e}", file=sys.stderr)
        return 1

    out_dir = cfg.distill.get("output_dir", "./distilled")
    folder = write(result, out_dir, cfg)
    print(f"完成！生成 {len(result['skills'])} 张技能卡 -> {folder}")
    print(f"  概览：{folder / 'BOOK_OVERVIEW.md'}")
    print(f"  索引：{folder / 'INDEX.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
