"""Compliant public-source buyer discovery for supplier accounts.

Search results are candidate leads, not verified buyers. This module does not
crawl websites, harvest contact data, bypass access controls, or send outreach.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.db import _con, _execute, _is_postgres, add_audit_event
from app.marketplace import _current_user, _require_role
from app.providers import search_provider, _safe_public_url
from app.settings import settings
from app.subscriptions import reserve_agent_credit, refund_agent_credit, get_agent_credit_usage

router = APIRouter(prefix="/marketplace/agent", tags=["marketplace-buyer-discovery"])


def init_buyer_discovery():
    con = _con()
    id_type = "BIGSERIAL PRIMARY KEY" if _is_postgres() else "INTEGER PRIMARY KEY"
    _execute(con, f"""CREATE TABLE IF NOT EXISTS marketplace_buyer_candidates (
        id {id_type}, user_id INTEGER NOT NULL, search_query TEXT NOT NULL,
        target_country TEXT NOT NULL, title TEXT NOT NULL, source_url TEXT NOT NULL,
        snippet TEXT NOT NULL DEFAULT '', source_provider TEXT NOT NULL,
        source_type TEXT NOT NULL DEFAULT 'public_search_result',
        collection_basis TEXT NOT NULL DEFAULT 'public_search_snippet',
        review_status TEXT NOT NULL DEFAULT 'needs_supplier_review',
        reviewer_note TEXT NOT NULL DEFAULT '',
        collected_at TIMESTAMP NOT NULL, retention_until TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id,source_url))""")
    _execute(con, """CREATE INDEX IF NOT EXISTS idx_marketplace_buyer_candidates_owner
        ON marketplace_buyer_candidates(user_id,review_status,collected_at)""")
    _execute(con, """CREATE INDEX IF NOT EXISTS idx_marketplace_buyer_candidates_retention
        ON marketplace_buyer_candidates(retention_until)""")
    # Expired rows are purged at startup and again when suppliers open their list.
    _execute(con, "DELETE FROM marketplace_buyer_candidates WHERE retention_until<=?",
             (datetime.now(timezone.utc).isoformat(),))
    con.commit()
    con.close()


class BuyerDiscoverySearch(BaseModel):
    product_terms: str = Field(min_length=3, max_length=180)
    target_country: str = Field(min_length=2, max_length=100)
    buyer_type: str = Field(default="importer distributor wholesaler", min_length=3, max_length=100)


class CandidateReview(BaseModel):
    relevant: bool
    note: str = Field(default="", max_length=1000)


@router.post("/buyer-discovery")
def discover_buyers(data: BuyerDiscoverySearch, user=Depends(_current_user)):
    _require_role(user, "producer")
    if (settings.search_provider or "").lower() != "serpapi" or not settings.search_api_key:
        raise HTTPException(503, detail={"code": "buyer_search_not_configured",
                                         "required": ["SEARCH_PROVIDER=serpapi", "SEARCH_API_KEY"]})
    product_terms = " ".join(data.product_terms.split())
    country = " ".join(data.target_country.split())
    buyer_type = " ".join(data.buyer_type.split())
    query = f"{product_terms} {buyer_type} in {country}"
    reserve_agent_credit(user["id"])
    try:
        raw_results = search_provider.search_buyers(query, country)
    except Exception:
        refund_agent_credit(user["id"])
        raise HTTPException(502, "buyer_search_provider_failed")
    now = datetime.now(timezone.utc)
    retention = (now + timedelta(days=90)).isoformat()
    con = _con()
    saved = []
    try:
        for item in raw_results[:10]:
            title = str(item.get("title") or "").strip()[:300]
            url = str(item.get("url") or "").strip()
            snippet = str(item.get("snippet") or "").strip()[:1500]
            source = str(item.get("source") or "search_provider")[:80]
            if not title or not _safe_public_url(url):
                continue
            _execute(con, """INSERT INTO marketplace_buyer_candidates
                (user_id,search_query,target_country,title,source_url,snippet,source_provider,
                 source_type,collection_basis,review_status,collected_at,retention_until)
                VALUES(?,?,?,?,?,?,?,'public_search_result','public_search_snippet',
                       'needs_supplier_review',?,?)
                ON CONFLICT(user_id,source_url) DO NOTHING""",
                (user["id"], query, country, title, url, snippet, source, now.isoformat(), retention))
            row = _execute(con, """SELECT id,title,source_url,snippet,source_provider,
                review_status,collected_at,retention_until FROM marketplace_buyer_candidates
                WHERE user_id=? AND source_url=?""", (user["id"], url)).fetchone()
            if row:
                saved.append(dict(row))
        con.commit()
    except Exception:
        con.rollback()
        refund_agent_credit(user["id"])
        raise
    finally:
        con.close()
    add_audit_event("marketplace.buyer_discovery_completed", user["email"], str(user["id"]),
                    "buyer_discovery", str(user["id"]),
                    {"country": country, "candidate_count": len(saved), "query_hash": __import__("hashlib").sha256(query.encode()).hexdigest()})
    return {"status": "needs_supplier_review", "query": query, "target_country": country,
            "candidates": saved, "credits": get_agent_credit_usage(user["id"]),
            "disclosure": "These are unverified public-search candidates. Check each source's terms, privacy basis and local marketing rules before outreach. No contact data was harvested and no message was sent."}


@router.get("/buyer-candidates")
def list_buyer_candidates(status: Optional[str] = Query(default=None, max_length=40),
                          limit: int = Query(default=50, ge=1, le=100),
                          user=Depends(_current_user)):
    _require_role(user, "producer")
    clauses = ["user_id=?", "retention_until>?"]
    values = [user["id"], datetime.now(timezone.utc).isoformat()]
    if status:
        if status not in ("needs_supplier_review", "supplier_marked_relevant", "rejected"):
            raise HTTPException(422, "invalid_candidate_status")
        clauses.append("review_status=?")
        values.append(status)
    con = _con()
    _execute(con, "DELETE FROM marketplace_buyer_candidates WHERE retention_until<=?",
             (datetime.now(timezone.utc).isoformat(),))
    rows = _execute(con, """SELECT id,search_query,target_country,title,source_url,snippet,
        source_provider,source_type,collection_basis,review_status,reviewer_note,collected_at,retention_until
        FROM marketplace_buyer_candidates WHERE """ + " AND ".join(clauses) +
        " ORDER BY id DESC LIMIT ?", values + [limit]).fetchall()
    con.close()
    return [dict(row) for row in rows]


@router.patch("/buyer-candidates/{candidate_id}")
def review_buyer_candidate(candidate_id: int, data: CandidateReview, user=Depends(_current_user)):
    _require_role(user, "producer")
    status = "supplier_marked_relevant" if data.relevant else "rejected"
    con = _con()
    cur = _execute(con, """UPDATE marketplace_buyer_candidates SET review_status=?,reviewer_note=?
        WHERE id=? AND user_id=?""", (status, data.note.strip(), candidate_id, user["id"]))
    con.commit()
    con.close()
    if cur.rowcount != 1:
        raise HTTPException(404, "buyer_candidate_not_found")
    add_audit_event("marketplace.buyer_candidate_reviewed", user["email"], str(candidate_id),
                    "buyer_candidate", str(candidate_id), {"status": status})
    return {"candidate_id": candidate_id, "review_status": status,
            "note": "This is the supplier's relevance review only; it does not establish permission to contact the company."}
