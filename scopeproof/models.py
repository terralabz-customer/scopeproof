"""Strict schemas for model-selected evidence; prose and prices stay outside the model."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EvidenceSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    segment_id: str = Field(min_length=2, max_length=12, description="An existing B or C segment ID from the brief.")
    capability_ids: list[str] = Field(default_factory=list, max_length=4, description="Only matching capability IDs from read_catalog.")
    assessment: Literal["included", "clarify", "excluded"] = Field(
        description="Required: included for an explicit matching request, clarify for an uncertain request, excluded for work outside this service."
    )


class ScopeSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_ids: list[Literal["landing", "node_api", "csv", "faq"]] = Field(max_length=4)
    items: list[EvidenceSelection] = Field(max_length=60)


class ScopeProofError(RuntimeError):
    """Base error that a caller may present without claiming a generated result."""


class ConfigurationError(ScopeProofError):
    """An explicitly selected, supported model is required."""


class GroundingError(ScopeProofError):
    """The model's selections failed evidence or catalogue validation."""


class ModelRunError(ScopeProofError):
    """The real agent could not finish its bounded analysis."""
