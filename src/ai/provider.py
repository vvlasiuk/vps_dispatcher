from __future__ import annotations

import base64
from pathlib import Path
from typing import TypeVar

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from common.settings import Settings
from contracts.input_message import InputMessage

SchemaModel = TypeVar("SchemaModel", bound=BaseModel)


def _convert_file_to_data_uri(file_path: str) -> str:
    """Convert local file to data URI (base64 encoded)."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    mime_type = mime_types.get(path.suffix.lower(), "image/jpeg")

    with open(path, "rb") as f:
        file_data = f.read()

    b64_data = base64.b64encode(file_data).decode("utf-8")
    return f"data:{mime_type};base64,{b64_data}"


class GeminiAIProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._llm = None
        if settings.gemini_api_key:
            llm_kwargs: dict = {
                "model": settings.gemini_model,
                "google_api_key": settings.gemini_api_key,
                "temperature": 0,
            }
            if settings.google_api_version:
                llm_kwargs["model_kwargs"] = {"api_version": settings.google_api_version}
            self._llm = ChatGoogleGenerativeAI(**llm_kwargs)

    async def generate_structured(
        self,
        *,
        prompt: str,
        response_model: type[SchemaModel],
        message: InputMessage,
    ) -> SchemaModel:
        if not self._llm:
            raise RuntimeError("GEMINI_API_KEY is required for AI workflow nodes")

        payload_blocks: list[dict[str, str]] = [{"type": "text", "text": prompt}]
        content = message.content
        if content and content.text:
            payload_blocks.append({"type": "text", "text": f"User text: {content.text}"})
        for attachment in (content.files if content else []):
            file_url = attachment.file_url
            if (
                not file_url.startswith("http")
                and not file_url.startswith("gs://")
                and not file_url.startswith("data:")
            ):
                file_url = _convert_file_to_data_uri(file_url)

            payload_blocks.append(
                {
                    "type": "image_url",
                    "image_url": file_url,
                }
            )

        structured_llm = self._llm.with_structured_output(response_model)
        result = await structured_llm.ainvoke([HumanMessage(content=payload_blocks)])

        if isinstance(result, response_model):
            validated = result
        else:
            validated = response_model.model_validate(result)

        confidence = getattr(validated, "confidence", None)
        if confidence is not None and confidence < self._settings.ai_confidence_threshold:
            raise ValueError(
                f"AI confidence {confidence} is below threshold {self._settings.ai_confidence_threshold}"
            )

        return validated
