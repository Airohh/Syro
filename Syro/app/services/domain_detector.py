"""Détection de domaine par mots-clés (FR + EN), sans modèle ML.

Utilisée pour (1) classer un document à l'ingestion quand aucun domaine
n'est fourni et (2) choisir la persona du LLM quand l'utilisateur n'a pas
sélectionné de domaine. Elle ne filtre jamais le retrieval à elle seule.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from typing import Any

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "tech": [
        "python",
        "sql",
        "api",
        "docker",
        "kubernetes",
        "cloud",
        "database",
        "base de donnees",
        "code",
        "programming",
        "programmation",
        "backend",
        "frontend",
        "fastapi",
        "flask",
        "django",
        "http",
        "rest",
        "jwt",
        "authentification",
        "authentication",
        "qdrant",
        "vector",
        "vectoriel",
        "embedding",
        "rag",
        "bm25",
        "reranking",
        "chunking",
        "retrieval",
        "terraform",
        "spark",
        "airflow",
        "snowflake",
        "etl",
        "git",
        "linux",
        "microservice",
        "compose",
        "rate limiting",
        "latence",
        "latency",
    ],
    "mlops": [
        "mlops",
        "mlflow",
        "model serving",
        "serving",
        "drift",
        "monitoring",
        "observabilite",
        "observability",
        "prometheus",
        "grafana",
        "ragas",
        "evaluation",
        "metrique",
        "metric",
        "kpi",
        "celery",
        "pipeline ml",
        "deploiement",
        "deployment",
        "feature store",
        "experiment tracking",
        "registry",
        "a/b test",
        "canary",
        "langfuse",
        "tracing",
    ],
    "medical": [
        "symptom",
        "symptome",
        "diagnosis",
        "diagnostic",
        "treatment",
        "traitement",
        "patient",
        "disease",
        "maladie",
        "medicine",
        "medecine",
        "pharmacy",
        "pharmacie",
        "clinical",
        "clinique",
        "therapy",
        "therapie",
        "medication",
        "medicament",
        "hospital",
        "hopital",
        "doctor",
        "medecin",
        "syndrome",
        "pathology",
        "pathologie",
    ],
    "legal": [
        "law",
        "loi",
        "legal",
        "juridique",
        "contract",
        "contrat",
        "jurisprudence",
        "court",
        "tribunal",
        "judge",
        "juge",
        "lawyer",
        "avocat",
        "litigation",
        "litige",
        "regulation",
        "reglementation",
        "compliance",
        "conformite",
        "rgpd",
        "gdpr",
        "statute",
        "clause",
        "code civil",
        "code penal",
    ],
    "finance": [
        "finance",
        "financier",
        "accounting",
        "comptabilite",
        "investment",
        "investissement",
        "stock",
        "action",
        "bourse",
        "market",
        "marche",
        "tax",
        "impot",
        "fiscal",
        "portfolio",
        "portefeuille",
        "revenue",
        "chiffre d'affaires",
        "profit",
        "banking",
        "banque",
        "credit",
        "loan",
        "pret",
        "interest",
        "interet",
        "equity",
        "debt",
        "dette",
        "bilan",
    ],
    "education": [
        "education",
        "teaching",
        "enseignement",
        "learning",
        "apprentissage",
        "pedagogy",
        "pedagogie",
        "curriculum",
        "student",
        "etudiant",
        "eleve",
        "teacher",
        "professeur",
        "enseignant",
        "school",
        "ecole",
        "course",
        "cours",
        "lesson",
        "lecon",
        "exam",
        "examen",
        "university",
        "universite",
        "formation",
    ],
}


def _fold(text: str) -> str:
    """Minuscules + suppression des accents (« Médecine » → « medecine »)."""
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in normalized if not unicodedata.combining(c))


@lru_cache(maxsize=1)
def _patterns() -> dict[str, list[re.Pattern[str]]]:
    # Frontières de mots : « art » ne matche plus « start », « tf » plus « pdf ».
    return {
        domain: [re.compile(rf"\b{re.escape(_fold(k))}\b") for k in keywords]
        for domain, keywords in DOMAIN_KEYWORDS.items()
    }


def score_domains(text: str) -> dict[str, int]:
    """Nombre de mots-clés distincts trouvés par domaine."""
    folded = _fold(text)
    return {
        domain: sum(1 for p in patterns if p.search(folded))
        for domain, patterns in _patterns().items()
    }


def classify_text(text: str, min_hits: int = 2) -> dict[str, Any]:
    """Classe un texte : {domain, confidence, alternatives}.

    `general` si aucun domaine n'atteint `min_hits` mots-clés distincts.
    """
    scores = score_domains(text[:5000])
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    total = sum(scores.values())
    best, best_hits = ranked[0]
    if best_hits < min_hits:
        return {"domain": "general", "confidence": 0.5, "alternatives": []}
    alternatives = [
        {"domain": d, "confidence": round(h / total, 3)}
        for d, h in ranked[1:4]
        if h > 0
    ]
    return {
        "domain": best,
        "confidence": round(best_hits / total, 3),
        "alternatives": alternatives,
    }


def detect_domain(query: str) -> str:
    """Domaine le plus probable d'une question (1 mot-clé suffit)."""
    return classify_text(query, min_hits=1)["domain"]
