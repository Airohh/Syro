import requests

BASE = "http://localhost:8000"

# Login
t = requests.post(f"{BASE}/auth/login", data={"username": "owner@example.com", "password": "ChangeMe123!"}).json()["access_token"]
h = {"Authorization": f"Bearer {t}"}
print("Token OK")

# Upload document
r = requests.post(f"{BASE}/documents/text", headers=h, json={
    "title": "test rag",
    "content": "FastAPI est un framework Python moderne pour construire des APIs REST. Il utilise Pydantic pour la validation des données et supporte nativement l'async. Il génère automatiquement une documentation Swagger.",
    "tags": "tech"
})
print("Upload:", r.json())

# Chat
r2 = requests.post(f"{BASE}/chat/message", headers=h, json={"content": "C'est quoi FastAPI ?"})
print("Chat:", r2.json())
