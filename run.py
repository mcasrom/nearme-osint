import sys
from datetime import datetime, timezone

COLLECTORS = []


def register_collectors():
    try:
        from src.collectors.aemet import AEMETCollector
        COLLECTORS.append(AEMETCollector())
    except Exception as e:
        print(f"[WARN] No se pudo cargar AEMET: {e}")
    try:
        from src.collectors.copernicus import CopernicusCollector
        COLLECTORS.append(CopernicusCollector())
    except Exception as e:
        print(f"[WARN] No se pudo cargar Copernicus: {e}")
    try:
        from src.collectors.ign import IGNCollector
        COLLECTORS.append(IGNCollector())
    except Exception as e:
        print(f"[WARN] No se pudo cargar IGN: {e}")
    try:
        from src.collectors.openaq import OpenAQCollector
        COLLECTORS.append(OpenAQCollector())
    except Exception as e:
        print(f"[WARN] No se pudo cargar OpenAQ: {e}")
    try:
        from src.collectors.dgt import DGTCollector
        COLLECTORS.append(DGTCollector())
    except Exception as e:
        print(f"[WARN] No se pudo cargar DGT: {e}")


def run_all():
    now = datetime.now(timezone.utc)
    print("=" * 60)
    print("NearMe OSINT — Pipeline de recolección")
    print(f"Fecha: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 60)

    from src.db import init_db, clean_expired
    init_db()
    cleaned = clean_expired()
    print(f"[*] Eventos expirados eliminados: {cleaned}")

    register_collectors()
    print(f"[*] Colectores registrados: {len(COLLECTORS)}")

    total_events = 0
    for collector in COLLECTORS:
        events = collector.run()
        total_events += len(events)

    print(f"\n[*] Total eventos recolectados: {total_events}")
    print("[OK] Pipeline completado")


if __name__ == "__main__":
    run_all()
