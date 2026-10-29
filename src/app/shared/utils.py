import random
import time
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator, TypeEngine
from yaml import SafeDumper, ScalarNode


# ------ Model ------
class PypoDumper(SafeDumper):
    pass

def _str_presenter(dumper: SafeDumper, data: str) -> ScalarNode:
    if '\n' in data or len(data.splitlines()) > 1:
        lines = [line.rstrip() for line in data.splitlines()]
        data = '\n'.join(lines) + '\n'
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

PypoDumper.add_representer(str, _str_presenter)

def normalize_model_name(model_name: str) -> tuple[str, str]:
    pass

# ------ TimeZone ------
class UtcDateTime(TypeDecorator[datetime]):
    impl: TypeEngine[Any] | type[TypeEngine[Any]] = DateTime(timezone=True)
    cache_ok = True

# ------ UUID ------
class UUID(uuid.UUID):
    __slots__ = ()

    def __init__(
        self,
        hex: str | None = None,
        bytes: bytes | None = None,
        bytes_le: bytes | None = None,
        fields: tuple[int, int, int, int, int, int] | None = None,
        int: int | None = None,
        version: int | None = None,
        *,
        is_safe: uuid.SafeUUID = uuid.SafeUUID.unknown,
    ) -> None:
        if int is None or [hex, bytes, bytes_le, fields].count(None) != 4:
            return super().__init__(
                hex=hex,
                bytes=bytes,
                bytes_le=bytes_le,
                fields=fields,
                int=int,
                version=version,
                is_safe=is_safe,
            )
        if not 0 <= int < 1 << 128:
            raise ValueError("int is out of range (need a 128-bit value)")
        if version is not None:
            if not 6 <= version <= 8:
                raise ValueError("illegal version number")
            int &= ~(0xC000 << 48)
            int |= 0x8000 << 48
            int &= ~(0xF000 << 64)
            int |= version << 76
        super().__init__(int=int, is_safe=is_safe)
    
    @property
    def subsec(self) -> int:
        return ((self.int >> 64) & 0x0FFF) << 8 | ((self.int >> 54) & 0xFF)

    @property
    def time(self) -> int:
        if self.version == 6:
            return (self.time_low << 28) | (self.time_mid << 12) | (self.time_hi_version & 0x0FFF)
        if self.version == 7:
            return self.int >> 80
        return super().time
        

def uuid7(nanoseconds: int | None = None) -> UUID:
        ns = nanoseconds if nanoseconds is not None else time.time_ns()
        timestamp_ms = ns // 10**6
        uuid_int = (timestamp_ms & 0xFFFFFFFFFFFF) << 80
        uuid_int |= random.getrandbits(74)
        return UUID(int=uuid_int, version=7)
