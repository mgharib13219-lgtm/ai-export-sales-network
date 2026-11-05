"""Server-enforced supplier subscription plans and listing entitlements.

Paid plans are activated only by an authorized operator until a payment provider
and signed webhook flow are integrated. This module never treats a client claim
or a submitted payment reference as proof of payment.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field

from app.auth import require_admin
from app.db import _con, _execute, _is_postgres, add_audit_event
from app.marketplace import _current_user, _require_role

router = APIRouter(prefix="/marketplace/subscription", tags=["marketplace-subscriptions"])

PLANS = {
    "free": {
        "name": "Free", "monthly_price_usd": None, "published_listing_limit": 3,
        "lead_access": "public_summary", "visibility": "standard",
        "agent_sourcing_credits": 0, "features": ["۳ آگهی فعال", "پروفایل پایه", "دریافت درخواست‌های عمومی"]
    },
    "starter": {
        "name": "Starter", "monthly_price_usd": None, "published_listing_limit": 10,
        "lead_access": "limited", "visibility": "enhanced",
        "agent_sourcing_credits": 5, "features": ["۱۰ آگهی فعال", "دسترسی محدود به سرنخ‌ها", "۵ اعتبار جستجوی ایجنت در ماه"]
    },
    "growth": {
        "name": "Growth", "monthly_price_usd": None, "published_listing_limit": 50,
        "lead_access": "expanded", "visibility": "priority",
        "agent_sourcing_credits": 30, "features": ["۵۰ آگهی فعال", "دسترسی گسترده‌تر به سرنخ‌ها", "۳۰ اعتبار جستجوی ایجنت در ماه", "گزارش عملکرد"]
    },
    "premium": {
        "name": "Premium", "monthly_price_usd": None, "published_listing_limit": 200,
        "lead_access": "premium", "visibility": "premium",
        "agent_sourcing_credits": 100, "features": ["۲۰۰ آگهی فعال", "بالاترین سطح دسترسی مجاز به سرنخ‌ها", "۱۰۰ اعتبار جستجوی ایجنت در ماه", "پشتیبانی اولویت‌دار"]
    },
}

class GrantSubscription(BaseModel):
    plan_code: str = Field(min_length=3, max_length=20)
    duration_days: int = Field(default=30, ge=1, le=3650)
    external_reference: Optional[str] = Field(default=None, max_length=160)


def init_subscriptions():
    con = _con()
    id_type = "BIGSERIAL PRIMARY KEY" if _is_postgres() else "INTEGER PRIMARY KEY"
    _execute(con, f"""CREATE TABLE IF NOT EXISTS marketplace_subscriptions (
        id {id_type}, user_id INTEGER NOT NULL, plan_code TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active', starts_at TEXT NOT NULL,
        ends_at TEXT NOT NULL, granted_by TEXT NOT NULL,
        external_reference TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    _execute(con, """CREATE INDEX IF NOT EXISTS idx_marketplace_subscriptions_user_status
        ON marketplace_subscriptions(user_id,status,ends_at)""")
    con.commit()
    con.close()


def get_effective_subscription(user_id: int, con=None) -> dict:
    owns_connection = con is None
    con = con or _con()
    try:
        now = datetime.now(timezone.utc).isoformat()
        row = _execute(con, """SELECT plan_code,status,starts_at,ends_at FROM marketplace_subscriptions
            WHERE user_id=? AND status='active' AND starts_at<=? AND ends_at>?
            ORDER BY ends_at DESC,id DESC LIMIT 1""", (user_id, now, now)).fetchone()
        plan_code = row["plan_code"] if row and row["plan_code"] in PLANS else "free"
        return {
            "plan_code": plan_code,
            "status": "active" if row else "free",
            "starts_at": row["starts_at"] if row else None,
            "ends_at": row["ends_at"] if row else None,
            "entitlements": PLANS[plan_code],
        }
    finally:
        if owns_connection:
            con.close()


def enforce_published_listing_limit(user_id: int):
    """Raise 403 when the account has reached its server-side plan limit."""
    # Use the marketplace's configured connection factory so all marketplace
    # tables share the same database/transaction context (also supports test DBs).
    from app.marketplace import _con as marketplace_connection
    con = marketplace_connection()
    try:
        subscription = get_effective_subscription(user_id, con)
        limit = int(subscription["entitlements"]["published_listing_limit"])
        count = _execute(con, """SELECT COUNT(*) AS total FROM marketplace_products
            WHERE owner_id=? AND status='published'""", (user_id,)).fetchone()["total"]
        if int(count) >= limit:
            raise HTTPException(403, detail={
                "code": "subscription_listing_limit_reached",
                "plan": subscription["plan_code"],
                "limit": limit,
                "upgrade_path": "/marketplace/subscription/plans",
            })
    finally:
        con.close()


@router.get("/plans")
def list_subscription_plans():
    return {"plans": [{"code": code, **plan} for code, plan in PLANS.items()],
            "pricing_note": "قیمت‌گذاری پرداختی هنوز فعال نشده؛ مبلغ نهایی پیش از خرید باید شفاف نمایش داده شود."}


@router.get("/me")
def my_subscription(user=Depends(_current_user)):
    _require_role(user, "producer")
    return get_effective_subscription(user["id"])


@router.post("/users/{user_id}", dependencies=[Depends(require_admin)])
def grant_subscription(user_id: int, data: GrantSubscription):
    plan_code = data.plan_code.strip().lower()
    if plan_code not in PLANS or plan_code == "free":
        raise HTTPException(422, "paid_plan_code_required")
    con = _con()
    exists = _execute(con, "SELECT id,email FROM marketplace_users WHERE id=?", (user_id,)).fetchone()
    if not exists:
        con.close()
        raise HTTPException(404, "marketplace_user_not_found")
    now = datetime.now(timezone.utc)
    ends = now + timedelta(days=data.duration_days)
    _execute(con, """UPDATE marketplace_subscriptions SET status='superseded'
        WHERE user_id=? AND status='active'""", (user_id,))
    _execute(con, """INSERT INTO marketplace_subscriptions
        (user_id,plan_code,status,starts_at,ends_at,granted_by,external_reference)
        VALUES(?,?,'active',?,?,?,?)""",
        (user_id, plan_code, now.isoformat(), ends.isoformat(), "admin", data.external_reference))
    con.commit()
    con.close()
    add_audit_event("marketplace.subscription_granted", "admin", str(user_id),
                    "subscription", str(user_id), {"plan": plan_code, "ends_at": ends.isoformat()})
    return {"user_id": user_id, "plan_code": plan_code, "status": "active",
            "ends_at": ends.isoformat(), "note": "Operator grant only; not a payment confirmation."}


@router.delete("/users/{user_id}", dependencies=[Depends(require_admin)])
def revoke_subscription(user_id: int):
    con = _con()
    cur = _execute(con, """UPDATE marketplace_subscriptions SET status='revoked'
        WHERE user_id=? AND status='active'""", (user_id,))
    con.commit()
    con.close()
    add_audit_event("marketplace.subscription_revoked", "admin", str(user_id),
                    "subscription", str(user_id), {"revoked_rows": cur.rowcount})
    return {"user_id": user_id, "status": "free", "revoked_rows": cur.rowcount}
