from typing import Any

from langgraph.graph import MessagesState
from pydantic import BaseModel, Field

class SearchInput(BaseModel):
    user_question: str = Field(
        min_length=1,
        description=(
            "A self-contained search query"
        ),
    )
    user_uuid: str | None = None

class SearchSubgraphState(MessagesState):
    user_question: str | None
    user_uuid: str | None
    context_query: str | None

    retrieval_results: list[dict[str, Any]] | None
    retrieval_failed: bool | None
    search_results: list[dict[str, Any]] | None

class SearchSubgraphOutput(MessagesState):
    retrieval_results: list[dict[str, Any]] 
    search_results: list[dict[str, Any]]
    structured_response: dict[str, Any]
