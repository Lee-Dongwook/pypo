import copy
from sqlalchemy import inspect

from ..model import Agent
from ..schemas import AgentResponse

def _bakes_an_identity(agent_model: Agent | AgentResponse) -> bool:
    return not agent_model.workflow

def _build_copy(agent_model: Agent | AgentResponse) -> Agent | AgentResponse:
     state = inspect(agent_model, raiseerr=False)
     if state is None:
        return copy.copy(agent_model)
     columns = {attr.key for attr in state.mapper.column_attrs}
     row_copy: Agent = state.mapper.class_(**{key: value for key, value in state.dict.items() if key in columns})
     return row_copy
