# Image unique pour l'API (uvicorn) et le worker (celery) : même code, même
# dépendances ; seule la commande change (voir docker-compose.yml).
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt requirements-ml.txt ./
# WITH_RERANKER=false → image plus légère (pas de torch), ordre RRF seul.
ARG WITH_RERANKER=true
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --user -r requirements.txt && \
    if [ "$WITH_RERANKER" = "true" ]; then \
      pip install --no-cache-dir --user \
        --extra-index-url https://download.pytorch.org/whl/cpu -r requirements-ml.txt; \
    fi

FROM python:3.11-slim

WORKDIR /app
RUN useradd -m -u 1000 syro \
    && mkdir -p /app/data /home/syro/.cache/huggingface \
    && chown -R syro:syro /app /home/syro/.cache

COPY --from=builder --chown=syro:syro /root/.local /home/syro/.local
ENV PATH=/home/syro/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    TIKTOKEN_CACHE_DIR=/home/syro/.cache/tiktoken \
    HF_HOME=/home/syro/.cache/huggingface

USER syro
# Tokenizer tiktoken téléchargé au build (pas au 1er upload, et OK hors-ligne).
RUN python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')" \
    || echo "tiktoken: téléchargement impossible, estimation du nb de tokens utilisée"

COPY --chown=syro:syro app/ ./app/
COPY --chown=syro:syro worker/ ./worker/
COPY --chown=syro:syro db/ ./db/
COPY --chown=syro:syro scripts/ ./scripts/
COPY --chown=syro:syro evaluation/ ./evaluation/
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
