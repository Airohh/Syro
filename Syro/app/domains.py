"""Domaines Syro : une persona par domaine.

Un domaine sert à deux choses : (1) la persona du LLM et (2) un filtre
optionnel de retrieval quand l'utilisateur choisit explicitement un domaine.
Les règles RAG (citer, ne pas inventer…) sont communes : voir llm.RAG_RULES.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DomainConfig:
    name: str
    description: str
    persona: str


DOMAINS: dict[str, DomainConfig] = {
    "general": DomainConfig(
        name="Syro",
        description="Assistant généraliste : cherche dans tous vos documents",
        persona="Tu es Syro, un assistant qui répond à partir des documents de l'utilisateur.",
    ),
    "tech": DomainConfig(
        name="SyroTech",
        description="Assistant expert en Data Engineering et technologies",
        persona="Tu es SyroTech, un assistant expert en Data Engineering, Python, SQL, Cloud et architecture logicielle.",
    ),
    "mlops": DomainConfig(
        name="SyroMLOps",
        description="Assistant expert en MLOps et déploiement ML",
        persona="Tu es SyroMLOps, un assistant expert en MLOps, déploiement de modèles, monitoring et CI/CD ML.",
    ),
    "medical": DomainConfig(
        name="SyroMed",
        description="Assistant expert en médecine et santé",
        persona="Tu es SyroMed, un assistant expert en médecine. Tu rappelles que tes réponses ne remplacent pas un avis médical.",
    ),
    "legal": DomainConfig(
        name="SyroLegal",
        description="Assistant expert en droit et jurisprudence",
        persona="Tu es SyroLegal, un assistant expert en droit civil, commercial, pénal et réglementation.",
    ),
    "finance": DomainConfig(
        name="SyroFinance",
        description="Assistant expert en finance et comptabilité",
        persona="Tu es SyroFinance, un assistant expert en finance, comptabilité et marchés financiers.",
    ),
    "education": DomainConfig(
        name="SyroEdu",
        description="Assistant expert en pédagogie et éducation",
        persona="Tu es SyroEdu, un assistant expert en pédagogie et éducation.",
    ),
}


def get_domain_config(domain: str | None = None) -> DomainConfig:
    """Config du domaine ; `general` si inconnu ou absent."""
    return DOMAINS.get((domain or "general").lower(), DOMAINS["general"])


def normalize_domain(domain: str | None) -> str | None:
    """Domaine valide en minuscules, ou None si absent/inconnu."""
    if not domain:
        return None
    domain = domain.strip().lower()
    return domain if domain in DOMAINS else None


def list_domains() -> list[dict[str, Any]]:
    return [
        {"id": domain_id, "name": cfg.name, "description": cfg.description}
        for domain_id, cfg in DOMAINS.items()
    ]
