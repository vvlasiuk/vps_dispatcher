from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class InputMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    source: MessageSource
    content: MessageContent

    @model_validator(mode="after")
    def validate_payload(self) -> "InputMessage":
        if not (self.content.text or self.content.files):
            raise ValueError("Message must contain text or files")
        return self

    @property
    def content_kind(self) -> ContentKind:
        has_text = bool(self.content.text and self.content.text.strip())
        has_files = bool(self.content.files)

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
        if not self.content.text:
            return None

        first_token = self.content.text.strip().split(maxsplit=1)[0].lower()
        if not first_token:
            return None
        return first_token.removeprefix("/")
