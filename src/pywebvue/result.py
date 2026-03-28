"""Unified error codes and Result wrapper type."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


class ErrCode:
    """Framework built-in error codes.

    Format: module_code (2 digits) + error_code (3 digits).
    """

    # 00: General (00xxx)
    OK = 0
    UNKNOWN = 1
    PARAM_INVALID = 2
    NOT_IMPLEMENTED = 3
    TIMEOUT = 4
    INTERNAL_ERROR = 5

    # 01: File system (01xxx)
    FILE_NOT_FOUND = 1001
    FILE_READ_ERROR = 1002
    FILE_WRITE_ERROR = 1003
    FILE_FORMAT_INVALID = 1004
    FILE_TOO_LARGE = 1005
    PATH_NOT_ACCESSIBLE = 1006

    # 02: Process management (02xxx)
    PROCESS_START_FAILED = 2001
    PROCESS_ALREADY_RUNNING = 2002
    PROCESS_NOT_RUNNING = 2003
    PROCESS_TIMEOUT = 2004
    PROCESS_KILLED = 2005

    # 03: Network / communication (03xxx)
    API_CALL_FAILED = 3001
    API_NOT_READY = 3002

    _MSG: dict[int, str] = {
        OK: "success",
        UNKNOWN: "unknown error",
        PARAM_INVALID: "invalid parameter",
        NOT_IMPLEMENTED: "not implemented",
        TIMEOUT: "operation timeout",
        INTERNAL_ERROR: "internal error",
        FILE_NOT_FOUND: "file not found",
        FILE_READ_ERROR: "file read failed",
        FILE_WRITE_ERROR: "file write failed",
        FILE_FORMAT_INVALID: "unsupported file format",
        FILE_TOO_LARGE: "file size exceeds limit",
        PATH_NOT_ACCESSIBLE: "path not accessible",
        PROCESS_START_FAILED: "failed to start process",
        PROCESS_ALREADY_RUNNING: "process is already running",
        PROCESS_NOT_RUNNING: "no running process",
        PROCESS_TIMEOUT: "process execution timeout",
        PROCESS_KILLED: "process was killed",
        API_CALL_FAILED: "backend call failed",
        API_NOT_READY: "backend is not ready",
    }

    @classmethod
    def to_msg(cls, code: int) -> str:
        """Convert an error code to its default message."""
        return cls._MSG.get(code, "unknown error")

    @classmethod
    def is_user_error(cls, code: int) -> bool:
        """Whether the error is caused by user action (safe to show friendly message)."""
        return code in (
            cls.PARAM_INVALID,
            cls.FILE_NOT_FOUND,
            cls.FILE_FORMAT_INVALID,
            cls.FILE_TOO_LARGE,
            cls.PROCESS_ALREADY_RUNNING,
            cls.PROCESS_NOT_RUNNING,
        )


def _serialize_value(v: Any) -> Any:
    """Convert non-JSON-serializable types (Path, etc.) to string."""
    if isinstance(v, Path):
        return str(v)
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if isinstance(v, (list, tuple)):
        return [_serialize_value(item) for item in v]
    if isinstance(v, dict):
        return {str(k): _serialize_value(val) for k, val in v.items()}
    # Fallback: try JSON, otherwise str
    try:
        json.dumps(v)
        return v
    except (TypeError, ValueError):
        return str(v)


@dataclass
class Result:
    """Standard API return type. All ApiBase methods must return Result."""

    code: int
    msg: str = ""
    data: Any = None

    @classmethod
    def ok(cls, data: Any = None, msg: str = "success") -> Result:
        return cls(code=ErrCode.OK, msg=msg, data=_serialize_value(data))

    @classmethod
    def fail(cls, code: int, detail: str = "", msg: str = "") -> Result:
        return cls(
            code=code,
            msg=msg or ErrCode.to_msg(code),
            data={"detail": detail} if detail else None,
        )

    @property
    def is_ok(self) -> bool:
        return self.code == ErrCode.OK

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "msg": self.msg,
            "data": _serialize_value(self.data),
        }
