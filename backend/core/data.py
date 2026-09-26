import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load(name: str) -> dict:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


@lru_cache
def _materials_file() -> dict:
    return _load("materials.json")


def materials() -> dict:
    return {m["id"]: m for m in _materials_file()["materials"]}


def defaults() -> dict:
    return _materials_file()["defaults"]


def processing_step(step_id: str | None) -> dict | None:
    return _materials_file()["processing_steps"].get(step_id) if step_id else None


def seasonality(sector: str) -> list[float]:
    s = _materials_file()["demand_seasonality"]
    return s.get(sector, s["default"])


@lru_cache
def geojson() -> dict:
    return _load("industries.geojson")


@lru_cache
def _base_sites() -> tuple:
    out = []
    for f in geojson()["features"]:
        lon, lat = f["geometry"]["coordinates"]
        out.append({**f["properties"], "lat": lat, "lon": lon, "custom": False})
    return tuple(out)


@lru_cache
def _base_profiles() -> dict:
    return _load("profiles.json")


@lru_cache
def schemes() -> tuple:
    return tuple(_load("schemes.json")["schemes"])


# ---- merged views (base dataset + user-added what-if industries) ----

def sites() -> list[dict]:
    from . import store
    return list(_base_sites()) + [c["site"] for c in store.custom_industries()]


def site(site_id: str) -> dict | None:
    return next((s for s in sites() if s["id"] == site_id), None)


def supply_profiles() -> list[dict]:
    from . import store
    custom = [p for c in store.custom_industries() for p in c["supply"]]
    return _base_profiles()["supply"] + custom


def demand_profiles() -> list[dict]:
    from . import store
    custom = [p for c in store.custom_industries() for p in c["demand"]]
    return _base_profiles()["demand"] + custom


def demand_for(site_row: dict, material_id: str, use: dict) -> dict | None:
    """Demand profile of a consumer for a material, filled with sector defaults."""
    prof = next((d for d in demand_profiles()
                 if d["industry_id"] == site_row["id"] and d["material_id"] == material_id), None)
    if not prof:
        return None
    return {
        "quantity_tpm": prof.get("quantity_tpm") or use["typical_demand_tpm"],
        "months": prof.get("months") or seasonality(site_row["sector"]),
        "basis": "profile" if prof.get("quantity_tpm") else "sector typical",
    }


def hubs() -> list[dict]:
    return [s for s in sites() if s["kind"] == "processor"]
