"""Person 3 — location intelligence: geocoding, distances, live road routing."""
import json
import math
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

from . import data

USER_AGENT = "IndustrialSymbiosisDiscovery/1.0 (hackathon prototype)"
HTTP_TIMEOUT = 4

# Town-level coordinates for common Indian industrial locations (offline fallback).
GAZETTEER = {
    "pune": ("Pune, Maharashtra", 18.52, 73.86),
    "chakan": ("Chakan, Maharashtra", 18.76, 73.86),
    "mumbai": ("Mumbai, Maharashtra", 19.08, 72.88),
    "navi mumbai": ("Navi Mumbai, Maharashtra", 19.03, 73.03),
    "thane": ("Thane, Maharashtra", 19.22, 72.98),
    "nagpur": ("Nagpur, Maharashtra", 21.15, 79.09),
    "chandrapur": ("Chandrapur, Maharashtra", 19.96, 79.30),
    "kolhapur": ("Kolhapur, Maharashtra", 16.70, 74.24),
    "nashik": ("Nashik, Maharashtra", 20.00, 73.79),
    "aurangabad": ("Chhatrapati Sambhajinagar, Maharashtra", 19.88, 75.34),
    "raigad": ("Raigad, Maharashtra", 18.52, 73.18),
    "dolvi": ("Dolvi, Maharashtra", 18.70, 73.03),
    "delhi": ("Delhi", 28.61, 77.21),
    "noida": ("Noida, Uttar Pradesh", 28.54, 77.39),
    "ghaziabad": ("Ghaziabad, Uttar Pradesh", 28.67, 77.45),
    "gurgaon": ("Gurugram, Haryana", 28.46, 77.03),
    "gurugram": ("Gurugram, Haryana", 28.46, 77.03),
    "faridabad": ("Faridabad, Haryana", 28.41, 77.32),
    "dadri": ("Dadri, Uttar Pradesh", 28.57, 77.55),
    "bangalore": ("Bengaluru, Karnataka", 12.97, 77.59),
    "bengaluru": ("Bengaluru, Karnataka", 12.97, 77.59),
    "ballari": ("Ballari, Karnataka", 15.14, 76.92),
    "bellary": ("Ballari, Karnataka", 15.14, 76.92),
    "hospet": ("Hosapete, Karnataka", 15.27, 76.39),
    "toranagallu": ("Toranagallu, Karnataka", 15.18, 76.66),
    "belgaum": ("Belagavi, Karnataka", 15.85, 74.50),
    "belagavi": ("Belagavi, Karnataka", 15.85, 74.50),
    "chennai": ("Chennai, Tamil Nadu", 13.08, 80.27),
    "coimbatore": ("Coimbatore, Tamil Nadu", 11.02, 76.96),
    "hyderabad": ("Hyderabad, Telangana", 17.39, 78.49),
    "visakhapatnam": ("Visakhapatnam, Andhra Pradesh", 17.69, 83.22),
    "vizag": ("Visakhapatnam, Andhra Pradesh", 17.69, 83.22),
    "kolkata": ("Kolkata, West Bengal", 22.57, 88.36),
    "durgapur": ("Durgapur, West Bengal", 23.52, 87.31),
    "jamshedpur": ("Jamshedpur, Jharkhand", 22.80, 86.20),
    "ranchi": ("Ranchi, Jharkhand", 23.34, 85.31),
    "bokaro": ("Bokaro, Jharkhand", 23.67, 86.15),
    "dhanbad": ("Dhanbad, Jharkhand", 23.80, 86.43),
    "rourkela": ("Rourkela, Odisha", 22.26, 84.85),
    "kalinganagar": ("Kalinganagar, Odisha", 20.95, 85.98),
    "angul": ("Angul, Odisha", 20.84, 85.10),
    "paradeep": ("Paradeep, Odisha", 20.26, 86.67),
    "paradip": ("Paradeep, Odisha", 20.26, 86.67),
    "bhubaneswar": ("Bhubaneswar, Odisha", 20.30, 85.82),
    "cuttack": ("Cuttack, Odisha", 20.46, 85.88),
    "lanjigarh": ("Lanjigarh, Odisha", 19.71, 83.40),
    "bhilai": ("Bhilai, Chhattisgarh", 21.19, 81.38),
    "raipur": ("Raipur, Chhattisgarh", 21.25, 81.63),
    "korba": ("Korba, Chhattisgarh", 22.35, 82.68),
    "singrauli": ("Singrauli, Madhya Pradesh", 24.20, 82.67),
    "indore": ("Indore, Madhya Pradesh", 22.72, 75.86),
    "ahmedabad": ("Ahmedabad, Gujarat", 23.02, 72.57),
    "vadodara": ("Vadodara, Gujarat", 22.31, 73.18),
    "surat": ("Surat, Gujarat", 21.17, 72.83),
    "hazira": ("Hazira, Gujarat", 21.10, 72.64),
    "rajkot": ("Rajkot, Gujarat", 22.30, 70.80),
    "jaipur": ("Jaipur, Rajasthan", 26.91, 75.79),
    "ludhiana": ("Ludhiana, Punjab", 30.90, 75.85),
    "kanpur": ("Kanpur, Uttar Pradesh", 26.45, 80.33),
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def estimated_road_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    return haversine_km(lat1, lon1, lat2, lon2) * data.defaults()["road_circuity_factor"]


def _get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def find_in_gazetteer(text: str) -> dict | None:
    lowered = text.lower()
    for key in sorted(GAZETTEER, key=len, reverse=True):
        if re.search(rf"\b{re.escape(key)}\b", lowered):
            label, lat, lon = GAZETTEER[key]
            return {"label": label, "lat": lat, "lon": lon, "source": "gazetteer"}
    return None


@lru_cache(maxsize=256)
def geocode(place: str) -> dict | None:
    """Gazetteer first, then live OpenStreetMap Nominatim lookup restricted to India."""
    hit = find_in_gazetteer(place)
    if hit:
        return hit
    query = urllib.parse.urlencode({"q": place, "countrycodes": "in", "format": "json", "limit": 1})
    try:
        results = _get_json(f"https://nominatim.openstreetmap.org/search?{query}")
    except Exception:
        return None
    if not results:
        return None
    r = results[0]
    return {
        "label": r.get("display_name", place).split(",")[0] + ", India",
        "lat": round(float(r["lat"]), 4),
        "lon": round(float(r["lon"]), 4),
        "source": "openstreetmap",
    }


@lru_cache(maxsize=1024)
def _osrm_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float | None:
    url = (
        "https://router.project-osrm.org/route/v1/driving/"
        f"{lon1},{lat1};{lon2},{lat2}?overview=false"
    )
    try:
        payload = _get_json(url)
        if payload.get("code") != "Ok" or not payload.get("routes"):
            return None
        return round(payload["routes"][0]["distance"] / 1000, 1)
    except Exception:
        return None


def live_road_km(pairs: list[tuple[float, float, float, float]]) -> list[float | None]:
    """Fetch live road distances for several origin/destination pairs in parallel."""
    if not pairs:
        return []
    with ThreadPoolExecutor(max_workers=min(6, len(pairs))) as pool:
        return list(pool.map(lambda p: _osrm_km(*p), pairs))


def nearby(lat: float, lon: float, radius_km: float) -> list[dict]:
    out = []
    for ind in data.sites():
        km = haversine_km(lat, lon, ind["lat"], ind["lon"])
        if km <= radius_km:
            out.append({**ind, "straight_km": round(km, 1)})
    return sorted(out, key=lambda i: i["straight_km"])
