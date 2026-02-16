from typing import List, Dict

def chunk_text(text: str, chunk_size=1200, overlap=200):
    text = text.replace("\r", "\n")
    paras = [p.strip() for p in text.split("\n") if p.strip()]
    joined = []
    buf = ""
    for p in paras:
        if len(buf) + len(p) + 1 <= chunk_size:
            buf = (buf + "\n" + p).strip()
        else:
            if buf:
                joined.append(buf)
            buf = p
    if buf:
        joined.append(buf)

    # add overlap using sliding window over joined chunks
    out = []
    for c in joined:
        if not out:
            out.append(c)
        else:
            prev = out[-1]
            out.append(prev[-overlap:] + "\n" + c)
    return out


def chunk_docs(docs: List[dict]) -> List[Dict]:
    """
    Returns list of chunks with metadata:
    [{"chunk_id": int, "doc_id": str, "text": str, "source": str}]
    """
    chunks = []
    cid = 0
    for d in docs:
        for c in chunk_text(d["text"]):
            chunks.append({
                "chunk_id": cid,
                "doc_id": d["doc_id"],
                "source": d["source"],
                "text": c,
            })
            cid += 1
    return chunks
