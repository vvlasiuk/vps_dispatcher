from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ContentKind(StrEnum):
    TEXT = "text"
    PHOTO = "photo"
    FILE = "file"
    MIXED = "mixed"
    EMPTY = "empty"


class FileAttachment(BaseModel):
    file_id: str
    file_url: str
    mime_type: str

    @property
    def is_image(self) -> bool:
        return self.mime_type.startswith("image/")


class MessageSource(BaseModel):
    system: str
    source_id: str
    chat_id: str
    user_id: str | None = None
    username: str | None = None
    message_id: str
    timestamp: datetime
    group_id: str | None = None


class MessageContent(BaseModel):
    text: str | None = None
    language: str | None = None
    files: list[FileAttachment] = Field(default_factory=list)


class CommandTag(BaseModel):
    name: str
    params: dict[str, object] = Field(default_factory=dict)


class MessageDestination(BaseModel):
    system: str | None = None
    chat_id: str | None = None


class InputMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    source: MessageSource
    content: MessageContent | None = None
    command_tag: CommandTag | None = Field(default=None, alias="command")
    data: dict[str, object] = Field(default_factory=dict, alias="DATA")
    destination: MessageDestination | None = Field(default=None, alias="destination")

    @property
    def content_kind(self) -> ContentKind:
        has_text = bool(self.content and self.content.text and self.content.text.strip())
        has_files = bool(self.content and self.content.files)

        if has_text and has_files:
            return ContentKind.MIXED
        if has_text:
            return ContentKind.TEXT
        if not has_files:
            return ContentKind.EMPTY
        if all(file.is_image for file in self.content.files):
            return ContentKind.PHOTO
        return ContentKind.FILE

    @property
    def command(self) -> str | None:
        if not self.content or not self.content.text:
            return None

        first_token = self.content.text.strip().split(maxsplit=1)[0].lower()
        if not first_token:
            return None
        return first_token.removeprefix("/")
