from abc import ABC, abstractmethod
from src.logging import get_logger
from src.models import Event

logger = get_logger("src.collectors.base")


class BaseCollector(ABC):
    name: str = ""
    source: str = ""  # used as DB source field for resolve_events
    interval_minutes: int = 30

    @abstractmethod
    async def collect(self) -> list[Event]:
        pass

    async def run(self) -> list[Event]:
        logger.info("[%s] Recopilando...", self.name)
        try:
            events = await self.collect()
            from src.db import save_events_batch
            saved = save_events_batch(events)
            logger.info("[OK] %d/%d eventos guardados", saved, len(events))

            # Mark events no longer returned by the API as resolved
            if self.source and events:
                from src.db import resolve_events
                sources = self.source if isinstance(self.source, list) else [self.source]
                for src in sources:
                    ids_with_source = {ev.source_id for ev in events if ev.source == src}
                    if ids_with_source:
                        resolved = resolve_events(src, ids_with_source)
                        if resolved:
                            logger.info("[%s] %d eventos resueltos para source=%s", self.name, resolved, src)

            return events
        except Exception as e:
            logger.error("%s", e)
            return []
