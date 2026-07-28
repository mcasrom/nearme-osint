from abc import ABC, abstractmethod
from src.logging import get_logger
from src.models import Event

logger = get_logger("src.collectors.base")


class BaseCollector(ABC):
    name: str = ""
    interval_minutes: int = 30

    @abstractmethod
    async def collect(self) -> list[Event]:
        pass

    async def run(self) -> list[Event]:
        logger.info("[%s] Recopilando...", self.name)
        try:
            events = await self.collect()
            saved = 0
            from src.db import save_event
            for ev in events:
                try:
                    save_event(ev)
                    saved += 1
                except Exception as e:
                    logger.warning("Error guardando evento: %s", e)
            logger.info("[OK] %d/%d eventos guardados", saved, len(events))
            return events
        except Exception as e:
            logger.error("%s", e)
            return []
