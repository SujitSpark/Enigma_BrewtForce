"""Person 1 — AI analysis engine: compatibility → pathways → 7-dimension feasibility → explainable score.

S = Σ w_i · dim_i / Σ w_i   over  material, quantity, geography, processing, timing, environment, economics
Weights are a prototype design choice (configurable per request), not an official formula.
"""
from dataclasses import dataclass, field

from . import data, geo, impact, store

DIMENSIONS = ("material", "quantity", "geography", "processing", "timing", "environment", "economics")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
STRETCH = 1.5


# ---------------------------------------------------------------- context & scenario

@dataclass
class Context:
    sites: list = field(default_factory=list)
    hubs: list = field(default_factory=list)
    demand: dict = field(default_factory=dict)
    feedback: dict = field(default_factory=dict)

    @classmethod
    def build(cls) -> "Context":
        sites = data.sites()
        demand = {(d["industry_id"], d["material_id"]): d for d in data.demand_profiles()}
        return cls(sites=sites, hubs=[s for s in sites if s["kind"] == "processor"], demand=demand,
                   feedback=store.feedback())


def scenario(params: dict | None = None) -> dict:
    p = params or {}
    d = data.defaults()
    weights = {k: float(v) for k, v in (p.get("weights") or d["weights"]).items() if k in DIMENSIONS}
    return {
        "weights": {k: weights.get(k, 0.0) for k in DIMENSIONS},
        "max_road_km": p.get("max_road_km"),
        "transport_inr_per_tkm": p.get("transport_inr_per_tkm") or d["transport_inr_per_tkm"],
        "carbon_price_inr_per_t": p.get("carbon_price_inr_per_t") or 0,
        "use_hubs": p.get("use_hubs", True),
    }


# ---------------------------------------------------------------- helpers

def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))


LOCAL_HAUL_KM = 5.0


def _road(a: dict, b: dict) -> float:
    return round(max(LOCAL_HAUL_KM, geo.estimated_road_km(a["lat"], a["lon"], b["lat"], b["lon"])), 1)


def _quantity(supply_tpm: float, demand_tpm: float) -> float:
    """70% share of supply absorbed + 30% share of the buyer's demand met."""
    moved = min(supply_tpm, demand_tpm)
    return 0.7 * moved / supply_tpm + 0.3 * moved / demand_tpm


def _node(s: dict) -> dict:
    return {k: s.get(k) for k in ("id", "name", "sector", "kind", "city", "state", "district", "lat", "lon")}


def _monthly_exchange(supply_tpm, s_months, demand_tpm, d_months, cap_tpm=None) -> list[float]:
    out = []
    for s, d in zip(s_months, d_months):
        m = min(supply_tpm * s, demand_tpm * d)
        out.append(min(m, cap_tpm) if cap_tpm else m)
    return out


def _timing(s_months, d_months) -> float:
    num = sum(min(s, d) for s, d in zip(s_months, d_months))
    den = sum(max(s, d) for s, d in zip(s_months, d_months))
    return num / den if den else 0.0


def _low_months(s_months, d_months) -> list[str]:
    return [MONTHS[i] for i, (s, d) in enumerate(zip(s_months, d_months)) if abs(s - d) >= 0.4]


def _nearest_town(lat: float, lon: float) -> str:
    best = min(geo.GAZETTEER.values(), key=lambda g: geo.haversine_km(lat, lon, g[1], g[2]))
    return best[0]


def _feedback_multiplier(fb: dict | None) -> tuple[float, str | None]:
    if not fb:
        return 1.0, None
    yes, info, no = fb.get("interested", 0), fb.get("more_info", 0), fb.get("not_feasible", 0)
    mult = max(0.6, min(1.1, 1 + 0.05 * yes - 0.2 * no))
    parts = [f"{n} {label}" for n, label in ((yes, "interested"), (info, "asked for info"), (no, "not feasible")) if n]
    return mult, "Past responses from this buyer: " + ", ".join(parts)


# ---------------------------------------------------------------- evaluation of one pathway

def _evaluate(sup: dict, material: dict, use: dict, sc: dict, ctx: Context, *, kind: str, consumers: list[dict],
              demand_tpm: float, d_months: list, legs: list[dict], hub: dict | None = None,
              hub_capacity: float | None = None, proposed_hub: dict | None = None) -> dict:
    step = data.processing_step(use["processing"])
    radius = material["max_radius_km"]
    road_km = sum(l["km"] for l in legs)

    monthly = _monthly_exchange(sup["quantity_tpm"], sup["months"], demand_tpm, d_months, hub_capacity)
    q_tpy = sum(monthly)
    imp, econ = impact.calculate(material, use, step, q_tpy, road_km, sc)

    dims = {
        "material": use["compatibility"],
        "quantity": _quantity(sup["quantity_tpm"], demand_tpm),
        "geography": _clip(1 - road_km / (radius * STRETCH)),
        "processing": {"direct": 1.0, "in_house": 0.85, "via_hub": 0.6 + 0.2 * _clip((hub_capacity or 0) / max(1, sup["quantity_tpm"])),
                       "missing_hub": 0.25}[kind],
        "timing": _timing(sup["months"], d_months),
        "environment": impact.environment_score(imp),
        "economics": impact.economics_score(econ),
    }
    w = sc["weights"]
    base = sum(w[k] * dims[k] for k in DIMENSIONS) / (sum(w.values()) or 1)

    primary = consumers[0]
    fb_mult, fb_note = (1.0, None) if kind == "missing_hub" else _feedback_multiplier(ctx.feedback.get((primary["id"], material["id"])))
    score = round(100 * base * fb_mult)

    category = "hidden" if (kind == "missing_hub" or use["novel"]) else ("multi_step" if kind == "via_hub" else "direct")
    feas = "Strong" if road_km <= radius * 0.5 else "Viable" if road_km <= radius else "Stretch"
    net_per_t = imp["net_tco2e_per_year"] / q_tpy if q_tpy else 0

    proc_label = step["label"] if step else None
    processing_text = {
        "direct": "No treatment needed before use",
        "in_house": f"{proc_label} — done in-house by the buyer",
        "via_hub": f"{proc_label} at {hub['name'] if hub else ''} ({(hub_capacity or 0):,.0f} t/mo capacity)",
        "missing_hub": f"Needs {(proc_label or '').lower()} — no processing hub within range",
    }[kind]
    low = _low_months(sup["months"], d_months)
    checks = [
        ("material", dims["material"] >= 0.75, dims["material"] >= 0.55, f"{use['use']} — compatibility {round(use['compatibility'] * 100)}%"),
        ("quantity", dims["quantity"] >= 0.6, dims["quantity"] >= 0.3,
         f"Supply {sup['quantity_tpm']:,.0f} t/mo vs demand {demand_tpm:,.0f} t/mo → about {q_tpy / 12:,.0f} t/mo exchanged"),
        ("geography", road_km <= radius, road_km <= radius * STRETCH, f"{road_km:,.0f} km by road (economic radius {radius} km)"),
        ("processing", kind in ("direct", "in_house"), kind == "via_hub", processing_text),
        ("timing", dims["timing"] >= 0.85, dims["timing"] >= 0.6,
         "Supply and demand overlap all year" if not low else f"{round(dims['timing'] * 100)}% overlap — mismatch in {', '.join(low)}; plan storage"),
        ("environment", imp["net_positive"], net_per_t > -0.01,
         f"Net {imp['net_tco2e_per_year']:,.0f} tCO₂e/yr after processing & transport; {imp['waste_diverted_t']:,} t/yr diverted"),
        ("economics", econ["net_inr_per_year"] > 0, False, f"Net ₹{econ['net_inr_per_year'] / 1e5:,.1f} lakh/yr estimated business case"),
    ]
    reasons = [{"dimension": d, "status": "ok" if ok else ("warn" if warn else "bad"), "text": t} for d, ok, warn, t in checks]
    if fb_note:
        reasons.append({"dimension": "feedback", "status": "ok" if fb_mult >= 1 else "bad", "text": fb_note})

    if kind == "missing_hub":
        title = f"Missing link: {step['short']} hub near {proposed_hub['label'].split(',')[0]}"
    else:
        title = primary["name"]

    return {
        "id": f"{sup.get('site_id') or 'input'}|{material['id']}|{kind}|{'+'.join(c['id'] for c in consumers)}|{hub['id'] if hub else ''}",
        "title": title,
        "category": category,
        "pathway_type": kind,
        "novel_use": use["novel"],
        "consumer": _node(primary),
        "consumers": [_node(c) for c in consumers],
        "hub": _node(hub) if hub else None,
        "proposed_hub": proposed_hub,
        "use": use["use"],
        "consumer_sector": use["consumer_sector"],
        "virgin_input": use["virgin_input"],
        "standards": use["standards"],
        "processing": {"step": use["processing"], "label": proc_label, "where": kind},
        "legs": legs,
        "road_km": round(road_km, 1),
        "distance_source": "live-osrm" if legs and all(l["source"] == "live-osrm" for l in legs) else "estimated",
        "volume": {"supply_tpm": sup["quantity_tpm"], "demand_tpm": round(demand_tpm), "exchanged_tpy": round(q_tpy),
                   "monthly": [round(m) for m in monthly], "supply_months": sup["months"], "demand_months": d_months},
        "dimensions": {k: round(v * 100) for k, v in dims.items()},
        "weights": w,
        "feedback_multiplier": round(fb_mult, 2),
        "score": score,
        "feasibility": feas,
        "carbon_negative": not imp["net_positive"],
        "impact": imp,
        "economics": econ,
        "environmental_score": round(dims["environment"] * 100),
        "pathways": impact.pathways(material["id"], sup.get("sector"), use["consumer_sector"], imp["net_tco2e_per_year"]),
        "reasons": reasons,
    }


# ---------------------------------------------------------------- discovery for one supply stream

def find_opportunities(sup: dict, sc: dict, ctx: Context | None = None, live: bool = False, limit: int = 12) -> list[dict]:
    """sup = {material_id, quantity_tpm, months, lat, lon, sector, site_id?, label?}"""
    ctx = ctx or Context.build()
    material = data.materials()[sup["material_id"]]
    uses = {u["consumer_sector"]: u for u in material["uses"]}
    limit_km = sc["max_road_km"] or material["max_radius_km"] * STRETCH
    origin = {"lat": sup["lat"], "lon": sup["lon"]}

    out, unmet = [], {}
    for site in ctx.sites:
        if site["kind"] == "processor" or site["id"] == sup.get("site_id"):
            continue
        use = uses.get(site["sector"])
        prof = ctx.demand.get((site["id"], material["id"]))
        if not use or not prof:
            continue
        demand_tpm = prof.get("quantity_tpm") or use["typical_demand_tpm"]
        d_months = prof.get("months") or data.seasonality(site["sector"])
        direct_km = _road(origin, site)

        if not use["processing"] or site["sector"] in use["in_house_sectors"]:
            if direct_km > limit_km:
                continue
            kind = "in_house" if use["processing"] else "direct"
            out.append(_evaluate(sup, material, use, sc, ctx, kind=kind, consumers=[site], demand_tpm=demand_tpm,
                                 d_months=d_months, legs=[{"from": "supplier", "to": site["id"], "km": direct_km, "source": "estimated"}]))
            continue

        best = None
        if sc["use_hubs"]:
            for hub in ctx.hubs:
                cap = next((c["capacity_tpm"] for c in hub.get("capabilities", []) if c["step"] == use["processing"]), None)
                if not cap:
                    continue
                k1, k2 = _road(origin, hub), _road(hub, site)
                if k1 + k2 <= limit_km and (best is None or k1 + k2 < best[1] + best[2]):
                    best = (hub, k1, k2, cap)
        if best:
            hub, k1, k2, cap = best
            out.append(_evaluate(sup, material, use, sc, ctx, kind="via_hub", consumers=[site], demand_tpm=demand_tpm,
                                 d_months=d_months, hub=hub, hub_capacity=cap,
                                 legs=[{"from": "supplier", "to": hub["id"], "km": k1, "source": "estimated"},
                                       {"from": hub["id"], "to": site["id"], "km": k2, "source": "estimated"}]))
        elif direct_km <= limit_km:
            unmet.setdefault(use["processing"], []).append((site, use, demand_tpm, d_months, direct_km))

    # Hidden opportunities: demand that exists but lacks a processing step → propose the missing hub.
    for step_id, group in unmet.items():
        total_demand = sum(g[2] for g in group)
        wsum = sum(g[2] for g in group)
        c_lat = sum(g[0]["lat"] * g[2] for g in group) / wsum
        c_lon = sum(g[0]["lon"] * g[2] for g in group) / wsum
        h_lat = sup["lat"] + (c_lat - sup["lat"]) / 3
        h_lon = sup["lon"] + (c_lon - sup["lon"]) / 3
        proposed = {"lat": round(h_lat, 3), "lon": round(h_lon, 3), "label": _nearest_town(h_lat, h_lon), "step": step_id,
                    "step_label": data.processing_step(step_id)["label"], "catchment_demand_tpm": round(total_demand)}
        hub_pt = {"lat": h_lat, "lon": h_lon}
        k1 = _road(origin, hub_pt)
        k2 = sum(_road(hub_pt, g[0]) * g[2] for g in group) / wsum
        consumers = [g[0] for g in sorted(group, key=lambda g: -g[2])]
        use = group[0][1]
        months = [sum(g[3][i] * g[2] for g in group) / wsum for i in range(12)]
        out.append(_evaluate(sup, material, use, sc, ctx, kind="missing_hub", consumers=consumers, demand_tpm=total_demand,
                             d_months=[round(m, 2) for m in months], proposed_hub=proposed,
                             legs=[{"from": "supplier", "to": "proposed-hub", "km": k1, "source": "estimated"},
                                   {"from": "proposed-hub", "to": "catchment", "km": round(k2, 1), "source": "estimated"}]))

    out.sort(key=lambda o: o["score"], reverse=True)
    out = out[:limit]
    if live:
        out = _refine_live(out, sup, material, sc, ctx)
    return out


def _refine_live(opps: list[dict], sup: dict, material: dict, sc: dict, ctx: Context) -> list[dict]:
    site_by_id = {s["id"]: s for s in ctx.sites}
    points = {"supplier": {"lat": sup["lat"], "lon": sup["lon"]}}
    pairs, index = [], []
    for oi, o in enumerate(opps):
        if o["pathway_type"] == "missing_hub":
            continue
        for li, leg in enumerate(o["legs"]):
            a = points.get(leg["from"]) or site_by_id[leg["from"]]
            b = site_by_id[leg["to"]]
            pairs.append((a["lat"], a["lon"], b["lat"], b["lon"]))
            index.append((oi, li))
    for (oi, li), km in zip(index, geo.live_road_km(pairs)):
        if km is not None:
            opps[oi]["legs"][li] = {**opps[oi]["legs"][li], "km": km, "source": "live-osrm"}

    uses = {u["consumer_sector"]: u for u in material["uses"]}
    refined = []
    for o in opps:
        if o["pathway_type"] == "missing_hub" or all(l["source"] == "estimated" for l in o["legs"]):
            refined.append(o)
            continue
        consumer = site_by_id[o["consumer"]["id"]]
        hub = site_by_id.get(o["hub"]["id"]) if o["hub"] else None
        cap = next((c["capacity_tpm"] for c in hub.get("capabilities", []) if c["step"] == o["processing"]["step"]), None) if hub else None
        refined.append(_evaluate(sup, material, uses[o["consumer_sector"]], sc, ctx, kind=o["pathway_type"],
                                 consumers=[consumer], demand_tpm=o["volume"]["demand_tpm"],
                                 d_months=o["volume"]["demand_months"], legs=o["legs"], hub=hub, hub_capacity=cap))
    limit_km = sc["max_road_km"] or material["max_radius_km"] * STRETCH
    refined = [o for o in refined if o["road_km"] <= limit_km * 1.1]
    refined.sort(key=lambda o: o["score"], reverse=True)
    return refined


# ---------------------------------------------------------------- network-wide discovery

def allocate(opps: list[dict], supply_tpy: float) -> list[dict]:
    """Greedy allocation of one stream's supply across its best opportunities (avoids double counting)."""
    remaining, out = supply_tpy, []
    for o in sorted(opps, key=lambda x: x["score"], reverse=True):
        if remaining <= 0 or (not o["impact"]["net_positive"] and o["economics"]["net_inr_per_year"] <= 0):
            continue
        take = min(remaining, o["volume"]["exchanged_tpy"])
        share = take / o["volume"]["exchanged_tpy"] if o["volume"]["exchanged_tpy"] else 0
        remaining -= take
        out.append({"id": o["id"], "tonnes": take, "tco2e": o["impact"]["net_tco2e_per_year"] * share,
                    "inr": o["economics"]["net_inr_per_year"] * share})
    return out


def network(sc: dict, per_stream: int = 4) -> dict:
    ctx = Context.build()
    site_by_id = {s["id"]: s for s in ctx.sites}
    streams, opportunities = [], []
    for p in data.supply_profiles():
        src = site_by_id.get(p["industry_id"])
        if not src:
            continue
        sup = {"material_id": p["material_id"], "quantity_tpm": p["quantity_tpm"], "months": p.get("months") or [1] * 12,
               "lat": src["lat"], "lon": src["lon"], "sector": src["sector"], "site_id": src["id"], "label": src["name"]}
        opps = find_opportunities(sup, sc, ctx, live=False, limit=per_stream)
        for o in opps:
            o["producer"] = _node(src)
            o["material_id"] = p["material_id"]
            o["material_name"] = data.materials()[p["material_id"]]["name"]
        alloc = allocate(opps, p["quantity_tpm"] * 12)
        streams.append({"producer": _node(src), "material_id": p["material_id"],
                        "material_name": data.materials()[p["material_id"]]["name"],
                        "supply_tpm": p["quantity_tpm"], "allocation": alloc})
        opportunities.extend(opps)
    opportunities.sort(key=lambda o: o["score"], reverse=True)
    return {"streams": streams, "opportunities": opportunities}
