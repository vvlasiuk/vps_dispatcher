from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, StateGraph

from ai.provider import GeminiAIProvider
from common.settings import Settings
from contracts.ai_outputs import FormExtractionResult, FormTypeDetection
from contracts.input_message import InputMessage
from contracts.outbound_tasks import GoogleSheetsWriteTask, TaskSourceContext
from contracts.workflow_state import WorkflowStage, WorkflowState


class FormRecognitionGraphState(TypedDict, total=False):
    inbound: InputMessage
    workflow_state: WorkflowState
    form_type_detection: FormTypeDetection
    extraction: FormExtractionResult
    validated_payload: dict[str, object]
    outbound_task: GoogleSheetsWriteTask


def build_form_recognition_graph(settings: Settings, provider: GeminiAIProvider):
    graph = StateGraph(FormRecognitionGraphState)

    async def detect_form_type(state: FormRecognitionGraphState) -> FormRecognitionGraphState:
        result = await provider.generate_structured(
            prompt=(
                "You classify document images. Determine the form type and return a concise type name."
            ),
            response_model=FormTypeDetection,
            message=state["inbound"],
        )
        workflow_state = state["workflow_state"].model_copy(
            update={
                "stage": WorkflowStage.EXTRACTING_FORM_DATA,
                "metadata": {
                    **state["workflow_state"].metadata,
                    "detected_form_type": result.form_type,
                },
            }
        )
        return {"form_type_detection": result, "workflow_state": workflow_state}

    async def extract_form_data(state: FormRecognitionGraphState) -> FormRecognitionGraphState:
        detection = state["form_type_detection"]
        result = await provider.generate_structured(
            prompt=(
                f"Extract structured JSON fields for the form type '{detection.form_type}'. "
                "Return recognized field values and suggested tags."
            ),
            response_model=FormExtractionResult,
            message=state["inbound"],
        )
        workflow_state = state["workflow_state"].model_copy(
            update={
                "stage": WorkflowStage.VALIDATING_FORM_DATA,
                "metadata": {
                    **state["workflow_state"].metadata,
                    "raw_extracted_form_data": result.extracted_data,
                },
            }
        )
        return {"extraction": result, "workflow_state": workflow_state}

    async def validate_extraction(state: FormRecognitionGraphState) -> FormRecognitionGraphState:
        extraction = state["extraction"]
        if not extraction.extracted_data:
            raise ValueError("Extracted form data is empty")

        validated_payload = {
            "form_type": extraction.form_type,
            "recognized_data": extraction.extracted_data,
            "language": state["inbound"].content.language or settings.default_language,
        }
        workflow_state = state["workflow_state"].model_copy(
            update={
                "stage": WorkflowStage.READY_FOR_GOOGLE_SHEETS,
                "metadata": {
                    **state["workflow_state"].metadata,
                    "extracted_form_data": extraction.extracted_data,
                },
            }
        )
        task = GoogleSheetsWriteTask(
            task_id=f"gs-{workflow_state.case_id}-{state['inbound'].source.message_id}",
            conversation_id=workflow_state.conversation_id,
            case_id=workflow_state.case_id,
            created_at=workflow_state.updated_at,
            source=TaskSourceContext(
                system=state["inbound"].source.system,
                source_id=state["inbound"].source.source_id,
                chat_id=state["inbound"].source.chat_id,
                user_id=state["inbound"].source.user_id,
                username=state["inbound"].source.username,
                group_id=state["inbound"].source.group_id,
                message_id=state["inbound"].source.message_id,
            ),
            payload=validated_payload,
        )
        return {
            "validated_payload": validated_payload,
            "outbound_task": task,
            "workflow_state": workflow_state,
        }

    graph.add_node("detect_form_type", detect_form_type)
    graph.add_node("extract_form_data", extract_form_data)
    graph.add_node("validate_extraction", validate_extraction)

    graph.set_entry_point("detect_form_type")
    graph.add_edge("detect_form_type", "extract_form_data")
    graph.add_edge("extract_form_data", "validate_extraction")
    graph.add_edge("validate_extraction", END)
    return graph.compile()

