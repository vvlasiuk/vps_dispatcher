from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ai.provider import GeminiAIProvider
from common.settings import Settings
from plugins.base import MessagePlugin


@dataclass(slots=True)
class PluginRegistry:
    plugins: list[MessagePlugin]


def build_plugin_registry(settings: Settings, provider: GeminiAIProvider) -> PluginRegistry:
    factories: dict[str, Callable[[], MessagePlugin]] = {}

    try:
        from plugins.clients.sys_registry import register_client_factories
        register_client_factories(factories, settings=settings, provider=provider)
    except ImportError:
        pass

    if not factories:
        raise ValueError("No active plugins configured — sys_registry.py not found or empty")

    return PluginRegistry(plugins=[factory() for factory in factories.values()])
