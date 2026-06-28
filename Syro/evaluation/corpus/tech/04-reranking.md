# Reranking dans un pipeline RAG

## Le problème

La recherche initiale (vectorielle ou hybride) est rapide mais approximative : elle récupère un ensemble de candidats (top-k, par exemple 10 à 20) dont l'ordre n'est pas parfait. Les passages réellement les plus pertinents ne sont pas toujours en tête.

## Le rôle du reranking

Le reranking est une **seconde étape de classement** appliquée aux candidats. Un modèle plus précis (mais plus coûteux) réévalue chaque paire (question, passage) et réordonne les résultats. On ne garde ensuite que les meilleurs (rerank top-k, par exemple 3 à 5) pour les envoyer au LLM.

## Cross-encoder

Le reranker est typiquement un **cross-encoder** (ex. BAAI/bge-reranker-v2-m3). Contrairement au bi-encoder qui encode question et passage séparément, le cross-encoder traite la paire **conjointement** dans un même passage avant : il modélise finement l'interaction entre les deux et produit un score de pertinence bien plus précis.

## Pourquoi c'est utile

- **Précision** : on remonte les vrais bons passages en tête.
- **Moins de bruit envoyé au LLM** : seuls 3 à 5 chunks vraiment pertinents entrent dans le prompt, ce qui réduit les hallucinations et le coût en tokens.
- **Compromis maîtrisé** : on récupère large (rappel élevé) puis on filtre fin (précision élevée).

Le coût est une latence supplémentaire ; on l'active en mode « qualité » et on peut le désactiver en mode « rapide ».
