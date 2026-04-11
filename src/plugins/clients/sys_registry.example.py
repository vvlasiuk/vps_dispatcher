from __future__ import annotations

from typing import Callable

from ai.provider import GeminiAIProvider
from common.settings import Settings
from plugins.base import MessagePlugin

# Uncomment and import only the plugins you need:
# from graphs.orchestrator import WorkflowOrchestrator
# from plugins.clients.recognize_documents import RecognizeDocumentsPlugin
# from plugins.clients.legacy_workflow import LegacyWorkflowPlugin


def register_client_factories(
    factories: dict[str, Callable[[], MessagePlugin]],
    *,
    settings: Settings,
    provider: GeminiAIProvider,
) -> None:
    # Register plugins for this deployment.
    # Copy this file to sys_registry.py and uncomment the relevant entries.

    # factories["recognize_documents"] = lambda: RecognizeDocumentsPlugin(
    #     settings=settings, provider=provider
    # )

    # orchestrator = WorkflowOrchestrator(settings, provider)
    # factories["legacy_workflow"] = lambda: LegacyWorkflowPlugin(
    #     settings=settings, orchestrator=orchestrator
    # )
    pass