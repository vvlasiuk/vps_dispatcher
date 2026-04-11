from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from itertools import islice
from uuid import uuid4

from aio_pika import IncomingMessage

from ai.provider import GeminiAIProvider
from common.cli import build_worker_arg_parser
from common.logging import configure_logging
from common.settings import load_settings
from contracts.input_message import InputMessage
from contracts.outbound_tasks import ErrorTask, TaskSourceContext
from contracts.workflow_state import MessageJournalEntry, WorkflowStage, WorkflowStatus
from messaging.rabbit import RabbitMQClient, decode_incoming_message
from persistence.sqlite_store import SQLiteStateStore
from plugins.base import MatchDecision, MessagePlugin, PluginContext
from plugins.registry import build_plugin_registry

LOGGER = logging.getLogger(__name__)
_TEST_MODE_IN = "test_in"
_TEST_MODE_OUT = "test_out"


def _build_error_task(
    *,
    message: InputMessage,
    conversation_id: str,
    case_id: str,
    error_code: str,
    error_message: str,
) -> ErrorTask:
    return ErrorTask(
        task_id=f"err-{uuid4().hex}",
        conversation_id=conversation_id,
        case_id=case_id,
        created_at=datetime.now(timezone.utc),
        source=TaskSourceContext(
            system=message.source.system,
            source_id=message.source.source_id,
            chat_id=message.source.chat_id,
            user_id=message.source.user_id,
            username=message.source.username,
            group_id=message.source.group_id,
            message_id=message.source.message_id,
        ),
        payload={"content_kind": message.content_kind.value},
        error_code=error_code,
        error_message=error_message,
    )


async def _journal_event(
    store: SQLiteStateStore,
    *,
    conversation_id: str,
    case_id: str,
    message_id: str,
    event_type: str,
    payload: dict,
) -> None:
    await store.append_journal(
        MessageJournalEntry(
            event_id=uuid4().hex,
            conversation_id=conversation_id,
            case_id=case_id,
            message_id=message_id,
            event_type=event_type,
            payload=payload,
            created_at=datetime.now(timezone.utc),
        )
    )


def _select_plugins(
    matched_plugins: list[tuple[MessagePlugin, MatchDecision]],
    policy: str,
) -> list[tuple[MessagePlugin, MatchDecision]]:
    if not matched_plugins:
        return []

    normalized_policy = policy.strip().lower()
    if normalized_policy == "first_match":
        return [matched_plugins[0]]
    if normalized_policy == "multi_cast":
        return matched_plugins

    best = max(matched_plugins, key=lambda item: item[1].score)
    return [best]


def _build_conversation_id(message: InputMessage) -> str:
    return ":".join(
        [
            message.source.system,
            message.source.source_id,
            message.source.chat_id,
        ]
    )


def _extract_test_tags(payload: dict) -> tuple[str | None, str | None]:
    test_mode = payload.get("test_mode")
    test_id = payload.get("test_id")

    normalized_mode = test_mode if isinstance(test_mode, str) else None
    normalized_id = str(test_id) if test_id is not None else None
    return normalized_mode, normalized_id


def _apply_test_out_tags(payload: dict, test_id: str | None) -> dict:
    tagged_payload = dict(payload)
    tagged_payload["test_mode"] = _TEST_MODE_OUT
    if test_id is not None:
        tagged_payload["test_id"] = test_id
    return tagged_payload


async def run_dispatcher(env_file: str | None) -> None:
    settings = load_settings(env_file)
    configure_logging(settings)

    input_rabbit = RabbitMQClient(settings, role="input")
    output_rabbit = RabbitMQClient(settings, role="output")
    store = SQLiteStateStore(str(settings.sqlite_path))
    provider = GeminiAIProvider(settings)
    registry = build_plugin_registry(settings, provider)

    await store.initialize()
    await input_rabbit.connect()
    await output_rabbit.connect()

    async def handle_message(incoming: IncomingMessage) -> None:
        payload = decode_incoming_message(incoming)
        LOGGER.info("received_message")
        input_test_mode, input_test_id = _extract_test_tags(payload)

        if input_test_mode == _TEST_MODE_OUT:
            LOGGER.info("skip_test_out_message")
            await incoming.reject(requeue=True)
            return

        try:
            message = InputMessage.model_validate(payload)
        except Exception as exc:
            LOGGER.exception("invalid_input_payload")
            await incoming.ack()
            return

        current_state = await store.get_active_state(
            source_system=message.source.system,
            source_id=message.source.source_id,
            chat_id=message.source.chat_id,
        )
        fallback_conversation_id = _build_conversation_id(message)
        fallback_case_id = current_state.case_id if current_state else uuid4().hex
        message_received_journaled = False
        plugin_context = PluginContext(message=message, current_state=current_state)
        matched_plugins: list[tuple[MessagePlugin, MatchDecision]] = []
        for plugin in registry.plugins:
            match = plugin.matches(plugin_context)
            if match.should_run:
                matched_plugins.append((plugin, match))

        selected_plugins = _select_plugins(matched_plugins, settings.plugin_execution_policy)
        if settings.plugin_execution_policy.strip().lower() == "multi_cast":
            selected_plugins = list(islice(selected_plugins, max(settings.plugin_max_selected_plugins, 1)))

        if not selected_plugins:
            LOGGER.warning("no_plugin_selected")
            await incoming.ack()
            return

        try:
            for plugin, match in selected_plugins:
                plugin_result = await plugin.run(plugin_context)
                final_state = plugin_result.workflow_state.model_copy(update={"updated_at": datetime.now(timezone.utc)})
                await store.upsert_state(final_state)
                plugin_context = PluginContext(message=message, current_state=final_state)

                if not message_received_journaled:
                    await _journal_event(
                        store,
                        conversation_id=final_state.conversation_id,
                        case_id=final_state.case_id,
                        message_id=message.source.message_id,
                        event_type="message_received",
                        payload=payload,
                    )
                    message_received_journaled = True

                for event_type, event_payload in plugin_result.journal_events:
                    await _journal_event(
                        store,
                        conversation_id=final_state.conversation_id,
                        case_id=final_state.case_id,
                        message_id=message.source.message_id,
                        event_type=event_type,
                        payload=event_payload,
                    )

                for output in plugin_result.outputs:
                    output_payload = output.payload
                    if input_test_mode == _TEST_MODE_IN:
                        output_payload = _apply_test_out_tags(output.payload, input_test_id)

                    if output_payload.get("test_mode") == _TEST_MODE_OUT:
                        exchange_name = (
                            settings.output_test_rabbitmq_exchange.strip()
                            or output.destination.exchange
                        )
                        routing_key = (
                            settings.output_test_rabbitmq_routing_key.strip()
                            or output.destination.routing_key
                        )
                    else:
                        exchange_name = output.destination.exchange
                        routing_key = output.destination.routing_key

                    await output_rabbit.publish_json(
                        output_payload,
                        exchange_name=exchange_name,
                        routing_key=routing_key,
                    )
                    LOGGER.info(
                        "plugin_output_published plugin=%s exchange=%s routing_key=%s",
                        plugin.name,
                        exchange_name,
                        routing_key,
                    )
                    await _journal_event(
                        store,
                        conversation_id=final_state.conversation_id,
                        case_id=final_state.case_id,
                        message_id=message.source.message_id,
                        event_type=output.event_type,
                        payload=output_payload,
                    )

                if not plugin_result.outputs:
                    LOGGER.info("plugin_executed_without_output plugin=%s", plugin.name)

                LOGGER.info(
                    "plugin_executed plugin=%s score=%s reason=%s",
                    plugin.name,
                    match.score,
                    match.reason,
                )

                if final_state.status != WorkflowStatus.ERROR and final_state.stage == WorkflowStage.COMPLETED:
                    await store.upsert_state(final_state.model_copy(update={"status": WorkflowStatus.COMPLETED}))

                if plugin_result.stop_processing:
                    LOGGER.info("plugin_requested_stop plugin=%s", plugin.name)
                    break

            await incoming.ack()
        except Exception as exc:
            LOGGER.exception("message_processing_failed")
            state_for_error = plugin_context.current_state
            conversation_id = fallback_conversation_id
            case_id = fallback_case_id
            if state_for_error is not None:
                failed_state = state_for_error.model_copy(
                    update={
                        "stage": WorkflowStage.ERROR,
                        "status": WorkflowStatus.ERROR,
                        "updated_at": datetime.now(timezone.utc),
                    }
                )
                await store.upsert_state(failed_state)
                conversation_id = failed_state.conversation_id
                case_id = failed_state.case_id
                error_task = _build_error_task(
                    message=message,
                    conversation_id=conversation_id,
                    case_id=case_id,
                    error_code="message_processing_failed",
                    error_message=str(exc),
                )
            else:
                error_task = _build_error_task(
                    message=message,
                    conversation_id=conversation_id,
                    case_id=case_id,
                    error_code="message_processing_failed",
                    error_message=str(exc),
                )

            await _journal_event(
                store,
                conversation_id=conversation_id,
                case_id=case_id,
                message_id=message.source.message_id,
                event_type="message_processing_failed",
                payload=error_task.model_dump(mode="json"),
            )
            LOGGER.error("message_processing_failed: %s", error_task)
            await incoming.reject(requeue=False)

    await input_rabbit.consume(settings.rabbitmq_queue, handle_message)
    LOGGER.info("dispatcher_started")
    try:
        await asyncio.Future()
    finally:
        await input_rabbit.close()
        await output_rabbit.close()


def main() -> None:
    parser = build_worker_arg_parser("RabbitMQ dispatcher")
    args = parser.parse_args()
    asyncio.run(run_dispatcher(args.env_file))


if __name__ == "__main__":
    main()


