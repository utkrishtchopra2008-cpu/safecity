"""Typed, bounded video measurements and detector observations."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BoundingBox(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    x_min: float = Field(ge=0, le=1)
    y_min: float = Field(ge=0, le=1)
    x_max: float = Field(ge=0, le=1)
    y_max: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def positive_area(self) -> BoundingBox:
        if self.x_max <= self.x_min or self.y_max <= self.y_min:
            raise ValueError("Bounding box must have positive area")
        return self


class ObjectDetection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    class_name: str = Field(min_length=1, max_length=80)
    score: float = Field(ge=0, le=1)
    score_semantics: Literal["uncalibrated_model_score"] = "uncalibrated_model_score"
    box: BoundingBox
    frame_index: int = Field(ge=0)
    timestamp_ms: int | None = Field(default=None, ge=0)
    timestamp_status: Literal["known", "unknown"]
    detector_version: str = Field(min_length=1, max_length=120)
    evidence_id: UUID

    @model_validator(mode="after")
    def timestamp_matches_status(self) -> ObjectDetection:
        if (self.timestamp_ms is not None) != (self.timestamp_status == "known"):
            raise ValueError("Timestamp value and status must agree")
        return self


class RawObjectDetection(BaseModel):
    """One validated model output before source-frame metadata is attached."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    class_name: str = Field(min_length=1, max_length=80)
    score: float = Field(ge=0, le=1)
    box: BoundingBox
    detector_version: str = Field(min_length=1, max_length=120)


class QualityMeasurement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    metric: str = Field(min_length=1, max_length=80)
    value: float | int | dict[str, int] | None
    unit: str | None = Field(default=None, max_length=40)
    algorithm: str = Field(min_length=1, max_length=120)
    algorithm_version: str = Field(min_length=1, max_length=80)
    configuration: dict[str, float | int | str | None]
    threshold: dict[str, float] | None = None
    status: Literal["measured", "below_threshold", "above_threshold", "unavailable"]
    reason_code: str | None = Field(default=None, max_length=80)


class QualityThresholds(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    minimum_mean_luma: float | None = Field(default=None, ge=0, le=255)
    maximum_mean_luma: float | None = Field(default=None, ge=0, le=255)
    minimum_laplacian_variance: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def ordered_luma_thresholds(self) -> QualityThresholds:
        if (
            self.minimum_mean_luma is not None
            and self.maximum_mean_luma is not None
            and self.minimum_mean_luma > self.maximum_mean_luma
        ):
            raise ValueError("Minimum brightness threshold must not exceed maximum")
        return self
