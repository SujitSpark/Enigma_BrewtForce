"""Person 2 — environmental impact, economics and policy-pathway mapping.

Net CO2e  = Q·EF_virgin − Q·EF_processing − Q·D·EF_transport
Economics = virgin savings + disposal savings + carbon value − transport − processing
Q is the quantity actually reused (after quantity and timing limits), not the quantity generated.
"""
from . import data


def calculate(material: dict, use: dict, step: dict | None, q_tpy: float, road_km: float, sc: dict) -> tuple[dict, dict]:
    d = data.defaults()
    ef_proc = step["tco2e_per_t"] if step else d["handling_tco2e_per_t"]

    virgin = q_tpy * use["avoided_tco2e_per_t"]
    processing = q_tpy * ef_proc
    transport = q_tpy * road_km * d["transport_tco2e_per_tkm"]
    net = virgin - processing - transport
    margin = use["avoided_tco2e_per_t"] - ef_proc
    breakeven = margin / d["transport_tco2e_per_tkm"] if margin > 0 else 0

    impact = {
        "waste_diverted_t": round(q_tpy),
        "virgin_replaced_t": round(q_tpy * use["substitution_ratio"]),
        "virgin_input": use["virgin_input"],
        "e_virgin_avoided": round(virgin, 1),
        "e_processing": round(processing, 1),
        "e_transport": round(transport, 1),
        "net_tco2e_per_year": round(net, 1),
        "carbon_breakeven_km": round(breakeven),
        "net_positive": net > 0,
    }

    virgin_savings = q_tpy * use["substitution_ratio"] * use["virgin_price_inr_per_t"]
    disposal_savings = q_tpy * material["disposal_cost_inr_per_t"]
    transport_cost = q_tpy * road_km * sc["transport_inr_per_tkm"]
    processing_cost = q_tpy * (step["cost_inr_per_t"] if step else 0)
    carbon_value = net * sc["carbon_price_inr_per_t"]
    net_inr = virgin_savings + disposal_savings + carbon_value - transport_cost - processing_cost

    economics = {
        "virgin_savings_inr": round(virgin_savings),
        "disposal_savings_inr": round(disposal_savings),
        "carbon_value_inr": round(carbon_value),
        "transport_cost_inr": round(transport_cost),
        "processing_cost_inr": round(processing_cost),
        "net_inr_per_year": round(net_inr),
        "net_inr_per_t": round(net_inr / q_tpy) if q_tpy else 0,
        "byproduct_revenue_inr": round(q_tpy * material["byproduct_price_inr_per_t"]),
        "byproduct_price_inr_per_t": material["byproduct_price_inr_per_t"],
        "carbon_price_inr_per_t": sc["carbon_price_inr_per_t"],
        "transport_inr_per_tkm": sc["transport_inr_per_tkm"],
    }
    return impact, economics


def environment_score(impact: dict) -> float:
    """0..1 — 40% for diverting waste, 60% carbon: 0.5 at net zero, 1.0 at ≥ +0.3 tCO2e/t, 0 at ≤ −0.3."""
    q = impact["waste_diverted_t"]
    if q <= 0:
        return 0.0
    intensity = impact["net_tco2e_per_year"] / q
    carbon = max(0.0, min(1.0, 0.5 + 0.5 * intensity / 0.3))
    return 0.4 + 0.6 * carbon


def economics_score(econ: dict) -> float:
    gross = econ["virgin_savings_inr"] + econ["disposal_savings_inr"] + max(0, econ["carbon_value_inr"])
    return max(0.0, min(1.0, econ["net_inr_per_year"] / gross)) if gross > 0 else 0.0


def pathways(material_id: str, producer_sector: str | None, consumer_sector: str | None, net_tco2e: float) -> list[dict]:
    out = []
    for s in data.schemes():
        cond = s["applies_if"]
        reasons = []
        if material_id in cond.get("materials", []):
            reasons.append("material")
        if producer_sector and producer_sector in cond.get("producer_sectors", []):
            reasons.append("supplier sector")
        if consumer_sector and consumer_sector in cond.get("consumer_sectors", []) \
                and net_tco2e >= cond.get("min_net_tco2e_per_year", 0):
            reasons.append("buyer sector + CO₂ reduction")
        if reasons:
            out.append({k: s[k] for k in ("id", "name", "authority", "year", "type", "relevance", "verify", "portal")}
                       | {"matched_on": reasons, "status": "Potentially applicable — eligibility verification required"})
    return out
