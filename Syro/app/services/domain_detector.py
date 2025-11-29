from __future__ import annotations

from typing import Any

from ..domains import DOMAINS, get_domain_config

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "tech": [
        "snowflake", "sql", "python", "pandas", "airflow", "databricks",
        "azure", "terraform", "spark", "data engineering", "code", "programming",
        "api", "docker", "kubernetes", "cloud", "database", "etl", "pipeline",
    ],
    "medical": [
        "symptom", "diagnosis", "treatment", "patient", "disease", "medicine",
        "pharmacy", "clinical", "pathology", "anatomy", "physiology", "medical",
        "health", "doctor", "hospital", "therapy", "medication", "syndrome",
    ],
    "legal": [
        "law", "legal", "contract", "jurisprudence", "court", "judge", "lawyer",
        "litigation", "regulation", "compliance", "rights", "legal advice",
        "civil", "penal", "commercial", "employment", "tort", "statute",
    ],
    "finance": [
        "finance", "accounting", "investment", "stock", "market", "tax",
        "portfolio", "revenue", "profit", "loss", "balance", "financial",
        "banking", "credit", "loan", "interest", "equity", "debt",
    ],
    "education": [
        "education", "teaching", "learning", "pedagogy", "curriculum",
        "student", "teacher", "school", "course", "lesson", "assessment",
        "exam", "grade", "study", "academic", "university", "training",
    ],
}

def detect_domain_simple(query: str) -> list[tuple[str, float]]:
    query_lower = query.lower()
    scores: dict[str, float] = {}
    
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = 0.0
        matches = 0
        
        for keyword in keywords:
            if keyword in query_lower:
                matches += 1
                score += len(keyword) * 0.1
        
        if matches > 0:
            scores[domain] = min(score / len(keywords) * 10, 1.0)
        else:
            scores[domain] = 0.0
    
    sorted_domains = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    threshold = 0.1
    filtered = [(domain, score) for domain, score in sorted_domains if score >= threshold]
    
    if not filtered:
        return [("general", 0.5)]
    
    return filtered

def detect_domain(query: str, top_k: int = 2) -> list[str]:
    detected = detect_domain_simple(query)
    domains = [domain for domain, _ in detected[:top_k]]
    
    if "general" not in domains:
        domains.append("general")
    
    return domains

def get_domain_confidence(query: str, domain: str) -> float:
    detected = detect_domain_simple(query)
    
    for detected_domain, score in detected:
        if detected_domain == domain:
            return score
    
    return 0.0

def should_use_multi_domain(query: str, threshold: float = 0.3) -> bool:
    detected = detect_domain_simple(query)
    high_confidence = [score for _, score in detected if score >= threshold]
    
    return len(high_confidence) > 1

def detect_domain_from_document(text: str, top_k: int = 1) -> str:
    sample_text = text[:2000] if len(text) > 2000 else text
    detected = detect_domain_simple(sample_text)
    
    if not detected:
        return "general"
    
    return detected[0][0]
