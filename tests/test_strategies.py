import unittest

from src.core.adapter import RunConfig
from src.core.strategies.orchestrator import DiscoveryOrchestrator


class _DummyStrategy:
    def __init__(self, name, urls):
        self.name = name
        self._urls = urls

    def discover(self, target_date: str, cfg: RunConfig):
        del target_date, cfg
        return list(self._urls)


class StrategyTests(unittest.TestCase):
    def test_orchestrator_deduplicates_and_respects_cap(self):
        cfg = RunConfig(max_discovery_urls=3)
        orchestrator = DiscoveryOrchestrator(
            [
                _DummyStrategy("a", ["u1", "u2"]),
                _DummyStrategy("b", ["u2", "u3", "u4"]),
            ]
        )

        urls, metrics = orchestrator.run(target_date="2026-03-13", cfg=cfg)

        self.assertEqual(urls, ["u1", "u2", "u3"])
        self.assertEqual(len(metrics), 2)
        self.assertEqual(metrics[1]["stop_reason"], "cap_candidates")


if __name__ == "__main__":
    unittest.main()
