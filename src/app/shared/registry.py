from __future__ import annotations

from sqlalchemy import event

from .utils import uuid7


class UnifiedResourceType:
    AGENT = "agent"

def new_uuid() -> str:
    return str(uuid7())

class AutoUUIDMixin:
    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)

        @event.listens_for(cls, "init")
        def _auto_uuid(target: AutoUUIDMixin, args: tuple, kwargs: dict) -> None:
            if not kwargs.get("uuid"):
                kwargs["uuid"] = new_uuid()

class RegistryMixin(AutoUUIDMixin):
    __registry_type__: str
