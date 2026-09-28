"""Endpoints de chat.

    POST /chat/message                    réponse JSON complète (+ sources)
    POST /chat/message/stream             Server-Sent Events
    POST /domains/{domain}/chat/message   idem, domaine imposé dans l'URL
    POST /domains/{domain}/chat/message/stream

Domaine : champ `domain` du body ou de l'URL. Absent ou `general` →
recherche dans tous les documents de l'organisation.
"""

from __future__ import annotations

import json
import logging
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from ..db import db_session, get_db
from ..dependencies import enforce_rate_limit, get_current_user, require_active_org
from ..domains import DOMAINS
from ..schemas import MessageCreate, MessageResponse
from ..services.chat import (
    ConversationNotFound,
    build_answer,
    build_answer_stream,
    charge_usage,
    get_or_create_conversation,
    load_conversation_history,
    store_message,
)
from ..services.llm import LLMUnavailableError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])
domain_router = APIRouter(prefix="/domains/{domain}/chat", tags=["chat"])

_LLM_DOWN = (
    "Le modèle de langage est indisponible. Vérifiez qu'Ollama tourne "
    "(ou OPENAI_API_KEY), puis réessayez."
)


def _sse(data: str, event: str | None = None) -> str:
    """Évènement SSE valide : un champ `data:` par ligne (sinon un `\\n`
    dans un fragment markdown casserait le cadrage)."""
    head = f"event: {event}\n" if event else ""
    body = "".join(f"data: {line}\n" for line in data.split("\n"))
    return f"{head}{body}\n"


def _check_domain(domain: str | None) -> str | None:
    if domain and domain.lower() not in DOMAINS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Domain '{domain}' not found. Available: {list(DOMAINS)}",
        )
    return domain


def _open_conversation(
    db: sqlite3.Connection, org, user, payload: MessageCreate
) -> tuple[int, list[dict[str, str]]]:
    """Conversation vérifiée + historique + message utilisateur (non commité)."""
    try:
        conversation_id = get_or_create_conversation(
            db, org["id"], user["id"], payload.conversation_id, title=payload.content
        )
    except ConversationNotFound:
        raise HTTPException(status_code=404, detail="Conversation not found")
    history = load_conversation_history(db, conversation_id)
    store_message(db, conversation_id, "user", payload.content, user["id"])
    return conversation_id, history


def _answer(
    payload: MessageCreate, domain: str | None, user, org, db
) -> MessageResponse:
    domain = _check_domain(domain)
    conversation_id, history = _open_conversation(db, org, user, payload)
    try:
        answer, usage, sources = build_answer(
            organization_id=org["id"],
            query=payload.content,
            user_id=user["id"],
            domain=domain,
            conversation_history=history,
        )
    except LLMUnavailableError as e:
        # Rien n'est persisté : pas de question orpheline dans l'historique.
        db.rollback()
        logger.warning("LLM unavailable: %s", e)
        raise HTTPException(status_code=503, detail=_LLM_DOWN)
    except Exception:
        db.rollback()
        logger.exception("Chat failed")
        raise HTTPException(
            status_code=500,
            detail="Erreur lors du traitement du message. Consultez les logs serveur.",
        )

    store_message(db, conversation_id, "assistant", answer, None)
    charge_usage(db, org["id"], user["id"], usage)
    db.commit()
    return MessageResponse(
        conversation_id=conversation_id, message=answer, usage=usage, sources=sources
    )


def _answer_stream(payload: MessageCreate, domain: str | None, user, org, db):
    domain = _check_domain(domain)
    conversation_id, history = _open_conversation(db, org, user, payload)
    db.commit()  # le générateur écrit la réponse avec sa propre connexion
    org_id, user_id = org["id"], user["id"]

    def generate():
        answer = ""
        try:
            sources, fragments = build_answer_stream(
                organization_id=org_id,
                query=payload.content,
                user_id=user_id,
                domain=domain,
                conversation_history=history,
            )
            yield _sse(
                json.dumps({"conversation_id": conversation_id, "sources": sources}),
                event="sources",
            )
            for fragment in fragments:
                answer += fragment
                yield _sse(fragment)
        except LLMUnavailableError:
            yield _sse(_LLM_DOWN, event="error")
            return
        except Exception:
            logger.exception("Streaming failed")
            yield _sse("Erreur serveur pendant la génération.", event="error")
            return

        # La connexion de la requête est déjà rendue : nouvelle session DB.
        usage = int((len(answer.split()) + len(payload.content.split())) * 1.3)
        with db_session() as conn:
            store_message(conn, conversation_id, "assistant", answer, None)
            charge_usage(conn, org_id, user_id, usage)
        yield _sse("[DONE]")

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/message", response_model=MessageResponse)
def send_message(
    payload: MessageCreate,
    user=Depends(get_current_user),
    org=Depends(require_active_org()),
    db: sqlite3.Connection = Depends(get_db),
    _: bool = Depends(enforce_rate_limit("chat")),
):
    return _answer(payload, payload.domain, user, org, db)


@router.post("/message/stream")
def send_message_stream(
    payload: MessageCreate,
    user=Depends(get_current_user),
    org=Depends(require_active_org()),
    db: sqlite3.Connection = Depends(get_db),
    _: bool = Depends(enforce_rate_limit("chat")),
):
    return _answer_stream(payload, payload.domain, user, org, db)


@domain_router.post("/message", response_model=MessageResponse)
def send_message_for_domain(
    domain: str,
    payload: MessageCreate,
    user=Depends(get_current_user),
    org=Depends(require_active_org()),
    db: sqlite3.Connection = Depends(get_db),
    _: bool = Depends(enforce_rate_limit("chat")),
):
    return _answer(payload, domain, user, org, db)


@domain_router.post("/message/stream")
def send_message_stream_for_domain(
    domain: str,
    payload: MessageCreate,
    user=Depends(get_current_user),
    org=Depends(require_active_org()),
    db: sqlite3.Connection = Depends(get_db),
    _: bool = Depends(enforce_rate_limit("chat")),
):
    return _answer_stream(payload, domain, user, org, db)
