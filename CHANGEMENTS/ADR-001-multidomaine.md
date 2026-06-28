# ADR-001 — Modèle multi-domaines

- **Statut** : Accepted (2026-06-28) — *ticket T0.4*
- **Date** : 2026-06-28
- **Décideurs** : TL · **Consultés** : BE, FE
- **Lié** : `ROADMAP_RAG.md` (E4), `docs/architecture.md`

## Contexte

Syro doit servir plusieurs domaines (tech, medical, legal, finance, education, mlops, general). Deux modèles ont coexisté sans décision formelle :

- **Multi-instances par port** : une instance API dédiée par domaine, le frontend route vers un port différent par domaine (`frontend/src/utils/domainPorts.ts`). Hérité du hack multi-instances (`create_syro_instance.py` / `update_instances.py`, désormais supprimés).
- **Multi-domaines mono-API** : une seule API, isolation par collections/filtres Qdrant et routes `/domains/{domain}/...`, sélection du domaine côté requête.

**État réel du code (vérifié)** : le second modèle est déjà en place. `domainPorts.ts` renvoie `8000` pour tous les domaines et `getDomainApiUrl()` pointe une base URL unique ; les routes `/domains/{domain}/chat/...` existent (`routers/chat.py`) ; le métadonnée `domain` est portée par les chunks. Le modèle par port n'est plus qu'une **indirection vestigiale**.

## Décision

Adopter **Option A — multi-domaines mono-API** comme modèle officiel et unique.

- 1 API FastAPI, 1 base URL côté frontend.
- Domaine transporté par la route (`/domains/{domain}/...`) et/ou un header `X-Domain`.
- Isolation par collection/filtre Qdrant par domaine (déjà en place via `_get_collection_for_domain`).
- Retrait planifié de l'indirection ports (`domainPorts.ts`) du chemin nominal.

## Alternatives écartées

- **Multi-instances par port** : isolation forte au prix d'une multiplication des process, de la conf et du déploiement ; incompatible avec la suppression déjà actée du hack multi-instances. Réservable à un déploiement avancé (scale-out par domaine) hors chemin par défaut, si un besoin réel émerge.

## Conséquences

**Positives**
- Cohérence produit (le code et la doc disent la même chose).
- Déploiement simple (un service), aligné sur `infra/docker-compose.yml`.
- Débloque les tickets E4 (durcissement) qui supposaient un modèle tranché.

**Fait (2026-06-28)**
- `domainPorts.ts` réduit à une **source unique** : `getDomainApiUrl`/`getDomainPort` renvoient une base URL pilotée par `VITE_API_URL` (défaut `http://127.0.0.1:8000`), constante `DOMAIN_PORTS` (morte) supprimée. Signatures conservées → aucun call-site cassé, `tsc --noEmit` clean.

**À faire (suivi)**
- Vérifier que tout appel frontend passe par les routes `/domains/{domain}/...` ou envoie le header de domaine.
- Documenter le header `X-Domain` si retenu en complément des routes.

**Risques**
- Faible : changement surtout frontend/déclaratif, le backend mono-API est déjà la réalité.
