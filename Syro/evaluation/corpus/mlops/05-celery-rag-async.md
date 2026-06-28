# Celery dans une architecture RAG asynchrone

## Qu'est-ce que Celery

Celery est une file de tâches distribuée pour Python. Elle permet d'exécuter des traitements **en arrière-plan**, hors du cycle requête/réponse HTTP, sur un ou plusieurs workers. Celery a besoin d'un **broker** de messages (souvent Redis ou RabbitMQ) pour transmettre les tâches, et optionnellement d'un **backend de résultats** pour stocker leur état.

## Pourquoi dans un RAG

L'ingestion d'un document est coûteuse : extraction du texte, chunking, calcul des embeddings, indexation dans la base vectorielle. Faire cela dans la requête HTTP d'upload bloquerait l'utilisateur plusieurs secondes ou minutes. On **délègue à Celery** :

1. L'API reçoit l'upload, enregistre le document avec le statut `queued` et renvoie immédiatement une réponse.
2. Une tâche Celery est **enqueue** via le broker.
3. Un **worker** consomme la tâche : il extrait, découpe, embedde et indexe le document, puis met le statut à `complete` (ou `failed`).
4. L'utilisateur suit l'avancement via le statut d'ingestion.

## Avantages

- **Non bloquant** : l'API reste réactive.
- **Scalabilité** : on ajoute des workers pour absorber la charge d'ingestion.
- **Résilience** : tâches ré-essayées en cas d'échec, isolation des traitements lourds.

## Fallback

Pour le développement ou les tests, on peut exécuter les tâches de façon synchrone (mode « eager », `task_always_eager=True`) ou via les `BackgroundTasks` de FastAPI, ce qui évite de devoir lancer un worker et un broker.
