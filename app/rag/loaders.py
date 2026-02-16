from pathlib import Path
from typing import List
from pypdf import PdfReader

def load_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    parts: List[str] = []
    for page in reader.pages:
        txt = page.extract_text() or ""
        if txt.strip():
            parts.append(txt)
    return "\n".join(parts)

def load_docs_from_dir(docs_dir: Path) -> List[dict]:
    """
    Returns [{"doc_id": "...", "text": "...", "source": "..."}]
    """
    out: List[dict] = []
    for p in sorted(docs_dir.glob("*.pdf")):
        out.append({
            "doc_id": p.stem,
            "text": load_pdf_text(p),
            "source": str(p.name),
        })
    return out
