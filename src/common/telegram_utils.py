from plugins.base import PluginOutput, RabbitDestination

_OUTPUT_EXCHANGE = "output_telegram.events"
_OUTPUT_ROUTING_KEY = "output_telegram.events"

class TelegramUtils:
    @staticmethod
    def emoji_output(emoji: str, chat_id, msg_id, event_type="emoji_sent"):
        return PluginOutput(
            payload={
                "type": "emoji",
                "content": emoji,
                "destination": {
                    "chat_id": chat_id,
                    "message_id": msg_id,
                },
            },
            destination=RabbitDestination(
                exchange=_OUTPUT_EXCHANGE,
                routing_key=_OUTPUT_ROUTING_KEY,
            ),
            event_type=event_type,
        )

    @staticmethod
    def file_output(file_path: str, chat_id, caption=None, event_type="file_sent"):
        return PluginOutput(
            payload={
                "destination": {
                    "system": "telegram",
                    "chat_id": chat_id #tr(getattr(message.source, "user_id", None) or message.source.chat_id),
                },
                "type": "file",
                "file_path": file_path,
                "caption": caption or "",
            },
            destination=RabbitDestination(
                exchange=_OUTPUT_EXCHANGE,
                routing_key=_OUTPUT_ROUTING_KEY,
            ),
            event_type=event_type,
        )

    @staticmethod
    def text_output(text: str, chat_id, caption=None, event_type="text_sent"):
        return PluginOutput(
            payload={
                "destination": {
                    "system": "telegram",
                    "chat_id": chat_id,
                },
                "type": "text",
                "content": text,
                "caption": caption or "",
            },
            destination=RabbitDestination(
                exchange=_OUTPUT_EXCHANGE,
                routing_key=_OUTPUT_ROUTING_KEY,
            ),
            event_type=event_type,
        )