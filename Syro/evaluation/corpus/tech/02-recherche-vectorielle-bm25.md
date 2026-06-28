# Recherche vectorielle, BM25 et recherche hybride

## Recherche vectorielle (dense)

La recherche vectorielle encode la requête et les documents en vecteurs denses via un modèle d'embeddings. La pertinence est mesurée par une similarité (cosinus le plus souvent) dans l'espace vectoriel. Elle capture le **sens sémantique** : « voiture » et « automobile » sont proches même sans mot commun. Faiblesse : elle peut manquer une correspondance exacte de terme rare (référence produit, acronyme précis).

## BM25 (recherche lexicale / sparse)

BM25 est une fonction de classement lexicale fondée sur la fréquence des termes (TF), la fréquence inverse de document (IDF) et la normalisation par la longueur du document. Elle excelle sur les **correspondances exactes de mots-clés** mais ignore les synonymes : « voiture » ne matchera pas « automobile ».

## Différence clé

- Vectorielle : comprend le **sens**, robuste aux reformulations, faible sur les termes exacts rares.
- BM25 : précise sur les **mots exacts**, aveugle au sens.

## Recherche hybride

La recherche hybride fusionne les deux scores, par exemple `score = α · score_vectoriel + (1 - α) · score_BM25`. Avec α = 0,7 on privilégie le sémantique tout en gardant la précision lexicale. C'est l'approche la plus robuste : elle récupère les bons passages aussi bien sur une question reformulée que sur une recherche d'identifiant exact. C'est la stratégie de retrieval par défaut d'un pipeline RAG de qualité.
