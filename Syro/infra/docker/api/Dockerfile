# Multi-stage build pour backend Syro API
FROM python:3.11-slim as builder

WORKDIR /app

# Installer dépendances système pour build
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copier requirements et installer dépendances Python
# Utiliser torch CPU-only (beaucoup plus léger que torch GPU)
COPY requirements-base.txt requirements-ml-light.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --user -r requirements-base.txt && \
    pip install --no-cache-dir --user --extra-index-url https://download.pytorch.org/whl/cpu -r requirements-ml-light.txt

# Stage runtime
FROM python:3.11-slim

WORKDIR /app

# Installer curl et libmagic pour healthcheck et validation fichiers
RUN apt-get update && apt-get install -y \
    curl \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Créer utilisateur non-root AVANT de copier les dépendances
RUN useradd -m -u 1000 syro

# Copier dépendances Python depuis builder vers le home de syro
COPY --from=builder /root/.local /home/syro/.local

# Copier code application
COPY app/ ./app/
COPY db/ ./db/

# Créer répertoires nécessaires et définir permissions
RUN mkdir -p /app/data /app/storage/mlruns && \
    chown -R syro:syro /app /home/syro/.local

USER syro

# Ajouter .local au PATH pour Python
ENV PATH=/home/syro/.local/bin:$PATH

# Exposer port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

