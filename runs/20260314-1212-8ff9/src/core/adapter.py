from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
import time
from typing import Iterable

from .contracts import validate_metrics_payload
from .models import Article


@dataclass
class RunConfig:
    max_discovery_urls: int = 300
    max_articles_to_extract: int = 120
    max_runtime_seconds: int = 90


class BaseSourceAdapter(ABC):
    source: str

    @abstractmethod
    def discover(self, target_date: str, cfg: RunConfig) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def extract(self, url: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def normalize(self, raw: dict) -> Article:
        raise NotImplementedError

    def run(self, target_date: str, cfg: RunConfig) -> tuple[list[Article], dict]:
        started = time.time()
        metrics = {
            "discovered": 0,
            "processed": 0,
            "kept": 0,
            "discarded_by_date": 0,
            "errors": 0,
            "stop_reason": "completed",
            "last_url": "",
        }
        out: list[Article] = []

        urls = self.discover(target_date=target_date, cfg=cfg)[: cfg.max_discovery_urls]
        metrics["discovered"] = len(urls)

        for url in urls:
            if time.time() - started >= cfg.max_runtime_seconds:
                metrics["stop_reason"] = "max_runtime_seconds"
                break
            if metrics["processed"] >= cfg.max_articles_to_extract:
                metrics["stop_reason"] = "max_articles_to_extract"
                break

            metrics["last_url"] = url
            metrics["processed"] += 1
            try:
                raw = self.extract(url)
                article = self.normalize(raw)
                if article.published_at[:10] != target_date:
                    metrics["discarded_by_date"] += 1
                    continue
                out.append(article)
                metrics["kept"] += 1
            except Exception:
                metrics["errors"] += 1
                if metrics["errors"] >= 20:
                    metrics["stop_reason"] = "too_many_errors"
                    break

        return out, validate_metrics_payload(metrics)
