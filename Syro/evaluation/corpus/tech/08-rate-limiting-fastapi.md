# Rate limiting dans une API FastAPI

## Pourquoi limiter le débit

Le rate limiting protège l'API contre les abus : attaques par force brute sur le login, déni de service, scraping, ou simplement un client mal codé qui boucle. On limite le nombre de requêtes autorisées par client sur une fenêtre de temps.

## Algorithmes courants

- **Fixed window** : N requêtes par fenêtre fixe (ex. 100/minute). Simple mais sujet aux pics en bordure de fenêtre.
- **Sliding window** : fenêtre glissante, plus lisse.
- **Token bucket** : un seau se remplit de jetons à débit constant ; chaque requête consomme un jeton. Autorise des rafales contrôlées.

## Mise en place dans FastAPI

1. **Identifier le client** : par IP, par clé d'API ou par utilisateur authentifié.
2. **Compter les requêtes** dans un stockage partagé. En mémoire pour une seule instance ; **Redis** dès qu'il y a plusieurs workers/instances, car le compteur doit être partagé.
3. **Appliquer la limite** via un middleware ou une dépendance : si le quota est dépassé, renvoyer `429 Too Many Requests` avec un en-tête `Retry-After`.

## Exemple de design

Un `RedisRateLimiter` incrémente une clé `ratelimit:<user>:<window>` avec une expiration égale à la fenêtre. Si le compteur dépasse le seuil, on rejette. Un fallback en mémoire permet de fonctionner si Redis est indisponible.

## Bonnes pratiques

- Limites plus strictes sur les endpoints sensibles (login).
- Exposer les en-têtes `X-RateLimit-Remaining` pour informer le client.
