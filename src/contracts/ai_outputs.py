from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AIResultBase(BaseModel):
    confidence: float = Field(ge=0.0, le=1.0)
    notes: str | None = None


class FormTypeDetection(AIResultBase):
    form_type: str


class FormExtractionResult(AIResultBase):
    form_type: str
    extracted_data: dict[str, Any] = Field(default_factory=dict)
    suggested_tags: list[str] = Field(default_factory=list)


class ToolIdentificationResult(AIResultBase):
    model_name: str | None = None
    article_number: str | None = None
    serial_number: str | None = None


class ToolConditionResult(AIResultBase):
    condition_summary: str
    defects: list[str] = Field(default_factory=list)


class CustomerIdentificationResult(AIResultBase):
    matched_by: str | None = None
    phone_number: str | None = None
    full_name: str | None = None
    consignment_note: str | None = None
