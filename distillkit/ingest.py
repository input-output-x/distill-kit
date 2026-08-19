"""输入摄取：书 / 视频字幕 / 文本 -> 纯文本，并按段落切片。"""

from __future__ import annotations

from pathlib import Path


def load_source(kind: str, path: str) -> str:
    """根据输入类型读取为纯文本。"""
    if kind == "text":
        return path  # 已经是文本
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"找不到输入文件：{path}")
    ext = p.suffix.lower()
    if kind == "video":
        # 视频模式接收「转录 / 字幕」文本（txt / srt / vtt / md）
        return p.read_text(encoding="utf-8", errors="ignore")
    if kind == "book":
        if ext in (".txt", ".md", ".markdown"):
            return p.read_text(encoding="utf-8", errors="ignore")
        if ext == ".pdf":
            return _load_pdf(path)
        if ext == ".epub":
            return _load_epub(path)
        raise ValueError(f"不支持的书本格式：{ext}（支持 .txt/.md/.pdf/.epub）")
    raise ValueError(f"未知输入类型：{kind}")


def _load_pdf(path: str) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise RuntimeError(
            "读取 PDF 需要 pypdf，请执行：pip install pypdf"
        ) from e
    reader = PdfReader(path)
    pages = [(p.extract_text() or "") for p in reader.pages]
    return "\n\n".join(pages)


def _load_epub(path: str) -> str:
    try:
        import ebooklib
        from ebooklib import epub
        from bs4 import BeautifulSoup
    except ImportError as e:
        raise RuntimeError(
            "读取 EPUB 需要 ebooklib + beautifulsoup4，请执行："
            "pip install ebooklib beautifulsoup4"
        ) from e
    book = epub.read_epub(path)
    parts = []
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_content(), "html.parser")
            parts.append(soup.get_text())
    return "\n\n".join(parts)


def chunk_text(text: str, chunk_chars: int = 6000) -> list[str]:
    """尽量按段落边界把长文本切成不超过 chunk_chars 的片段。"""
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    cur = ""
    for para in text.split("\n"):
        para = para.rstrip()
        if cur and len(cur) + len(para) + 1 > chunk_chars:
            chunks.append(cur.strip())
            cur = para
        else:
            cur = f"{cur}\n{para}" if cur else para
    if cur.strip():
        chunks.append(cur.strip())
    return chunks
