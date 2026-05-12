from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parent.parent.parent


class AgentSettings(BaseSettings):
    """
    Configuration for the agentic-RAG layer.

    Reads OPENAI_API_KEY (and any other variables) from the project's `.env`.
    Per-call-center artefacts (Chroma collections, FAQ json) live under
    ``<repo>/data/cc_<id>/`` so different call centers never overlap.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    OPENAI_API_KEY: str = ""

    # Models
    chat_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    # Storage
    data_dir: Path = ROOT_DIR / "data"

    # Retrieval
    top_k: int = 6

    # FAQ matching
    faq_similarity_threshold: float = 0.86

    # Conversation behaviour
    history_limit: int = 12
    max_tool_iterations: int = 5
    fallback_message: str = "I can't find a relevant answer for your question."

    # Memory TTL
    memory_ttl_seconds: int = 3600


agent_settings = AgentSettings()
agent_settings.data_dir.mkdir(parents=True, exist_ok=True)


def cc_data_dir(call_center_id: int) -> Path:
    """Per-call-center data folder. Created on demand."""
    p = agent_settings.data_dir / f"cc_{call_center_id}"
    p.mkdir(parents=True, exist_ok=True)
    return p
