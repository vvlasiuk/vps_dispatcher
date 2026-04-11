from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DownstreamTaskKind(StrEnum):
    GOOGLE_SHEETS = "google_sheets"
    ONE_C = "one_c"
    ERROR = "error"


class TaskSourceContext(BaseModel):
    system: str
    source_id: str
    chat_id: str
    user_id: str | None = None
    username: str | None = None
    group_id: str | None = None
    message_id: str


class OutboundTask(BaseModel):
    task_id: str
    task_kind: DownstreamTaskKind
    conversation_id: str
    case_id: str
    created_at: datetime
    source: TaskSourceContext
    payload: dict[str, Any] = Field(default_factory=dict)


class GoogleSheetsWriteTask(OutboundTask):
    task_kind: DownstreamTaskKind = DownstreamTaskKind.GOOGLE_SHEETS


class OneCWriteTask(OutboundTask):
    task_kind: DownstreamTaskKind = DownstreamTaskKind.ONE_C


class ErrorTask(OutboundTask):
    task_kind: DownstreamTaskKind = DownstreamTaskKind.ERROR
    error_code: str
    error_message: str
