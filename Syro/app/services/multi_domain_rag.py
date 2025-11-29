from __future__ import annotations

from typing import Any

from ..config import settings
from ..domains import get_domain_config
from .domain_detector import detect_domain, get_domain_confidence
from .hybrid_search import hybrid_search

def search_multi_domain(
    organization_id: int,
    query: str,
    domains: list[str] | None = None,
    top_k_per_domain: int = 5,
    top_k_final: int | None = None,
) -> list[dict[str, Any]]:
    if top_k_final is None:
        top_k_final = settings.rerank_top_k
    
    if domains is None:
        domains = detect_domain(query)
    
    if len(domains) == 1:
        results = hybrid_search(
            organization_id=organization_id,
            query=query,
            top_k=top_k_final,
            filters=None,
            domain=domains[0],
        )
        for result in results:
            result["metadata"] = result.get("metadata", {})
            result["metadata"]["detected_domain"] = domains[0]
        return results
    
    all_results: list[dict[str, Any]] = []
    domain_weights: dict[str, float] = {}
    
    for domain in domains:
        confidence = get_domain_confidence(query, domain)
        domain_weights[domain] = confidence
        
        results = hybrid_search(
            organization_id=organization_id,
            query=query,
            top_k=top_k_per_domain,
            filters=None,
            domain=domain,
        )
        
        for result in results:
            result["metadata"] = result.get("metadata", {})
            result["metadata"]["detected_domain"] = domain
            result["metadata"]["domain_confidence"] = confidence
            result["score"] = float(result.get("score", 0.0)) * confidence
        
        all_results.extend(results)
    
    all_results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return all_results[:top_k_final]

def get_adaptive_prompt(domains: list[str], query: str) -> str:
    if len(domains) == 1:
        return get_domain_config(domains[0]).system_prompt
    
    domain_configs = [get_domain_config(d) for d in domains]
    domain_names = [config.name for config in domain_configs]
    
    prompt = f"""Tu es Syro, un assistant polyvalent expert dans plusieurs domaines :
{', '.join(domain_names)}

La question de l'utilisateur concerne principalement : {', '.join(domains)}

Instructions importantes :
1. Utilise UNIQUEMENT le contexte fourni. Ne génère pas d'informations non présentes dans les sources.
2. Cite tes sources en référençant [Source X] dans ta réponse.
3. Si le contexte ne contient pas assez d'informations, dis-le clairement.
4. Adapte ton style selon le domaine principal de la question.
5. Si la question touche plusieurs domaines, fais des liens entre eux quand c'est pertinent.
6. Sois précis et factuel dans tous les domaines."""
    
    return prompt

