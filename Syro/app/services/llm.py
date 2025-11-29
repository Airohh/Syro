from __future__ import annotations

import hashlib
import io
import sys
from collections import OrderedDict
from typing import Sequence

import numpy as np

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

_embedding_cache: OrderedDict[str, np.ndarray] = OrderedDict()
_cache_max_size = settings.embedding_cache_size if settings.embedding_cache_enabled else 0

class LLMProvider:
    def __init__(self) -> None:
        self._provider = settings.llm_provider.lower()
        self._embedder = None
        self._chat_model = None
        self._has_llm = False
        
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
            # Check GPU availability (direct CUDA check + Ollama status)
            gpu_info = ""
            gpu_available = False
            if settings.ollama_use_gpu:
                # Method 1: Direct CUDA check (most reliable)
                try:
                    import torch
                    if torch.cuda.is_available():
                        gpu_available = True
                        gpu_info = f" (GPU: {torch.cuda.get_device_name(0)})"
                except ImportError:
                    pass
                except Exception:
                    pass
                
                # Method 2: Check nvidia-smi (fallback)
                if not gpu_available:
                    try:
                        import subprocess
                        result = subprocess.run(
                            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                            capture_output=True,
                            text=True,
                            timeout=2,
                        )
                        if result.returncode == 0 and result.stdout.strip():
                            gpu_available = True
                            gpu_name = result.stdout.strip().split("\n")[0]
                            gpu_info = f" (GPU: {gpu_name})"
                    except Exception:
                        pass
                
                # Method 3: Check Ollama status (last resort)
                if not gpu_available:
                    try:
                        import subprocess
                        result = subprocess.run(
                            ["ollama", "ps"],
                            capture_output=True,
                            text=True,
                            timeout=2,
                        )
                        if "gpu" in result.stdout.lower() or "cuda" in result.stdout.lower():
                            gpu_available = True
                            gpu_info = " (GPU enabled via Ollama)"
                    except Exception:
                        pass
            
            self._embedder = OpenAIEmbeddings(
                model=settings.embeddings_model,
                api_key="ollama",  # Ollama doesn't need a real key, but langchain requires something
                base_url=base_url,
            )
            self._chat_model = ChatOpenAI(
                model=settings.chat_model,
                api_key="ollama",
                base_url=base_url,
                temperature=settings.chat_temperature,
            )
            self._has_llm = True
            print(f"Ollama configured: {settings.chat_model} at {base_url}{gpu_info}")
        except Exception:
            pass
    
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
            )
            self._chat_model = ChatOpenAI(
                model=settings.chat_model,
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                temperature=settings.chat_temperature,
            )
            self._has_llm = True
            print(f"OpenAI configured: {settings.chat_model}")
        except Exception:
            pass

    @staticmethod
    def _fake_embed(text: str) -> np.ndarray:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        rng = np.random.default_rng(int.from_bytes(digest[:8], "little"))
        return rng.normal(size=settings.embedding_dimensions).astype(np.float32)

    def embed(self, text: str) -> np.ndarray:
        cache_key = None
        if settings.embedding_cache_enabled:
            cache_key = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if cache_key in _embedding_cache:
                _embedding_cache.move_to_end(cache_key)
                return _embedding_cache[cache_key]
        
        if self._embedder:
            try:
                vector = self._embedder.embed_query(text)
                result = np.array(vector, dtype=np.float32)
            except Exception:
                result = self._fake_embed(text)
        else:
            result = self._fake_embed(text)
        
        if settings.embedding_cache_enabled and _cache_max_size > 0 and cache_key:
            if len(_embedding_cache) >= _cache_max_size:
                _embedding_cache.popitem(last=False)
            _embedding_cache[cache_key] = result
            _embedding_cache.move_to_end(cache_key)
        
        return result

    def chat(self, question: str, context_chunks: Sequence[str], domain: str | None = None) -> tuple[str, int]:
        context_block = "\n\n".join(
            f"[Source {i+1}]\n{chunk}" for i, chunk in enumerate(context_chunks)
        )
        
        domain_to_use = domain or settings.domain
        domain_config = get_domain_config(domain_to_use)
        system_prompt = domain_config.system_prompt
        
        if self._chat_model and HumanMessage and SystemMessage:
            try:
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(
                        content=f"Question: {question}\n\nContexte:\n{context_block if context_block else 'Aucun contexte disponible.'}",
                    ),
                ]
                response = self._chat_model.invoke(messages)
                text = response.content if isinstance(response.content, str) else str(response.content)
                usage = 0
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    usage = int(response.usage_metadata.get("total_tokens", 0))
                if usage == 0:
                    usage = len(question.split()) + sum(len(chunk.split()) for chunk in context_chunks)
                return text, usage
            except Exception:
                pass

        provider_status = "Ollama unavailable" if self._provider == "ollama" else "LLM not configured"
        fallback = f"LLM unavailable ({provider_status}).\n\nQuestion: {question}\n\nContext:\n{context_block or 'No documents indexed.'}"
        usage = len(question.split()) + sum(len(chunk.split()) for chunk in context_chunks)
        return fallback, usage
    
    def chat_stream(self, question: str, context_chunks: Sequence[str], domain: str | None = None):
        context_block = "\n\n".join(
            f"[Source {i+1}]\n{chunk}" for i, chunk in enumerate(context_chunks)
        )
        
        domain_to_use = domain or settings.domain
        domain_config = get_domain_config(domain_to_use)
        system_prompt = domain_config.system_prompt
        
        if self._chat_model and HumanMessage and SystemMessage:
            try:
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(
                        content=f"Question: {question}\n\nContexte:\n{context_block if context_block else 'Aucun contexte disponible.'}",
                    ),
                ]
                # Stream response
                for chunk in self._chat_model.stream(messages):
                    if hasattr(chunk, "content") and chunk.content:
                        yield chunk.content
            except Exception as e:
                provider_name = "Ollama" if self._provider == "ollama" else "OpenAI"
                print(f"Warning: {provider_name} chat stream failed ({e})")
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

def answer_from_context(question: str, context_chunks: Sequence[str], domain: str | None = None) -> tuple[str, int]:
    return provider.chat(question, context_chunks, domain=domain)

def answer_from_context_stream(question: str, context_chunks: Sequence[str], domain: str | None = None):
    """Stream answer from context (generator)."""
    return provider.chat_stream(question, context_chunks, domain=domain)
