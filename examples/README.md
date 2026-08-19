# 示例蒸馏产物

本目录下的 `sample-output/` 由以下命令**自动生成**，仅用于展示文件格式：

```bash
distill book ../tests/fixtures/sample.txt --mock --output-dir ./sample-output
```

> 注意：示例内容来自 `--mock` 演示模式（未调用真实大模型），所以文字是占位演示，
> **不代表真实蒸馏质量**。装上 API Key 后，对真实书籍/视频跑一遍即可得到高质量产物。

## 目录结构（与真实运行一致）

```
sample-output/
└── <书名>/
    ├── README.md            # 本产物说明 + 使用方式
    ├── BOOK_OVERVIEW.md     # 整书全局理解
    ├── INDEX.md             # 技能全景图 + 学习顺序
    ├── skills/              # 技能卡（Agent Skill 兼容）
    │   ├── 行动闭环法.md
    │   ├── 每日复盘框架.md
    │   └── 知识卡片法.md
    ├── flashcards.md        # 复习卡片
    ├── action-checklist.md  # 行动清单
    └── distill.meta.json    # 生成元信息
```
