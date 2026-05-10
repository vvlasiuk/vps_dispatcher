from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_env_file(cli_env_file: str | None) -> Path | None:
    if cli_env_file:
        return Path(cli_env_file)

    env_override = os.getenv("APP_ENV_FILE")
    if env_override:
        return Path(env_override)

    local_env = Path.cwd() / ".env"
    if local_env.exists():
        return local_env

    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    app_name: str = Field(default="input-messages-dispatcher", alias="APP_NAME")
    rabbitmq_host: str = Field(default="localhost", alias="RABBITMQ_HOST")
    rabbitmq_port: int = Field(default=5672, alias="RABBITMQ_PORT")
    rabbitmq_user: str = Field(default="guest", alias="RABBITMQ_USER")
    rabbitmq_password: str = Field(default="guest", alias="RABBITMQ_PASSWORD")
    rabbitmq_vhost: str = Field(alias="RABBITMQ_VHOST")
    rabbitmq_exchange: str = Field(alias="RABBITMQ_EXCHANGE")
    rabbitmq_exchange_type: str = Field(default="direct", alias="RABBITMQ_EXCHANGE_TYPE")
    rabbitmq_queue: str = Field(alias="RABBITMQ_QUEUE")
    rabbitmq_routing_key: str = Field(alias="RABBITMQ_ROUTING_KEY")
    output_rabbitmq_host: str = Field(default="localhost", alias="OUTPUT_RABBITMQ_HOST")
    output_rabbitmq_port: int = Field(default=5672, alias="OUTPUT_RABBITMQ_PORT")
    output_rabbitmq_user: str = Field(default="guest", alias="OUTPUT_RABBITMQ_USER")
    output_rabbitmq_password: str = Field(default="guest", alias="OUTPUT_RABBITMQ_PASSWORD")
    output_rabbitmq_vhost: str = Field(default="output_messages", alias="OUTPUT_RABBITMQ_VHOST")
    output_rabbitmq_exchange: str = Field(
        default="output_messages_exchange",
        alias="OUTPUT_RABBITMQ_EXCHANGE",
    )
    output_rabbitmq_exchange_type: str = Field(default="direct", alias="OUTPUT_RABBITMQ_EXCHANGE_TYPE")
    output_rabbitmq_queue: str = Field(default="output_messages.queue", alias="OUTPUT_RABBITMQ_QUEUE")
    output_rabbitmq_routing_key: str = Field(
        default="output_messages.queue",
        alias="OUTPUT_RABBITMQ_ROUTING_KEY",
    )
    output_test_rabbitmq_exchange: str = Field(alias="OUTPUT_TEST_RABBITMQ_EXCHANGE")
    output_test_rabbitmq_routing_key: str = Field(alias="OUTPUT_TEST_RABBITMQ_ROUTING_KEY")
    rabbitmq_heartbeat_seconds: int = Field(default=60, alias="RABBITMQ_HEARTBEAT_SECONDS")
    rabbitmq_blocked_connection_timeout_seconds: int = Field(
        default=300,
        alias="RABBITMQ_BLOCKED_CONNECTION_TIMEOUT_SECONDS",
    )
    rabbitmq_prefetch_count: int = Field(default=10, alias="RABBITMQ_PREFETCH_COUNT")
    sqlite_path: Path = Field(alias="SQLITE_PATH")
    log_file_path: Path = Field(alias="LOG_FILE_PATH")
    log_max_bytes: int = Field(default=1_048_576, alias="LOG_MAX_BYTES")
    log_backup_count: int = Field(default=5, alias="LOG_BACKUP_COUNT")
    gemini_model: str = Field(default="gemini-2.0-flash", alias="GEMINI_MODEL")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    google_api_version: str = Field(default="", alias="GOOGLE_API_VERSION")
    ai_confidence_threshold: float = Field(default=0.7, alias="AI_CONFIDENCE_THRESHOLD")
    default_language: str = Field(default="uk", alias="DEFAULT_LANGUAGE")
    workflow_one_active_case_per_chat: bool = Field(
        default=True,
        alias="WORKFLOW_ONE_ACTIVE_CASE_PER_CHAT",
    )
    plugin_execution_policy: str = Field(default="highest_score", alias="PLUGIN_EXECUTION_POLICY")
    plugin_max_selected_plugins: int = Field(default=2, alias="PLUGIN_MAX_SELECTED_PLUGINS")
    temp_files_dir: Path = Field(default="temp_files", alias="TEMP_FILES_DIR")

    # === API SERVER ===
    api_server_host: str = Field(default="", alias="API_SERVER_HOST")
    api_server_port: int = Field(default=0, alias="API_SERVER_PORT")
    api_access_token: str = Field(default="", alias="API_ACCESS_TOKEN")


@lru_cache(maxsize=8)
def load_settings(cli_env_file: str | None = None) -> Settings:
    env_file = _resolve_env_file(cli_env_file)
    kwargs = {"_env_file": env_file} if env_file else {}
    settings = Settings(**kwargs)
    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    settings.log_file_path.parent.mkdir(parents=True, exist_ok=True)
    settings.temp_files_dir.mkdir(parents=True, exist_ok=True)
    return settings
