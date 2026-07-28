from abc import ABC, abstractmethod
from src.models import Event


class BaseCollector(ABC):
    name: str = ""
    interval_minutes: int = 30

    @abstractmethod
    def collect(self) -> list[Event]:
        pass

    def run(self) -> list[Event]:
        print(f"  [{self.name}] Recopilando...")
        try:
            events = self.collect()
            saved = 0
            from src.db import save_event
            for ev in events:
                try:
                    save_event(ev)
                    saved += 1
                except Exception as e:
                    print(f"    [WARN] Error guardando evento: {e}")
            print(f"    [OK] {saved}/{len(events)} eventos guardados")
            return events
        except Exception as e:
            print(f"    [ERROR] {e}")
            return []
