from pathlib import Path
from app.rag.config import rag_settings
from app.rag.loaders import load_docs_from_dir
from app.rag.chunking import chunk_docs
from app.rag.index import RagIndex

def ingest_call_center(call_center_id: int) -> None:
    base_dir = Path(rag_settings.data_dir) / f"cc_{call_center_id}"
    docs_dir = base_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    docs = load_docs_from_dir(docs_dir)

    chunks = chunk_docs(docs)

    idx = RagIndex(base_dir=base_dir, embedding_model_name=rag_settings.embedding_model)
    idx.build(chunks)