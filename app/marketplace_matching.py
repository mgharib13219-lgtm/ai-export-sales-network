"""Deterministic, explainable buyer-request to supplier-listing matching.

Scores are discovery aids only. Unverified identity, product claims, and compliance
status always remain explicit review holds; a score is never a clearance or guarantee.
"""
import re
from typing import Any


def _tokens(value: Any) -> set[str]:
    if value is None:
        return set()
    return set(re.findall(r"[a-z0-9]{2,}", str(value).casefold()))


def _overlap(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def score_listing_for_request(request: dict, listing: dict) -> dict:
    """Return a 0-100 discovery score with reasons, gaps, and mandatory review holds."""
    request_category = str(request.get("category") or "").strip().casefold()
    listing_category = str(listing.get("category") or "").strip().casefold()
    category_exact = bool(request_category and listing_category and request_category == listing_category)

    request_terms = _tokens(" ".join(str(request.get(k) or "") for k in ("title", "specification")))
    listing_terms = _tokens(" ".join(str(listing.get(k) or "") for k in ("name", "description")))
    spec_overlap = _overlap(request_terms, listing_terms)

    score = (55.0 if category_exact else 0.0) + (45.0 * spec_overlap)
    reasons = []
    gaps = []
    if category_exact:
        reasons.append("Exact category match")
    else:
        gaps.append("Category is not an exact match")
    if spec_overlap:
        reasons.append("Shared specification terms")
    else:
        gaps.append("No shared specification terms")
    if not request.get("quantity"):
        gaps.append("Buyer quantity is unspecified")
    if not listing.get("capacity"):
        gaps.append("Supplier capacity is unspecified")
    if not listing.get("moq"):
        gaps.append("Supplier minimum order quantity is unspecified")

    # These are intentionally not inferred from free-text descriptions.
    holds = ["supplier_identity_not_independently_verified",
             "product_claims_and_certificates_not_independently_verified",
             "destination_compliance_not_screened"]
    if not request.get("destination"):
        holds.append("destination_missing")
    if not listing.get("origin"):
        holds.append("origin_missing")

    return {
        "listing_id": listing.get("id"),
        "supplier_company": listing.get("company_name"),
        "score": round(min(100.0, max(0.0, score)), 1),
        "status": "discovery_candidate_needs_human_review",
        "reasons": reasons,
        "information_gaps": gaps,
        "mandatory_holds": holds,
        "automatically_cleared": False,
    }


def rank_listings_for_request(request: dict, listings: list[dict], limit: int = 25) -> list[dict]:
    bounded = max(1, min(int(limit), 100))
    scored = [score_listing_for_request(request, item) for item in listings]
    return sorted(scored, key=lambda item: (-item["score"], str(item.get("supplier_company") or "")))[:bounded]
