import os
import secrets
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent

_DEFAULT_SECRET_KEY = "dev-secret-change-me"

# Profils de retrieval appliqués au démarrage (PERFORMANCE_MODE).
_PERFORMANCE_MODE_CONFIGS: dict[str, dict[str, Any]] = {
    "fast": {
        "retrieval_top_k": 10,
        "rerank_top_k": 4,
        "enable_reranking": False,
    },
    "quality": {
        "retrieval_top_k": 20,
        "rerank_top_k": 5,
        "enable_reranking": True,
    },
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",  # ignore les clés .env non déclarées
    )

    # --- Application -------------------------------------------------------
    app_name: str = "Syro"
    domain: str = "general"  # persona par défaut quand aucun domaine n'est choisi
    debug: bool = False
    # Laisser vide : un secret aléatoire est généré et persisté dans data_dir.
    secret_key: str = _DEFAULT_SECRET_KEY
    access_token_exp_minutes: int = 60 * 24

    # --- LLM & embeddings --------------------------------------------------
    llm_provider: str = "ollama"  # ollama | openai
    ollama_base_url: str = "http://localhost:11434/v1"
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    chat_model: str = "llama3.2"
    chat_temperature: float = 0.2
    chat_max_tokens: int = 1024
    embeddings_model: str = "nomic-embed-text"
    embedding_dimensions: int = 768
    # Préfixes de tâche (nomic-embed-text est entraîné avec). None = auto
    # selon le modèle ; "" = désactivé.
    embedding_query_prefix: str | None = None
    embedding_document_prefix: str | None = None
    embedding_cache_enabled: bool = True
    embedding_cache_size: int = 1000
    llm_timeout: float = 60.0
    embedding_timeout: float = 30.0
    llm_max_retries: int = 2
    circuit_breaker_threshold: int = 5
    circuit_breaker_reset_seconds: float = 30.0

    # --- Stockage ----------------------------------------------------------
    data_dir: Path = PROJECT_ROOT / "storage"
    db_path: Path = PROJECT_ROOT / "db" / "syro.db"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection_name: str = "syro_chunks"

    # --- Ingestion ---------------------------------------------------------
    chunk_size_tokens: int = 400
    chunk_overlap_tokens: int = 60

    # --- Retrieval ---------------------------------------------------------
    performance_mode: str = "quality"  # fast | quality
    retrieval_top_k: int = 20  # candidats par retriever (dense, BM25) avant rerank
    rerank_top_k: int = 5  # chunks finaux envoyés au LLM
    rrf_k: int = 60  # constante Reciprocal Rank Fusion (standard = 60)
    enable_reranking: bool = True
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    # Score cross-encoder (sigmoïde, 0–1) minimal pour garder un chunk. Sous ce
    # seuil pour tous les candidats → aucun contexte → le LLM dit « je ne sais pas ».
    rerank_min_score: float = 0.02
    reranker_preload: bool = True  # charge le modèle au démarrage (1re requête rapide)

    # Couches optionnelles (off par défaut — mesurer avant d'activer)
    enable_query_rewriting: bool = False
    query_rewrite_max_variants: int = 2
    enable_hyde: bool = False
    enable_crag: bool = False
    crag_retry_threshold: float = 0.25
    crag_incorrect_threshold: float = 0.12
    crag_retry_top_k_multiplier: int = 2
    enable_self_rag: bool = False
    self_rag_min_relevance: float = 0.15
    self_rag_min_chunks: int = 3
    self_rag_max_chunks: int = 8
    enable_query_decomposition: bool = False
    query_decomposition_max_subqueries: int = 3
    enable_semantic_cache: bool = False
    semantic_cache_similarity_threshold: float = 0.95
    semantic_cache_max_entries: int = 500
    semantic_cache_ttl_seconds: int = 3600

    # --- MLOps -------------------------------------------------------------
    mlops_enabled: bool = True
    mlflow_tracking_uri: str | None = None
    mlops_experiment_name: str = "syro_rag"
    mlops_alerts_enabled: bool = False
    mlops_alerts_email_enabled: bool = False
    mlops_alerts_webhook_enabled: bool = False
    mlops_alerts_smtp_host: str | None = None
    mlops_alerts_smtp_port: int = 587
    mlops_alerts_smtp_user: str | None = None
    mlops_alerts_smtp_password: str | None = None
    mlops_alerts_email_from: str | None = None
    mlops_alerts_email_to: str | None = None
    mlops_alerts_webhook_url: str | None = None

    # --- Celery ------------------------------------------------------------
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    celery_task_always_eager: bool = False  # True = ingestion synchrone (dev)

    # --- Observabilité -----------------------------------------------------
    log_level: str = "INFO"
    log_json_format: bool = True
    metrics_enabled: bool = True
    tracing_enabled: bool = False
    otlp_endpoint: str | None = None
    langfuse_enabled: bool = False
    langfuse_host: str = "http://localhost:3000"
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None

    # --- Sécurité ----------------------------------------------------------
    cors_allow_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    cors_allow_credentials: bool = True
    max_file_size_mb: int = 100
    max_text_size_mb: int = 10
    enable_file_validation: bool = True
    enable_security_headers: bool = True

    def apply_performance_mode(self) -> None:
        config = _PERFORMANCE_MODE_CONFIGS.get(self.performance_mode)
        if config is None:
            return
        for key, value in config.items():
            # Une valeur explicitement fournie (env / .env) garde la priorité.
            if key not in self.model_fields_set:
                setattr(self, key, value)

    def ensure_secret_key(self) -> None:
        """Garantit un secret JWT fort sans configuration manuelle.

        Si SECRET_KEY n'est pas fourni, un secret aléatoire est généré une
        fois puis persisté dans `data_dir/.secret_key` (partagé par tous les
        workers uvicorn, et stable entre redémarrages).
        """
        if self.secret_key and self.secret_key != _DEFAULT_SECRET_KEY:
            return
        path = self.data_dir / ".secret_key"
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            self.secret_key = path.read_text(encoding="utf-8").strip()
            return
        generated = secrets.token_urlsafe(48)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(generated)
        self.secret_key = generated


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
(settings.data_dir / "tmp").mkdir(exist_ok=True)
settings.apply_performance_mode()
