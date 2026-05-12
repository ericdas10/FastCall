from __future__ import annotations

from threading import Lock
from typing import Dict, List, Optional

import chromadb

from app.agent.config import cc_data_dir
from app.agent.openai_client import embed_texts


class CallCenterVectorStore:
    """
    Chroma-backed vector store, isolated per call center.

    The persistent directory is `data/cc_<id>/chroma/` and the collection name
    is `cc_<id>`, so multiple call centers can never share documents.
    Embeddings are computed via OpenAI (`text-embedding-3-small` by default).
    """

    def __init__(self, call_center_id: int) -> None:
        self.call_center_id = call_center_id
        self.dir = cc_data_dir(call_center_id) / "chroma"
        self.dir.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(path=str(self.dir))
        self._collection = self._client.get_or_create_collection(
            name=f"cc_{call_center_id}",
            metadata={"hnsw:space": "cosine"},
        )

    # ---------- indexing ----------

    def index_documents(self, *, documents: List[Dict]) -> int:
        """
        Upsert a list of pre-chunked documents into the collection.

        Each document must have: ``id`` (stable), ``text``, optional ``source``
        and ``mtime``. Returns the number of records written.
        """
        if not documents:
            return 0

        ids = [str(d["id"]) for d in documents]
        texts = [d["text"] for d in documents]
        metadatas = [
            {
                "source": str(d.get("source", "")),
                "mtime": float(d.get("mtime", 0.0)),
            }
            for d in documents
        ]

        # OpenAI embeddings can be large batches; chunk to keep request size sane.
        embeddings: List[List[float]] = []
        BATCH = 64
        for i in range(0, len(texts), BATCH):
            embeddings.extend(embed_texts(texts[i : i + BATCH]))

        # Upsert by id (delete first so updated content fully replaces old).
        try:
            self._collection.delete(ids=ids)
        except Exception:
            pass

        self._collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        return len(ids)

    # ---------- query ----------

    def search(self, query: str, top_k: int = 6) -> List[Dict]:
        if not query or not query.strip():
            return []
        if self._collection.count() == 0:
            return []

        q_emb = embed_texts([query])[0]
        res = self._collection.query(query_embeddings=[q_emb], n_results=top_k)

        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        ids = (res.get("ids") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]

        out: List[Dict] = []
        for i, doc in enumerate(docs):
            md = metas[i] if i < len(metas) else {}
            out.append(
                {
                    "id": ids[i] if i < len(ids) else None,
                    "text": doc,
                    "source": md.get("source", ""),
                    "distance": dists[i] if i < len(dists) else None,
                }
            )
        return out

    def is_empty(self) -> bool:
        try:
            return self._collection.count() == 0
        except Exception:
            return True


# ---- per-call-center store cache ----

_stores: Dict[int, CallCenterVectorStore] = {}
_stores_lock = Lock()


def get_vector_store(call_center_id: int) -> CallCenterVectorStore:
    with _stores_lock:
        s = _stores.get(call_center_id)
        if s is None:
            s = CallCenterVectorStore(call_center_id)
            _stores[call_center_id] = s
        return s
