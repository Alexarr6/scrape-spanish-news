from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

FIXTURE_DIR = Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "editorial_replay"

ReplayExpectationMode = Literal["success", "normalization_error"]


class ReplayCaseExpectation(BaseModel):
    mode: ReplayExpectationMode
    editorial_applicability: str | None = None
    editorial_applicability_reason: str | None = None
    unclear_reasons: list[str] = Field(default_factory=list)
    final_payload: dict[str, Any] | None = None
    dimension_status: dict[str, str] = Field(default_factory=dict)
    preserved_signal_groups: dict[str, list[str]] = Field(default_factory=dict)
    repair_warnings_contains: list[str] = Field(default_factory=list)
    normalization_warnings_contains: list[str] = Field(default_factory=list)
    error_contains: str | None = None


class ReplayCaseFixture(BaseModel):
    fixture_id: str
    family: str
    source_artifact: str | None = None
    notes: str
    article: dict[str, Any] = Field(default_factory=dict)
    provider: dict[str, Any] = Field(default_factory=dict)
    raw_provider_output: str | None = None
    parsed_json: dict[str, Any] | None = None
    repaired_payload: dict[str, Any] | None = None
    final_payload: dict[str, Any] | None = None
    diagnostics: dict[str, Any] | None = None
    expectation: ReplayCaseExpectation


class ReplayCaseResult(BaseModel):
    fixture_id: str
    family: str
    status: Literal["pass", "fail"]
    mode: ReplayExpectationMode
    editorial_applicability: str | None = None
    editorial_applicability_reason: str | None = None
    unclear_reasons: list[str] = Field(default_factory=list)
    dimension_status: dict[str, str] = Field(default_factory=dict)
    preserved_signals: dict[str, list[str]] = Field(default_factory=dict)
    final_payload: dict[str, Any] | None = None
    diagnostics: dict[str, Any] | None = None
    error: str | None = None
    mismatches: list[str] = Field(default_factory=list)

    @property
    def summary_bucket(self) -> str:
        if self.mode == "normalization_error":
            return "normalization_error" if self.error else "unexpected_success"
        if self.editorial_applicability == "out_of_domain":
            return "out_of_domain"
        if self.editorial_applicability == "limited":
            return "limited"
        if "mapping_loss" in self.unclear_reasons:
            return "mapping_loss"
        if "provider_missing" in self.unclear_reasons:
            return "provider_missing"
        if (
            "weak_signal_abstain" in self.unclear_reasons
            or "semantic_weak_signal" in self.unclear_reasons
        ):
            return "honest_abstention"
        return "resolved_or_mixed"
