from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StartSolveRequest:
    task: str
    repo_path: str | None = None
    options: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "StartSolveRequest":
        if not isinstance(payload, dict):
            raise TypeError("StartSolveRequest payload must be an object")
        task = payload.get("task")
        if not task:
            raise ValueError("StartSolveRequest.task is required")
        repo_path = payload.get("repo_path")
        options = payload.get("options")
        if options is not None and not isinstance(options, dict):
            raise TypeError("StartSolveRequest.options must be an object if provided")
        return cls(task=str(task), repo_path=repo_path, options=options)


class Event:
    def __init__(self, event: str, **fields: Any) -> None:
        self.event = event
        self._fields = fields

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"event": self.event}
        for key, value in self._fields.items():
            if value is None:
                continue
            data[key] = value
        return data

