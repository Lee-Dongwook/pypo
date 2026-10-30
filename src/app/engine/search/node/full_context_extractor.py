from __future__ import annotations

import logging
import textwrap
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from src.app.engine.models import get_search_model
from src.app.shared.prompts import prompt_pull, prompt_push

from ..queries import escape_lucene
from ..state import SearchSubgraphState

logger = logging.getLogger(__name__)

_MAX_QUESTION = 200
_MAX_HISTORY = 12

CONTEXT_EXTRACT_PROMPT = textwrap.dedent(
    """\
    You are a specialized tool for generating Neo4j full-text search queries.
    Your main task is to extract core keywords from the user's request and convert them into a valid Neo4j Lucene query.

    Instructions:
    1. Extract the most relevant keywords from the user's request.
    2. Formulate a Lucene query using these keywords.
    3. Identify any common abbreviations and their full forms.
    4. Group each abbreviation and its full form using the `OR` operator, enclosed in parentheses.
    5. Combine distinct concepts or keyword groups using the `AND` operator.
    6. Make the result suitable as the `$kw` parameter of
       `CALL db.index.fulltext.queryNodes('combinedIndex', $kw)`.

    Output Format:
    A valid Lucene query.
    **CRITICAL**: Output only the query. Do not include any additional text or explanations.
    """
).strip()

prompt_push("context_extract_prompt", CONTEXT_EXTRACT_PROMPT)


def _next(query: str) -> Command[Literal["full_context_retriever"]]:
    return Command(
        goto="full_context_retriever",
        update={"context_query": query},
    )


def _last_human_message(messages: list) -> tuple[int, HumanMessage] | None:
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if isinstance(message, HumanMessage):
            return index, message
    return None


def _fallback_query(text: str) -> str:
    return escape_lucene(text[:_MAX_QUESTION].strip().lower())


async def full_context_extractor(
    state: SearchSubgraphState,
    config: RunnableConfig,
) -> Command[Literal["full_context_retriever"]]:
    """Build the Lucene query used by the full-text retriever.

    A caller-supplied ``user_question`` is already self-contained, so it is used
    directly. Otherwise the recent conversation is rewritten into a query by the
    configured search model.
    """
    user_question = (state.get("user_question") or "").strip()
    if user_question:
        return _next(_fallback_query(user_question))

    messages = state.get("messages") or []
    found = _last_human_message(messages)
    if found is None:
        raise ValueError("search subgraph needs `user_question` or a human message")

    human_index, last_message = found
    question = last_message.text.strip()
    if not question:
        raise ValueError("the last human message is empty")

    history = messages[max(0, human_index - _MAX_HISTORY) : human_index]
    filtered_history = [
        message
        for message in history
        if not isinstance(message, ToolMessage)
        and message.content
        and not message.additional_kwargs.get("tool_calls", [])
    ]

    try:
        response = await get_search_model(config).ainvoke(
            [SystemMessage(content=prompt_pull("context_extract_prompt")), *filtered_history, last_message]
        )
        context_query = response.text.strip()
        if not context_query:
            raise ValueError("the model returned an empty query")
    except Exception:
        logger.exception("Failed to extract a context query; using the raw question")
        context_query = _fallback_query(question)

    return _next(context_query)


__all__ = ["CONTEXT_EXTRACT_PROMPT", "full_context_extractor"]
