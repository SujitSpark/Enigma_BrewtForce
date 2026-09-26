import html
import re
import time

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from core import data, engine, geo, nlp, outreach, store

DEFAULT_QTY_PM = 1000

app = FastAPI(title="Industrial Symbiosis Discovery API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)
store.init()


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError):
    msgs = [f"{'.'.join(str(p) for p in e['loc'][1:]) or 'body'}: {e['msg']}" for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": "; ".join(msgs)})


# ---------------------------------------------------------------- models

class Scenario(BaseModel):
    weights: dict[str, float] | None = None
    max_road_km: float | None = Field(default=None, gt=0, le=3000)
    transport_inr_per_tkm: float | None = Field(default=None, gt=0, le=100)
    carbon_price_inr_per_t: float | None = Field(default=None, ge=0, le=50_000)
    use_hubs: bool = True


class ExtractRequest(BaseModel):
    text: str = Field(min_length=10, max_length=10_000)


class AnalyzeRequest(BaseModel):
    text: str | None = Field(default=None, max_length=10_000)
    material_id: str | None = None
    quantity_tpm: float | None = Field(default=None, gt=0, le=10_000_000)
    months: list[float] | None = Field(default=None, min_length=12, max_length=12)
    location: str | None = Field(default=None, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    scenario: Scenario = Scenario()
    live_routing: bool = True


class OutreachCreate(BaseModel):
    opportunity: dict
    supplier: dict
    material_name: str
    analysis_id: int | None = None
    recipient_email: str | None = Field(default=None, max_length=200)


class OutreachUpdate(BaseModel):
    status: str | None = None
    recipient_email: str | None = Field(default=None, max_length=200)
    response_note: str | None = Field(default=None, max_length=1000)
    subject: str | None = Field(default=None, max_length=300)
    body: str | None = Field(default=None, max_length=20_000)


class CustomIndustry(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    sector: str
    location: str = Field(min_length=2, max_length=200)
    role: str = Field(pattern="^(supplier|consumer|processor)$")
    material_id: str | None = None
    quantity_tpm: float | None = Field(default=None, gt=0, le=10_000_000)
    processing_step: str | None = None


# ---------------------------------------------------------------- reference data

@app.get("/api/health")
def health():
    return {"status": "ok", "materials": len(data.materials()), "sites": len(data.sites()),
            "hubs": len(data.hubs()), "schemes": len(data.schemes()), "smtp": outreach.smtp_configured()}


@app.get("/api/meta")
def meta():
    f = data._materials_file()
    sectors = sorted({s["sector"] for s in data.sites()})
    return {"dimensions": engine.DIMENSIONS, "default_weights": data.defaults()["weights"], "months": engine.MONTHS,
            "defaults": data.defaults(), "sectors": sectors,
            "processing_steps": [{"id": k, **v} for k, v in f["processing_steps"].items()],
            "materials": [{"id": m["id"], "name": m["name"], "source_sectors": m["source_sectors"],
                           "max_radius_km": m["max_radius_km"], "uses": [u["consumer_sector"] for u in m["uses"]]}
                          for m in data.materials().values()]}


@app.get("/api/geojson")
def geojson():
    feats = []
    for s in data.sites():
        props = {k: v for k, v in s.items() if k not in ("lat", "lon")}
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [s["lon"], s["lat"]]}, "properties": props})
    return {"type": "FeatureCollection", "features": feats}


@app.get("/api/schemes")
def schemes():
    return data.schemes()


@app.get("/api/materials/{material_id}")
def material_detail(material_id: str):
    m = data.materials().get(material_id)
    if not m:
        raise HTTPException(404, f"Unknown material '{material_id}'")
    by_id = {s["id"]: s for s in data.sites()}
    uses = {u["consumer_sector"]: u for u in m["uses"]}
    suppliers = [{**engine._node(by_id[p["industry_id"]]), "quantity_tpm": p["quantity_tpm"]}
                 for p in data.supply_profiles() if p["material_id"] == material_id and p["industry_id"] in by_id]
    consumers = []
    for d in data.demand_profiles():
        s = by_id.get(d["industry_id"])
        if d["material_id"] != material_id or not s or s["sector"] not in uses:
            continue
        consumers.append({**engine._node(s), "quantity_tpm": d.get("quantity_tpm") or uses[s["sector"]]["typical_demand_tpm"],
                          "use": uses[s["sector"]]["use"]})
    steps = {u["processing"] for u in m["uses"] if u["processing"]}
    hubs = [{**engine._node(h), "capabilities": h.get("capabilities", [])} for h in data.hubs()
            if any(c["step"] == st for c in h.get("capabilities", []) for st in steps)]
    return {
        "material": {k: m[k] for k in ("id", "name", "properties", "source_sectors", "max_radius_km",
                                        "disposal_cost_inr_per_t", "byproduct_price_inr_per_t")},
        "uses": [u | {"processing_label": (data.processing_step(u["processing"]) or {}).get("label")} for u in m["uses"]],
        "suppliers": sorted(suppliers, key=lambda s: -s["quantity_tpm"]),
        "consumers": sorted(consumers, key=lambda c: -c["quantity_tpm"]),
        "hubs": hubs,
        "totals": {"supply_tpm": sum(s["quantity_tpm"] for s in suppliers), "demand_tpm": sum(c["quantity_tpm"] for c in consumers)},
    }


# ---------------------------------------------------------------- analysis

@app.post("/api/extract")
def extract(req: ExtractRequest):
    return nlp.extract(req.text)


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    ex = nlp.extract(req.text) if req.text and req.text.strip() else None
    assumptions = []

    material_id = req.material_id or (ex and ex["material_id"])
    if not material_id:
        raise HTTPException(422, "Couldn't identify a by-product in the text. Pick a material and run again.")
    material = data.materials().get(material_id)
    if not material:
        raise HTTPException(422, f"Unknown material '{material_id}'")

    loc = geo.geocode(req.location) if req.location else (ex and ex["location"])
    if req.location and not loc:
        raise HTTPException(422, f"Couldn't locate '{req.location}' in India. Try a nearby city name.")
    if not loc:
        raise HTTPException(422, "No plant location found. Add the city where the material is generated.")

    qty = req.quantity_tpm or (ex and ex["quantity"] and ex["quantity"]["tonnes_per_month"])
    if not qty:
        qty = DEFAULT_QTY_PM
        assumptions.append(f"No quantity found; assumed {DEFAULT_QTY_PM:,} t/month")
    months = req.months or (ex and ex["availability"] and ex["availability"]["months"])
    if not months:
        months = [1] * 12
        assumptions.append("No availability window found; assumed year-round supply")

    sector = (ex and ex["sector"]) or material["source_sectors"][0]
    supplier = {"company": req.company or (ex and ex["company"]), "sector": sector, "location_label": loc["label"],
                "lat": loc["lat"], "lon": loc["lon"], "location_source": loc["source"]}
    sc = engine.scenario(req.scenario.model_dump())
    sup = {"material_id": material_id, "quantity_tpm": qty, "months": months, "lat": loc["lat"], "lon": loc["lon"],
           "sector": sector, "label": supplier["company"] or loc["label"]}

    opps = engine.find_opportunities(sup, sc, live=req.live_routing, limit=15)
    if req.live_routing and opps and all(o["distance_source"] == "estimated" for o in opps if o["pathway_type"] != "missing_hub"):
        assumptions.append("Live routing unavailable; road distance estimated as straight-line × 1.3")
    alloc = engine.allocate(opps, qty * 12)

    result = {
        "extraction": ex,
        "supplier": supplier,
        "material": {k: material[k] for k in ("id", "name", "properties", "max_radius_km")},
        "supply": {"quantity_tpm": qty, "months": months},
        "scenario": sc,
        "assumptions": assumptions,
        "opportunities": opps,
        "summary": {
            "count": len(opps),
            "by_category": {c: sum(o["category"] == c for o in opps) for c in ("direct", "multi_step", "hidden")},
            "allocated_tpy": round(sum(a["tonnes"] for a in alloc)),
            "allocated_tco2e": round(sum(a["tco2e"] for a in alloc)),
            "allocated_inr": round(sum(a["inr"] for a in alloc)),
            "supply_tpy": round(qty * 12),
        },
    }
    result["analysis_id"] = store.save_analysis(result)
    return result


_network_cache: dict = {}


def _network(sc_model: Scenario) -> dict:
    key = (sc_model.model_dump_json(), len(store.custom_industries()), str(store.feedback()))
    hit = _network_cache.get(key)
    if hit and time.time() - hit[0] < 300:
        return hit[1]
    result = engine.network(engine.scenario(sc_model.model_dump()))
    _network_cache.clear()
    _network_cache[key] = (time.time(), result)
    return result


def _totals(net: dict) -> dict:
    allocs = [a for s in net["streams"] for a in s["allocation"]]
    opps = net["opportunities"]
    tracked = store.list_outreach()
    return {
        "streams": len(net["streams"]),
        "waste_available_tpy": round(sum(s["supply_tpm"] for s in net["streams"]) * 12),
        "potentially_diverted_tpy": round(sum(a["tonnes"] for a in allocs)),
        "net_tco2e_per_year": round(sum(a["tco2e"] for a in allocs)),
        "net_inr_per_year": round(sum(a["inr"] for a in allocs)),
        "opportunities": len(opps),
        "by_category": {c: sum(o["category"] == c for o in opps) for c in ("direct", "multi_step", "hidden")},
        "active_exchanges": sum(t["status"] == "interested" for t in tracked),
        "awaiting_response": sum(t["status"] == "sent" for t in tracked),
    }


@app.post("/api/network")
def network(sc: Scenario = Scenario(), limit: int = Query(80, ge=1, le=300)):
    net = _network(sc)
    return {"totals": _totals(net), "streams": net["streams"], "opportunities": net["opportunities"][:limit]}


@app.get("/api/overview")
def overview():
    net = _network(Scenario())
    tracked = store.list_outreach()
    return {
        "totals": _totals(net),
        "top": net["opportunities"][:40],
        "responses": [t for t in tracked if t["status"] in store.RESPONSES][:8],
        "hubs": [engine._node(h) | {"capabilities": h.get("capabilities", [])} for h in data.hubs()],
    }


@app.get("/api/history")
def history(limit: int = Query(10, ge=1, le=50)):
    return store.history(limit)


@app.get("/api/history/{analysis_id}")
def history_item(analysis_id: int):
    item = store.get_analysis(analysis_id)
    if not item:
        raise HTTPException(404, "Analysis not found")
    return item | {"analysis_id": analysis_id}


# ---------------------------------------------------------------- outreach & response loop

def _outreach_view(rec: dict) -> dict:
    base = f"{outreach.public_base_url()}/respond/{rec['token']}"
    return rec | {"response_links": {k: f"{base}/{k}" for k in outreach.RESPONSE_LABELS}}


@app.get("/api/outreach")
def list_outreach():
    return [_outreach_view(r) for r in store.list_outreach()]


@app.post("/api/outreach")
def create_outreach(req: OutreachCreate):
    o = req.opportunity
    required = {"id", "consumer", "use", "virgin_input", "volume", "impact", "economics", "score", "pathway_type"}
    if not required <= o.keys():
        raise HTTPException(422, "Opportunity payload is incomplete")
    rec = store.create_outreach({
        "analysis_id": req.analysis_id, "opportunity_id": o["id"],
        "supplier_name": req.supplier.get("company"), "supplier_location": req.supplier.get("location_label"),
        "material_id": o.get("material_id") or o["id"].split("|")[1], "material_name": req.material_name,
        "consumer_id": o["consumer"]["id"] if o["pathway_type"] != "missing_hub" else None,
        "consumer_name": o["consumer"]["name"], "pathway_type": o["pathway_type"], "score": o["score"],
        "net_tco2e_per_year": o["impact"]["net_tco2e_per_year"], "net_inr_per_year": o["economics"]["net_inr_per_year"],
        "recipient_email": req.recipient_email, "subject": "(pending)", "body": "(pending)",
    })
    email = outreach.draft(o, req.supplier, req.material_name, token=rec["token"])
    return _outreach_view(store.update_outreach(rec["id"], subject=email["subject"], body=email["body"]))


@app.patch("/api/outreach/{outreach_id}")
def update_outreach(outreach_id: int, req: OutreachUpdate):
    if not store.get_outreach(outreach_id):
        raise HTTPException(404, "Outreach not found")
    fields = {k: v for k, v in req.model_dump().items() if v is not None}
    if "status" in fields and fields["status"] not in store.STATUSES:
        raise HTTPException(422, f"Status must be one of {', '.join(store.STATUSES)}")
    return _outreach_view(store.update_outreach(outreach_id, **fields))


@app.post("/api/outreach/{outreach_id}/send")
def send_outreach(outreach_id: int):
    rec = store.get_outreach(outreach_id)
    if not rec:
        raise HTTPException(404, "Outreach not found")
    if not rec["recipient_email"] or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", rec["recipient_email"]):
        raise HTTPException(422, "Add a valid recipient email first")
    if not outreach.smtp_configured():
        raise HTTPException(409, "SMTP is not configured on the server. Use 'Open in mail app', then mark it as sent.")
    try:
        outreach.send(rec["recipient_email"], rec["subject"], rec["body"])
    except Exception as e:
        raise HTTPException(502, f"Sending failed: {e}") from e
    return _outreach_view(store.update_outreach(outreach_id, status="sent"))


@app.get("/respond/{token}/{status}", response_class=HTMLResponse)
def respond(token: str, status: str):
    rec = store.outreach_by_token(token)
    if not rec or status not in store.RESPONSES:
        return HTMLResponse("<h1>Link not recognised</h1>", status_code=404)
    store.update_outreach(rec["id"], status=status)
    label = outreach.RESPONSE_LABELS[status]
    return HTMLResponse(f"""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Response recorded</title>
<body style="font-family:system-ui;max-width:520px;margin:15vh auto;padding:0 16px;color:#17191b;background:#f4f2ec">
<h1 style="font-size:20px">Thanks, your response was recorded</h1>
<p>You marked <b>{html.escape(rec['material_name'])}</b> from <b>{html.escape(rec['supplier_name'] or 'the supplier')}</b>
as <b>{label}</b>. The supplier will see this in their dashboard.</p></body>""")


# ---------------------------------------------------------------- what-if: add industries

@app.get("/api/custom-industries")
def list_custom():
    return store.custom_industries()


@app.post("/api/custom-industries")
def add_custom(req: CustomIndustry):
    loc = geo.geocode(req.location)
    if not loc:
        raise HTTPException(422, f"Couldn't locate '{req.location}' in India")
    if req.role != "processor" and req.material_id not in data.materials():
        raise HTTPException(422, "Choose a material for this industry")
    if req.role == "processor" and not data.processing_step(req.processing_step):
        raise HTTPException(422, "Choose a processing capability")
    site_id = f"x-{re.sub(r'[^a-z0-9]+', '-', req.name.lower()).strip('-')}-{int(time.time()) % 100000}"
    sector = "Processing" if req.role == "processor" else req.sector
    site = {"id": site_id, "name": req.name, "sector": sector, "kind": "processor" if req.role == "processor" else "custom",
            "city": loc["label"], "state": None, "district": None, "industry_type": "User-added", "lat": loc["lat"],
            "lon": loc["lon"], "custom": True}
    payload = {"site": site, "supply": [], "demand": []}
    if req.role == "processor":
        site["capabilities"] = [{"step": req.processing_step, "capacity_tpm": req.quantity_tpm or 10000}]
    elif req.role == "supplier":
        payload["supply"].append({"industry_id": site_id, "material_id": req.material_id,
                                  "quantity_tpm": req.quantity_tpm or DEFAULT_QTY_PM, "months": [1] * 12})
    else:
        payload["demand"].append({"industry_id": site_id, "material_id": req.material_id,
                                  "quantity_tpm": req.quantity_tpm, "months": None})
    store.add_custom_industry(payload)
    return payload


@app.delete("/api/custom-industries/{site_id}")
def delete_custom(site_id: str):
    if not store.delete_custom_industry(site_id):
        raise HTTPException(404, "Not found")
    return {"deleted": site_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)
