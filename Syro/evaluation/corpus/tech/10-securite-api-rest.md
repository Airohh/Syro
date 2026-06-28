# Sécuriser une API REST exposée publiquement

## Authentification et autorisation

- **Authentification forte** : JWT ou OAuth2, mots de passe hashés avec bcrypt/argon2 (jamais en clair).
- **Autorisation** : contrôle d'accès par rôle (RBAC), vérifier les permissions à chaque endpoint, isoler les données par tenant/organisation.

## Transport

- **HTTPS partout** (TLS) pour chiffrer les échanges et protéger les tokens.
- En-têtes de sécurité HTTP : `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `X-Frame-Options`, `Content-Security-Policy`.

## Validation et entrées

- **Valider toutes les entrées** (Pydantic) : types, tailles, formats. Rejeter ce qui ne correspond pas au schéma.
- **Validation des uploads** : vérifier le type MIME et la taille des fichiers, refuser les extensions dangereuses.
- Se prémunir contre l'injection (requêtes paramétrées, jamais de concaténation SQL).

## Disponibilité et abus

- **Rate limiting** pour contrer le brute force et le DoS, réponses `429`.
- **CORS** configuré strictement : autoriser uniquement les origines de confiance, pas `*` en production.
- Limiter la taille des corps de requête.

## Observabilité et secrets

- **Logs structurés** avec un identifiant de corrélation par requête, sans fuiter de données sensibles.
- **Ne jamais exposer les détails d'exception** au client (pas de stack trace) ; renvoyer un message générique et logguer le détail côté serveur.
- **Secrets** (clés, mots de passe) dans des variables d'environnement ou un coffre, jamais dans le code ni le dépôt.

## Maintenance

- Mettre à jour les dépendances (scanner les CVE).
- Principe du moindre privilège pour les comptes de service et les accès base de données.
