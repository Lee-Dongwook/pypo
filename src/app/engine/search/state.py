from __future__ import annotations

from typing import Annotated, Any

from langchain_core.messages import AnyMessage
from langgraph.graph import MessagesState, add_messages
from pydantic import BaseModel, Field


class SearchInput(BaseModel):
    """Input accepted by the search subgraph.

    A self-contained ``user_question`` is used as-is (after Lucene escaping).
    When it is omitted the extractor rewrites the last human message from
    ``messages`` into a full-text query instead.
    """

    user_question: str | None = Field(
        default=None,
        min_length=1,
        description="A self-contained search query. Omit to derive it from `messages`.",
    )
    user_uuid: str | None = Field(default=None, description="Owner scope for the search.")
    messages: Annotated[list[AnyMessage], add_messages] = Field(default_factory=list)


class SearchSubgraphState(MessagesState):
    user_question: str | None
    user_uuid: str | None
    context_query: str | None

    retrieval_results: list[dict[str, Any]] | None
    retrieval_failed: bool | None
    search_results: list[dict[str, Any]] | None
    structured_response: dict[str, Any] | None


class SearchSubgraphOutput(MessagesState):
    search_results: list[dict[str, Any]]
    structured_response: dict[str, Any] | None
