# distillkit · Knowledge Distiller

> Turn a book / a video / any long text into a structured **knowledge pack** of reusable skills.

"Distillation" here follows the idea popularized by kangarooking's **Cangjie Skill**: a general LLM
often answers with a "something's missing" feeling because it hasn't read the material that is
*new to the model but valuable to you*. Distillation extracts the methodologies, frameworks,
principles and mental models from that material into callable "skill cards".

This repo is an **open-source, self-hostable implementation** of that idea — your API key, your
machine, your data stays local. (Distinct from Cangjie Skill; prompts and pipeline are original.)

## What it produces

| File | Content |
| --- | --- |
| `BOOK_OVERVIEW.md` | Global understanding: one-liner, core thesis, structure, key topics |
| `INDEX.md` | Skill panorama + recommended order + usage |
| `skills/*.md` | Executable skill cards (Agent-Skill compatible) |
| `flashcards.md` | Q&A review cards |
| `action-checklist.md` | Actionable checklist |
| `rejected.md` | Rejected candidates + reasons |
| `distill.meta.json` | Run metadata |

## Install

```bash
pip install -e .
pip install pypdf ebooklib beautifulsoup4   # for PDF / EPUB
```

## Quick start

```bash
distill --init
export DISTILL_API_KEY=sk-xxx
distill book my-book.pdf --output-dir ./distilled
distill video transcript.txt
echo "some text..." | distill text -
distill book sample.txt --mock   # demo without a real model
```

## Inputs

- `distill book file` — `.txt` `.md` `.pdf` `.epub`
- `distill video transcript.txt` — transcript/subtitle text (transcribe online videos with yt-dlp/whisper first)
- `distill text -` — any text from stdin

## Models

Any **OpenAI Chat Completions** endpoint works (OpenAI / DeepSeek / Qwen / GLM / local llama.cpp / vLLM).
Configure via `distill.yaml` or env vars `DISTILL_API_KEY` / `DISTILL_BASE_URL` / `DISTILL_MODEL`.

## License

[MIT](./LICENSE)
