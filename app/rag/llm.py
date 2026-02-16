# app/rag/llm.py
import requests
from app.rag.config import rag_settings

class LocalLlm:
    def __init__(self):
        self.model = rag_settings.ollama_model
        self.url = rag_settings.ollama_url.rstrip("/") + "/api/generate"

    def generate(self, *, prompt: str) -> str:
        try:
            r = requests.post(
                self.url,
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=120,
            )
            r.raise_for_status()
            return (r.json().get("response") or "").strip() or rag_settings.fallback_message
        except Exception:
            return rag_settings.fallback_message
