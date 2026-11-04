#!/usr/bin/env python3
import json, urllib.parse, urllib.request, io
from pathlib import Path
import openpyxl
GEOS=["ES","FR","DE","IT"]
BASE="https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/rail_pa_total"
ERA_URL="https://www.era.europa.eu/sites/default/files/2025-11/csidata_2006-2024.xlsx"
def get(unit):
    q=urllib.parse.urlencode([("format","JSON"),("lang","EN"),("unit",unit),("sinceTimePeriod","2013")]+[("geo",g) for g in GEOS])
    req=urllib.request.Request(BASE+"?"+q,headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req,timeout=30) as r: return json.load(r)
def decode(d,div):
    sizes=d["size"]; times=sorted(d["dimension"]["time"]["category"]["index"].items(),key=lambda x:int(x[0])); geoidx=d["dimension"]["geo"]["category"]["index"]
    out={}
    for g in GEOS:
        gi=geoidx[g]; row={}
        for t,ti in times:
            pos=(((0*sizes[1]+0)*sizes[2]+gi)*sizes[3]+ti)
            v=d.get("value",{}).get(str(pos)); row[t]=None if v is None else round(v/div,1)
        out[g]=row
    return [t for t,_ in times],out
def era_table(wb,name,code):
    ws=wb[name]; rows=list(ws.iter_rows(values_only=True)); hdr=next(r for r in rows if r and "Code" in r)
    cols={hdr[i]:i for i in range(len(hdr)) if isinstance(hdr[i],str) and len(hdr[i])==2}
    cur=None; out={}
    for r in rows:
        if len(r)>3 and r[1] is not None: cur=r[1]
        if cur==code and isinstance(r[3],int): out[r[3]]={c:r[cols[c]] for c in GEOS}
    return out
# Eurostat total rail, 2013-2024. 2025 exists but is provisional; not used.
pax_years,pax=decode(get("THS_PAS"),1000)
pkm_years,pkm=decode(get("MIO_PKM"),1000)
years=[y for y in pax_years if int(y)<=2024]
# ERA CSIs 2006-2024
req=urllib.request.Request(ERA_URL,headers={"User-Agent":"Mozilla/5.0"})
wb=openpyxl.load_workbook(io.BytesIO(urllib.request.urlopen(req,timeout=60).read()),read_only=True,data_only=True)
acc=era_table(wb,"Table 0","N00"); km=era_table(wb,"Table 6","R01")
sy=sorted(set(acc)&set(km))
safety={"source":"ERA · Common Safety Indicators (CSIs) 2006-2024","source_url":"https://www.era.europa.eu/domains/accident-incident/common-safety-indicators-csis","updated":"2026-01-14","years":sy,"accidents":{g:[acc[y].get(g) for y in sy] for g in GEOS},"train_km_m":{g:[round(km[y].get(g),3) if km[y].get(g) is not None else None for y in sy] for g in GEOS}}
safety["rate_per_million_train_km"]={g:[round(acc[y][g]/km[y][g],3) if acc[y].get(g) is not None and km[y].get(g) else None for y in sy] for g in GEOS}
out={"year":2024,"source":"Eurostat · RAIL_PA_TOTAL","source_url":"https://doi.org/10.2908/RAIL_PA_TOTAL","note":"Ferrocarril total; Eurostat no desglosa alta velocidad. Serie 2013-2024; 2025 no se usa por provisional.","countries":[{"code":g,"pax_m":pax[g]["2024"],"pkm_bn":pkm[g]["2024"]} for g in GEOS],"series":{"years":years,"pax_m":{g:[pax[g][y] for y in years] for g in GEOS},"pkm_bn":{g:[pkm[g][y] for y in years] for g in GEOS}},"hs":{"source":"UIC High-Speed Atlas 2025","source_url":"https://uic.org/activities/high-speed-data-and-atlas","network_state":"2024-12-31","traffic_year":2023,"lines_km":{"ES":3993,"FR":2760,"DE":1941,"IT":1097},"traffic_pkm_bn":{"ES":15.3,"FR":59.7,"DE":38.0,"IT":26.0}},"context":{"source":"Banco Mundial · SP.POP.TOTL y AG.SRF.TOTL.K2","source_url":"https://data.worldbank.org/indicator/SP.POP.TOTL","year":2023,"population":{"ES":48352528,"FR":68372286,"DE":83287273,"IT":58984216},"area_km2":{"ES":505975.98,"FR":606410.0,"DE":357680.0,"IT":302070.0}},"safety":safety}
ctx=out["context"]
ctx["hs_density_per_1000_km2"]={k:round(out["hs"]["lines_km"][k]/v*1000,2) for k,v in ctx["area_km2"].items()}
ctx["hs_km_per_million_inhabitants"]={k:round(out["hs"]["lines_km"][k]/(v/1_000_000),2) for k,v in ctx["population"].items()}
ctx["hs_pkm_per_network_km_m"]={k:round(out["hs"]["traffic_pkm_bn"][k]*1000/out["hs"]["lines_km"][k],2) for k in GEOS}
ctx["hs_pkm_per_capita"]={k:round(out["hs"]["traffic_pkm_bn"][k]*1_000_000_000/ctx["population"][k],1) for k in GEOS}
with open("/var/www/radar/datos/railes-cifras.json","w",encoding="utf-8") as f: json.dump(out,f,ensure_ascii=False,indent=2)
print(json.dumps({"year":out["year"],"countries":out["countries"],"series_years":years,"hs":out["hs"],"context":ctx,"safety_last":{k:list(zip(safety["years"],safety["rate_per_million_train_km"][k]))[-5:] for k in GEOS}},ensure_ascii=False,indent=2))
