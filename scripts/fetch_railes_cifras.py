#!/usr/bin/env python3
import json, urllib.parse, urllib.request
from pathlib import Path
GEOS=["ES","FR","DE","IT","EU27_2020"]
BASE="https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/rail_pa_total"
def get(unit):
    q=urllib.parse.urlencode([("format","JSON"),("lang","EN"),("unit",unit),("time","2023")]+[("geo",g) for g in GEOS])
    req=urllib.request.Request(BASE+"?"+q,headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req,timeout=30) as r: return json.load(r)
out={"year":2023,"source":"Eurostat · RAIL_PA_TOTAL","source_url":"https://doi.org/10.2908/RAIL_PA_TOTAL","note":"Ferrocarril total; Eurostat no desglosa alta velocidad.","countries":[]}
by={}
for code,unitkey in (("pax_m","THS_PAS"),("pkm_bn","MIO_PKM")):
 d=get(unitkey); idx=d["dimension"]["geo"]["category"]["index"]; vals=d.get("value",{})
 for geo,pos in idx.items():
  by.setdefault(geo,{"code":geo})[code]=vals.get(str(pos))
for geo in GEOS:
 row=by.get(geo)
 if not row: continue
 if row.get("pax_m") is not None: row["pax_m"]=round(row["pax_m"]/1000,1)
 if row.get("pkm_bn") is not None: row["pkm_bn"]=round(row["pkm_bn"]/1000,1)
 out["countries"].append(row)
with open("/var/www/radar/datos/railes-cifras.json","w",encoding="utf-8") as f:
 json.dump(out,f,ensure_ascii=False,indent=2)
print(json.dumps(out,ensure_ascii=False,indent=2))
