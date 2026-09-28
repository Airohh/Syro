# Contribuer à Syro

1. Créer une branche (`git checkout -b feature/ma-feature`).
2. Installer l'environnement de dev : `cd Syro && pip install -r requirements-dev.txt`.
3. Avant de pousser :

```bash
make test     # 147 tests, sans service externe
make lint     # ruff + black, comme la CI
cd frontend && npm run build   # type-check + build du frontend
```

4. Ouvrir une Pull Request. La CI lance tests, lint et build du frontend.

Conventions : type hints, un test pour chaque bug corrigé, et la doc (`README.md`, `docs/architecture.md`) mise à jour quand le comportement change.
