# Chunking hiérarchique de documents

## Pourquoi découper les documents

Un LLM et un modèle d'embeddings ont une fenêtre de contexte limitée. On découpe donc les documents en **chunks** (morceaux) avant indexation. La qualité du chunking détermine directement la qualité du retrieval : un chunk trop grand dilue le signal, un chunk trop petit perd le contexte.

## Principe du chunking hiérarchique

Le chunking hiérarchique respecte la **structure logique** du document plutôt que de couper à l'aveugle tous les N caractères :

1. On découpe d'abord par **titres et sections** (headers Markdown `#`, `##`, etc.).
2. Si une section dépasse la taille maximale, on la **sous-découpe** en passages plus petits.
3. On applique un **chevauchement (overlap)** entre chunks consécutifs pour ne pas perdre une idée à cheval sur une frontière.

## Avantages

- Chaque chunk reste **sémantiquement cohérent** (un sujet = un chunk).
- On peut conserver le **chemin de titres** comme métadonnée, ce qui améliore le contexte fourni au LLM.
- Le retrieval est plus précis car les frontières suivent le sens, pas un compteur de caractères.

## Paramètres typiques

- Taille cible : 300 à 800 tokens par chunk.
- Overlap : 10 à 20 % de la taille du chunk.

Un bon chunking hiérarchique est souvent le levier le plus rentable pour améliorer un pipeline RAG, avant même de changer de modèle.
