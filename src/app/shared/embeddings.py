import logging
import os
import threading
from dataclasses import dataclass, field

from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Embedding:
    base_url: str
    api_key: str | None
    is_binding: bool
    embedding_model_name: str
    embedding_model: Embeddings | None = None
    embedding_model_lock: threading.Lock = field(
        default_factory=threading.Lock,
        compare=False,
        repr=False,
    )

    def client_key(self) -> str:
        key = self.api_key
        if key is None and self.is_binding:
            key = os.environ.get("OPENAI_API_KEY")
            if key:
                logger.info(
                    f"No Embedding binding api key set; sending OPENAI_API_KEY to {self.base_url}."
                )
        return key or "dummy"


embedding_model_endpoint: Embedding | None = None


def embedding_binding() -> tuple[str | None, str | None]:
    return (
        os.environ.get("EMBEDDING_BINDING_HOST") or None,
        os.environ.get("EMBEDDING_BINDING_API_KEY") or None,
    )

def embedding_endpoint(model_name: str) -> Embedding | None:
    host, key = embedding_binding()
    if host:
        return Embedding(host, key, is_binding=True)
    return None
