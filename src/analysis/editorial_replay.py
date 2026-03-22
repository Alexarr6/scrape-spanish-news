from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.analysis.editorial_normalization import (
    EditorialNormalizationError,
    normalize_editorial_payload,
)

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "editorial_replay"

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


def load_replay_fixtures(fixtures_dir: Path | None = None) -> list[ReplayCaseFixture]:
    root = fixtures_dir or FIXTURE_DIR
    return [
        ReplayCaseFixture.model_validate_json(path.read_text(encoding="utf-8"))
        for path in sorted(root.glob("*.json"))
    ]


def evaluate_replay_fixture(fixture: ReplayCaseFixture) -> ReplayCaseResult:
    raw_payload = fixture.parsed_json
    if raw_payload is None:
        if fixture.raw_provider_output is None:
            raise ValueError(
                f"fixture {fixture.fixture_id} has neither parsed_json "
                "nor raw_provider_output"
            )
        raw_payload = json.loads(_extract_json_block(fixture.raw_provider_output))

    mismatches: list[str] = []
    try:
        normalization = normalize_editorial_payload(raw_payload)
    except EditorialNormalizationError as exc:
        if fixture.expectation.mode != "normalization_error":
            mismatches.append(f"unexpected normalization error: {exc}")
            return ReplayCaseResult(
                fixture_id=fixture.fixture_id,
                family=fixture.family,
                status="fail",
                mode=fixture.expectation.mode,
                error=str(exc),
                mismatches=mismatches,
            )
        if (
            fixture.expectation.error_contains
            and fixture.expectation.error_contains not in str(exc)
        ):
            mismatches.append(
                "expected error containing "
                f"{fixture.expectation.error_contains!r}, got {str(exc)!r}"
            )
        return ReplayCaseResult(
            fixture_id=fixture.fixture_id,
            family=fixture.family,
            status="pass" if not mismatches else "fail",
            mode="normalization_error",
            error=str(exc),
            mismatches=mismatches,
        )

    diagnostics = normalization.diagnostics
    final_payload = normalization.final_payload.model_dump(mode="json")
    dimension_status = {name: diag.status for name, diag in diagnostics.dimension_status.items()}

    if fixture.expectation.mode != "success":
        mismatches.append("expected normalization_error but normalization succeeded")
    if fixture.expectation.editorial_applicability and (
        diagnostics.editorial_applicability != fixture.expectation.editorial_applicability
    ):
        mismatches.append(
            "editorial_applicability expected "
            f"{fixture.expectation.editorial_applicability!r} got "
            f"{diagnostics.editorial_applicability!r}"
        )
    if fixture.expectation.editorial_applicability_reason and (
        diagnostics.editorial_applicability_reason
        != fixture.expectation.editorial_applicability_reason
    ):
        mismatches.append(
            "editorial_applicability_reason expected "
            f"{fixture.expectation.editorial_applicability_reason!r} got "
            f"{diagnostics.editorial_applicability_reason!r}"
        )
    if fixture.expectation.final_payload and final_payload != fixture.expectation.final_payload:
        mismatches.append("final_payload mismatch")
    if sorted(normalization.unclear_reasons) != sorted(fixture.expectation.unclear_reasons):
        mismatches.append(
            "unclear_reasons expected "
            f"{fixture.expectation.unclear_reasons!r} got "
            f"{list(normalization.unclear_reasons)!r}"
        )
    for name, expected_status in fixture.expectation.dimension_status.items():
        actual = dimension_status.get(name)
        if actual != expected_status:
            mismatches.append(
                f"dimension {name!r} expected status {expected_status!r} got {actual!r}"
            )
    for group, expected_values in fixture.expectation.preserved_signal_groups.items():
        actual_values = diagnostics.preserved_signals.get(group, [])
        for value in expected_values:
            if value not in actual_values:
                mismatches.append(
                    f"preserved signal {group!r} missing expected value {value!r}"
                )
    for fragment in fixture.expectation.repair_warnings_contains:
        if not any(fragment in warning for warning in normalization.repair_warnings):
            mismatches.append(f"repair warning fragment missing: {fragment!r}")
    for fragment in fixture.expectation.normalization_warnings_contains:
        if not any(fragment in warning for warning in normalization.normalization_warnings):
            mismatches.append(f"normalization warning fragment missing: {fragment!r}")

    return ReplayCaseResult(
        fixture_id=fixture.fixture_id,
        family=fixture.family,
        status="pass" if not mismatches else "fail",
        mode="success",
        editorial_applicability=diagnostics.editorial_applicability,
        editorial_applicability_reason=diagnostics.editorial_applicability_reason,
        unclear_reasons=list(normalization.unclear_reasons),
        dimension_status=dimension_status,
        preserved_signals=diagnostics.preserved_signals,
        final_payload=final_payload,
        diagnostics=diagnostics.model_dump(mode="json"),
        mismatches=mismatches,
    )


def evaluate_replay_corpus(fixtures_dir: Path | None = None) -> list[ReplayCaseResult]:
    return [evaluate_replay_fixture(fixture) for fixture in load_replay_fixtures(fixtures_dir)]


def render_replay_report(results: list[ReplayCaseResult]) -> str:
    lines = []
    pass_count = sum(1 for result in results if result.status == "pass")
    fail_count = len(results) - pass_count
    lines.append(
        f"Editorial replay corpus: {pass_count} passed, {fail_count} failed, "
        f"{len(results)} total"
    )

    applicability_counts = Counter(
        result.editorial_applicability or result.mode for result in results
    )
    summary_counts = Counter(result.summary_bucket for result in results)
    lines.append("Applicability/mode counts: " + _render_counts(applicability_counts))
    lines.append("Signal bucket counts: " + _render_counts(summary_counts))
    lines.append("")
    for result in results:
        preserved = ", ".join(sorted(result.preserved_signals)) or "-"
        unclear = ", ".join(result.unclear_reasons) or "-"
        dimension_bits = ", ".join(
            f"{name}={status}" for name, status in sorted(result.dimension_status.items())
        ) or "-"
        lines.append(
            f"[{result.status.upper()}] {result.fixture_id} | family={result.family} | "
            f"mode={result.mode} | applicability={result.editorial_applicability or '-'} | "
            f"bucket={result.summary_bucket}"
        )
        lines.append(f"  unclear_reasons: {unclear}")
        lines.append(f"  dimension_status: {dimension_bits}")
        lines.append(f"  preserved_signals: {preserved}")
        if result.error:
            lines.append(f"  error: {result.error}")
        for mismatch in result.mismatches:
            lines.append(f"  mismatch: {mismatch}")
    return "\n".join(lines)


def _render_counts(counter: Counter[str]) -> str:
    if not counter:
        return "-"
    return ", ".join(f"{key}={counter[key]}" for key in sorted(counter))


def _extract_json_block(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            inner = "\n".join(lines[1:-1]).strip()
            if inner.lower().startswith("json\n"):
                inner = inner[5:].strip()
            if inner:
                return inner
    return stripped
