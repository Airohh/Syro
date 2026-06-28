from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
import sqlite3
import logging

from ..dependencies import enforce_rate_limit, get_current_user, require_active_org
from ..domains import DOMAINS
from ..schemas import MessageCreate, MessageResponse
from ..services.chat import (
    build_answer,
    build_answer_stream,
    create_conversation_if_needed,
    load_conversation_history,
    store_message,
)
from ..db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])
domain_router = APIRouter(prefix="/domains/{domain}/chat", tags=["chat"])


def _sse(chunk: str) -> str:
    """Formate un fragment en évènement SSE valide.

    Un fragment contenant un saut de ligne (réponses markdown, code) casse le
    cadrage si on émet `data: {chunk}\\n\\n` brut : le `\\n` interne coupe
    l'évènement. La spec SSE veut un champ `data:` par ligne.
    """
    body = "".join(f"data: {line}\n" for line in chunk.split("\n"))
    return f"{body}\n"

@router.post("/message", response_model=MessageResponse)
def send_message(
    payload: MessageCreate,
    user=Depends(get_current_user),
    org=Depends(require_active_org()),
    db: sqlite3.Connection = Depends(get_db),
    _: bool = Depends(enforce_rate_limit("chat")),
):
    """
    Endpoint historique utilisé par l'UI actuelle.
    Le domaine est déterminé par la configuration (settings.domain)
    et éventuellement par l'auto-détection.
    """
    try:
        conversation_id = create_conversation_if_needed(
            db, org["id"], payload.conversation_id
        )
        history = load_conversation_history(db, conversation_id)
        store_message(db, conversation_id, "user", payload.content, user["id"])
        
        logger.info(f"Building answer for org {org['id']}, query: {payload.content[:50]}...")
        answer, usage, sources = build_answer(
            org["id"],
            payload.content,
            include_sources=True,
            user_id=user["id"],
            conversation_history=history,
        )
        
        store_message(db, conversation_id, "assistant", answer, None)
        db.execute(
            "INSERT INTO usage_events (organization_id, user_id, event_type, amount, metadata) VALUES (?, ?, ?, ?, ?)",
            (org["id"], user["id"], "chat_completion", usage, None),
        )
        db.execute(
            "UPDATE organizations SET credit_balance = MAX(credit_balance - ?, 0) WHERE id = ?",
            (usage, org["id"]),
        )
        db.commit()
        
        return MessageResponse(
            conversation_id=conversation_id,
            message=answer,
            usage=usage,
            sources=sources,
        )
    except Exception as e:
        logger.error(f"Error in send_message: {type(e).__name__}: {str(e)}", exc_info=True)
        db.rollback()
        # Détails de l'exception réservés aux logs (pas d'info disclosure côté client)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du traitement du message. Consultez les logs serveur.",
        )

@router.post("/message/stream")
def send_message_stream(
    payload: MessageCreate,
    user=Depends(get_current_user),
    org=Depends(require_active_org()),
    db: sqlite3.Connection = Depends(get_db),
    _: bool = Depends(enforce_rate_limit("chat")),
):
    """Stream chat response (Server-Sent Events) – endpoint historique."""
    conversation_id = create_conversation_if_needed(
        db, org["id"], payload.conversation_id
    )
    history = load_conversation_history(db, conversation_id)
    store_message(db, conversation_id, "user", payload.content, user["id"])

    def generate():
        full_answer = ""
        try:
            for chunk in build_answer_stream(
                org["id"],
                payload.content,
                user_id=user["id"],
                conversation_history=history,
            ):
                full_answer += chunk
                yield _sse(chunk)

            store_message(db, conversation_id, "assistant", full_answer, None)
            usage = len(full_answer.split()) + len(payload.content.split())
            db.execute(
                "INSERT INTO usage_events (organization_id, user_id, event_type, amount, metadata) VALUES (?, ?, ?, ?, ?)",
                (org["id"], user["id"], "chat_completion", usage, None),
            )
            db.execute(
                "UPDATE organizations SET credit_balance = MAX(credit_balance - ?, 0) WHERE id = ?",
                (usage, org["id"]),
            )
            db.commit()
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error("Streaming error: %s", e, exc_info=True)
            db.rollback()
            yield f"data: [ERROR]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@domain_router.post("/message", response_model=MessageResponse)
def send_message_for_domain(
    domain: str,
    payload: MessageCreate,
    user=Depends(get_current_user),
    org=Depends(require_active_org()),
    db: sqlite3.Connection = Depends(get_db),
    _: bool = Depends(enforce_rate_limit("chat")),
):
    """
    Nouveau endpoint explicitement multi-domaine.

    - Le domaine est passé dans l'URL: /domains/{domain}/chat/message
    - Aucun auto-detect: le domaine est imposé.
    """
    if domain not in DOMAINS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Domain '{domain}' not found. Available: {list(DOMAINS.keys())}",
        )
    try:
        conversation_id = create_conversation_if_needed(
            db, org["id"], payload.conversation_id
        )
        history = load_conversation_history(db, conversation_id)
        store_message(db, conversation_id, "user", payload.content, user["id"])
        answer, usage, sources = build_answer(
            organization_id=org["id"],
            query=payload.content,
            include_sources=True,
            auto_detect_domain=False,
            domain=domain,
            user_id=user["id"],
            conversation_history=history,
        )
        store_message(db, conversation_id, "assistant", answer, None)
        db.execute(
            "INSERT INTO usage_events (organization_id, user_id, event_type, amount, metadata) VALUES (?, ?, ?, ?, ?)",
            (org["id"], user["id"], "chat_completion", usage, None),
        )
        db.execute(
            "UPDATE organizations SET credit_balance = MAX(credit_balance - ?, 0) WHERE id = ?",
            (usage, org["id"]),
        )
        db.commit()
        return MessageResponse(
            conversation_id=conversation_id,
            message=answer,
            usage=usage,
            sources=sources,
        )
    except Exception as e:
        logger.error(
            f"Error in send_message_for_domain: {type(e).__name__}: {str(e)}",
            exc_info=True,
        )
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du traitement du message. Consultez les logs serveur.",
        )

@domain_router.post("/message/stream")
def send_message_stream_for_domain(
    domain: str,
    payload: MessageCreate,
    user=Depends(get_current_user),
    org=Depends(require_active_org()),
    db: sqlite3.Connection = Depends(get_db),
    _: bool = Depends(enforce_rate_limit("chat")),
):
    """Streaming multi-domaine explicite: /domains/{domain}/chat/message/stream."""
    if domain not in DOMAINS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Domain '{domain}' not found. Available: {list(DOMAINS.keys())}",
        )
    conversation_id = create_conversation_if_needed(
        db, org["id"], payload.conversation_id
    )
    history = load_conversation_history(db, conversation_id)
    store_message(db, conversation_id, "user", payload.content, user["id"])

    def generate():
        full_answer = ""
        try:
            for chunk in build_answer_stream(
                organization_id=org["id"],
                query=payload.content,
                auto_detect_domain=False,
                domain=domain,
                user_id=user["id"],
                conversation_history=history,
            ):
                full_answer += chunk
                yield _sse(chunk)

            store_message(db, conversation_id, "assistant", full_answer, None)
            usage = len(full_answer.split()) + len(payload.content.split())
            db.execute(
                "INSERT INTO usage_events (organization_id, user_id, event_type, amount, metadata) VALUES (?, ?, ?, ?, ?)",
                (org["id"], user["id"], "chat_completion", usage, None),
            )
            db.execute(
                "UPDATE organizations SET credit_balance = MAX(credit_balance - ?, 0) WHERE id = ?",
                (usage, org["id"]),
            )
            db.commit()
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error("Domain streaming error: %s", e, exc_info=True)
            db.rollback()
            yield f"data: [ERROR]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
