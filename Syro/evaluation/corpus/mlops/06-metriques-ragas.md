# Les métriques RAGAS

## Qu'est-ce que RAGAS

RAGAS (Retrieval-Augmented Generation Assessment) est un framework d'évaluation **automatique** des pipelines RAG. Il utilise un LLM comme juge pour noter la qualité, sans avoir besoin d'annotations humaines à grande échelle. Chaque métrique est un score entre 0 et 1.

## Les quatre métriques principales

- **Faithfulness (fidélité)** : mesure si la réponse est **fidèle au contexte récupéré**, c'est-à-dire si chaque affirmation de la réponse est soutenue par les passages fournis. Une faithfulness basse = hallucination. Évalue la **génération**.

- **Answer Relevancy (pertinence de la réponse)** : mesure si la réponse est **pertinente par rapport à la question** posée (pas hors-sujet, pas incomplète, pas verbeuse). Évalue la **génération**.

- **Context Recall (rappel du contexte)** : mesure si les passages récupérés contiennent **toute l'information nécessaire** pour produire la réponse de référence (ground truth). Un recall bas = le retrieval a manqué des passages utiles. Évalue le **retrieval**.

- **Context Precision (précision du contexte)** : mesure si les passages **pertinents sont bien classés en tête** parmi ceux récupérés (peu de bruit). Évalue la qualité du classement du **retrieval / reranking**.

## Lecture des scores

- Faithfulness + Answer Relevancy faibles → problème côté **LLM / prompt**.
- Context Recall + Precision faibles → problème côté **retrieval** (chunking, embeddings, top-k, reranking).

## En pratique

On fournit à RAGAS un jeu de (question, réponse générée, contextes récupérés, réponse de référence). RAGAS interroge le LLM juge pour chaque métrique, puis agrège. C'est un benchmark **reproductible** qui permet de mesurer l'impact de chaque changement de configuration.
