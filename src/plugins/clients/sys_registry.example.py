from __future__ import annotations

from typing import Callable

from ai.provider import GeminiAIProvider
from common.settings import Settings
from plugins.base import MessagePlugin
from plugins.clients.example_plugin.plugin import ExamplePlugin


def register_client_factories(
    factories: dict[str, Callable[[], MessagePlugin]],
    *,
    settings: Settings,
    provider: GeminiAIProvider,
) -> None:
    
    factories["example_plugin"] = lambda: ExamplePlugin(
        settings=settings,
        provider=provider,
    )

    pass