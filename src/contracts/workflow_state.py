from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class WorkflowAlgorithm(StrEnum):
    UNKNOWN = "unknown"
    FORM_RECOGNITION = "form_recognition"
    TOOL_SERVICE_INTAKE = "tool_service_intake"


class WorkflowStage(StrEnum):
    WAITING_FOR_COMMAND = "waiting_for_command"
    WAITING_FOR_FORM_IMAGE = "waiting_for_form_image"
    DETECTING_FORM_TYPE = "detecting_form_type"
    EXTRACTING_FORM_DATA = "extracting_form_data"
    VALIDATING_FORM_DATA = "validating_form_data"
    WAITING_FOR_TOOL_PHOTO = "waiting_for_tool_photo"
    IDENTIFYING_TOOL = "identifying_tool"
    ASSESSING_TOOL_CONDITION = "assessing_tool_condition"
    IDENTIFYING_CUSTOMER = "identifying_customer"
    WAITING_FOR_PROBLEM_DESCRIPTION = "waiting_for_problem_description"
    READY_FOR_GOOGLE_SHEETS = "ready_for_google_sheets"
    READY_FOR_1C = "ready_for_1c"
    COMPLETED = "completed"
    ERROR = "error"


class WorkflowStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ERROR = "error"


class IdentityHints(BaseModel):
    phone_number: str | None = None
    full_name: str | None = None
    consignment_note: str | None = None
    greeted_via_hello: bool = False


class WorkflowState(BaseModel):
    conversation_id: str
    case_id: str
    source_system: str
    source_id: str
    chat_id: str
    group_id: str | None = None
    algorithm: WorkflowAlgorithm = WorkflowAlgorithm.UNKNOWN
    stage: WorkflowStage = WorkflowStage.WAITING_FOR_COMMAND
    status: WorkflowStatus = WorkflowStatus.ACTIVE
    related_document_id: str | None = None
    last_message_id: str | None = None
    identity_hints: IdentityHints = Field(default_factory=IdentityHints)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class MessageJournalEntry(BaseModel):
    event_id: str
    conversation_id: str
    case_id: str
    message_id: str
    event_type: str
    payload: dict[str, Any]
    created_at: datetime
