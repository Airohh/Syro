# Détecter et gérer le data drift

## Qu'est-ce que le data drift

Le data drift est le changement de la distribution des données d'entrée d'un modèle entre l'entraînement et la production. Le modèle a appris sur une certaine distribution ; si le monde change, ses prédictions se dégradent. On distingue :

- **Data drift (covariate shift)** : la distribution des features `P(X)` change.
- **Concept drift** : la relation `P(y|X)` entre entrées et cible change.
- **Label drift** : la distribution de la cible `P(y)` change.

## Comment le détecter

- **Tests statistiques** entre la distribution de référence (entraînement) et la distribution courante :
  - **PSI** (Population Stability Index) pour les variables numériques/binnées.
  - **Test de Kolmogorov-Smirnov** pour comparer deux distributions continues.
  - **Chi-2** pour les variables catégorielles.
- **Surveillance des prédictions** : dérive du score moyen, de la proportion de classes prédites.
- **Monitoring de la performance** quand les labels réels arrivent (chute d'accuracy/F1).
- Outils : Evidently, NannyML, ou des checks maison loggés dans MLflow.

## Comment le gérer

1. **Alerter** dès qu'une métrique de drift dépasse un seuil.
2. **Investiguer** : bug de pipeline, changement amont, vraie évolution du phénomène ?
3. **Réentraîner** le modèle sur des données récentes (réentraînement périodique ou déclenché par le drift).
4. **Versionner** données et modèle pour comparer et faire un rollback si besoin.

La détection de drift est au cœur d'un pipeline MLOps mature : elle ferme la boucle entre production et réentraînement.
