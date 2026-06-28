from __future__ import annotations

import hashlib
import io
import logging
import sys
from collections import OrderedDict
from typing import Sequence

import numpy as np

logger = logging.getLogger(__name__)

# Fix encoding for Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

try:
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI  # type: ignore
    from langchain_core.messages import HumanMessage, SystemMessage  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    OpenAIEmbeddings = None  # type: ignore
    ChatOpenAI = None  # type: ignore
    HumanMessage = None  # type: ignore
    SystemMessage = None  # type: ignore

from ..config import settings
from ..domains import get_domain_config
from .circuit_breaker import CircuitBreaker

_embedding_cache: OrderedDict[str, np.ndarray] = OrderedDict()
_cache_max_size = settings.embedding_cache_size if settings.embedding_cache_enabled else 0


def _history_block(conversation_history: Sequence[str] | None) -> str:
    if not conversation_history:
        return ""
    return "Historique récent:\n" + "\n".join(conversation_history) + "\n\n"


class LLMProvider:
    def __init__(self) -> None:
        self._provider = settings.llm_provider.lower()
        self._embedder = None
        self._chat_model = None
        self._has_llm = False
        # Breakers séparés : un backend peut servir les embeddings mais pas le chat
        self._chat_breaker = CircuitBreaker(
            failure_threshold=settings.circuit_breaker_threshold,
            reset_timeout=settings.circuit_breaker_reset_seconds,
        )
        self._embed_breaker = CircuitBreaker(
            failure_threshold=settings.circuit_breaker_threshold,
            reset_timeout=settings.circuit_breaker_reset_seconds,
        )
        
        # Use Ollama by default (free and local)
        if self._provider == "ollama" or (self._provider != "openai" and not settings.openai_api_key):
            self._setup_ollama()
        # Fallback to OpenAI if explicitly requested and API key is provided
        elif self._provider == "openai" and settings.openai_api_key:
            self._setup_openai()
        # Default to Ollama if no preference
        else:
            self._setup_ollama()
    
    def _setup_ollama(self) -> None:
        """Configure Ollama (free, local LLM) with optional GPU support."""
        if not OpenAIEmbeddings or not ChatOpenAI:
            return
        
        # Ollama uses OpenAI-compatible API, so we can use the same clients
        # Just point to Ollama's base URL
        base_url = settings.ollama_base_url or "http://localhost:11434/v1"
        
        try:
            # GPU info purement cosmétique (Ollama gère son propre placement
            # device) : un simple check torch.cuda pour le log, sans sondes
            # subprocess nvidia-smi/ollama coûteuses.
            gpu_info = ""
            if settings.ollama_use_gpu:
                try:
                    import torch
                    if torch.cuda.is_available():
                        gpu_info = f" (GPU: {torch.cuda.get_device_name(0)})"
                except Exception:
                    pass

            self._embedder = OpenAIEmbeddings(
                model=settings.embeddings_model,
                api_key="ollama",  # Ollama doesn't need a real key, but langchain requires something
                base_url=base_url,
                timeout=settings.embedding_timeout,
                max_retries=settings.llm_max_retries,
                # Ollama's OpenAI-compat /v1/embeddings rejects the tiktoken
                # token-id arrays langchain sends by default ("invalid input
                # type" 400). Force raw-string input so batch embed_documents()
                # works against Ollama.
                check_embedding_ctx_length=False,
            )
            self._chat_model = ChatOpenAI(
                model=settings.chat_model,
                api_key="ollama",
                base_url=base_url,
                temperature=settings.chat_temperature,
                timeout=settings.llm_timeout,
                max_retries=settings.llm_max_retries,
            )
            self._has_llm = True
            logger.info("Ollama configured: %s at %s%s", settings.chat_model, base_url, gpu_info)
        except Exception as e:
            logger.warning("Ollama setup failed — embeddings and chat unavailable: %s", e)
    
    def _setup_openai(self) -> None:
        """Configure OpenAI (paid, cloud-based)."""
        if not OpenAIEmbeddings or not ChatOpenAI:
            return
        
        if not settings.openai_api_key:
            return
        
        try:
            self._embedder = OpenAIEmbeddings(
                model=settings.embeddings_model,
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                timeout=settings.embedding_timeout,
                max_retries=settings.llm_max_retries,
            )
            self._chat_model = ChatOpenAI(
                model=settings.chat_model,
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                temperature=settings.chat_temperature,
                timeout=settings.llm_timeout,
                max_retries=settings.llm_max_retries,
            )
            self._has_llm = True
            logger.info("OpenAI configured: %s", settings.chat_model)
        except Exception as e:
            logger.warning("OpenAI setup failed — embeddings and chat unavailable: %s", e)

    @staticmethod
    def _fake_embed(text: str) -> np.ndarray:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        rng = np.random.default_rng(int.from_bytes(digest[:8], "little"))
        return rng.normal(size=settings.embedding_dimensions).astype(np.float32)

    def embed(self, text: str) -> np.ndarray:
        cache_key = None
        if settings.embedding_cache_enabled:
            # Clé inclut le modèle : changer EMBEDDINGS_MODEL ne doit pas
            # servir des vecteurs de l'ancien modèle.
            cache_key = hashlib.sha256(
                f"{settings.embeddings_model}::{text}".encode("utf-8")
            ).hexdigest()
            if cache_key in _embedding_cache:
                _embedding_cache.move_to_end(cache_key)
                return _embedding_cache[cache_key]

        if not self._embedder:
            raise RuntimeError(
                "LLM provider not configured — cannot generate embeddings. "
                "Check that Ollama is running or OPENAI_API_KEY is set."
            )

        if not self._embed_breaker.allow():
            # Circuit ouvert : échec immédiat au lieu de payer le timeout.
            # La recherche hybride dégrade alors en BM25-only.
            raise RuntimeError("Embedding backend circuit open — failing fast")

        try:
            vector = self._embedder.embed_query(text)
            result = np.array(vector, dtype=np.float32)
        except Exception:
            self._embed_breaker.record_failure()
            raise
        self._embed_breaker.record_success()
        
        if settings.embedding_cache_enabled and _cache_max_size > 0 and cache_key:
            if len(_embedding_cache) >= _cache_max_size:
                _embedding_cache.popitem(last=False)
            _embedding_cache[cache_key] = result
            _embedding_cache.move_to_end(cache_key)
        
        return result

    def embed_many(self, texts: Sequence[str]) -> list[np.ndarray]:
        """Embedding par lot. Un seul appel réseau pour tous les cache-miss
        (langchain `embed_documents`), au lieu d'un round-trip par texte.
        Respecte le cache LRU et le circuit breaker comme `embed`."""
        if not texts:
            return []

        results: list[np.ndarray | None] = [None] * len(texts)
        keys: list[str | None] = [None] * len(texts)
        miss_idx: list[int] = []
        miss_texts: list[str] = []

        for i, text in enumerate(texts):
            if settings.embedding_cache_enabled:
                key = hashlib.sha256(
                    f"{settings.embeddings_model}::{text}".encode("utf-8")
                ).hexdigest()
                keys[i] = key
                cached = _embedding_cache.get(key)
                if cached is not None:
                    _embedding_cache.move_to_end(key)
                    results[i] = cached
                    continue
            miss_idx.append(i)
            miss_texts.append(text)

        if miss_texts:
            if not self._embedder:
                raise RuntimeError(
                    "LLM provider not configured — cannot generate embeddings. "
                    "Check that Ollama is running or OPENAI_API_KEY is set."
                )
            if not self._embed_breaker.allow():
                raise RuntimeError("Embedding backend circuit open — failing fast")
            try:
                vectors = self._embedder.embed_documents(list(miss_texts))
            except Exception:
                self._embed_breaker.record_failure()
                raise
            self._embed_breaker.record_success()

            for j, i in enumerate(miss_idx):
                vec = np.array(vectors[j], dtype=np.float32)
                results[i] = vec
                key = keys[i]
                if settings.embedding_cache_enabled and _cache_max_size > 0 and key:
                    if len(_embedding_cache) >= _cache_max_size:
                        _embedding_cache.popitem(last=False)
                    _embedding_cache[key] = vec
                    _embedding_cache.move_to_end(key)

        return [v for v in results]  # type: ignore[misc]

    def chat(
        self,
        question: str,
        context_chunks: Sequence[str],
        domain: str | None = None,
        conversation_history: Sequence[str] | None = None,
    ) -> tuple[str, int]:
        context_block = "\n\n".join(
            f"[Source {i+1}]\n{chunk}" for i, chunk in enumerate(context_chunks)
        )
        
        domain_to_use = domain or settings.domain
        domain_config = get_domain_config(domain_to_use)
        system_prompt = domain_config.system_prompt

        history_block = _history_block(conversation_history)
        
        if self._chat_model and HumanMessage and SystemMessage and self._chat_breaker.allow():
            try:
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(
                        content=(
                            f"{history_block}Question: {question}\n\n"
                            f"Contexte:\n{context_block if context_block else 'Aucun contexte disponible.'}"
                        ),
                    ),
                ]
                response = self._chat_model.invoke(messages)
                text = response.content if isinstance(response.content, str) else str(response.content)
                usage = 0
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    usage = int(response.usage_metadata.get("total_tokens", 0))
                if usage == 0:
                    usage = len(question.split()) + sum(len(chunk.split()) for chunk in context_chunks)
                self._chat_breaker.record_success()
                return text, usage
            except Exception as e:
                self._chat_breaker.record_failure()
                logger.warning("LLM invoke failed: %s", e, exc_info=True)

        provider_status = "Ollama unavailable" if self._provider == "ollama" else "LLM not configured"
        fallback = f"LLM unavailable ({provider_status}).\n\nQuestion: {question}\n\nContext:\n{context_block or 'No documents indexed.'}"
        usage = len(question.split()) + sum(len(chunk.split()) for chunk in context_chunks)
        return fallback, usage
    
    def chat_stream(
        self,
        question: str,
        context_chunks: Sequence[str],
        domain: str | None = None,
        conversation_history: Sequence[str] | None = None,
    ):
        context_block = "\n\n".join(
            f"[Source {i+1}]\n{chunk}" for i, chunk in enumerate(context_chunks)
        )
        
        domain_to_use = domain or settings.domain
        domain_config = get_domain_config(domain_to_use)
        system_prompt = domain_config.system_prompt

        history_block = _history_block(conversation_history)
        
        if self._chat_model and HumanMessage and SystemMessage and self._chat_breaker.allow():
            try:
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(
                        content=(
                            f"{history_block}Question: {question}\n\n"
                            f"Contexte:\n{context_block if context_block else 'Aucun contexte disponible.'}"
                        ),
                    ),
                ]
                # Stream response
                for chunk in self._chat_model.stream(messages):
                    if hasattr(chunk, "content") and chunk.content:
                        yield chunk.content
                self._chat_breaker.record_success()
            except Exception as e:
                self._chat_breaker.record_failure()
                provider_name = "Ollama" if self._provider == "ollama" else "OpenAI"
                logger.warning("%s stream failed: %s", provider_name, e)
                yield f"Error: {provider_name} unavailable."
        else:
            yield "LLM not configured."

provider = LLMProvider()

def get_embedding_bytes(text: str) -> bytes:
    vec = provider.embed(text)
    buffer = io.BytesIO()
    buffer.write(vec.astype(np.float32).tobytes())
    return buffer.getvalue()

def get_embedding_vector(text: str) -> np.ndarray:
    return provider.embed(text)

def get_embedding_vectors(texts: Sequence[str]) -> list[np.ndarray]:
    """Embedding par lot (1 appel réseau). Voir `LLMProvider.embed_many`."""
    return provider.embed_many(texts)

def answer_from_context(
    question: str,
    context_chunks: Sequence[str],
    domain: str | None = None,
    conversation_history: Sequence[str] | None = None,
) -> tuple[str, int]:
    return provider.chat(question, context_chunks, domain=domain, conversation_history=conversation_history)

def answer_from_context_stream(
    question: str,
    context_chunks: Sequence[str],
    domain: str | None = None,
    conversation_history: Sequence[str] | None = None,
):
    """Stream answer from context (generator)."""
    return provider.chat_stream(
        question, context_chunks, domain=domain, conversation_history=conversation_history
    )
