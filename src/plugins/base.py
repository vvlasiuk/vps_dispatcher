from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal, Optional, TYPE_CHECKING

from contracts.input_message import InputMessage
from contracts.workflow_state import WorkflowState
from messaging.rabbit import RabbitMQClient

if TYPE_CHECKING:
    from messaging.rabbit import RabbitMQClient


@dataclass(slots=True)
class PluginContext:
    message: InputMessage
    current_state: WorkflowState | None
    rabbit_client: RabbitMQClient | None = None


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
    workflow_state: Optional[object] = None  # або Optional[WorkflowState] якщо імпорт залишаєш
    outputs: list[PluginOutput] = None
    # journal_events: list[tuple[str, dict]] = None
    stop_processing: bool = False


class MessagePlugin(ABC):
    name: str

    @abstractmethod
    def matches(self, context: PluginContext) -> MatchDecision:
        raise NotImplementedError

    @abstractmethod
    async def run(self, context: PluginContext) -> PluginResult:
        raise NotImplementedError

