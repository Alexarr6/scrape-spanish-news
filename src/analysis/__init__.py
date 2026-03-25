from __future__ import annotations

__all__ = ["AnalysisPipeline", "ClusterPipeline"]


def __getattr__(name: str):
    if name == "AnalysisPipeline":
        from src.analysis.pipeline import AnalysisPipeline

        return AnalysisPipeline
    if name == "ClusterPipeline":
        from src.analysis.pipeline import ClusterPipeline

        return ClusterPipeline
    raise AttributeError(name)
