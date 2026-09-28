# ADR-002 — Une collection Qdrant, le domaine comme filtre

- **Statut** : Accepted (2026-09-28)
- **Remplace** : la partie « une collection Qdrant par domaine » d'ADR-001 (le choix mono-API reste valable)

## Contexte

Chaque domaine avait sa collection (`syro_{domaine}_chunks`). Le domaine d'un document était calculé à trois endroits différents : tag `domain:x` à l'upload, détection par mots-clés à l'ingestion (collection Qdrant), premier tag pour BM25. Conséquences constatées :

- BM25 ne renvoyait **rien** dès qu'un domaine était demandé (il comparait `"domain:tech"` à `"tech"`), donc l'hybride tournait en dense seul ;
- un document classé autrement que `tech` devenait invisible pour le chat par défaut ;
- une réindexation qui changeait le domaine laissait des points orphelins, et la suppression devait balayer toutes les collections.

## Décision

- Colonne `documents.domain` = **source unique**.
- **Une** collection Qdrant ; `organization_id`, `document_id` et `domain` dans le payload, **indexés** ; le domaine est un filtre.
- BM25 filtre sur la même colonne.
- `general` / absent = recherche dans tous les documents autorisés ; un domaine choisi par l'utilisateur filtre et fixe la persona du LLM.

## Conséquences

- Moins de code (suppression de la recherche multi-domaines « fan-out ») et plus de cohérence.
- Filtrage multi-tenant natif de Qdrant sur des champs indexés.
- Migration : réindexation (`make reindex`). Les anciennes collections par domaine peuvent être supprimées depuis le dashboard Qdrant.
