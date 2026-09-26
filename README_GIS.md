# GIS / Location Intelligence Module

**Project:** Industrial Symbiosis Discovery Engine
**Owner:** Person 3
**Branch:** `feature/gis-location-intelligence`

A standalone, dependency-light **Python + FastAPI** backend that answers the
geographic questions of the project:

- Where are the industries? (coordinates)
- How far apart are they? (Haversine distance)
- Are they close enough? (radius filtering + nearby discovery)
- How good is the geography for a match? (transparent feasibility score)
- What data does the map need? (map-ready JSON)
- What would the road distance be? (pluggable routing, straight-line by default)

> **Scope note:** This module contains **no** NLP, no AI matching, no material
> compatibility logic, no environmental-impact maths, no scheme matching, no
> email/outreach, and **no frontend**. Those belong to other team members. GIS
> only answers *where* and *how far*.

> **Data note:** All bundled industry records are **DEMO / PROTOTYPE DATA**.
> Names like "ABC Steel (DEMO)" are illustrative placeholders. They are **not**
> verified real industrial partners.

---

## 1. What this module does

| Feature | Implementation |
|---|---|
| 1. Coordinate resolution | Stored coordinates first, optional (off-by-default) city geocoding |
| 2. Distance calculation | Haversine great-circle distance, in km |
| 3. Radius filtering | `radius_km` filter with inclusive boundary |
| 4. Nearby discovery | Nearest-first scan, optional candidate whitelist from Person 1 |
| 5. Geographic feasibility | Transparent, configurable piecewise-linear score + band label |
| 6. Route information | Pluggable providers; straight-line default, optional OSRM |
| 7. Map data output | Source/consumer/distance JSON for Leaflet or any map library |

Everything runs offline on a normal laptop. No GPU, no ML, no paid APIs.

---

## 2. Install dependencies

Requires Python 3.10+ (tested on Python 3.13, Windows).

```bat
cd C:\Users\Shruti Subramanian\Downloads\Enigma_BrewtForce

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
```

`geopy` is **optional** and only needed if you want city-name geocoding:

```bat
pip install geopy
```

---

## 3. Run the API

From the project root (the folder containing `backend/`):

```bat
uvicorn backend.main:app --reload
```

- Base URL: `http://127.0.0.1:8000`
- Interactive docs (Swagger UI): `http://127.0.0.1:8000/docs`

---

## 4. API endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/gis/health` | Module health + dataset size |
| GET | `/gis/industries` | List all industries |
| GET | `/gis/industry/{industry_id}` | One industry with coordinates |
| GET | `/gis/nearby/{industry_id}?radius_km=50` | Nearby industries (path form) |
| GET | `/gis/nearby?industry_id=IND001&radius_km=50` | Nearby industries (query form) |
| POST | `/gis/distance` | Distance between two coordinate pairs |
| POST | `/gis/evaluate` | Full feasibility for a source/consumer pair |
| POST | `/gis/opportunities` | **Integration contract**: batch of candidates |
| GET | `/gis/map/{source_id}/{consumer_id}` | Map-ready JSON |
| GET | `/gis/route/{source_id}/{consumer_id}?provider=straight_line` | Route info |

### Examples

**GET** `/gis/industry/IND001`

```json
{
  "id": "IND001",
  "name": "ABC Steel (DEMO)",
  "industry_type": "Steel",
  "city": "Pune",
  "latitude": 18.5204,
  "longitude": 73.8567,
  "materials": ["Steel scrap", "Finished steel"],
  "byproducts": ["Slag", "Mill scale"],
  "data_note": "DEMO / PROTOTYPE DATA - not verified real industrial partners"
}
```

**GET** `/gis/nearby/IND001?radius_km=50`

```json
{
  "source_id": "IND001",
  "source_name": "ABC Steel (DEMO)",
  "radius_km": 50.0,
  "count": 4,
  "results": [
    {
      "industry_id": "IND015",
      "name": "Pune Bioenergy (DEMO)",
      "industry_type": "Bioenergy",
      "city": "Pune",
      "latitude": 18.5018,
      "longitude": 73.8636,
      "distance_km": 2.19,
      "within_radius": true,
      "geographic_score": 99,
      "feasibility": "VERY_HIGH"
    }
  ]
}
```

**POST** `/gis/distance`

```json
{ "source": { "latitude": 18.5204, "longitude": 73.8567 },
  "destination": { "latitude": 18.6000, "longitude": 73.8000 } }
```

```json
{ "distance_km": 10.68, "method": "haversine" }
```

**POST** `/gis/evaluate`

```json
{ "source_id": "IND001", "consumer_id": "IND002", "max_radius_km": 50 }
```

```json
{
  "source": "ABC Steel (DEMO)",
  "consumer": "XYZ Cement (DEMO)",
  "source_id": "IND001",
  "consumer_id": "IND002",
  "distance_km": 13.32,
  "method": "haversine",
  "max_radius_km": 50.0,
  "within_radius": true,
  "geographic_score": 95,
  "feasibility": "VERY_HIGH",
  "map_data": { "source": { "...": "..." }, "consumer": { "...": "..." }, "distance_km": 13.32 }
}
```

---

## 5. Geographic scoring logic (transparent + configurable)

Everything lives in `backend/gis/config.py` and can be overridden per request
via `max_radius_km`, or globally by constructing a custom `ScoringConfig`.

**Feasibility bands** (distance in km → label). The upper edge is inclusive:

| Distance | Label |
|---|---|
| 0 – 25 km | `VERY_HIGH` |
| 25 – 50 km | `HIGH` |
| 50 – 100 km | `MODERATE` |
| 100+ km | `LOW` |

**Score (0–100)** is piecewise-linear interpolation between these anchors:

| Distance | Score |
|---|---|
| 0 km | 100 |
| 25 km | 90 |
| 50 km | 70 |
| 100 km | 40 |
| 250 km | 10 |
| 500 km | 0 |

`within_radius` is computed separately as `distance_km <= max_radius_km`.

> These thresholds are **prototype heuristics chosen for a hackathon demo**.
> They are **not** scientifically derived and **not** a government standard.
> They are deliberately exposed as configuration so anyone can tune them.

---

## 6. How another teammate integrates it

### Option A — call the HTTP API (recommended)

```python
import httpx

BASE = "http://127.0.0.1:8000"

resp = httpx.post(f"{BASE}/gis/opportunities", json={
    "source_id": "IND001",
    "potential_consumers": ["IND005", "IND008", "IND011"],
    "max_radius_km": 50,
})
for opp in resp.json()["opportunities"]:
    print(opp["consumer_id"], opp["distance_km"], opp["feasibility"])
```

### Option B — import the Python service directly

```python
from backend.gis import get_default_service

svc = get_default_service()
svc.evaluate("IND001", "IND002", max_radius_km=50)
svc.nearby("IND001", radius_km=50)
svc.nearby_opportunities("IND001", ["IND002", "IND004"], max_radius_km=50)
svc.distance({"latitude": 18.52, "longitude": 73.85},
             {"latitude": 18.60, "longitude": 73.80})
```

---

## 7. Exact JSON contract

### Person 1 → GIS (`POST /gis/opportunities` request)

```json
{
  "source_id": "IND001",
  "potential_consumers": ["IND005", "IND008", "IND011"],
  "max_radius_km": 50
}
```

### GIS → Person 1 / Person 2 (response)

```json
{
  "source_id": "IND001",
  "source_name": "ABC Steel (DEMO)",
  "max_radius_km": 50.0,
  "opportunities": [
    {
      "consumer_id": "IND005",
      "consumer_name": "GreenRoad Materials (DEMO)",
      "distance_km": 54.14,
      "within_radius": false,
      "geographic_score": 68,
      "feasibility": "MODERATE"
    }
  ]
}
```

(Values above are real output from the bundled DEMO dataset.)

**Field semantics**

| Field | Type | Meaning |
|---|---|---|
| `consumer_id` | string | Industry id from the dataset |
| `consumer_name` | string | Display name (DEMO data) |
| `distance_km` | number | Haversine straight-line distance, km |
| `within_radius` | boolean | `distance_km <= max_radius_km` |
| `geographic_score` | integer | 0–100, higher = better geography |
| `feasibility` | string | `VERY_HIGH` / `HIGH` / `MODERATE` / `LOW` |

Person 2 can use `distance_km` together with their own quantity data for
transport/impact calculations — GIS deliberately supplies no environmental
numbers.

---

## 8. Tests

```bat
python -m pytest -q
```

Covers: Haversine correctness & symmetry, same-point = 0 km, coordinate
validation, radius filtering, inclusive radius boundary, empty results,
industry-type filtering, candidate whitelisting, geographic score anchors &
monotonicity, configurable thresholds, missing industry id, and all API
endpoints (including 404 / 422 cases).

---

## 9. Project layout

```
backend/
    __init__.py
    main.py                 # FastAPI app (adds /gis router)
    api/
        __init__.py
        gis_routes.py       # HTTP endpoints
    gis/
        __init__.py         # public exports
        config.py           # tunable thresholds/anchors
        schemas.py          # Pydantic models = integration contract
        coordinates.py      # FEATURE 1
        distance.py         # FEATURE 2 (Haversine)
        nearby.py           # FEATURE 3 + 4
        feasibility.py      # FEATURE 5
        routes.py           # FEATURE 6 (pluggable)
        service.py          # orchestration / single entry point
    data/
        industries.json     # DEMO / PROTOTYPE dataset
tests/
    test_distance.py
    test_feasibility.py
    test_nearby.py
    test_api.py
```

## 10. Road routing (optional, off by default)

`backend/gis/routes.py` defines a `RoutingProvider` interface.

- `StraightLineProvider` — default, offline, always labelled `"haversine"`.
- `OSRMProvider` — optional road routing against a public/self-hosted OSRM
  server. Disabled unless explicitly enabled, and it automatically falls back
  to straight-line on any failure, so the module **never depends on a paid API**.
