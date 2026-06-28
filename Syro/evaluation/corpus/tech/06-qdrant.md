# Qdrant — base de données vectorielle

## Qu'est-ce que Qdrant

Qdrant est une base de données vectorielle open source écrite en Rust. Elle stocke des vecteurs (embeddings) accompagnés d'un payload (métadonnées JSON) et permet de rechercher les vecteurs les plus proches d'une requête par similarité (cosinus, produit scalaire ou distance euclidienne).

## Pourquoi l'utiliser dans un RAG

- **Recherche ANN performante** : Qdrant utilise l'index HNSW (Hierarchical Navigable Small World) pour une recherche approximative des plus proches voisins, rapide même sur des millions de vecteurs.
- **Filtrage par métadonnées** : on peut combiner la similarité vectorielle avec des filtres exacts sur le payload (par exemple `domain = "tech"` ou `organization_id = 1`), essentiel pour le multi-tenant.
- **Collections isolées** : on peut créer une collection par domaine ou par tenant, ce qui isole les données.
- **API simple** : REST et gRPC, avec un client Python officiel.
- **Persistance et scalabilité** : stockage sur disque, snapshots, sharding et réplication pour la production.

## Concepts clés

- **Collection** : ensemble de points partageant la même dimension de vecteur et la même métrique de distance.
- **Point** : un vecteur + son id + son payload.
- **HNSW** : structure de graphe qui rend la recherche sous-linéaire.

Dans un pipeline RAG, Qdrant tient le rôle de mémoire sémantique : on y indexe les chunks embeddés, puis on l'interroge à chaque requête pour récupérer les passages pertinents.
