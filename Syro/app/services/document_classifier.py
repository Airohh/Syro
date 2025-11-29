# Classification de documents par domaine

from __future__ import annotations
from typing import Any
from .domain_detector import detect_domain_simple, DOMAIN_KEYWORDS

def classify_document(
    text: str,
    filename: str | None = None,
    mime_type: str | None = None
) -> dict[str, Any]:
    """Detecte le domaine d'un document."""
    text_sample = text[:2000] if len(text) > 2000 else text
    domain_scores = detect_domain_simple(text_sample)
    
    filename_scores = {}
    if filename:
        filename_lower = filename.lower()
        for domain, keywords in DOMAIN_KEYWORDS.items():
            score = 0.0
            for keyword in keywords:
                if keyword in filename_lower:
                    score += 0.15
            if score > 0:
                filename_scores[domain] = score
    
    final_scores = {}
    for domain, score in domain_scores:
        final_scores[domain] = score
    
    # Fusion avec le nom de fichier
    for domain, score in filename_scores.items():
        if domain in final_scores:
            final_scores[domain] = final_scores[domain] * 0.8 + score * 0.2
        else:
            final_scores[domain] = score * 0.3
    
    # Normalisation
    if final_scores:
        max_score = max(final_scores.values())
        if max_score > 0:
            for domain in final_scores:
                final_scores[domain] = min(final_scores[domain] / max_score, 1.0)
    
    if not final_scores:
        return {"domain": "general", "confidence": 0.3, "alternatives": []}
    
    best_domain = max(final_scores.items(), key=lambda x: x[1])
    confidence = best_domain[1]
    sorted_domains = sorted(
        final_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    alternatives = [
        {"domain": domain, "confidence": round(score, 3)}
        for domain, score in sorted_domains
        if domain != best_domain[0] and score > 0.1
    ][:3]
    
    return {
        "domain": best_domain[0],
        "confidence": round(confidence, 3),
        "alternatives": alternatives
    }

def should_ask_confirmation(classification_result: dict[str, Any], threshold: float = 0.7) -> bool:
    """Check si on doit demander confirmation."""
    confidence = classification_result["confidence"]
    
    if confidence < threshold:
        return True
    
    # Si alternative trop proche
    if classification_result["alternatives"]:
        best_alt = classification_result["alternatives"][0]
        if confidence - best_alt["confidence"] < 0.2:
            return True
    
    return False

