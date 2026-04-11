from __future__ import annotations

from dataclasses import dataclass

from ai.provider import GeminiAIProvider
from common.settings import Settings
from contracts.input_message import InputMessage
from contracts.outbound_tasks import GoogleSheetsWriteTask, OneCWriteTask, OutboundTask
from contracts.workflow_state import WorkflowAlgorithm, WorkflowState
from graphs.form_recognition import build_form_recognition_graph
from graphs.tool_intake import build_tool_intake_graph


@dataclass(slots=True)
class OrchestrationResult:
    workflow_state: WorkflowState
    outbound_task: OutboundTask | None


class WorkflowOrchestrator:
    def __init__(self, settings: Settings, provider: GeminiAIProvider) -> None:
        self._form_graph = build_form_recognition_graph(settings, provider)
        self._tool_graph = build_tool_intake_graph(settings, provider)

    async def run(self, message: InputMessage, state: WorkflowState) -> OrchestrationResult:
        graph_state = {
            "inbound": message,
            "workflow_state": state,
        }

        if state.algorithm == WorkflowAlgorithm.FORM_RECOGNITION:
            result = await self._form_graph.ainvoke(graph_state)
        elif state.algorithm == WorkflowAlgorithm.TOOL_SERVICE_INTAKE:
            result = await self._tool_graph.ainvoke(graph_state)
        else:
            return OrchestrationResult(workflow_state=state, outbound_task=None)

        task = result.get("outbound_task")
        if task and not isinstance(task, (GoogleSheetsWriteTask, OneCWriteTask)):
            raise TypeError("Workflow returned unsupported outbound task type")
        return OrchestrationResult(
            workflow_state=result["workflow_state"],
            outbound_task=task,
        )
