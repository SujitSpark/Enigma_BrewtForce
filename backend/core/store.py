import json
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "symbiosis.db"
RESPONSES = ("interested", "more_info", "not_feasible")
STATUSES = ("draft", "sent") + RESPONSES


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init() -> None:
    with _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                company TEXT, material_id TEXT NOT NULL, material_name TEXT NOT NULL,
                tonnes_per_month REAL NOT NULL, location TEXT,
                opportunities INTEGER NOT NULL, top_name TEXT, top_score INTEGER,
                net_tco2e_per_year REAL, net_inr_per_year REAL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS outreach (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                analysis_id INTEGER, opportunity_id TEXT NOT NULL,
                supplier_name TEXT, supplier_location TEXT,
                material_id TEXT NOT NULL, material_name TEXT NOT NULL,
                consumer_id TEXT, consumer_name TEXT NOT NULL,
                pathway_type TEXT, score INTEGER,
                net_tco2e_per_year REAL, net_inr_per_year REAL,
                recipient_email TEXT, subject TEXT NOT NULL, body TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                response_note TEXT, responded_at TEXT
            );
            CREATE TABLE IF NOT EXISTS custom_industries (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                payload TEXT NOT NULL
            );
        """)


# ---------- analyses ----------

def save_analysis(result: dict) -> int:
    top = result["opportunities"][0] if result["opportunities"] else None
    with _conn() as c:
        cur = c.execute(
            """INSERT INTO analyses (created_at, company, material_id, material_name, tonnes_per_month, location,
                   opportunities, top_name, top_score, net_tco2e_per_year, net_inr_per_year, payload)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (_now(), result["supplier"].get("company"), result["material"]["id"], result["material"]["name"],
             result["supply"]["quantity_tpm"], result["supplier"].get("location_label"), len(result["opportunities"]),
             top["title"] if top else None, top["score"] if top else None,
             top["impact"]["net_tco2e_per_year"] if top else None,
             top["economics"]["net_inr_per_year"] if top else None, json.dumps(result)),
        )
        return cur.lastrowid


def history(limit: int = 10) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT id, created_at, company, material_name, tonnes_per_month, location, opportunities, top_name, "
            "top_score, net_tco2e_per_year, net_inr_per_year FROM analyses ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_analysis(analysis_id: int) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT payload FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    return json.loads(row["payload"]) if row else None


# ---------- outreach & responses ----------

def create_outreach(rec: dict) -> dict:
    token = secrets.token_urlsafe(12)
    now = _now()
    with _conn() as c:
        cur = c.execute(
            """INSERT INTO outreach (token, created_at, updated_at, analysis_id, opportunity_id, supplier_name,
                   supplier_location, material_id, material_name, consumer_id, consumer_name, pathway_type, score,
                   net_tco2e_per_year, net_inr_per_year, recipient_email, subject, body, status)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (token, now, now, rec.get("analysis_id"), rec["opportunity_id"], rec.get("supplier_name"),
             rec.get("supplier_location"), rec["material_id"], rec["material_name"], rec.get("consumer_id"),
             rec["consumer_name"], rec.get("pathway_type"), rec.get("score"), rec.get("net_tco2e_per_year"),
             rec.get("net_inr_per_year"), rec.get("recipient_email"), rec["subject"], rec["body"], "draft"),
        )
        new_id = cur.lastrowid
    return get_outreach(new_id)


def get_outreach(outreach_id: int) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM outreach WHERE id = ?", (outreach_id,)).fetchone()
    return dict(row) if row else None


def outreach_by_token(token: str) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM outreach WHERE token = ?", (token,)).fetchone()
    return dict(row) if row else None


def list_outreach() -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM outreach ORDER BY updated_at DESC, id DESC").fetchall()
    return [dict(r) for r in rows]


def update_outreach(outreach_id: int, **fields) -> dict | None:
    fields["updated_at"] = _now()
    if fields.get("status") in RESPONSES:
        fields["responded_at"] = fields["updated_at"]
    cols = ", ".join(f"{k} = ?" for k in fields)
    with _conn() as c:
        c.execute(f"UPDATE outreach SET {cols} WHERE id = ?", (*fields.values(), outreach_id))
    return get_outreach(outreach_id)


def feedback() -> dict:
    """Response counts per (consumer_id, material_id): the loop that re-weights future recommendations."""
    with _conn() as c:
        rows = c.execute(
            "SELECT consumer_id, material_id, status, COUNT(*) n FROM outreach "
            "WHERE status IN ('interested','more_info','not_feasible') AND consumer_id IS NOT NULL "
            "GROUP BY consumer_id, material_id, status"
        ).fetchall()
    out: dict = {}
    for r in rows:
        out.setdefault((r["consumer_id"], r["material_id"]), {})[r["status"]] = r["n"]
    return out


# ---------- what-if: user-added industries ----------

def custom_industries() -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT payload FROM custom_industries ORDER BY created_at").fetchall()
    return [json.loads(r["payload"]) for r in rows]


def add_custom_industry(payload: dict) -> None:
    with _conn() as c:
        c.execute("INSERT INTO custom_industries (id, created_at, payload) VALUES (?,?,?)",
                  (payload["site"]["id"], _now(), json.dumps(payload)))


def delete_custom_industry(site_id: str) -> bool:
    with _conn() as c:
        return c.execute("DELETE FROM custom_industries WHERE id = ?", (site_id,)).rowcount > 0
