from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from contracts.input_message import ContentKind, InputMessage
from contracts.workflow_state import WorkflowAlgorithm, WorkflowStage, WorkflowState, WorkflowStatus


KNOWN_COMMANDS: dict[str, WorkflowAlgorithm] = {
    "hello": WorkflowAlgorithm.TOOL_SERVICE_INTAKE,
    "start_form_recognition": WorkflowAlgorithm.FORM_RECOGNITION,
    "start_tool_intake": WorkflowAlgorithm.TOOL_SERVICE_INTAKE,
}


@dataclass(slots=True)
class RouteDecision:
    algorithm: WorkflowAlgorithm
    next_stage: WorkflowStage
    command: str | None
    reason: str


def build_conversation_id(message: InputMessage) -> str:
    return ":".join(
        [
            message.source.system,
            message.source.source_id,
            message.source.chat_id,
        ]
    )


def build_case_id() -> str:
    return uuid4().hex


def create_initial_state(message: InputMessage, decision: RouteDecision) -> WorkflowState:
    now = datetime.now(timezone.utc)
    metadata = {
        "routing_reason": decision.reason,
        "content_kind": message.content_kind.value,
    }
    if decision.command == "hello":
        metadata["customer_context_initialized"] = True

    return WorkflowState(
        conversation_id=build_conversation_id(message),
        case_id=build_case_id(),
        source_system=message.source.system,
        source_id=message.source.source_id,
        chat_id=message.source.chat_id,
        group_id=message.source.group_id,
        algorithm=decision.algorithm,
        stage=decision.next_stage,
        status=WorkflowStatus.ACTIVE,
        last_message_id=message.source.message_id,
        metadata=metadata,
        created_at=now,
        updated_at=now,
    )


def classify_message(message: InputMessage, current_state: WorkflowState | None) -> RouteDecision:
    command = message.command
    if command in KNOWN_COMMANDS:
        algorithm = KNOWN_COMMANDS[command]
        if command == "hello":
            return RouteDecision(
                algorithm=algorithm,
                next_stage=WorkflowStage.WAITING_FOR_TOOL_PHOTO,
                command=command,
                reason="recognized_command",
            )
        if algorithm == WorkflowAlgorithm.FORM_RECOGNITION:
            return RouteDecision(
                algorithm=algorithm,
                next_stage=WorkflowStage.WAITING_FOR_FORM_IMAGE,
                command=command,
                reason="recognized_command",
            )
        return RouteDecision(
            algorithm=algorithm,
            next_stage=WorkflowStage.WAITING_FOR_TOOL_PHOTO,
            command=command,
            reason="recognized_command",
        )

    if current_state and current_state.status == WorkflowStatus.ACTIVE:
        return RouteDecision(
            algorithm=current_state.algorithm,
            next_stage=current_state.stage,
            command=command,
            reason="resume_active_state",
        )

    if message.source.group_id:
        return RouteDecision(
            algorithm=WorkflowAlgorithm.FORM_RECOGNITION,
            next_stage=WorkflowStage.WAITING_FOR_FORM_IMAGE,
            command=command,
            reason="group_context_default",
        )

    if message.content_kind == ContentKind.PHOTO:
        return RouteDecision(
            algorithm=WorkflowAlgorithm.TOOL_SERVICE_INTAKE,
            next_stage=WorkflowStage.IDENTIFYING_TOOL,
            command=command,
            reason="photo_default_tool_intake",
        )

    text = (message.content.text if message.content and message.content.text else "").lower()
    if any(keyword in text for keyword in ("бланк", "форма", "form")):
        return RouteDecision(
            algorithm=WorkflowAlgorithm.FORM_RECOGNITION,
            next_stage=WorkflowStage.WAITING_FOR_FORM_IMAGE,
            command=command,
            reason="text_keyword_form",
        )

    if any(keyword in text for keyword in ("ремонт", "інструмент", "service")):
        return RouteDecision(
            algorithm=WorkflowAlgorithm.TOOL_SERVICE_INTAKE,
            next_stage=WorkflowStage.WAITING_FOR_TOOL_PHOTO,
            command=command,
            reason="text_keyword_tool_service",
        )

    return RouteDecision(
        algorithm=WorkflowAlgorithm.UNKNOWN,
        next_stage=WorkflowStage.ERROR,
        command=command,
        reason="unsupported_message",
    )
