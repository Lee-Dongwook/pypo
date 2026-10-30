import re
import textwrap
import logging
from typing import Literal

from langchain_core.load.dump import dumps
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from src.app.engine.search.state import SearchSubgraphState
from src.app.shared.prompts import prompt_pull, prompt_push

logger = logging.getLogger(__name__)
_LUCENE_SPECIAL = re.compile(r'([+\-!(){}\[\]^"~*?:\\/&|])')
_MAX_QUESTION = 200

context_prompt = textwrap.dedent("""\ 
    You are a specialized tool for generating Neo4j full-text search queries. \
    Your main task is to extract core keywords from the user's request and convert them into a valid Neo4j Lucene query.

    Instructions:
    1. Extract the most relevant keywords from the user's request.
    2. Formulate a Lucene query using these keywords.
    3. Identify any common abbreviations and their full forms.
    4. Group each abbreviation and its full form using the `OR` operator, enclosed in parentheses.
    5. Combine distinct concepts or keyword groups using the `AND` operator.
    6. make `$kw` part suitable for `CALL db.index.fulltext.queryNodes('combinedIndex', $kw)`


    Output Format:
    A valid Lucene query.
    **CRITICAL**: Output only the query. Do not include any additional text or explanations.
""")

prompt_push("context_extract_prompt", context_prompt)

async def full_context_extractor(
    state: SearchSubgraphState,
    config: RunnableConfig,
) -> Command[Literal["full_context_retriever"]]:
    user_question = state.get("user_question")
    if user_question:
        return Command(
            goto="full_context_retriever",
            update={
                "context_query": _LUCENE_SPECIAL.sub(r"\\\1", user_question[:_MAX_QUESTION].lower()),
            },
        )
    messages = state.get("messages", [])
    if not messages:
        raise ValueError("No messages found.")
    
    human_index = -1

    for idx, message in enumerate(reversed(messages)):
        if isinstance(message, HumanMessage):
            human_index = -1 - idx
            break
        if idx > 3 * 4:
            break
    
    last_message = messages[human_index]

    if abs(human_index) < 3:
        messages = messages[:human_index]
    
    user_query = last_message.text
    context_prompt = prompt_pull("context_extract_prompt")

    filtered_messages = [
        msg
        for msg in messages
        if not isinstance(msg, ToolMessage) and msg.content and not msg.additional_kwargs.get("tool_calls", [])
    ]

    llm = _get_model(config, "openai", "search_model")

    try:
        response = await llm.ainvoke(
            [SystemMessage(content=context_prompt)] + filtered_messages + [last_message],
            config={
                **config,
                "configurable": {
                    **config.get("configurable", {}),
                    "search_disable_streaming": True,
                },
            },
        )
        context_query = response.content
    except Exception as e: 
        logger.info(f"ERROR: Fail to get context query: {e}")
        context_query = user_query

    return Command(
        goto="full_context_retriever",
        update={         
            "context_query": context_query,   
        }
    )
