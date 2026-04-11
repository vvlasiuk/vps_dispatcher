from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

from contracts.input_message import InputMessage
from contracts.workflow_state import WorkflowState


@dataclass(slots=True)
class PluginContext:
    message: InputMessage
    current_state: WorkflowState | None


@dataclass(slots=True)
class MatchDecision:
    should_run: bool
    score: float
    reason: str
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RabbitDestination:
    exchange: str
    routing_key: str


@dataclass(slots=True)
class PluginOutput:
    payload: dict[str, Any]
    destination: RabbitDestination
    event_type: str = "result_published"


@dataclass(slots=True)
class PluginResult:
    workflow_state: WorkflowState
    outputs: list[PluginOutput] = field(default_factory=list)
    journal_events: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    stop_processing: bool = False


class MessagePlugin(ABC):
    name: str

    @abstractmethod
    def matches(self, context: PluginContext) -> MatchDecision:
        raise NotImplementedError

    @abstractmethod
    async def run(self, context: PluginContext) -> PluginResult:
        raise NotImplementedError

