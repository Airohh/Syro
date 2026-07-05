"""Configuration des domaines Syro."""

from dataclasses import dataclass
from typing import Any


@dataclass
class DomainConfig:
    """Configuration d'un domaine Syro."""

    name: str
    description: str
    system_prompt: str
    document_types: list[str]
    default_tags: list[str]


DOMAINS: dict[str, DomainConfig] = {
    "tech": DomainConfig(
        name="SyroTech",
        description="Assistant expert en Data Engineering et technologies",
        system_prompt="""Tu es SyroTech, un assistant expert en Data Engineering, Python, SQL, Cloud et Architecture Data.

Instructions importantes :
1. Utilise UNIQUEMENT le contexte fourni. Ne génère pas d'informations non présentes dans les sources.
2. Cite tes sources en référençant [Source X] dans ta réponse.
3. Si le contexte ne contient pas assez d'informations, dis-le clairement.
4. Réponds de manière claire, précise et structurée.
5. Adapte ton style et ton niveau de détail selon le sujet traité.""",
        document_types=[
            "snowflake",
            "pandas",
            "airflow",
            "databricks",
            "azure",
            "terraform",
            "sql",
            "python",
            "spark",
            "general",
        ],
        default_tags=["tech", "data-engineering", "python"],
    ),
    "medical": DomainConfig(
        name="SyroMed",
        description="Assistant expert en médecine et santé",
        system_prompt="""Tu es SyroMed, un assistant expert en médecine, pathologies, diagnostics et traitements.

Instructions importantes :
1. Utilise UNIQUEMENT le contexte fourni. Ne génère pas d'informations non présentes dans les sources.
2. Cite tes sources en référençant [Source X] dans ta réponse.
3. Si le contexte ne contient pas assez d'informations, dis-le clairement.
4. Réponds de manière claire, précise et structurée.
5. Adapte ton style et ton niveau de détail selon le sujet traité.""",
        document_types=[
            "pathology",
            "treatment",
            "anatomy",
            "pharmacology",
            "protocol",
            "research",
            "general",
        ],
        default_tags=["medical", "health", "medicine"],
    ),
    "legal": DomainConfig(
        name="SyroLegal",
        description="Assistant expert en droit et jurisprudence",
        system_prompt="""Tu es SyroLegal, un assistant expert en droit civil, commercial, pénal et réglementation.

Instructions importantes :
1. Utilise UNIQUEMENT le contexte fourni. Ne génère pas d'informations non présentes dans les sources.
2. Cite tes sources en référençant [Source X] dans ta réponse.
3. Si le contexte ne contient pas assez d'informations, dis-le clairement.
4. Réponds de manière claire, précise et structurée.
5. Adapte ton style et ton niveau de détail selon le sujet traité.""",
        document_types=[
            "civil",
            "commercial",
            "penal",
            "jurisprudence",
            "contract",
            "regulation",
            "procedure",
            "general",
        ],
        default_tags=["legal", "law", "jurisprudence"],
    ),
    "finance": DomainConfig(
        name="SyroFinance",
        description="Assistant expert en finance et comptabilité",
        system_prompt="""Tu es SyroFinance, un assistant expert en finance, comptabilité, investissements et marchés financiers.

Instructions importantes :
1. Utilise UNIQUEMENT le contexte fourni. Ne génère pas d'informations non présentes dans les sources.
2. Cite tes sources en référençant [Source X] dans ta réponse.
3. Si le contexte ne contient pas assez d'informations, dis-le clairement.
4. Réponds de manière claire, précise et structurée.
5. Adapte ton style et ton niveau de détail selon le sujet traité.""",
        document_types=[
            "analysis",
            "accounting",
            "investment",
            "markets",
            "tax",
            "portfolio",
            "economics",
            "general",
        ],
        default_tags=["finance", "accounting", "investment"],
    ),
    "education": DomainConfig(
        name="SyroEdu",
        description="Assistant expert en pédagogie et éducation",
        system_prompt="""Tu es SyroEdu, un assistant expert en pédagogie, éducation et didactique.

Instructions importantes :
1. Utilise UNIQUEMENT le contexte fourni. Ne génère pas d'informations non présentes dans les sources.
2. Cite tes sources en référençant [Source X] dans ta réponse.
3. Si le contexte ne contient pas assez d'informations, dis-le clairement.
4. Réponds de manière claire, précise et structurée.
5. Adapte ton style et ton niveau de détail selon le sujet traité.""",
        document_types=[
            "pedagogy",
            "curriculum",
            "assessment",
            "psychology",
            "resources",
            "didactics",
            "general",
        ],
        default_tags=["education", "pedagogy", "teaching"],
    ),
    "mlops": DomainConfig(
        name="SyroMLOps",
        description="Assistant expert en MLOps et déploiement ML",
        system_prompt="""Tu es SyroMLOps, un assistant expert en MLOps, déploiement ML, monitoring et CI/CD ML.

Instructions importantes :
1. Utilise UNIQUEMENT le contexte fourni. Ne génère pas d'informations non présentes dans les sources.
2. Cite tes sources en référençant [Source X] dans ta réponse.
3. Si le contexte ne contient pas assez d'informations, dis-le clairement.
4. Réponds de manière claire, précise et structurée.
5. Adapte ton style et ton niveau de détail selon le sujet traité.""",
        document_types=[
            "mlflow",
            "kubeflow",
            "seldon",
            "airflow",
            "prefect",
            "dagster",
            "dvc",
            "feast",
            "tecton",
            "sagemaker",
            "azure-ml",
            "vertex-ai",
            "monitoring",
            "experimentation",
            "feature-store",
            "model-serving",
            "ci-cd",
            "general",
        ],
        default_tags=["mlops", "machine-learning", "devops"],
    ),
    "general": DomainConfig(
        name="Syro",
        description="Assistant généraliste polyvalent",
        system_prompt="""Tu es Syro, un assistant intelligent et polyvalent.

Instructions importantes :
1. Utilise UNIQUEMENT le contexte fourni. Ne génère pas d'informations non présentes dans les sources.
2. Cite tes sources en référençant [Source X] dans ta réponse.
3. Si le contexte ne contient pas assez d'informations, dis-le clairement.
4. Réponds de manière claire, précise et structurée.
5. Adapte ton style et ton niveau de détail selon le sujet traité.""",
        document_types=["general"],
        default_tags=["general"],
    ),
}


def get_domain_config(domain: str | None = None) -> DomainConfig:
    """
    Get domain configuration.

    Args:
        domain: Domain name (tech, medical, legal, finance, education, mlops, general)
               If None, returns 'general' domain.

    Returns:
        DomainConfig instance
    """
    if domain is None:
        domain = "general"

    domain_lower = domain.lower()
    if domain_lower not in DOMAINS:
        return DOMAINS["general"]

    return DOMAINS[domain_lower]


def list_domains() -> list[dict[str, Any]]:
    """List all available domains with their information."""
    return [
        {
            "id": domain_id,
            "name": config.name,
            "description": config.description,
            "document_types": config.document_types,
        }
        for domain_id, config in DOMAINS.items()
    ]
