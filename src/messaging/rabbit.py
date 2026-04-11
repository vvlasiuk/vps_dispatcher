from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import aio_pika
from aio_pika import ExchangeType, IncomingMessage, Message, RobustChannel, RobustConnection

from common.settings import Settings


@dataclass(slots=True)
class RabbitTopology:
    main_exchange: str
    main_exchange_type: ExchangeType
    queue: str
    routing_key: str


class RabbitMQClient:
    def __init__(self, settings: Settings, *, role: str = "input") -> None:
        self._settings = settings
        self._role = role
        self._connection: RobustConnection | None = None
        self._channel: RobustChannel | None = None

        if role == "output":
            self._host = settings.output_rabbitmq_host
            self._port = settings.output_rabbitmq_port
            self._user = settings.output_rabbitmq_user
            self._password = settings.output_rabbitmq_password
            self._vhost = settings.output_rabbitmq_vhost
            self.topology = RabbitTopology(
                main_exchange=settings.output_rabbitmq_exchange,
                main_exchange_type=ExchangeType(settings.output_rabbitmq_exchange_type),
                queue=settings.output_rabbitmq_queue,
                routing_key=settings.output_rabbitmq_routing_key,
            )
        else:
            self._host = settings.rabbitmq_host
            self._port = settings.rabbitmq_port
            self._user = settings.rabbitmq_user
            self._password = settings.rabbitmq_password
            self._vhost = settings.rabbitmq_vhost
            self.topology = RabbitTopology(
                main_exchange=settings.rabbitmq_exchange,
                main_exchange_type=ExchangeType(settings.rabbitmq_exchange_type),
                queue=settings.rabbitmq_queue,
                routing_key=settings.rabbitmq_routing_key,
            )

    async def connect(self) -> None:
        user = quote(self._user, safe="")
        password = quote(self._password, safe="")
        host = self._host
        port = self._port
        vhost = quote(self._vhost, safe="")
        heartbeat = self._settings.rabbitmq_heartbeat_seconds
        blocked_timeout = self._settings.rabbitmq_blocked_connection_timeout_seconds
        connection_url = (
            f"amqp://{user}:{password}@{host}:{port}/{vhost}"
            f"?heartbeat={heartbeat}&blocked_connection_timeout={blocked_timeout}"
        )
        self._connection = await aio_pika.connect_robust(connection_url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=self._settings.rabbitmq_prefetch_count)

    async def close(self) -> None:
        if self._channel and not self._channel.is_closed:
            await self._channel.close()
        if self._connection and not self._connection.is_closed:
            await self._connection.close()

    async def consume(self, queue_name: str, callback: Any) -> None:
        channel = self._require_channel()
        queue = await channel.get_queue(queue_name, ensure=True)
        await queue.consume(callback)

    async def publish_json(self, payload: dict[str, Any], *, exchange_name: str, routing_key: str) -> None:
        channel = self._require_channel()
        exchange = await channel.get_exchange(exchange_name)
        await exchange.publish(self._build_message(payload), routing_key=routing_key)

    def _require_channel(self) -> RobustChannel:
        if self._channel is None:
            raise RuntimeError("RabbitMQ channel is not initialized")
        return self._channel

    @staticmethod
    def _build_message(payload: dict[str, Any]) -> Message:
        return Message(
            body=json.dumps(payload, ensure_ascii=True, default=str).encode("utf-8"),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )


def decode_incoming_message(message: IncomingMessage) -> dict[str, Any]:
    return json.loads(message.body.decode("utf-8"))
