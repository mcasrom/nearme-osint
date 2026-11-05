#!/usr/bin/env python3
"""Registro de macroinversiones ferroviarias. Datos curados con fuente y estado."""
from __future__ import annotations
import json
from pathlib import Path
from string import Template
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_railes_info import HEADER, FOOTER, CSS, THEME_CSS, THEME_JS

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(__file__).resolve().parent / "railes-inversiones.json"
OUT = Path("/var/www/radar/railes-inversiones.html")
PUBLIC = Path("/var/www/radar/datos/railes-inversiones.json")

def main():
    d = json.loads(SRC.read_text(encoding="utf-8"))
    projects = sorted(d.get("projects", []), key=lambda p: (-(p.get("amount_m") or 0), p.get("name", "")))
    kinds = sorted({p.get("kind", "") for p in projects})
    total = len(projects)
    kinds_opts = "".join(f'<option value="{k}">{k}</option>' for k in kinds)
    rows = []
    for p in projects:
        src = p.get("source_url", "")
        title = p.get("source_title", "Fuente")
        date = p.get("source_date", "")
        rows.append(f'''<tr data-kind="{p.get("kind","")}">
<td><strong>{p.get("name","")}</strong><br><span class="muted">{p.get("scope","")}</span></td>
<td>{p.get("type","")}</td>
<td class="num"><strong>{p.get("amount_text","sin dato")}</strong><br><span class="muted">{p.get("vat","")}</span></td>
<td>{p.get("kind","")}<br><span class="muted">{p.get("status","")}</span></td>
<td>{p.get("period","")}</td>
<td><a href="{src}" target="_blank" rel="noopener">{date}</a><br><span class="muted">{title[:85]}{"…" if len(title)>85 else ""}</span></td>
</tr>''')
    html = '''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Macroinversiones ferroviarias · Raíles</title>
<meta name="description" content="Registro de macroinversiones ferroviarias en España con fuente oficial, estado e importe. No es el total del sistema; los importes no se suman.">
<meta name="robots" content="index,follow,max-image-preview:large"><meta name="author" content="Miguel Castillo"><meta name="theme-color" content="#101827">
<link rel="canonical" href="https://radar.viajeinteligencia.com/railes-inversiones.html">
<meta property="og:title" content="Macroinversiones ferroviarias · Raíles"><meta property="og:description" content="Proyectos concretos, importe, estado y fuente. No es el total del sistema."><meta property="og:type" content="website"><meta property="og:url" content="https://radar.viajeinteligencia.com/railes-inversiones.html"><meta property="og:image" content="https://radar.viajeinteligencia.com/railes-inversiones-og.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="Registro de macroinversiones ferroviarias"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="https://radar.viajeinteligencia.com/railes-inversiones-og.png">
<style>__CSS__</style><script type="application/ld+json">__JSONLD__</script></head><body>__HEADER__<main class="wrap">
<h1>Macroinversiones ferroviarias</h1>
<p class="lead">Registro de proyectos concretos con fuente oficial: corredores, cercanías, estaciones e integraciones urbanas. La cifra es el importe que declara la fuente, no una suma del sistema.</p>
<p class="meta">Actualizado: __UPDATED__ · __TOTAL__ fichas · fuente: __SOURCE__</p>
<div class="warn"><b>No es el total de la inversión ferroviaria.</b> Los importes mezclan <b>licitado</b>, <b>adjudicado</b>, <b>movilizado</b> e <b>inversión prevista</b> de años distintos. No se suman. Cuando no consta IVA o ejecución, se dice.</div>
<div class="warn"><b>Estado del registro: MVP · 60 %.</b> <b>Inversión ejecutada y mantenimiento: pendientes.</b> ADIF/ADIF AV publican cuentas anuales y memorias en PDF, sin API ni desglose homogéneo por proyecto; el PGE/IGAE da agregados, no proyectos. Próxima revisión: <b>diciembre de 2026</b>. No se estima.</div>
<div class="kpis"><div class="kpi"><b>__TOTAL__</b><span>fichas con fuente</span></div><div class="kpi"><b>__CORR__</b><span>corredores</span></div><div class="kpi"><b>__KINDS__</b><span>estados distintos</span></div></div>
<div class="card"><h2>Filtro</h2><label for="inv-kind">Estado del importe</label> <select id="inv-kind" style="padding:7px;border-radius:6px;border:1px solid #cbd5e1"><option value="">Todos</option>__KINDS_OPTS__</select><p class="muted small" id="inv-count">__TOTAL__ fichas</p></div>
<div class="card"><h2>Registro</h2><div class="tablewrap"><table><thead><tr><th>Proyecto</th><th>Tipo</th><th>Importe declarado</th><th>Estado</th><th>Periodo</th><th>Fuente</th></tr></thead><tbody>__ROWS__</tbody></table></div><p class="muted small">Cada fila enlaza a la nota de prensa del Ministerio. No se usa una cifra de prensa como ejecución certificada. JSON: <a href="/datos/railes-inversiones.json">datos abiertos</a>.</p></div>
<div class="card"><h2>Qué falta</h2><ul><li><b>Inversión ejecutada</b> por año y por proyecto: cuentas anuales de ADIF/ADIF AV.</li><li><b>Mantenimiento</b> separado de la inversión nueva.</li><li><b>Desglose por corredor</b> con denominador y año homogéneos.</li><li><b>PGE</b> y ejecución presupuestaria, no solo notas de prensa.</li></ul><p class="muted small">Mientras no exista una serie pública limpia, este registro es una lista de proyectos, no un ranking ni un total.</p></div>
<div class="card"><h2>Cómo leer un importe</h2><ul><li><b>Licitado:</b> contrato convocado; no adjudicado ni ejecutado.</li><li><b>Adjudicado:</b> contrato asignado; no ejecutado.</li><li><b>Movilizado:</b> parte del presupuesto comprometida; no gasto certificado.</li><li><b>Inversión prevista:</b> plan o anuncio; no ejecución.</li></ul></div>
<script>
(function(){
  var sel=document.getElementById('inv-kind'), rows=Array.prototype.slice.call(document.querySelectorAll('tbody tr[data-kind]')), count=document.getElementById('inv-count');
  if(!sel) return;
  function update(){
    var v=sel.value, n=0;
    rows.forEach(function(tr){ var ok=!v||tr.dataset.kind===v; tr.style.display=ok?'':'none'; if(ok)n++; });
    if(count) count.textContent=n+' fichas';
  }
  sel.addEventListener('change',update); update();
})();
</script>
<div class="cta"><a class="btn" href="/railes-cifras.html">Volver a Cifras</a> <a class="btn ghost" href="/railes-fuentes.html">Fuentes y método</a> <a class="btn ghost" href="/datos/railes-inversiones.json">JSON</a></div>
</main>__FOOTER__</body></html>'''
    jsonld = json.dumps({"@context":"https://schema.org","@type":"Dataset","name":"Macroinversiones ferroviarias en España","description":"Registro de proyectos ferroviarios con importe declarado, estado y fuente oficial. No es el total del sistema ni una serie de inversión ejecutada.","url":"https://radar.viajeinteligencia.com/railes-inversiones.html","creator":{"@type":"Person","name":"Miguel Castillo","url":"https://viajeinteligencia.com"},"isAccessibleForFree":True,"inLanguage":"es","dateModified":d.get("updated",""),"spatialCoverage":"España","variableMeasured":["importe licitado","importe adjudicado","importe movilizado","inversión prevista"],"distribution":{"@type":"DataDownload","encodingFormat":"application/json","contentUrl":"https://radar.viajeinteligencia.com/datos/railes-inversiones.json"}},ensure_ascii=False)
    html = (html.replace("__CSS__", CSS).replace("__HEADER__", HEADER).replace("__FOOTER__", FOOTER)
            .replace("__UPDATED__", d.get("updated","—")).replace("__TOTAL__", str(total))
            .replace("__SOURCE__", d.get("source","—")).replace("__ROWS__", "".join(rows))
            .replace("__KINDS_OPTS__", kinds_opts).replace("__KINDS__", str(len(kinds)))
            .replace("__CORR__", str(len({p.get("name","").split(" · ")[0] for p in projects if "Corredor" in p.get("name","")})))
            .replace("__JSONLD__", jsonld))
    html = html.replace("</style>", THEME_CSS + "</style>").replace("</body>", THEME_JS + "</body>")
    OUT.write_text(html, encoding="utf-8")
    PUBLIC.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print("inversiones ok", OUT, len(html), "projects", total)

if __name__ == "__main__": main()
