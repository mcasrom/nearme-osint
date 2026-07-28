from datetime import datetime, timezone
from typing import Dict, List


class PipelineMetrics:
    _instance: "PipelineMetrics | None" = None

    def __init__(self):
        self._runs: List[Dict] = []

    @classmethod
    def get(cls) -> "PipelineMetrics":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def record_run(self, collector_name: str, success: bool, latency_s: float, events: int) -> None:
        self._runs.append({
            "collector": collector_name,
            "success": success,
            "latency_s": round(latency_s, 3),
            "events": events,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def last_run(self) -> List[Dict]:
        return list(self._runs)

    def last_n(self, n: int = 20) -> List[Dict]:
        return list(self._runs[-n:])

    def summary(self) -> Dict:
        total_runs = len(self._runs)
        if total_runs == 0:
            return {"total_runs": 0}
        successes = sum(1 for r in self._runs if r["success"])
        total_events = sum(r["events"] for r in self._runs)
        total_latency = sum(r["latency_s"] for r in self._runs)
        by_collector: Dict[str, Dict] = {}
        for r in self._runs:
            name = r["collector"]
            if name not in by_collector:
                by_collector[name] = {"runs": 0, "successes": 0, "total_events": 0, "total_latency": 0.0}
            by_collector[name]["runs"] += 1
            if r["success"]:
                by_collector[name]["successes"] += 1
            by_collector[name]["total_events"] += r["events"]
            by_collector[name]["total_latency"] += r["latency_s"]
        return {
            "total_runs": total_runs,
            "success_rate": round(successes / total_runs * 100, 1),
            "total_events": total_events,
            "total_latency_s": round(total_latency, 2),
            "by_collector": by_collector,
        }

    def reset(self) -> None:
        self._runs.clear()