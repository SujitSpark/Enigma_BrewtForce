"""Person 4 — outreach drafts, response links and optional SMTP sending."""
import os
import smtplib
from email.message import EmailMessage

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
RESPONSE_LABELS = {"interested": "Interested", "more_info": "Need more information", "not_feasible": "Not feasible"}


def public_base_url() -> str:
    return os.environ.get("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def _lower_first(s: str) -> str:
    return s[:1].lower() + s[1:]


def _availability(months: list[float]) -> str:
    on = [MONTHS[i] for i, v in enumerate(months) if v >= 0.5]
    if len(on) == 12:
        return "available year-round"
    return f"available {', '.join(on)}" if on else "availability to be confirmed"


def draft(opp: dict, supplier: dict, material_name: str, token: str | None = None) -> dict:
    c = opp["consumer"]
    imp, econ, vol = opp["impact"], opp["economics"], opp["volume"]
    company = supplier.get("company")
    origin = supplier.get("location_label") or "our site"
    opener = f"{company} ({origin})" if company else f"Our facility in {origin}"
    material = _lower_first(material_name)
    virgin = _lower_first(opp["virgin_input"])
    monthly = vol["exchanged_tpy"] / 12

    subject = f"By-product supply opportunity: {monthly:,.0f} t/month {material} for {c['name']}"
    lines = [
        f"Dear {c['name']} procurement team,",
        "",
        f"{opener} generates about {vol['supply_tpm']:,.0f} tonnes per month of {material} "
        f"({_availability(vol['supply_months'])}). Our screening suggests it could replace part of your {virgin} "
        f"in this application: {opp['use']}.",
        "",
        f"Opportunity score: {opp['score']}/100",
        f"  • Proposed volume: about {monthly:,.0f} t/month, matched to your typical demand",
        f"  • Distance: about {opp['road_km']:,.0f} km by road",
    ]
    if opp["pathway_type"] == "via_hub" and opp["hub"]:
        lines.append(f"  • Processing: {opp['processing']['label']} at {opp['hub']['name']}")
    elif opp["pathway_type"] == "in_house":
        lines.append(f"  • Processing: {opp['processing']['label']} (typically done at your plant)")
    else:
        lines.append("  • Processing: none expected beyond standard handling")
    lines += [
        f"  • Environmental benefit: about {imp['net_tco2e_per_year']:,.0f} tCO₂e per year net, "
        f"{imp['virgin_replaced_t']:,} t/yr of {virgin} replaced",
        f"  • Indicative business case: ₹{econ['net_inr_per_year'] / 1e5:,.1f} lakh per year across both parties",
    ]
    if opp["standards"]:
        lines.append(f"  • Specifications to verify: {', '.join(opp['standards'])}")
    if opp["pathways"]:
        lines.append(f"  • Possible policy context: {', '.join(p['name'] for p in opp['pathways'][:2])} (eligibility to be verified)")
    lines += [
        "",
        "Next steps: share your material specification, and we will send a representative sample and test certificate.",
    ]
    if token:
        base = f"{public_base_url()}/respond/{token}"
        lines += ["", "Please let us know with one click:"]
        lines += [f"  {label}: {base}/{key}" for key, label in RESPONSE_LABELS.items()]
    lines += [
        "",
        "All figures are screening estimates to be validated with lab tests and logistics quotes.",
        "",
        "Regards,",
        company or "[Your name]",
    ]
    return {"to": c["name"], "subject": subject, "body": "\n".join(lines)}


def smtp_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_FROM"))


def send(to_addr: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = os.environ["SMTP_FROM"]
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", 587)), timeout=15) as s:
        s.starttls()
        if os.environ.get("SMTP_USER"):
            s.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASSWORD", ""))
        s.send_message(msg)
