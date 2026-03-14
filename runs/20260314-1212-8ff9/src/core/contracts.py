from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class NewsItemModel:
    source: str
    title: str
    url: str
    published_at: str
    section: str = ""
    author: str = ""
    summary: str = ""
    article_text: str = ""
    tags: str = ""

    @classmethod
    def model_validate(cls, value: dict[str, Any]) -> "NewsItemModel":
        if not isinstance(value, dict):
            raise TypeError("news item must be a dict")
        required = ["source", "title", "url", "published_at"]
        missing = [k for k in required if k not in value]
        if missing:
            raise ValueError(f"missing required fields: {','.join(missing)}")
        data = {
            "source": value.get("source", ""),
            "title": value.get("title", ""),
            "url": value.get("url", ""),
            "published_at": value.get("published_at", ""),
            "section": value.get("section", ""),
            "author": value.get("author", ""),
            "summary": value.get("summary", ""),
            "article_text": value.get("article_text", ""),
            "tags": value.get("tags", ""),
        }
        for k, v in data.items():
            if not isinstance(v, str):
                raise TypeError(f"{k} must be str")
        return cls(**data)

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunMetricsModel:
    discovered: int
    processed: int
    kept: int
    discarded_by_date: int
    errors: int = 0
    stop_reason: str = "completed"
    last_url: str = ""
    strategy_metrics: dict[str, Any] | None = None

    @classmethod
    def model_validate(cls, value: dict[str, Any]) -> "RunMetricsModel":
        if not isinstance(value, dict):
            raise TypeError("metrics must be a dict")
        required = ["discovered", "processed", "kept", "discarded_by_date", "stop_reason"]
        missing = [k for k in required if k not in value]
        if missing:
            raise ValueError(f"missing required fields: {','.join(missing)}")

        int_fields = ["discovered", "processed", "kept", "discarded_by_date", "errors"]
        parsed: dict[str, Any] = {
            "stop_reason": value.get("stop_reason", "completed"),
            "last_url": value.get("last_url", ""),
            "strategy_metrics": value.get("strategy_metrics"),
        }

        for field in int_fields:
            raw = value.get(field, 0)
            if isinstance(raw, bool) or not isinstance(raw, int):
                raise TypeError(f"{field} must be int")
            parsed[field] = raw

        if not isinstance(parsed["stop_reason"], str):
            raise TypeError("stop_reason must be str")
        if not isinstance(parsed["last_url"], str):
            raise TypeError("last_url must be str")

        strategy_metrics = parsed["strategy_metrics"]
        if strategy_metrics is not None:
            # Backward-compatible bridge: allow legacy list shape and normalize it.
            if isinstance(strategy_metrics, list):
                strategy_metrics = {
                    "schema_version": "discovery_strategy_metrics.v1",
                    "strategies": strategy_metrics,
                }
                parsed["strategy_metrics"] = strategy_metrics
            if not isinstance(strategy_metrics, dict):
                raise TypeError("strategy_metrics must be object when provided")
            if "schema_version" not in strategy_metrics or "strategies" not in strategy_metrics:
                raise ValueError("strategy_metrics must include schema_version and strategies")
            if not isinstance(strategy_metrics["schema_version"], str):
                raise TypeError("strategy_metrics.schema_version must be str")
            if not isinstance(strategy_metrics["strategies"], list):
                raise TypeError("strategy_metrics.strategies must be list")
            for row in strategy_metrics["strategies"]:
                if not isinstance(row, dict):
                    raise TypeError("strategy_metrics rows must be dict")

        return cls(**parsed)

    def model_dump(self) -> dict[str, Any]:
        payload = asdict(self)
        if payload.get("strategy_metrics") is None:
            payload.pop("strategy_metrics", None)
        return payload


@dataclass
class ComparisonRowModel:
    source: str
    baseline_count: int
    current_count: int
    delta_abs: int
    delta_pct: float
    status: str
    warnings: list[str]
    metrics: RunMetricsModel

    @classmethod
    def model_validate(cls, value: dict[str, Any]) -> "ComparisonRowModel":
        if not isinstance(value, dict):
            raise TypeError("comparison row must be dict")
        required = [
            "source",
            "baseline_count",
            "current_count",
            "delta_abs",
            "delta_pct",
            "status",
            "warnings",
            "metrics",
        ]
        missing = [k for k in required if k not in value]
        if missing:
            raise ValueError(f"missing required fields: {','.join(missing)}")

        if not isinstance(value["source"], str):
            raise TypeError("source must be str")
        for key in ["baseline_count", "current_count", "delta_abs"]:
            if isinstance(value[key], bool) or not isinstance(value[key], int):
                raise TypeError(f"{key} must be int")
        if not isinstance(value["delta_pct"], (int, float)):
            raise TypeError("delta_pct must be number")
        if not isinstance(value["status"], str):
            raise TypeError("status must be str")
        if not isinstance(value["warnings"], list) or any(not isinstance(w, str) for w in value["warnings"]):
            raise TypeError("warnings must be list[str]")

        metrics = RunMetricsModel.model_validate(value["metrics"])

        return cls(
            source=value["source"],
            baseline_count=value["baseline_count"],
            current_count=value["current_count"],
            delta_abs=value["delta_abs"],
            delta_pct=float(value["delta_pct"]),
            status=value["status"],
            warnings=value["warnings"],
            metrics=metrics,
        )

    def model_dump(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["metrics"] = self.metrics.model_dump()
        return payload


@dataclass
class ComparisonSummaryModel:
    schema_version: str
    generated_at: str
    date: str
    baseline_ref: str
    current_ref: str
    status: str
    warnings: list[str]
    sources: list[ComparisonRowModel]

    @classmethod
    def model_validate(cls, value: dict[str, Any]) -> "ComparisonSummaryModel":
        if not isinstance(value, dict):
            raise TypeError("comparison summary must be dict")
        required = [
            "schema_version",
            "generated_at",
            "date",
            "baseline_ref",
            "current_ref",
            "status",
            "warnings",
            "sources",
        ]
        missing = [k for k in required if k not in value]
        if missing:
            raise ValueError(f"missing required fields: {','.join(missing)}")

        for key in ["schema_version", "generated_at", "date", "baseline_ref", "current_ref", "status"]:
            if not isinstance(value[key], str):
                raise TypeError(f"{key} must be str")
        if not isinstance(value["warnings"], list) or any(not isinstance(w, str) for w in value["warnings"]):
            raise TypeError("warnings must be list[str]")
        if not isinstance(value["sources"], list):
            raise TypeError("sources must be list")

        rows = [ComparisonRowModel.model_validate(row) for row in value["sources"]]
        return cls(
            schema_version=value["schema_version"],
            generated_at=value["generated_at"],
            date=value["date"],
            baseline_ref=value["baseline_ref"],
            current_ref=value["current_ref"],
            status=value["status"],
            warnings=value["warnings"],
            sources=rows,
        )

    def model_dump(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["sources"] = [row.model_dump() for row in self.sources]
        return payload

    @classmethod
    def model_json_schema(cls) -> dict[str, Any]:
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "ComparisonSummaryModel",
            "type": "object",
            "required": [
                "schema_version",
                "generated_at",
                "date",
                "baseline_ref",
                "current_ref",
                "status",
                "warnings",
                "sources",
            ],
            "properties": {
                "schema_version": {"type": "string"},
                "generated_at": {"type": "string"},
                "date": {"type": "string"},
                "baseline_ref": {"type": "string"},
                "current_ref": {"type": "string"},
                "status": {"type": "string"},
                "warnings": {"type": "array", "items": {"type": "string"}},
                "sources": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": [
                            "source",
                            "baseline_count",
                            "current_count",
                            "delta_abs",
                            "delta_pct",
                            "status",
                            "warnings",
                            "metrics",
                        ],
                    },
                },
            },
        }


def validate_article_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return NewsItemModel.model_validate(payload).model_dump()


def validate_metrics_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return RunMetricsModel.model_validate(payload).model_dump()


def validate_comparison_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return ComparisonSummaryModel.model_validate(payload).model_dump()
