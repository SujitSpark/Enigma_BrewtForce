# Symbiosis — Industrial Resource Intelligence

Sustainability track, PS 5: *Discovering Hidden Industrial Symbiosis*.

An AI-driven platform that discovers opportunities for industries to exchange by-products as resources. It weighs material compatibility, quantity, location, timing, processing, economics and environmental impact. It then connects the matched industries through outreach and learns from their responses.

## Run

```bash
cd backend
pip install -r requirements.txt
python app.py            # API on http://127.0.0.1:8000  (docs: /docs)
```

```bash
cd frontend
npm install
npm start                # UI on http://localhost:3000  (npm run dev also works)
```

## Sections

| Section | What it does |
|---|---|
| **Command Center** | Live resource-network map (sources → hubs → consumers), KPIs (waste available, potentially diverted, net CO₂e, ₹ opportunity, active exchanges), top opportunities, industry-response feed |
| **Analyse & What-if** | Email → structured supply profile (material, t/month, location, company, availability months) → ranked opportunities. The simulator changes radius, freight ₹/t·km, carbon price, hub availability and the 7 weights, or adds a new industry; results recalculate and show the delta (e.g. *Opportunities 1 → 3*) |
| **Opportunities** | Every exchange across known plants, filterable by pathway, material and outreach status |
| **Materials** | Search a by-product: properties, possible uses, suppliers, consumers, processing hubs, supply vs demand |
| **Network** | Ecosystem graph (sources → processing hubs → consumers), with link width = tonnes/yr |
| **Impact** | Waste diverted, net CO₂e and ₹ value by material and pathway, allocated without double counting |
| **Schemes** | Indian policy pathways linked to opportunities, with verification requirements |
| **Outreach** | Email drafts with one-click response links (Interested / Need info / Not feasible), a status tracker, and optional SMTP sending |

## How the engine works

1. **Structure**: `core/nlp.py` extracts material, quantity (t/month, TPD, lakh t/yr, MT/yr), location, company and availability months.
2. **Discover pathways**: `core/engine.py`
   - **Direct**: the consumer uses the material as-is, or processes it in-house.
   - **Multi-step**: source → an existing processing hub with the required capability and capacity → consumer.
   - **Hidden**: a non-obvious cross-sector use, or a **missing processing hub**. Demand exists within range but nothing can process the material, so the engine proposes where a hub should go and what it would unlock.
3. **Feasibility**: every pathway is scored on 7 dimensions. The weights are a configurable prototype choice, not an official formula.
   `S = 25%·Material + 15%·Quantity + 15%·Geography + 10%·Processing + 10%·Timing + 15%·Environment + 10%·Economics`
   Each score comes with its reasons (✓ / ! / ×).
4. **Impact** (`core/impact.py`), on the quantity *actually reused* after quantity and month-by-month timing limits:
   - `Net CO₂e = Q·EF_virgin − Q·EF_processing − Q·D·EF_transport`
   - `Economic benefit = virgin savings + disposal savings + carbon value − transport − processing`. By-product revenue is shown separately, because it's a transfer between the two parties.
5. **Policy pathways**: real instruments (Fly Ash Notification, HWM Rules, C&D Rules, Steel Scrap Recycling Policy, Green Steel Taxonomy, CCTS 2023), always marked *eligibility verification required*.
6. **Geography**: live road distance (OSRM) and geocoding (OpenStreetMap Nominatim), with an offline fallback.
7. **Feedback loop**: responses to outreach re-weight future scores for that buyer and material (*not feasible* → ×0.8, *interested* → ×1.05).

## Data (`backend/data/`)

The location layer is kept separate from resource profiles, as the architecture requires.

- `industries.geojson`: **where** things are. 36 plants and demand hubs plus 12 processing hubs, with state and district. Named facilities are real plants at approximate, town-level coordinates. `cluster` and `processor` entries are illustrative.
- `profiles.json`: **what** each site supplies or needs, how much, and when. Volumes are illustrative order-of-magnitude estimates, not company disclosures.
- `materials.json`: 9 by-products, their uses, processing steps, emission factors, prices and seasonality. All are indicative screening values.
- `schemes.json`: policy instruments. No subsidy amounts are asserted.

## Team modules

| Person | Owns | Code |
|---|---|---|
| 1 · AI/NLP & matching | extraction, pathway discovery, 7-dimension ranking, hidden hubs | `core/nlp.py`, `core/engine.py` |
| 2 · Data, impact & schemes | datasets, CO₂ + ₹ models, environment score, policy mapping | `data/`, `core/impact.py` |
| 3 · GIS | GeoJSON layer, geocoding, live routing, maps | `core/geo.py`, `frontend/src/components/NetworkMap.jsx` |
| 4 · Application & engagement | all UI sections, what-if, outreach, response loop, integration | `frontend/src/`, `core/outreach.py`, `core/store.py`, `app.py` |

## Optional: real email sending

Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` and `SMTP_FROM` before starting the backend. To make the response links in emails work outside your machine, set `PUBLIC_BASE_URL` to a public URL for the API. Without SMTP, use *Open in mail app*, then *Mark as sent*.
