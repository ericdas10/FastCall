from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parent.parent.parent
class RagSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_dir: Path = ROOT_DIR / "app" / "rag" / "data"

    top_k: int = 8
    min_score: float = 0.15
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "mistral"

    fallback_message: str = "I can't find a relevant answer for your question"

    memory_ttl_seconds: int = 3600
    hybrid_alpha: float = 0.65

rag_settings = RagSettings()
rag_settings.data_dir.mkdir(parents=True, exist_ok=True)
