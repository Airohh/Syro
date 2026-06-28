# RAG — Retrieval-Augmented Generation

## Définition

Le RAG (Retrieval-Augmented Generation) est une architecture qui combine la recherche documentaire et la génération de texte par un LLM. Plutôt que de répondre uniquement à partir de ses paramètres entraînés, le modèle récupère d'abord des passages pertinents dans une base de connaissances externe, puis les fournit comme contexte pour générer la réponse.

## Fonctionnement

Le pipeline RAG comporte trois étapes :

1. **Indexation** — les documents sont découpés en chunks, transformés en embeddings (vecteurs) et stockés dans une base vectorielle.
2. **Récupération (retrieval)** — la question de l'utilisateur est encodée puis comparée aux chunks indexés pour récupérer les plus pertinents (top-k).
3. **Génération** — les chunks récupérés sont injectés dans le prompt du LLM, qui produit une réponse ancrée dans ces sources.

## Avantages par rapport à un LLM seul

- **Réduction des hallucinations** : la réponse est ancrée dans des documents réels, citables.
- **Fraîcheur** : on met à jour la base de connaissances sans réentraîner le modèle.
- **Traçabilité** : chaque réponse peut citer ses sources.
- **Données privées** : on interroge des documents propriétaires que le LLM n'a jamais vus.
- **Coût** : pas de fine-tuning coûteux pour ajouter de la connaissance.

Le RAG est donc préférable dès qu'il faut répondre sur un corpus spécifique, à jour et vérifiable.
