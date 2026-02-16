from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json
import math
import re

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

@dataclass
class SearchResult:
    score: float
    text: str
    source: str
    chunk_id: int

def _tokenize(text: str) -> List[str]:
    # simple, fast tokenizer
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    return [t for t in text.split() if t]

class _BM25:
    """
    Minimal BM25 implementation (no external deps).
    """
    def __init__(self, corpus_tokens: List[List[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_tokens = corpus_tokens
        self.N = len(corpus_tokens)
        self.avgdl = sum(len(d) for d in corpus_tokens) / max(1, self.N)

        # document frequencies
        df: Dict[str, int] = {}
        for doc in corpus_tokens:
            for term in set(doc):
                df[term] = df.get(term, 0) + 1
        self.df = df

        # idf
        self.idf: Dict[str, float] = {}
        for term, freq in df.items():
            # BM25+ style smoothing
            self.idf[term] = math.log(1 + (self.N - freq + 0.5) / (freq + 0.5))

    def scores(self, query_tokens: List[str]) -> np.ndarray:
        scores = np.zeros(self.N, dtype=np.float32)
        if self.N == 0:
            return scores

        qfreq: Dict[str, int] = {}
        for t in query_tokens:
            qfreq[t] = qfreq.get(t, 0) + 1

        for i, doc in enumerate(self.corpus_tokens):
            dl = len(doc)
            if dl == 0:
                continue
            tf: Dict[str, int] = {}
            for t in doc:
                tf[t] = tf.get(t, 0) + 1

            s = 0.0
            for term in qfreq.keys():
                if term not in tf:
                    continue
                idf = self.idf.get(term, 0.0)
                f = tf[term]
                denom = f + self.k1 * (1 - self.b + self.b * (dl / self.avgdl))
                s += idf * (f * (self.k1 + 1)) / (denom + 1e-9)
            scores[i] = s
        return scores

class RagIndex:
    def __init__(self, *, base_dir: Path, embedding_model_name: str):
        self.base_dir = base_dir
        self.embedding_model_name = embedding_model_name
        self.model = SentenceTransformer(embedding_model_name)

        self.index_path = base_dir / "faiss.index"
        self.chunks_path = base_dir / "chunks.json"
        self.meta_path = base_dir / "meta.json"
        self.bm25_path = base_dir / "bm25.json"

        self._faiss = None
        self._chunks: Optional[List[dict]] = None
        self._bm25: Optional[_BM25] = None
        self._bm25_tokens: Optional[List[List[str]]] = None

    def _embed(self, texts: List[str]) -> np.ndarray:
        embs = self.model.encode(texts, normalize_embeddings=True)
        return np.asarray(embs, dtype="float32")

    def build(self, chunks: List[dict]) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)

        texts = [c["text"] for c in chunks]
        if not texts:
            dim = 384
            self._faiss = faiss.IndexFlatIP(dim)
            self._chunks = []
            self._bm25_tokens = []
            self._bm25 = _BM25([])
            self.save()
            return

        vecs = self._embed(texts)
        dim = vecs.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(vecs)

        self._faiss = index
        self._chunks = chunks

        # BM25 store
        self._bm25_tokens = [_tokenize(t) for t in texts]
        self._bm25 = _BM25(self._bm25_tokens)

        self.save()

    def save(self) -> None:
        faiss.write_index(self._faiss, str(self.index_path))
        with open(self.chunks_path, "w", encoding="utf-8") as f:
            json.dump(self._chunks, f, ensure_ascii=False, indent=2)
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump({"embedding_model": self.embedding_model_name}, f, indent=2)
        with open(self.bm25_path, "w", encoding="utf-8") as f:
            # store only tokens; bm25 is rebuilt on load
            json.dump({"tokens": self._bm25_tokens or []}, f)

    def load(self) -> None:
        self._faiss = faiss.read_index(str(self.index_path))
        with open(self.chunks_path, "r", encoding="utf-8") as f:
            self._chunks = json.load(f)
        if self.bm25_path.exists():
            with open(self.bm25_path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            self._bm25_tokens = obj.get("tokens", [])
            self._bm25 = _BM25(self._bm25_tokens)
        else:
            # backward compatibility
            texts = [c["text"] for c in (self._chunks or [])]
            self._bm25_tokens = [_tokenize(t) for t in texts]
            self._bm25 = _BM25(self._bm25_tokens)

    def exists(self) -> bool:
        return self.index_path.exists() and self.chunks_path.exists()

    def search_dense(self, query: str, *, top_k: int) -> List[SearchResult]:
        if self._faiss is None or self._chunks is None:
            self.load()

        qvec = self._embed([query])
        scores, idxs = self._faiss.search(qvec, top_k)

        out: List[SearchResult] = []
        for score, idx in zip(scores[0].tolist(), idxs[0].tolist()):
            if idx < 0:
                continue
            ch = self._chunks[idx]
            out.append(SearchResult(
                score=float(score),
                text=ch["text"],
                source=ch.get("source", ""),
                chunk_id=int(ch.get("chunk_id", idx)),
            ))
        return out

    def search_hybrid(self, query: str, *, top_k: int, alpha: float = 0.65) -> List[SearchResult]:
        """
        alpha: weight for dense score; (1-alpha) for bm25
        """
        if self._faiss is None or self._chunks is None or self._bm25 is None:
            self.load()

        # 1. Fetch more candidates than needed for better re-ranking
        dense = self.search_dense(query, top_k=max(top_k * 4, 20))

        # 2. Get BM25 scores
        qtok = _tokenize(query)
        bm25_scores = self._bm25.scores(qtok) if self._bm25 else np.zeros(len(self._chunks), dtype=np.float32)

        # 3. ROBUST NORMALIZATION: Prevent division by zero
        if bm25_scores.size and bm25_scores.max() > 0:
            bm_min, bm_max = float(bm25_scores.min()), float(bm25_scores.max())
            # Use max(..., 1e-9) to ensure the denominator is never zero
            bm_norm = (bm25_scores - bm_min) / (bm_max - bm_min + 1e-9)
        else:
            bm_norm = bm25_scores

        # 4. Dense normalization over retrieved candidates
        if dense:
            dvals = np.array([r.score for r in dense], dtype=np.float32)
            dmin, dmax = float(dvals.min()), float(dvals.max())
            denom = dmax - dmin + 1e-9
        else:
            dmin, dmax, denom = 0.0, 1.0, 1.0

        # 5. Merging Logic
        seen = set()
        merged: List[Tuple[float, int]] = []

        # Process dense candidates first
        for r in dense:
            idx = r.chunk_id
            if idx in seen:
                continue
            seen.add(idx)

            d_norm = (r.score - dmin) / denom
            b_norm_val = float(bm_norm[idx]) if idx < len(bm_norm) else 0.0

            # Weighted average
            combined_score = (alpha * d_norm) + ((1 - alpha) * b_norm_val)
            merged.append((combined_score, idx))

        # 6. Include top BM25 candidates that weren't in the dense results
        if len(self._chunks) > 0:
            # Sort all BM25 scores descending and take the top N
            top_b_indices = np.argsort(-bm_norm)[: max(top_k * 4, 20)]
            for idx in top_b_indices.tolist():
                if idx in seen:
                    continue
                seen.add(idx)
                # For BM25-only results, we assume d_norm is 0
                b_val = float(bm_norm[idx])
                merged.append(((1 - alpha) * b_val, idx))

        # 7. Final Sort and Trim
        merged.sort(key=lambda x: x[0], reverse=True)
        merged = merged[:top_k]

        out: List[SearchResult] = []
        for score, idx in merged:
            ch = self._chunks[idx]
            out.append(SearchResult(
                score=float(score),
                text=ch["text"],
                source=ch.get("source", ""),
                chunk_id=int(ch.get("chunk_id", idx)),
            ))
        return out
