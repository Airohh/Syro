# Évaluer un pipeline RAG sans RAGAS

## Pourquoi des alternatives

RAGAS est pratique mais dépend d'un LLM juge (coût, variance). On peut évaluer un RAG autrement, en séparant les deux sous-systèmes : le **retrieval** et la **génération**.

## Évaluer le retrieval (métriques de ranking)

Avec un jeu de questions annotées des passages pertinents (« golden chunks ») :

- **Recall@k** : proportion des passages pertinents retrouvés dans le top-k.
- **Precision@k** : proportion de passages pertinents parmi le top-k.
- **MRR (Mean Reciprocal Rank)** : inverse du rang du premier passage pertinent — récompense le fait de le placer en tête.
- **nDCG** : gain cumulé actualisé, tient compte de la position et de la gradation de pertinence.

Ces métriques sont **déterministes** et ne demandent pas de LLM.

## Évaluer la génération

- **Métriques de chevauchement** : BLEU, ROUGE, METEOR comparent la réponse à une référence (utiles mais sensibles à la formulation).
- **Similarité sémantique** : cosinus entre l'embedding de la réponse et celui de la référence (BERTScore).
- **Exact match / F1** sur des questions factuelles à réponse courte.

## Évaluation humaine et en ligne

- **Annotation humaine** : des évaluateurs notent fidélité, pertinence, utilité sur un échantillon. Référence de qualité mais coûteuse.
- **Feedback utilisateur en production** : pouce haut/bas, taux de reformulation, taux d'abandon.
- **A/B testing** : comparer deux configurations sur du trafic réel.

## Bonne pratique

Combiner : métriques de retrieval automatiques (recall@k, MRR) pour itérer vite, plus une évaluation humaine périodique sur un échantillon pour valider la qualité perçue. RAGAS devient un complément, pas l'unique source de vérité.
