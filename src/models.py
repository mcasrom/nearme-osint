from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional


EVENT_TYPES = {
    "fire": "Incendio",
    "flood": "Inundación",
    "earthquake": "Terremoto",
    "storm": "Tormenta",
    "wind": "Viento",
    "snow": "Nieve",
    "heatwave": "Ola de calor",
    "air_quality": "Calidad del aire",
    "traffic": "Tráfico",
    "road_incident": "Incidencia vial",
    "road_closure": "Corte de carretera",
    "train_delay": "Retraso tren",
    "flight_delay": "Retraso vuelo",
    "port_incident": "Incidencia portuaria",
    "blackout": "Apagón eléctrico",
    "water_cut": "Corte de agua",
    "telecom": "Incidencia telecomunicaciones",
    "radiation": "Radiación UV",
    "pollen": "Polen",
    "reservoir": "Nivel embalse",
    "warning": "Aviso oficial",
    "missing": "Desaparición",
    "crime": "Incidente seguridad",
    "news": "Noticia local",
    "other": "Otro",
}

LEVELS = {"info": "info", "warning": "warning", "alert": "alert", "critical": "critical"}


@dataclass
class Event:
    source: str
    source_id: str
    event_type: str
    subtype: str
    lat: float
    lon: float
    radius_m: float = 0
    level: str = "info"
    title: str = ""
    description: str = ""
    country: str = ""
    region: str = ""
    municipality: str = ""
    raw_json: Optional[dict] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: Optional[str] = None
    id: Optional[int] = None

    def to_dict(self):
        d = {}
        for k, v in self.__dict__.items():
            if v is not None:
                d[k] = v
        return d
