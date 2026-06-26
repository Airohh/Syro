# Diagnostic — Erreur 500 sur /chat/message

> **RÉSOLU (2026-06-10)** — Cause racine identifiée : `get_embedding_vector(query)` dans
> `hybrid_search()` n'était pas protégé. Si l'appel embeddings échoue (Ollama down,
> endpoint `/v1/embeddings` indisponible, timeout), l'exception remontait jusqu'au router → 500.
> Les pistes 1 (Qdrant) et 2 (domain_detector) étaient fausses : `VectorStore` wrappe tout en
> `VectorStoreError` (catchée → `[]`), et `detect_domain` est keyword-based, sans modèle ML.
>
> Fixes appliqués :
> - `hybrid_search.py` : embedding en échec → dégradation BM25-only (plus de 500)
> - `rag.py` : même garde sur le chemin vector-only → `[]`
> - `llm.py` : `timeout` + `max_retries` sur ChatOpenAI/OpenAIEmbeddings (Ollama + OpenAI)
> - `config.py` / `.env.example` : `LLM_TIMEOUT`, `EMBEDDING_TIMEOUT`, `LLM_MAX_RETRIES`
> - `routers/chat.py` : le détail d'exception n'est plus renvoyé au client
> - Test : `test_hybrid_search_embedding_failure_falls_back_to_bm25`

## Symptôme
Login OK. Premier message → 500 "Une erreur s'est produite sur le serveur."

## Ce qu'on sait

### Fonctionne :
- Backend health : `GET /health` → `{"status":"ok"}`
- Ollama : accessible sur port 11434, `llama3.2` + `nomic-embed-text` disponibles
- Embedding API : `POST /api/embeddings` → vecteur 768 dims OK
- Auth / SQLite : login réussi → DB init OK

### Pas encore vérifié :
- **Qdrant** : pas accessible sur port 6333 au moment des tests
  - Docker `docker ps` n'a pas affiché de containers via Git Bash
  - `curl http://127.0.0.1:6333/` → pas de réponse
  - Le script `start-syro.ps1` a lancé `docker compose up -d` mais Qdrant peut encore être en pull

## Pistes les plus probables (dans l'ordre)

### 1. Qdrant down → mais normalement géré
- `_vector_search_sync` catch `VectorStoreError` → retourne `[]`
- MAIS : si l'exception n'est pas `VectorStoreError` (ex: timeout, RPC error), elle remonte

### 2. `detect_domain(query)` plante
- Appelé dans `_get_detected_domains` (chat.py:54)
- Charge un modèle ML de classification → peut planter si dépendances manquantes
- Fichier : `app/services/domain_detector.py`

### 3. `mlops_tracker` ou `adaptive_performance` plante
- Appelés dans `build_answer` (chat.py imports)
- Si Redis pas accessible → peut lever une exception

### 4. `answer_from_context` (LLM) plante
- `provider.chat()` → Ollama LLM call
- Si le modèle llama3.2 n'est pas chargé ou timeout → exception

## Plan de diagnostic

Relancer uvicorn avec logs DEBUG pour voir l'exception exacte :

```powershell
cd C:\Users\Utilisateur\Desktop\Syro\Syro\Syro
uvicorn app.main:app --port 8000 --log-level debug 2>&1 | Tee-Object -FilePath uvicorn.log
```

Puis envoyer un message dans le chat et regarder le log.

Chercher dans uvicorn.log la ligne :
```
ERROR ... Error in send_message: <ExceptionType>: <message>
```

## Commandes utiles pour isoler

```powershell
# Qdrant running ?
docker ps | Select-String "qdrant"

# Lancer Qdrant si pas running
docker compose -f infra\docker-compose.dev-local.yml up -d
curl http://127.0.0.1:6333/

# Tester domain detector
python -c "from app.services.domain_detector import detect_domain; print(detect_domain('snowflake sql'))"

# Tester LLM direct
python -c "from app.services.llm import answer_from_context; print(answer_from_context('test', []))"
```

## Fix potentiel si c'est le domain_detector

Si `detect_domain` plante (ML model manquant), court-circuiter dans chat.py:54 :

```python
# Dans _get_detected_domains, remplacer :
detected_domains = detect_domain(query)
# Par :
try:
    detected_domains = detect_domain(query)
except Exception:
    detected_domains = [settings.domain]
```

## Fix potentiel si c'est Redis/Celery

Dans `.env`, set :
```
CELERY_TASK_ALWAYS_EAGER=true
```
Puis redémarrer uvicorn.
