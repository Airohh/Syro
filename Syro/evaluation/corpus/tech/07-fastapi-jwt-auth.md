# Authentification JWT dans une API FastAPI

## Le principe du JWT

Un JWT (JSON Web Token) est un jeton signé composé de trois parties encodées en base64url : un **header**, un **payload** (les claims, par exemple `sub`, `exp`, `role`) et une **signature**. La signature, calculée avec une clé secrète serveur (HMAC-SHA256) ou une paire de clés, garantit que le token n'a pas été altéré. Le JWT est **stateless** : le serveur n'a pas besoin de stocker la session, il vérifie la signature.

## Flux dans FastAPI

1. **Login** : l'utilisateur envoie ses identifiants. Le serveur vérifie le mot de passe (hashé avec bcrypt) et renvoie un JWT signé contenant l'id utilisateur et une expiration (`exp`).
2. **Requêtes authentifiées** : le client envoie le token dans l'en-tête `Authorization: Bearer <token>`.
3. **Vérification** : une dépendance FastAPI décode et valide le token (signature + expiration), récupère l'utilisateur et le rend disponible à la route.

## Mise en œuvre

- `OAuth2PasswordBearer` fournit le schéma de récupération du token depuis le header.
- Une fonction `get_current_user` en `Depends()` décode le JWT (PyJWT), lève `401` si invalide ou expiré, et retourne l'utilisateur.
- On protège une route en ajoutant `user = Depends(get_current_user)`.

## Bonnes pratiques

- Expiration courte des access tokens, refresh token pour prolonger.
- Clé secrète forte, jamais en dur dans le code.
- Toujours servir l'API en HTTPS pour éviter l'interception du token.
