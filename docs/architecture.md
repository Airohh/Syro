#  Architecture pour un Syro Général
## 🎯 Objectif

Créer un **Syro général** qui peut :
1. **Détecter automatiquement** le domaine d'une question
2. **Rechercher dans plusieurs domaines** simultanément si nécessaire
3. **Fusionner intelligemment** les résultats de différents domaines
4. **S'adapter dynamiquement** au contexte de la conversation
##  Architecture Proposée
### Option 1 : Architecture Multi-Domaines par Organisation (Recommandée)

```
┌─────────────────────────────────────────────────────────┐
│                    Organisation                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Configuration : domaines = ["tech", "legal"]     │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Documents   │  │  Documents   │  │  Documents   │ │
│  │   Tech       │  │   Legal      │  │   General    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│         │                  │                  │         │
│         └──────────────────┴──────────────────┘         │
│                          │                               │
│                    ┌─────▼─────┐                        │
│                    │   RAG      │                        │
│                    │  Router    │                        │
│                    └─────┬─────┘                        │
│                          │                               │
│         ┌────────────────┼────────────────┐             │
│         │                │                │             │
│    ┌────▼────┐    ┌─────▼─────┐    ┌─────▼────┐        │
│    │  Tech   │    │  Legal    │    │ General  │        │
│    │  Search │    │  Search   │    │  Search  │        │
│    └─────────┘    └───────────┘    └──────────┘        │
│         │                │                │             │
│         └────────────────┼────────────────┘             │
│                          │                               │
│                    ┌─────▼─────┐                        │
│                    │  Fusion   │                        │
│                    │  Results  │                        │
│                    └─────┬─────┘                        │
│                          │                               │
│                    ┌─────▼─────┐                        │
│                    │    LLM    │                        │
│                    │  Response │                        │
│                    └───────────┘                        │
└─────────────────────────────────────────────────────────┘
```

**Avantages** :
-  Une organisation peut avoir plusieurs domaines
-  Isolation des données par organisation
-  Flexibilité maximale
### Option 2 : Architecture avec Détection Automatique de Domaine

```
Question Utilisateur
        │
        ▼
┌───────────────────┐
│  Domain Detector  │  ← Classifie la question (tech, legal, medical, etc.)
└────────┬──────────┘
         │
    ┌────┴────┐
    │        │
    ▼        ▼
┌──────┐  ┌──────┐
│ Tech │  │Legal │  ← Recherche dans le(s) domaine(s) détecté(s)
└──┬───┘  └──┬───┘
   │         │
   └────┬────┘
        │
        ▼
┌──────────────┐
│  Fusion +    │
│  Reranking   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  LLM avec    │
│  Prompt      │
│  Adaptatif   │
└──────────────┘
```
## 🔧 Implémentation Proposée
### 1. Détection Automatique de Domaine

**Service de classification** qui analyse la question pour déterminer le(s) domaine(s) pertinent(s).

```python
# app/services/domain_detector.py
def detect_domain(query: str) -> list[str]:
    """
    Détecte le(s) domaine(s) pertinent(s) pour une question.
    
    Retourne une liste de domaines triés par pertinence.
    """
    # Utilise des embeddings pour classifier
    # ou des mots-clés spécifiques
    # ou un modèle de classification léger
```
### 2. Recherche Multi-Domaines

**Router intelligent** qui peut chercher dans plusieurs domaines.

```python
# app/services/multi_domain_rag.py
def search_multi_domain(
    organization_id: int,
    query: str,
    domains: list[str] | None = None,
) -> list[dict]:
    """
    Recherche dans plusieurs domaines et fusionne les résultats.
    """
    if domains is None:
        domains = detect_domain(query)
    
    all_results = []
    for domain in domains:
        results = hybrid_search(
            organization_id=organization_id,
            query=query,
            filters={"domain": domain},  # Nouveau filtre
            top_k=5,
        )
        all_results.extend(results)
    
    # Fusion et reranking global
    return merge_and_rerank(all_results)
```
### 3. Configuration par Organisation

**Ajouter un champ `domains` dans la table `organizations`** :

```sql
ALTER TABLE organizations ADD COLUMN domains TEXT;
-- JSON array: ["tech", "legal", "general"]
```
### 4. Prompts Adaptatifs

**Système de prompts qui s'adapte au contexte détecté** :

```python
def get_adaptive_prompt(domains: list[str], query: str) -> str:
    """
    Génère un prompt adapté aux domaines détectés.
    """
    if len(domains) == 1:
        return get_domain_config(domains[0]).system_prompt
    
    # Prompt multi-domaines
    return f"""Tu es Syro, un assistant polyvalent expert dans :
{', '.join([get_domain_config(d).name for d in domains])}

La question concerne principalement : {', '.join(domains)}
...
"""
```
##  Améliorations Proposées
### 1. **Détection Automatique de Domaine** ⭐⭐⭐

**Priorité : Haute**

- Utiliser un modèle de classification léger (ex: sentence-transformers)
- Créer un dictionnaire de mots-clés par domaine
- Combiner classification ML + règles pour plus de robustesse

**Avantages** :
- L'utilisateur n'a pas à spécifier le domaine
- Recherche plus pertinente automatiquement
- Expérience utilisateur améliorée
### 2. **Recherche Multi-Domaines** ⭐⭐⭐

**Priorité : Haute**

- Permettre à une organisation d'avoir plusieurs domaines actifs
- Recherche parallèle dans plusieurs domaines
- Fusion intelligente des résultats

**Avantages** :
- Une seule instance pour plusieurs domaines
- Réponses plus complètes
- Pas besoin de créer plusieurs instances
### 3. **Métadonnées de Domaine dans les Chunks** ⭐⭐

**Priorité : Moyenne**

- Ajouter un champ `domain` dans les métadonnées des chunks
- Permet de filtrer et organiser par domaine
- Facilite la recherche multi-domaines
### 4. **Système de Confiance par Domaine** ⭐⭐

**Priorité : Moyenne**

- Score de confiance pour chaque domaine détecté
- Utiliser seulement les domaines avec confiance > seuil
- Améliorer la précision
### 5. **Cache de Classification** ⭐

**Priorité : Basse**

- Mettre en cache les classifications de questions similaires
- Réduire les appels au modèle de classification
- Améliorer les performances
### 6. **Interface de Configuration** ⭐

**Priorité : Basse**

- Interface admin pour configurer les domaines par organisation
- Permettre d'activer/désactiver des domaines
- Gérer les prompts personnalisés
## 📋 Plan d'Implémentation
### Phase 1 : Base Multi-Domaines
1.  Système de domaines (déjà fait)
2. ⬜ Ajouter champ `domains` dans `organizations`
3. ⬜ Modifier la recherche pour supporter plusieurs domaines
4. ⬜ Ajouter métadonnée `domain` dans les chunks
### Phase 2 : Détection Automatique
1. ⬜ Créer service de détection de domaine
2. ⬜ Intégrer dans le pipeline RAG
3. ⬜ Tests et validation
### Phase 3 : Fusion Intelligente
1. ⬜ Algorithme de fusion multi-domaines
2. ⬜ Reranking global
3. ⬜ Prompts adaptatifs
### Phase 4 : Optimisations
1. ⬜ Cache de classification
2. ⬜ Interface de configuration
3. ⬜ Monitoring et analytics
## 🎯 Architecture Recommandée : Hybride

**La meilleure approche** combine les deux options :

1. **Par défaut** : Détection automatique du domaine
2. **Optionnel** : L'utilisateur peut forcer un domaine spécifique
3. **Organisation** : Peut configurer quels domaines sont actifs
4. **Recherche** : Multi-domaines si plusieurs domaines pertinents détectés
### Exemple de Flux

```
Question: "Comment créer une table Snowflake et quelles sont les implications légales ?"

1. Détection → ["tech", "legal"] (confiance: 0.9, 0.7)
2. Recherche parallèle dans tech ET legal
3. Fusion des résultats (10 chunks tech + 5 chunks legal)
4. Reranking global
5. LLM avec prompt adaptatif multi-domaines
6. Réponse qui combine les deux domaines
```
## 💡 Avantages de cette Architecture

1. **Flexibilité** : Supporte un seul domaine ou plusieurs
2. **Intelligence** : Détection automatique sans configuration
3. **Performance** : Recherche parallèle optimisée
4. **Évolutivité** : Facile d'ajouter de nouveaux domaines
5. **Isolation** : Chaque organisation contrôle ses domaines
##  Comparaison des Options

| Critère | Option 1 (Multi-org) | Option 2 (Auto-detect) | Hybride (Recommandé) |
|---------|---------------------|------------------------|----------------------|
| Simplicité | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Flexibilité | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Intelligence | ⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Performance | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Maintenance | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ |

---

**Conclusion** : L'architecture hybride offre le meilleur compromis entre simplicité, flexibilité et intelligence.

