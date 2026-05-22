from plugins.base import PluginOutput, RabbitDestination
# import requests

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
    def text_output(
        text: str, 
        chat_id, 
        caption=None, 
        reply_markup: dict | None = None, 
        event_type="text_sent",
        global_msg_id=None,
    ):
        return PluginOutput(
            payload={
                "destination": {
                    "system": "telegram",
                    "chat_id": chat_id,
                },
                "type": "text",
                "content": text,
                "caption": caption or "",
                "global_msg_id": global_msg_id,
                **({"reply_markup": reply_markup} if reply_markup is not None else {}),
            },
            destination=RabbitDestination(
                exchange=_OUTPUT_EXCHANGE,
                routing_key=_OUTPUT_ROUTING_KEY,
            ),
            event_type=event_type,
        )

    @staticmethod
    def edit_text_output(chat_id, message_id, text: str, event_type="text_edited"):
        return PluginOutput(
            payload={
                "type": "edit_text",
                "content": text,
                "destination": {
                    "chat_id": chat_id,
                    "message_id": message_id,
                },
            },
            destination=RabbitDestination(
                exchange=_OUTPUT_EXCHANGE,
                routing_key=_OUTPUT_ROUTING_KEY,
            ),
            event_type=event_type,
        )

    # def read_global_message_telegram(self, global_msg_id: int = None) -> Optional[list]:
    #     if not self._is_configured():
    #         logging.warning("API parameters are missing. Cannot read global_message_telegram.")
    #         return None
    #     url = f"{self.url}/global_message_telegram/"
    #     headers = {
    #         "Authorization": f"Bearer {self.master_token}",
    #         "Content-Type": "application/json"
    #     }
    #     params = {}
    #     if global_msg_id is not None:
    #         params["global_msg_id"] = global_msg_id
    #     try:
    #         response = requests.get(url, headers=headers, params=params, timeout=10, verify=True)
    #         response.raise_for_status()
    #         return response.json()
    #     except Exception as e:
    #         logging.error(f"Failed to read global_message_telegram: {e}")
    #         return None