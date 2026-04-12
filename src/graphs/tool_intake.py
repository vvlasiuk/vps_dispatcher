from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, StateGraph

from ai.provider import GeminiAIProvider
from common.settings import Settings
from contracts.ai_outputs import (
    CustomerIdentificationResult,
    ToolConditionResult,
    ToolIdentificationResult,
)
from contracts.input_message import InputMessage
from contracts.outbound_tasks import OneCWriteTask, TaskSourceContext
from contracts.workflow_state import IdentityHints, WorkflowStage, WorkflowState


class ToolIntakeGraphState(TypedDict, total=False):
    inbound: InputMessage
    workflow_state: WorkflowState
    tool_identification: ToolIdentificationResult
    tool_condition: ToolConditionResult
    customer_identification: CustomerIdentificationResult
    outbound_task: OneCWriteTask


def build_tool_intake_graph(settings: Settings, provider: GeminiAIProvider):
    graph = StateGraph(ToolIntakeGraphState)

    async def identify_tool(state: ToolIntakeGraphState) -> ToolIntakeGraphState:
        result = await provider.generate_structured(
            prompt=(
                "You identify a service tool from photos. Determine model, article number and serial number."
            ),
            response_model=ToolIdentificationResult,
            message=state["inbound"],
        )
        workflow_state = state["workflow_state"].model_copy(update={"stage": WorkflowStage.ASSESSING_TOOL_CONDITION})
        return {"tool_identification": result, "workflow_state": workflow_state}

    async def assess_condition(state: ToolIntakeGraphState) -> ToolIntakeGraphState:
        result = await provider.generate_structured(
            prompt=(
                "Assess the visible condition of the tool. Summarize condition and list visible defects."
            ),
            response_model=ToolConditionResult,
            message=state["inbound"],
        )
        workflow_state = state["workflow_state"].model_copy(update={"stage": WorkflowStage.IDENTIFYING_CUSTOMER})
        return {"tool_condition": result, "workflow_state": workflow_state}

    async def identify_customer(state: ToolIntakeGraphState) -> ToolIntakeGraphState:
        inbound = state["inbound"]
        result = await provider.generate_structured(
            prompt=(
                "Identify the customer hints from the message. Prefer phone number, full name, "
                "consignment note, or greeting context."
            ),
            response_model=CustomerIdentificationResult,
            message=inbound,
        )
        workflow_state = state["workflow_state"].model_copy(
            update={
                "stage": WorkflowStage.READY_FOR_1C,
                "identity_hints": IdentityHints(
                    phone_number=result.phone_number,
                    full_name=result.full_name,
                    consignment_note=result.consignment_note,
                    greeted_via_hello=state["workflow_state"].metadata.get(
                        "customer_context_initialized",
                        False,
                    ),
                ),
            }
        )

        task = OneCWriteTask(
            task_id=f"1c-{workflow_state.case_id}-{inbound.source.message_id}",
            conversation_id=workflow_state.conversation_id,
            case_id=workflow_state.case_id,
            created_at=workflow_state.updated_at,
            source=TaskSourceContext(
                system=inbound.source.system,
                source_id=inbound.source.source_id,
                chat_id=inbound.source.chat_id,
                user_id=inbound.source.user_id,
                username=inbound.source.username,
                group_id=inbound.source.group_id,
                message_id=inbound.source.message_id,
            ),
            payload={
                "tool": state["tool_identification"].model_dump(mode="json"),
                "condition": state["tool_condition"].model_dump(mode="json"),
                "customer": result.model_dump(mode="json"),
                "problem_description": inbound.content.text if inbound.content else None,
                "default_language": settings.default_language,
            },
        )
        return {
            "customer_identification": result,
            "workflow_state": workflow_state,
            "outbound_task": task,
        }

    graph.add_node("identify_tool", identify_tool)
    graph.add_node("assess_condition", assess_condition)
    graph.add_node("identify_customer", identify_customer)

    graph.set_entry_point("identify_tool")
    graph.add_edge("identify_tool", "assess_condition")
    graph.add_edge("assess_condition", "identify_customer")
    graph.add_edge("identify_customer", END)
    return graph.compile()
