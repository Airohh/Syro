from pathlib import Path
from typing import Any
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    app_name: str = "Syro"
    domain: str = "tech"
    debug: bool = True
    secret_key: str = "dev-secret-change-me"
    access_token_exp_minutes: int = 60 * 24
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434/v1"
    embeddings_model: str = "nomic-embed-text"
    embedding_dimensions: int = 768
    chat_model: str = "llama3.2"
    chat_temperature: float = 0.2
    llm_timeout: float = 60.0  # Timeout (s) des appels chat LLM
    embedding_timeout: float = 30.0  # Timeout (s) des appels embeddings
    llm_max_retries: int = 2  # Retries automatiques sur erreurs transitoires
    circuit_breaker_threshold: int = 5  # Échecs consécutifs avant ouverture
    circuit_breaker_reset_seconds: float = 30.0  # Repos avant essai half-open
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    data_dir: Path = PROJECT_ROOT / "storage"
    db_path: Path = PROJECT_ROOT / "db" / "syro.db"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection_name: str = "syro_chunks"
    enable_domain_routing: bool = True
    performance_mode: str = "quality"
    adaptive_fast_threshold_ms: float = 3000.0
    adaptive_quality_threshold_ms: float = 1500.0
    adaptive_window_size: int = 5
    hybrid_search_alpha: float = 0.7
    retrieval_top_k: int = 10
    rerank_top_k: int = 5
    enable_reranking: bool = True
    rerank_weight: float = 0.7
    ollama_use_gpu: bool = True
    embedding_cache_enabled: bool = True
    embedding_cache_size: int = 1000
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
    
    # Celery configuration (pour worker async)
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    celery_task_always_eager: bool = False  # True pour désactiver Celery en dev (tâches synchrones)
    
    # Observabilité
    log_level: str = "INFO"
    log_json_format: bool = True  # True pour logs JSON structurés
    metrics_enabled: bool = True
    tracing_enabled: bool = False  # Désactivé par défaut (nécessite OTLP endpoint)
    otlp_endpoint: str | None = None  # Ex: http://localhost:4317
    
    # Sécurité
    cors_allow_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    cors_allow_credentials: bool = True
    max_file_size_mb: int = 100  # Taille maximale des fichiers uploadés (MB)
    max_text_size_mb: int = 10  # Taille maximale du texte uploadé (MB)
    enable_file_validation: bool = True  # Valider strictement les types MIME
    enable_security_headers: bool = True  # Ajouter les headers de sécurité HTTP

    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def get_fast_mode_config(self) -> dict[str, Any]:
        return {
            "retrieval_top_k": 5,
            "rerank_top_k": 3,
            "enable_reranking": False,
            "hybrid_search_alpha": 0.8,
        }
    
    def get_quality_mode_config(self) -> dict[str, Any]:
        return {
            "retrieval_top_k": 15,
            "rerank_top_k": 5,
            "enable_reranking": True,
            "hybrid_search_alpha": 0.7,
        }
    
    def apply_performance_mode(self) -> None:
        if self.performance_mode == "fast":
            config = self.get_fast_mode_config()
            self.retrieval_top_k = config["retrieval_top_k"]
            self.rerank_top_k = config["rerank_top_k"]
            self.enable_reranking = config["enable_reranking"]
            self.hybrid_search_alpha = config["hybrid_search_alpha"]
        elif self.performance_mode == "quality":
            config = self.get_quality_mode_config()
            self.retrieval_top_k = config["retrieval_top_k"]
            self.rerank_top_k = config["rerank_top_k"]
            self.enable_reranking = config["enable_reranking"]
            self.hybrid_search_alpha = config["hybrid_search_alpha"]
        elif self.performance_mode == "adaptive":
            config = self.get_quality_mode_config()
            self.retrieval_top_k = config["retrieval_top_k"]
            self.rerank_top_k = config["rerank_top_k"]
            self.enable_reranking = config["enable_reranking"]
            self.hybrid_search_alpha = config["hybrid_search_alpha"]

settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
(settings.data_dir / "tmp").mkdir(exist_ok=True)
settings.apply_performance_mode()
