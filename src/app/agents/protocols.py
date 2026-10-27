from typing import Protocol

from .mcp.schemas import MCPServerSpec
from .model import Agent

class SubAgentResolver(Protocol):
    async def resolve(self, slugs: set[str], user_uuid: str | None = None) -> dict[str, Agent]:
        ...
    
    async def resolve_available(self, user_uuid: str | None = None) -> dict[str, Agent]:
        ...


class MCPResolver(Protocol):
    async def resolve(self, agent: Agent | None = None, user_uuid: str | None = None) -> dict[str, MCPServerSpec]:
        ...
