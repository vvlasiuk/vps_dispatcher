from dataclasses import dataclass
from ai.provider import GeminiAIProvider
from common.settings import Settings
from plugins.base import MessagePlugin, PluginContext, PluginResult, MatchDecision, PluginOutput, RabbitDestination
from contracts.input_message import InputMessage
from contracts.workflow_state import WorkflowState, WorkflowAlgorithm, WorkflowStage, WorkflowStatus
import json
from pathlib import Path
import logging


_RESOURCES_DIR = Path(__file__).parent / "resources"
_KEYBOARD_PATH = _RESOURCES_DIR / "keyboard.json"
_OUTPUT_EXCHANGE = "output_telegram.events"
_OUTPUT_ROUTING_KEY = "output_telegram.events"
_LOGGER = logging.getLogger(__name__)

@dataclass(slots=True)
class ExamplePlugin(MessagePlugin):
    settings: Settings
    provider: GeminiAIProvider
    name: str = "example_plugin"


    def matches(self, context: PluginContext) -> MatchDecision:
        """
        Визначає, чи повинен цей плагін обробляти поточне повідомлення (контекст).
        
        Завдання:
        - Аналізувати вхідний контекст (наприклад, текст, команду, теги, тип джерела тощо).
        - Повернути MatchDecision з should_run=True, якщо плагін підходить для обробки цього повідомлення.
        - Вказати score (оцінку релевантності) та reason (пояснення рішення).
        - Дозволяє фреймворку автоматично вибирати відповідний плагін для кожного повідомлення.
        
        У цьому шаблоні — заглушка, яка завжди повертає should_run=True.
        """
        return MatchDecision(
            should_run=True,
            score=0.0,
            reason="example_plugin_stub"
        )

    async def run(self, context: PluginContext) -> PluginResult:
        """
        Основний метод виконання плагіна.
        
        Завдання:
        - Реалізувати бізнес-логіку для обробки повідомлення, якщо matches повернув should_run=True.
        - Може виконувати асинхронні операції (запити до AI, БД, зовнішніх API тощо).
        - Формує та повертає PluginResult з результатами обробки (outputs, journal_events, workflow_state тощо).
        
        У цьому шаблоні — заглушка без логіки.
        """
        message = context.message
        state = context.current_state or self._make_state(message)

        # --- Обробка /start ---
        if message.content and message.content.text and message.content.text.strip() == "/start":
            return self._handle_start(message, state)
        # --- Кінець блоку /start ---

        # --- Шаблон для інших команд (розширюйте тут) ---
        # if message.content and message.content.text and message.content.text.strip() == "/help":
        #     return self._handle_help(message, state)
        # --- Кінець шаблону ---

        return PluginResult(workflow_state=state)

    def _handle_start(self, message: InputMessage, state: WorkflowState) -> PluginResult:
        """
        Обробляє команду /start: повертає клавіатуру для користувача.
        """
        try:
            keyboard = json.loads(_KEYBOARD_PATH.read_text(encoding="utf-8"))
            if not isinstance(keyboard, dict) or "keyboard" not in keyboard:
                _LOGGER.warning("keyboard.json має некоректну структуру: %s", keyboard)
                keyboard = {"keyboard": [["/start"]], "resize_keyboard": True}
        except Exception as e:
            _LOGGER.error("Не вдалося зчитати keyboard.json: %s", e)
            keyboard = {"keyboard": [["/start"]], "resize_keyboard": True}

        payload = {
            "destination": {
                "system": message.source.system,
                "chat_id": message.source.chat_id,
            },
            "keyboard": keyboard,
        }
        return PluginResult(
            workflow_state=state,
            outputs=[
                PluginOutput(
                    payload=payload,
                    destination=RabbitDestination(
                        exchange=_OUTPUT_EXCHANGE,
                        routing_key=_OUTPUT_ROUTING_KEY,
                    ),
                    event_type="keyboard_sent",
                )
            ],
            journal_events=[
                ("keyboard_sent", {"destination": payload["destination"], "content": keyboard}),
            ],
            stop_processing=True,
        )

    def _make_state(self, message: InputMessage) -> WorkflowState:
        """
        Створює новий WorkflowState для повідомлення (аналогічно іншим плагінам).
        """
        from datetime import datetime, timezone
        from uuid import uuid4
        now = datetime.now(timezone.utc)
        return WorkflowState(
            conversation_id=":".join([
                message.source.system,
                message.source.source_id,
                message.source.chat_id,
            ]),
            case_id=uuid4().hex,
            source_system=message.source.system,
            source_id=message.source.source_id,
            chat_id=message.source.chat_id,
            group_id=message.source.group_id,
            algorithm=WorkflowAlgorithm.UNKNOWN,
            stage=WorkflowStage.COMPLETED,
            status=WorkflowStatus.COMPLETED,
            last_message_id=message.source.message_id,
            created_at=now,
            updated_at=now,
        )

