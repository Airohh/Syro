from __future__ import annotations

from typing import Any

from ..config import settings
from ..domains import get_domain_config
from .llm import answer_from_context
from .rag import retrieve_chunks_with_metadata

class Agent:
    def __init__(
        self,
        name: str,
        personality: str,
        domain: str | None = None,
        system_prompt_override: str | None = None,
    ):
        self.name = name
        self.personality = personality
        self.domain = domain or settings.domain
        self.domain_config = get_domain_config(self.domain)
        
        if system_prompt_override:
            self.system_prompt = system_prompt_override
        else:
            base_prompt = self.domain_config.system_prompt
            self.system_prompt = f"""{base_prompt}

Tu es {name}, {personality}.
Utilise ton style dans tes réponses et adapte selon le contexte."""
    
    def answer(
        self,
        organization_id: int,
        query: str,
        include_sources: bool = True,
        filters: dict[str, Any] | None = None,
    ) -> tuple[str, int, list[dict[str, Any]]]:
        chunk_results = retrieve_chunks_with_metadata(
            organization_id=organization_id,
            query=query,
            filters=filters,
            use_hybrid=True,
        )
        
        context_chunks = [r["text"] for r in chunk_results]
        answer, usage = answer_from_context(query, context_chunks, domain=self.domain)
        
        sources = []
        if include_sources:
            sources = [
                {
                    "text": r["text"][:200] + "..." if len(r["text"]) > 200 else r["text"],
                    "score": float(r.get("score", 0.0)),
                    "metadata": r.get("metadata", {}) or {},
                }
                for r in chunk_results
            ]
        
        return answer, usage, sources

class AgentManager:
    def __init__(self):
        self.agents: dict[str, Agent] = {}
        self._create_default_agents()
    
    def _create_default_agents(self):
        self.add_agent(
            name="Assistant",
            personality="un assistant intelligent et serviable",
            domain="general",
        )
        
        self.add_agent(
            name="Expert Tech",
            personality="un expert technique spécialisé en data engineering et développement",
            domain="tech",
        )
        
        self.add_agent(
            name="Expert Médical",
            personality="un expert médical avec une approche professionnelle et empathique",
            domain="medical",
        )
        
        self.add_agent(
            name="Expert Juridique",
            personality="un juriste expert, précis et rigoureux dans ses analyses",
            domain="legal",
        )
    
    def add_agent(
        self,
        name: str,
        personality: str,
        domain: str | None = None,
        system_prompt: str | None = None,
    ) -> Agent:
        agent = Agent(
            name=name,
            personality=personality,
            domain=domain,
            system_prompt_override=system_prompt,
        )
        self.agents[name] = agent
        return agent
    
    def get_agent(self, name: str) -> Agent | None:
        return self.agents.get(name)
    
    def list_agents(self) -> list[dict[str, Any]]:
        return [
            {
                "name": agent.name,
                "personality": agent.personality,
                "domain": agent.domain,
            }
            for agent in self.agents.values()
        ]

# Global agent manager
agent_manager = AgentManager()

