# Bi-encoder vs cross-encoder, et recherche sémantique

## Bi-encoder

Un bi-encoder encode la requête et chaque document **séparément** en deux vecteurs, puis compare ces vecteurs par similarité cosinus. Comme les embeddings des documents peuvent être **calculés à l'avance et indexés**, la recherche est très rapide : on compare un vecteur de requête à des millions de vecteurs pré-calculés. C'est le modèle utilisé pour le retrieval initial (sentence-transformers, nomic-embed-text, etc.).

## Cross-encoder

Un cross-encoder prend la **paire (requête, document) ensemble** en entrée et produit directement un score de pertinence. Il modélise l'interaction fine entre les deux textes, donc il est **plus précis** — mais il ne peut rien pré-calculer : il faut une passe du modèle par paire. Trop lent pour chercher dans toute la base, parfait pour **reranker** quelques dizaines de candidats.

## Compromis

- Bi-encoder : rapide, scalable, moins précis → **retrieval**.
- Cross-encoder : lent, très précis → **reranking**.

La combinaison des deux (récupération large par bi-encoder, puis reranking par cross-encoder) est le pattern standard d'un RAG performant.

## Recherche sémantique avec sentence-transformers

`sentence-transformers` fournit des bi-encoders prêts à l'emploi. Mise en place :

1. Charger un modèle : `SentenceTransformer("all-MiniLM-L6-v2")`.
2. Encoder le corpus : `model.encode(passages)` → matrice d'embeddings, stockée dans une base vectorielle.
3. Encoder la requête et calculer la similarité cosinus avec les passages.
4. Retourner les top-k passages les plus proches.

C'est la brique de base de la recherche sémantique dense.
