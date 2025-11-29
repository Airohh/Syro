"""Agent endpoints for personalized assistants."""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Any
from pydantic import BaseModel

from ..dependencies import get_current_user, require_active_org
from ..schemas import MessageCreate, MessageResponse
from ..services.agent import agent_manager
from ..db import get_db
import sqlite3

router = APIRouter(prefix="/agents", tags=["agents"])

class AgentCreate(BaseModel):
    name: str
    personality: str
    domain: str | None = None

@router.get("/list")
def list_agents():
    """List all available agents."""
    return {
        "agents": agent_manager.list_agents(),
    }

@router.post("/chat/{agent_name}", response_model=MessageResponse)
def chat_with_agent(
    agent_name: str,
    payload: MessageCreate,
    user = Depends(get_current_user),
    org = Depends(require_active_org()),
    db: sqlite3.Connection = Depends(get_db),
):
    """Chat with a specific agent."""
    agent = agent_manager.get_agent(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    
    # Get answer from agent
    answer, usage, sources = agent.answer(
        organization_id=org["id"],
        query=payload.content,
        include_sources=True,
    )
    
    # Store conversation (simplified - you might want to enhance this)
    from ..services.chat import create_conversation_if_needed, store_message
    conversation_id = create_conversation_if_needed(
        db, org["id"], payload.conversation_id, title=f"Chat with {agent_name}"
    )
    store_message(db, conversation_id, "user", payload.content, user["id"])
    store_message(db, conversation_id, "assistant", answer, None)
    
    return MessageResponse(
        conversation_id=conversation_id,
        message=answer,
        usage=usage,
        sources=sources,
    )

@router.post("/create")
def create_agent(
    payload: AgentCreate = Body(...),
    user = Depends(get_current_user),
):
    """Create a custom agent."""
    # In a real implementation, you might want to store custom agents per user/org
    agent = agent_manager.add_agent(
        name=payload.name,
        personality=payload.personality,
        domain=payload.domain,
    )
    return {
        "name": agent.name,
        "personality": agent.personality,
        "domain": agent.domain,
        "message": f"Agent '{payload.name}' created successfully",
    }

