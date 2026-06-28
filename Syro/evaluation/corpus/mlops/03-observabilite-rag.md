# Observabilité d'un système RAG en production

## Définition

L'observabilité, c'est la capacité à comprendre l'état interne d'un système à partir de ses sorties. Elle repose sur trois piliers : **logs**, **métriques** et **traces**. Pour un RAG, elle couvre à la fois l'infrastructure et la qualité des réponses.

## Les trois piliers

- **Logs** : journaux structurés (JSON) avec un **correlation ID** par requête pour suivre une question de bout en bout (retrieval, reranking, génération).
- **Métriques** : valeurs numériques agrégées exposées à Prometheus (latence par étape, nombre de chunks récupérés, taux d'erreur, tokens consommés).
- **Traces** : OpenTelemetry permet de tracer une requête à travers chaque service et chaque étape du pipeline, pour identifier où le temps est passé.

## Spécificités RAG à instrumenter

- **Qualité du retrieval** : combien de chunks récupérés, score de similarité, est-ce que des sources ont été trouvées ?
- **Qualité de la génération** : longueur de réponse, présence de citations, détection de réponses hors-sujet.
- **Évaluation continue** : échantillonner des réponses et les noter (RAGAS, ou feedback utilisateur) pour suivre la qualité dans le temps.
- **Coût et latence** par étape (embedding, recherche vectorielle, reranking, LLM).

## Mise en place

1. Middleware qui ajoute un correlation ID et logue chaque requête.
2. Export Prometheus sur `/metrics`, dashboards Grafana.
3. Tracing OpenTelemetry optionnel pour le détail par span.
4. Alertes sur seuils (latence p95, taux d'erreur, chute de qualité).

L'observabilité transforme un RAG « boîte noire » en système pilotable et débogable.
