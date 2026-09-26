# Byloop: Industrial Resource Intelligence

An AI-driven platform that discovers hidden opportunities for industries to exchange by-products as resources. It evaluates whether each exchange is actually feasible, links it to relevant Indian policy pathways, and connects the plants through automated outreach.

---

## Team Name & Members

**Team BrewtForce**

- Shruti Subramanian
- Shubhashri Sriram
- Sakshi Podhade
- Sujit Shiravle

---

## Problem Statement

**Sustainability Track: Discovering Hidden Industrial Symbiosis**

Industries generate large quantities of by-products and residual materials that are often treated as waste. At the same time, other industries buy virgin raw materials that suitable industrial by-products could replace. These opportunities are hard to identify, because they depend on material properties, quantity, location, timing, transportation, processing requirements and environmental impact.

**Objective:** develop a practical, data-driven solution that helps uncover and assess opportunities for industrial resource exchange:
- improve the identification of opportunities for better use of industrial resources;
- consider the relevant practical, operational and environmental factors when assessing opportunities;
- show how the approach can be useful across different industrial contexts.

### Our solution

Byloop turns an industrial email into ranked, explainable resource-exchange opportunities:

1. **Understands** free text: material, quantity, location and availability.
2. **Discovers three pathway types:**
   - **direct** (source → consumer);
   - **multi-step** (source → processing hub → consumer);
   - **hidden** (non-obvious uses, or a *missing processing hub* that would unlock existing demand).
3. **Scores every opportunity on 7 dimensions** (material, quantity, geography, processing, timing, environment, economics), with a reason for each.
4. **Quantifies impact honestly**: net CO₂e *after* processing and transport, plus a ₹ business case.
5. **Maps policy pathways**: Fly Ash Utilisation Notification, Carbon Credit Trading Scheme, Green Steel Taxonomy, Steel Scrap Recycling Policy, Hazardous Waste Rules and C&D Waste Rules, each marked *verify eligibility*.
6. **Closes the loop**: generates outreach emails with one-click replies (Interested / Need info / Not feasible), and responses re-rank future recommendations.
7. **What-if simulator**: change the radius, freight cost, carbon price, hubs or priorities, or add a new industry, and watch opportunities appear or disappear.

---

## Tech Stack Used

| Layer | Technology |
|---|---|
| **Backend** | Python 3.10+ · FastAPI · Uvicorn · Pydantic v2 |
| **Database** | SQLite (Python `sqlite3`) for analyses, outreach, responses and user-added industries |
| **Engine** | Custom Python modules: NLP extraction (`core/nlp.py`), 7-dimension feasibility and pathway discovery (`core/engine.py`), impact, economics and policy mapping (`core/impact.py`) |
| **Geospatial** | GeoJSON industrial layer · Haversine distances · **OSRM** live road routing · **OpenStreetMap Nominatim** geocoding (with offline fallback) |
| **Frontend** | React 18 (Create React App) · Leaflet + React-Leaflet · OpenStreetMap tiles · custom SVG network graph and charts |
| **Design** | Vanilla × Moonstone palette (contrast-checked) · Instrument Serif + IBM Plex Sans/Mono · CSS animations that respect *reduce motion* |
| **Outreach** | Auto-generated emails, tokenised response links, optional SMTP sending |

### AI Tools Used

| Tool | Used for |
|---|---|
| **ChatGPT** (OpenAI) | Ideation, problem framing, research on materials and policies, content drafting |
| **Antigravity** (Google) | AI-assisted coding and development |

---

## Setup Instructions

### Prerequisites
- **Python 3.10+**
- **Node.js 18+** and npm
- Internet connection (for map tiles, live routing and geocoding; the app falls back to estimates if offline)

### 1. Clone the repository
```bash
git clone https://github.com/SujitSpark/Enigma_BrewtForce.git
cd Enigma_BrewtForce
```

### 2. Start the backend (terminal 1)
```bash
cd backend
pip install -r requirements.txt
python app.py
```
The API runs on **http://127.0.0.1:8000**, with interactive docs at http://127.0.0.1:8000/docs.
The SQLite database (`backend/symbiosis.db`) is created automatically on first run.

### 3. Start the frontend (terminal 2)
```bash
cd frontend
npm install
npm start
```
The app opens on **http://localhost:3000**. `npm run dev` also works. The dev server proxies `/api` to the backend.

### 4. Try it
1. The **landing page** loads first. Click **Launch platform**.
2. **Analyse & What-if**: click the *"Fly ash · Chandrapur"* sample, then **Discover opportunities**.
3. Open any opportunity to see its 7-dimension score, carbon and ₹ breakdown, and **policy pathways**.
4. **Outreach**: click **Load demo activity** to see the full outreach funnel. Demo records are labelled and can be cleared.

### Optional: real email sending
Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` and `SMTP_FROM` before starting the backend. Set `PUBLIC_BASE_URL` to a public API URL so response links work outside your machine. Without SMTP, use **Open in mail app**, then **Mark as sent**.

### Troubleshooting
| Symptom | Fix |
|---|---|
| App stuck loading, or "API returned a web page" | Make sure the backend is running, then restart `npm start` so the `/api` proxy is picked up |
| Port 8000 or 3000 already in use | Stop the other process, or set `PORT=3001` before `npm start` |
| Map tiles or road distances missing | Check the internet connection; distances fall back to straight-line × 1.3 |

---

## Project Structure

```
backend/
  app.py              FastAPI routes
  core/               nlp · engine · impact · geo · outreach · store
  data/               industries.geojson · profiles.json · materials.json · schemes.json
frontend/
  src/pages/          Landing · CommandCenter · Analyse · Opportunities · Materials · Network · Impact · Schemes · Outreach
  src/components/     NetworkMap · OpportunityDetail · WhatIfPanel · IntakePanel · Motion …
demo/                 Demo video timeline & voice-over script
PRESENTATION.md       Presentation guide
SCRIPT.md             3:30 pitch script
```

## Data Note

Plant names and town-level locations, the policy instruments and the BIS/IRC standards are real. Supply and demand volumes, prices and emission factors are **illustrative screening values**, clearly labelled in the app. Policy matches are **potential pathways subject to eligibility verification**, not guaranteed subsidies or certified carbon credits.
