#!/usr/bin/env python3
"""Genera /var/www/radar/railes.html: esquema Leaflet de corredores de alta velocidad."""
from __future__ import annotations
import argparse
from pathlib import Path

THEME_CSS = '.site-head{background:var(--card)!important;border-color:var(--line)!important}.site-foot{background:var(--card)!important;border-color:var(--line)!important}.brandtext{max-width:520px;line-height:1.1}.site-head nav a,.tag,.footwrap,.meta,.lead,.card p,.card li,.kpi span,.panel .k,.muted{color:var(--muted)}.site-head nav a:hover{color:var(--accent)}.headcta{background:var(--accent);color:#fff!important;border-radius:7px;padding:6px 10px;text-decoration:none;font-weight:700;font-size:.82rem}.themebtn{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:7px;padding:6px 9px;cursor:pointer;font:inherit;font-size:.8rem}.hero-cta{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}.btn{display:inline-block;border:1px solid var(--line);border-radius:7px;padding:8px 12px;text-decoration:none;font-weight:700;font-size:.85rem;color:var(--ink)}.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff}.btn:hover{filter:brightness(.97)}\n:root[data-theme="dark"] body{background:#0f1026!important;color:#eef0f6!important}:root[data-theme="dark"] .card,:root[data-theme="dark"] .panel,:root[data-theme="dark"] .kpi,:root[data-theme="dark"] .warn{background:#171a34!important;color:#eef0f6!important;border-color:#30344f!important}:root[data-theme="dark"] .card h2,:root[data-theme="dark"] .panel h2{border-color:#3a3f62!important}:root[data-theme="dark"] .card p,:root[data-theme="dark"] .card li,:root[data-theme="dark"] .lead,:root[data-theme="dark"] .barrow span,:root[data-theme="dark"] .barrow b,:root[data-theme="dark"] .kpi span,:root[data-theme="dark"] .meta,:root[data-theme="dark"] .muted{color:#b9bfd6!important}:root[data-theme="dark"] .bar{background:#242844!important}:root[data-theme="dark"] table th,:root[data-theme="dark"] table td{border-color:#30344f!important}:root[data-theme="dark"] th{color:#a7abc4!important}'
THEME_JS = "<script>\n(function(){var r=document.documentElement,b=document.getElementById('railes-theme');function sync(){var d=r.dataset.theme==='dark';if(b){b.textContent=d?'☀ Claro':'☾ Oscuro';b.setAttribute('aria-pressed',d?'true':'false');}}var saved=localStorage.getItem('railes-theme');if(saved==='dark'||saved==='light')r.dataset.theme=saved;sync();window.toggleRailesTheme=function(){r.dataset.theme=r.dataset.theme==='dark'?'light':'dark';localStorage.setItem('railes-theme',r.dataset.theme);sync();};})();\n</script>"
OUT = Path("/var/www/radar/railes.html")
AXES = [
    {"id":"madrid-sevilla","name":"Madrid–Sevilla","color":"#ff5a1f","speed":"300 km/h","stations":[
        ("Madrid Atocha",40.406,-3.690),("Ciudad Real",38.986,-3.929),("Puertollano",38.687,-4.107),("Córdoba",37.888,-4.779),("Sevilla Santa Justa",37.392,-5.975)]},
    {"id":"madrid-barcelona","name":"Madrid–Barcelona–Figueres","color":"#3ddc97","speed":"300–310 km/h","stations":[
        ("Madrid Atocha",40.406,-3.690),("Guadalajara",40.633,-3.167),("Calatayud",41.353,-1.643),("Zaragoza Delicias",41.658,-0.876),("Lleida Pirineus",41.620,0.624),("Camp de Tarragona",41.192,1.253),("Barcelona Sants",41.379,2.140),("Girona",41.979,2.816),("Figueres",42.266,2.961)]},
    {"id":"madrid-levante","name":"Madrid–Levante","color":"#8ec5ff","speed":"300 km/h","stations":[
        ("Madrid Atocha",40.406,-3.690),("Cuenca",40.070,-2.137),("Albacete",38.995,-1.856),("Valencia Joaquín Sorolla",39.467,-0.377),("Alicante",38.345,-0.495),("Murcia del Carmen",37.992,-1.130)]},
    {"id":"madrid-norte","name":"Madrid–Valladolid–León","color":"#f2c94c","speed":"300 km/h","stations":[
        ("Madrid Chamartín",40.472,-3.682),("Segovia",40.948,-4.118),("Valladolid",41.652,-4.724),("Palencia",42.012,-4.532),("León",42.598,-5.567)]},
    {"id":"madrid-galicia","name":"Madrid–Galicia","color":"#bb6bd9","speed":"300 km/h","stations":[
        ("Madrid Chamartín",40.472,-3.682),("Zamora",41.503,-5.744),("Ourense",42.335,-7.864),("Santiago de Compostela",42.880,-8.545),("A Coruña",43.362,-8.411),("Vigo",42.240,-8.720)]},
    {"id":"madrid-asturias","name":"Madrid–Asturias","color":"#56ccf2","speed":"300 km/h","stations":[
        ("Madrid Chamartín",40.472,-3.682),("Valladolid",41.652,-4.724),("Palencia",42.012,-4.532),("León",42.598,-5.567),("Oviedo",43.366,-5.845),("Gijón",43.535,-5.661)]},
    {"id":"madrid-extremadura","name":"Madrid–Extremadura","color":"#f28cb1","speed":"300 km/h","stations":[
        ("Madrid Atocha",40.406,-3.690),("Plasencia",40.031,-6.088),("Cáceres",39.476,-6.372),("Mérida",38.916,-6.337),("Badajoz",38.878,-6.970)]},
]

HTML = '''<!doctype html><html lang="es"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="index,follow,max-image-preview:large">
<title>El Observatorio Ciudadano del Ferrocarril · Raíles</title>
<meta name="description" content="Mapa esquemático de los principales corredores de alta velocidad de España, con estaciones, velocidad y enlaces a los retrasos de Renfe.">
<link rel="canonical" href="https://radar.viajeinteligencia.com/railes.html">
<meta property="og:title" content="Raíles · Alta velocidad española, eje a eje">
<meta property="og:description" content="Corredores, estaciones y velocidad. Esquema, no trazado oficial; sin pasajeros por eje inventados.">
<meta property="og:type" content="website"><meta property="og:url" content="https://radar.viajeinteligencia.com/railes.html">
<meta property="og:image" content="https://radar.viajeinteligencia.com/retrasos-renfe-og.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
:root{--ink:#172033;--muted:#64748b;--line:#e2e8f0;--paper:#fffaf5;--accent:#ff5a1f}
*{box-sizing:border-box}body{margin:0;background:#fafafa;color:var(--ink);font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;line-height:1.55}
.wrap{max-width:1100px;margin:0 auto;padding:24px 16px 56px}a{color:#c2410c}.top{font-size:.85rem;margin-bottom:14px}
h1{font-size:2rem;line-height:1.1;margin:.1em 0}.lead{max-width:800px;color:#334155}.meta{font-size:.82rem;color:var(--muted)}
.layout{display:grid;grid-template-columns:1fr 310px;gap:16px;margin-top:18px}@media(max-width:820px){.layout{grid-template-columns:1fr}}
#map{height:620px;border:1px solid var(--line);border-radius:12px;background:#eef3f7}@media(max-width:820px){#map{height:480px}}
.panel{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px;height:max-content;position:sticky;top:16px}
.panel h2{font-size:1.15rem;margin:0 0 4px}.panel .k{font-size:.85rem;color:var(--muted);margin:2px 0}
.kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:16px 0}.kpi{background:var(--paper);border:1px solid #fde68a;border-radius:9px;padding:9px;text-align:center}.kpi b{display:block;font-size:1.2rem;color:#b45309}.kpi span{font-size:.7rem;color:var(--muted)}
.legend{display:flex;gap:12px;flex-wrap:wrap;font-size:.8rem;color:#475569;margin:10px 0}.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:4px;vertical-align:-1px}
.card{background:#fff;border:1px solid var(--line);border-radius:10px;padding:16px;margin:18px 0}.card h2{font-size:1.1rem;margin:0 0 8px;border-bottom:2px solid #fde68a;padding-bottom:5px}.card p,.card li{font-size:.9rem;color:#334155}
.warn{background:#fff7ed;border-left:4px solid #b45309;padding:10px 14px;border-radius:7px;font-size:.9rem}.muted{color:var(--muted);font-size:.82rem}
.station{background:#fff;border:2px solid #fff;border-radius:50%;box-shadow:0 1px 3px #0004}.leaflet-popup-content{font-size:.85rem}
.site-head{position:sticky;top:0;z-index:1000;background:#fff;border-bottom:1px solid #e2e8f0}.headwrap{max-width:1100px;margin:auto;display:flex;align-items:center;gap:12px;padding:10px 16px;flex-wrap:wrap}.brand{font-weight:800;font-size:1.25rem;color:#172033;text-decoration:none;display:flex;align-items:center;gap:7px}.brand .mark{display:inline-block;width:10px;height:24px;border-radius:3px;background:#ff5a1f}.tag{font-size:.78rem;color:#64748b}.site-head nav{display:flex;gap:12px;margin-left:auto;flex-wrap:wrap}.site-head nav a{font-size:.86rem;color:#334155;text-decoration:none}.site-head nav a:hover{color:#c2410c}.site-foot{background:#fff;border-top:1px solid #e2e8f0;margin-top:28px;padding:20px 16px}.footwrap{max-width:1100px;margin:auto;font-size:.85rem;color:#475569}.footwrap p{margin:4px 0}.footlinks{display:flex;gap:12px;flex-wrap:wrap}.footlinks a{color:#c2410c;text-decoration:none}.kofi{display:inline-flex;align-items:center;gap:6px;background:#13C3A5;color:#fff!important;border-radius:7px;padding:8px 12px;text-decoration:none;font-weight:700}.fine{color:#94a3b8;font-size:.78rem}@media(max-width:600px){.tag{display:none}.site-head nav{gap:10px}.site-head nav a{font-size:.8rem}}</style><script type="application/ld+json">{"@context":"https://schema.org","@type":"WebPage","name":"El Observatorio Ciudadano del Ferrocarril · Raíles","description":"Mapa esquemático de corredores de alta velocidad, estaciones y enlaces a retrasos de Renfe.","url":"https://radar.viajeinteligencia.com/railes.html"}</script></head><body><main class="wrap">
<header class="site-head"><div class="headwrap"><a class="brand" href="/railes.html"><span class="mark"></span><span class="brandtext">El Observatorio Ciudadano del Ferrocarril</span></a><span class="tag">Raíles · alta velocidad</span><nav><a href="/railes.html">Mapa</a><a href="/railes-cifras.html">Cifras</a><a href="/railes-inversiones.html">Inversiones</a><a href="/railes-fuentes.html">Fuentes</a><a href="/railes-about.html">About</a><a href="/retrasos-renfe-mapa.html">Retrasos</a><a href="/">Radar</a></nav><button class="themebtn" id="railes-theme" type="button" onclick="toggleRailesTheme()" aria-label="Cambiar tema">☾ Oscuro</button></div></header>
<p class="meta" style="margin:16px 0 0">El Observatorio Ciudadano del Ferrocarril</p><h1>Raíles</h1>
<p class="lead">La alta velocidad española, <b>eje a eje</b>. Un esquema de los corredores principales, sus estaciones y su velocidad. No es un trazado oficial ni una estimación de pasajeros por corredor.</p>
<p class="meta">Mapa esquemático · fuentes: Renfe/ADIF para estaciones y líneas; OpenStreetMap para el mapa base · actualizado con el build.</p>
<div class="hero-cta"><a class="btn primary" href="/railes-cifras.html">Ver cifras →</a><a class="btn" href="/retrasos-renfe-mapa.html">Retrasos en vivo</a></div>
<div class="layout"><div id="map" role="img" aria-label="Mapa esquemático de corredores de alta velocidad"></div>
<aside class="panel"><h2 id="p-name">Elige un eje</h2><p class="k" id="p-speed">—</p><p class="k" id="p-stations">—</p><div id="p-list" class="muted"></div><p style="margin-top:14px"><a href="/retrasos-renfe-mapa.html">Ver retrasos actuales →</a></p></aside></div>
<div class="kpis"><div class="kpi"><b id="k-axes">7</b><span>corredores</span></div><div class="kpi"><b id="k-stations">—</b><span>estaciones</span></div><div class="kpi"><b>300+</b><span>km/h máx.</span></div></div>
<div class="legend"><span><i class="dot" style="background:#ff5a1f"></i>Madrid–Sevilla</span><span><i class="dot" style="background:#3ddc97"></i>Madrid–Barcelona</span><span><i class="dot" style="background:#8ec5ff"></i>Levante</span><span><i class="dot" style="background:#f2c94c"></i>Norte</span><span><i class="dot" style="background:#bb6bd9"></i>Galicia</span><span><i class="dot" style="background:#56ccf2"></i>Asturias</span><span><i class="dot" style="background:#f28cb1"></i>Extremadura</span></div>
<div class="warn"><b>Qué es y qué no.</b> Es un <b>esquema de corredores</b>, no el trazado oficial. No atribuye pasajeros, inversión ni mantenimiento por eje: esos datos no existen con esa granularidad. Los retrasos son de Renfe y se ven en el mapa enlazado; no incluyen Iryo ni Ouigo.</div>
<div class="card"><h2>Cómo leerlo</h2><ul><li><b>Punto</b> = estación principal del corredor.</li><li><b>Línea</b> = conexión esquemática, no geometría oficial.</li><li><b>Velocidad</b> = máxima nominal del corredor; no se mide en tiempo real.</li><li><b>Uso</b> = solo hay datos agregados nacionales/anuales, no por eje.</li></ul><p class="muted">Para retrasos operativos: <a href="/retrasos-renfe-mapa.html">mapa de Renfe</a> · <a href="/retrasos-renfe-hoy.html">estado del día</a>. Para el panel anual de red, demanda y seguridad, la fuente debe ser Eurostat/ERA, no este mapa.</p></div>
<footer class="site-foot"><div class="footwrap"><p><strong>El Observatorio Ciudadano del Ferrocarril</strong> · alta velocidad, datos abiertos y límites explícitos.</p><p class="footlinks"><a href="/railes.html">Mapa</a><a href="/railes-cifras.html">Cifras</a><a href="/railes-inversiones.html">Inversiones</a><a href="/railes-fuentes.html">Fuentes</a><a href="/railes-about.html">About</a><a href="/retrasos-renfe-mapa.html">Retrasos Renfe</a><a href="/">Radar</a><a href="https://github.com/mcasrom/nearme-osint">Código</a></p><p><strong>Ecosistema:</strong> <a href="https://www.viajeinteligencia.com">ViajeInteligencia</a> · <a href="https://www.pruebapublica.com">Prueba Pública</a> · <a href="https://fimi.viajeinteligencia.com">FIMI</a> · <a href="https://analisis.pruebapublica.com">Análisis</a> · <a href="/railes-about.html#ecosistema">Todos los proyectos</a></p><p><a class="kofi" href="https://ko-fi.com/m_castillo" target="_blank" rel="noopener noreferrer">☕ Invítame a un café</a></p><p class="fine">Raíles v1.0 · AGPL-3.0 · Sin rastreo ni cuentas · Proyecto personal</p></div></footer>
</main><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const AXES=__AXES__;
const map=L.map('map',{scrollWheelZoom:false}).setView([40.2,-3.5],5);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18,attribution:'© OpenStreetMap'}).addTo(map);
const all=[]; const stations=new Set();
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
AXES.forEach(function(ax){
  const latlngs=ax.stations.map(s=>[s[1],s[2]]); all.push(...latlngs);
  L.polyline(latlngs,{color:ax.color,weight:5,opacity:.85,lineCap:'round'}).addTo(map).on('click',()=>select(ax));
  ax.stations.forEach(function(s){stations.add(s[0]); L.circleMarker([s[1],s[2]],{radius:5,color:'#fff',weight:2,fillColor:ax.color,fillOpacity:1}).addTo(map).bindPopup('<b>'+esc(s[0])+'</b><br>'+esc(ax.name)+'<br>'+esc(ax.speed));});
});
function select(ax){
  document.getElementById('p-name').textContent=ax.name;
  document.getElementById('p-speed').textContent='Velocidad nominal: '+ax.speed;
  document.getElementById('p-stations').textContent=ax.stations.length+' estaciones principales';
  document.getElementById('p-list').innerHTML='<ul>'+ax.stations.map(s=>'<li>'+esc(s[0])+'</li>').join('')+'</ul>';
}
document.getElementById('k-stations').textContent=stations.size;
map.fitBounds(all,{padding:[25,25]}); select(AXES[0]);
</script></body></html>'''

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--out",default=str(OUT)); a=ap.parse_args()
    import json
    html=HTML.replace("__AXES__",json.dumps(AXES,ensure_ascii=False))
    html=html.replace("</style>",THEME_CSS+"</style>").replace("</body>",THEME_JS+"</body>")
    Path(a.out).write_text(html,encoding="utf-8")
    print("railes ok",a.out,len(html))

if __name__=="__main__": main()
