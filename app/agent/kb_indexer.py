from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, List, Optional


CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200
SUPPORTED_EXTS = {".txt", ".md", ".pdf", ".rst", ".csv", ".log"}


def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


def _read_file(p: Path) -> str:
    suffix = p.suffix.lower()
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(p))
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception:
            return ""
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def collect_chunks(kb_path: Optional[str]) -> List[Dict]:
    """
    Walk a knowledge-base path and produce a list of chunk dicts ready to be
    sent to the vector store.

    Returns an empty list if the path is missing or empty.

    Each entry: ``{"id", "text", "source", "mtime"}``.
    """
    if not kb_path:
        return []

    root = Path(kb_path)
    if not root.exists():
        return []

    files: List[Path]
    if root.is_file():
        files = [root]
    else:
        files = [
            f
            for f in root.rglob("*")
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS
        ]

    out: List[Dict] = []
    for f in files:
        text = _read_file(f)
        if not text:
            continue
        try:
            mtime = f.stat().st_mtime
        except Exception:
            mtime = 0.0
        for i, ch in enumerate(_chunk_text(text)):
            base = f"{f.resolve()}::{i}::{mtime}"
            cid = hashlib.sha1(base.encode("utf-8")).hexdigest()
            out.append(
                {
                    "id": cid,
                    "text": ch,
                    "source": str(f),
                    "mtime": mtime,
                }
            )
    return out
