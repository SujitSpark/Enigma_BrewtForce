"""Person 1 — understanding free-text industrial emails."""
import re

from . import data, geo

MULTIPLIERS = {"lakh": 100_000, "lac": 100_000, "lakhs": 100_000, "k": 1_000, "thousand": 1_000, "million": 1_000_000}
PERIOD_TO_MONTHLY = {"day": 30, "daily": 30, "tpd": 30, "week": 4.33, "weekly": 4.33,
                     "month": 1, "monthly": 1, "tpm": 1,
                     "year": 1 / 12, "annum": 1 / 12, "annually": 1 / 12, "yr": 1 / 12, "tpa": 1 / 12}

QTY_RE = re.compile(
    r"(?P<num>\d{1,3}(?:,\d{2,3})+|\d+(?:\.\d+)?)\s*"
    r"(?P<mult>lakhs?|lac|k|thousand|million)?\s*"
    r"(?P<unit>metric\s+tonnes?|tonnes?|tons?|mt|tpd|tpa|tpm|t)\b"
    r"(?P<tail>[^.\n]{0,25})",
    re.IGNORECASE,
)
PERIOD_RE = re.compile(r"\b(day|daily|week|weekly|month|monthly|year|annum|annually|yr)\b", re.IGNORECASE)

COMPANY_RE = re.compile(
    r"\b([A-Z][\w&.\-]*(?:\s+[A-Z][\w&.\-]*){0,5}\s+"
    r"(?:Pvt\.?\s*Ltd\.?|Private\s+Limited|Ltd\.?|Limited|LLP|Industries|Steels?|Cements?|Foundry|Foundries|Power|Works))"
)
LOCATION_HINT_RE = re.compile(
    r"\b(?:located\s+(?:in|at)|based\s+(?:in|at)|plant\s+(?:in|at)|facility\s+(?:in|at)|unit\s+(?:in|at)|situated\s+(?:in|at))\s+"
    r"([A-Z][A-Za-z]+(?:[\s,]+[A-Z][A-Za-z]+){0,2})"
)

SECTOR_KEYWORDS = {
    "Steel": ["steel", "blast furnace", "sms", "rolling mill", "sponge iron", "ironmaking"],
    "Thermal power": ["thermal power", "power plant", "power station", "tps", "boiler", "coal-fired"],
    "Foundry": ["foundry", "casting", "castings"],
    "Aluminium": ["alumina", "aluminium", "aluminum", "refinery", "bauxite"],
    "Fertiliser": ["fertiliser", "fertilizer", "phosphoric acid", "dap"],
    "Construction": ["construction", "demolition", "builder", "real estate"],
}


def _to_float(num: str) -> float:
    return float(num.replace(",", ""))


def parse_quantity(text: str) -> dict | None:
    m = QTY_RE.search(text)
    if not m:
        return None
    value = _to_float(m.group("num"))
    if m.group("mult"):
        value *= MULTIPLIERS[m.group("mult").lower()]
    unit = m.group("unit").lower()
    raw_end = m.start("tail")
    if unit in ("tpd", "tpa", "tpm"):
        period = unit
    else:
        p = PERIOD_RE.search(m.group("tail") or "")
        period = p.group(1).lower() if p else "month"
        if p:
            raw_end += p.end()
    monthly = value * PERIOD_TO_MONTHLY[period]
    return {"raw": text[m.start():raw_end].strip(), "tonnes_per_month": round(monthly, 1), "period": period}


def detect_material(text: str) -> tuple[dict | None, str | None]:
    lowered = text.lower()
    best, best_alias = None, None
    for mat in data.materials().values():
        for alias in mat["aliases"]:
            if re.search(rf"\b{re.escape(alias)}\b", lowered) and (best_alias is None or len(alias) > len(best_alias)):
                best, best_alias = mat, alias
    return best, best_alias


def detect_sector(text: str, material: dict | None) -> str | None:
    lowered = text.lower()
    for sector, words in SECTOR_KEYWORDS.items():
        if any(re.search(rf"\b{re.escape(w)}\b", lowered) for w in words):
            if material is None or sector in material["source_sectors"]:
                return sector
    return material["source_sectors"][0] if material else None


def detect_location(text: str) -> dict | None:
    hinted = LOCATION_HINT_RE.search(text)
    if hinted:
        loc = geo.geocode(hinted.group(1).strip(" ,"))
        if loc:
            return loc
    return geo.find_in_gazetteer(text)


MONTH_NAMES = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
MONTH_RE = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
RANGE_RE = re.compile(rf"\b(?:from\s+)?{MONTH_RE}\s*(?:to|till|until|through|-|–)\s*{MONTH_RE}\b", re.IGNORECASE)
YEAR_ROUND_RE = re.compile(r"\b(year[- ]round|all year|throughout the year|round the year|continuous(?:ly)?|every month)\b", re.IGNORECASE)


def parse_availability(text: str) -> dict | None:
    r = RANGE_RE.search(text)
    if r:
        a, b = MONTH_NAMES.index(r.group(1)[:3].lower()), MONTH_NAMES.index(r.group(2)[:3].lower())
        months = [0] * 12
        i = a
        while True:
            months[i] = 1
            if i == b:
                break
            i = (i + 1) % 12
        return {"raw": r.group(0), "months": months}
    y = YEAR_ROUND_RE.search(text)
    if y:
        return {"raw": y.group(0), "months": [1] * 12}
    return None


def extract(text: str) -> dict:
    material, alias = detect_material(text)
    quantity = parse_quantity(text)
    location = detect_location(text)
    company = COMPANY_RE.search(text)
    sector = detect_sector(text, material)

    found = [material is not None, quantity is not None, location is not None, company is not None]
    missing = [name for name, ok in zip(["material", "quantity", "location", "company"], found) if not ok]

    return {
        "company": company.group(1).strip() if company else None,
        "sector": sector,
        "material_id": material["id"] if material else None,
        "material_name": material["name"] if material else None,
        "matched_term": alias,
        "properties": material["properties"] if material else [],
        "potential_uses": [u["use"] for u in material["uses"]] if material else [],
        "quantity": quantity,
        "availability": parse_availability(text),
        "location": location,
        "confidence": round(sum(found) / len(found), 2),
        "missing": missing,
    }
