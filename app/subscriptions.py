"""Server-enforced supplier subscription plans and listing entitlements.

Paid plans are activated only by an authorized operator until a payment provider
and signed webhook flow are integrated. This module never treats a client claim
or a submitted payment reference as proof of payment.
"""
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel, Field

from app.auth import require_admin
from app.db import _con, _execute, _is_postgres, add_audit_event
from app.marketplace import _current_user, _require_role
from app.settings import settings

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
    _execute(con, """CREATE TABLE IF NOT EXISTS marketplace_agent_credit_usage (
        user_id INTEGER NOT NULL, period TEXT NOT NULL, credits_used INTEGER NOT NULL DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user_id,period))""")
    _execute(con, f"""CREATE TABLE IF NOT EXISTS marketplace_upgrade_requests (
        id {id_type}, user_id INTEGER NOT NULL, plan_code TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending', note TEXT NOT NULL DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, reviewed_at TIMESTAMP)""")
    _execute(con, """CREATE TABLE IF NOT EXISTS marketplace_billing_events (
        event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL,
        received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
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


def _stripe_price_id(plan_code: str) -> str:
    return str(getattr(settings, "stripe_price_id_" + plan_code, "") or "").strip()


def _stripe_price_display(plan_code: str) -> str:
    return str(getattr(settings, "stripe_price_display_" + plan_code, "") or "").strip()


@router.get("/plans")
def list_subscription_plans():
    plans = []
    for code, plan in PLANS.items():
        item = {"code": code, **plan}
        if code != "free":
            item["monthly_price_display"] = _stripe_price_display(code) or None
            item["billing_enabled"] = bool(
                settings.stripe_secret_key and settings.stripe_webhook_secret
                and _stripe_price_id(code) and _stripe_price_display(code)
                and settings.billing_success_url and settings.billing_cancel_url
            )
        else:
            item["monthly_price_display"] = "رایگان"
            item["billing_enabled"] = True
        plans.append(item)
    return {"plans": plans,
            "pricing_note": "مبلغ پلن‌های پولی فقط پس از تنظیم مبلغ دقیق و همان Price در Stripe قابل خرید است."}


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


def _period_key(now=None):
    now = now or datetime.now(timezone.utc)
    return now.strftime("%Y-%m")


def get_agent_credit_usage(user_id: int) -> dict:
    sub = get_effective_subscription(user_id)
    limit = int(sub["entitlements"]["agent_sourcing_credits"])
    period = _period_key()
    con = _con()
    row = _execute(con, "SELECT credits_used FROM marketplace_agent_credit_usage WHERE user_id=? AND period=?",
                   (user_id, period)).fetchone()
    con.close()
    used = int(row["credits_used"]) if row else 0
    return {"plan_code": sub["plan_code"], "period": period, "limit": limit,
            "used": used, "remaining": max(0, limit - used)}


def reserve_agent_credit(user_id: int) -> dict:
    """Atomically reserve one monthly agent credit before contacting a search provider."""
    sub = get_effective_subscription(user_id)
    limit = int(sub["entitlements"]["agent_sourcing_credits"])
    if limit <= 0:
        raise HTTPException(403, detail={"code": "agent_credits_not_included",
                                         "plan": sub["plan_code"], "upgrade_path": "/marketplace/subscription/plans"})
    period = _period_key()
    con = _con()
    try:
        _execute(con, """INSERT INTO marketplace_agent_credit_usage(user_id,period,credits_used)
            VALUES(?,?,0) ON CONFLICT(user_id,period) DO NOTHING""", (user_id, period))
        cur = _execute(con, """UPDATE marketplace_agent_credit_usage
            SET credits_used=credits_used+1,updated_at=CURRENT_TIMESTAMP
            WHERE user_id=? AND period=? AND credits_used<?""", (user_id, period, limit))
        if cur.rowcount != 1:
            con.rollback()
            raise HTTPException(429, detail={"code": "agent_monthly_credits_exhausted",
                                             "limit": limit, "period": period,
                                             "upgrade_path": "/marketplace/subscription/plans"})
        con.commit()
    finally:
        con.close()
    return get_agent_credit_usage(user_id)


def refund_agent_credit(user_id: int):
    period = _period_key()
    con = _con()
    _execute(con, """UPDATE marketplace_agent_credit_usage
        SET credits_used=CASE WHEN credits_used>0 THEN credits_used-1 ELSE 0 END,
            updated_at=CURRENT_TIMESTAMP WHERE user_id=? AND period=?""", (user_id, period))
    con.commit()
    con.close()


@router.get("/credits")
def my_agent_credits(user=Depends(_current_user)):
    _require_role(user, "producer")
    return get_agent_credit_usage(user["id"])


class UpgradeRequest(BaseModel):
    plan_code: str = Field(min_length=3, max_length=20)
    note: str = Field(default="", max_length=1000)


@router.post("/upgrade-requests")
def request_plan_upgrade(data: UpgradeRequest, user=Depends(_current_user)):
    _require_role(user, "producer")
    code = data.plan_code.strip().lower()
    if code not in PLANS or code == "free":
        raise HTTPException(422, "paid_plan_code_required")
    con = _con()
    existing = _execute(con, """SELECT id FROM marketplace_upgrade_requests
        WHERE user_id=? AND plan_code=? AND status='pending' ORDER BY id DESC LIMIT 1""",
        (user["id"], code)).fetchone()
    if existing:
        con.close()
        return {"request_id": existing["id"], "status": "pending", "duplicate": True}
    if _is_postgres():
        cur = _execute(con, """INSERT INTO marketplace_upgrade_requests(user_id,plan_code,note)
            VALUES(?,?,?) RETURNING id""", (user["id"], code, data.note.strip()))
        request_id = cur.fetchone()["id"]
    else:
        cur = _execute(con, """INSERT INTO marketplace_upgrade_requests(user_id,plan_code,note)
            VALUES(?,?,?)""", (user["id"], code, data.note.strip()))
        request_id = cur.lastrowid
    con.commit()
    con.close()
    add_audit_event("marketplace.upgrade_requested", user["email"], str(request_id),
                    "subscription_request", str(request_id), {"plan": code})
    return {"request_id": request_id, "status": "pending",
            "note": "درخواست ثبت شد؛ تا فعال‌سازی رسمی، پلن فعلی شما تغییر نمی‌کند."}


@router.get("/upgrade-requests", dependencies=[Depends(require_admin)])
def admin_upgrade_requests(limit: int = 100):
    con = _con()
    rows = _execute(con, """SELECT r.id,r.user_id,r.plan_code,r.status,r.note,r.created_at,
        u.company_name,u.email,u.country FROM marketplace_upgrade_requests r
        JOIN marketplace_users u ON u.id=r.user_id
        WHERE r.status='pending' ORDER BY r.id ASC LIMIT ?""", (max(1, min(limit, 300)),)).fetchall()
    con.close()
    return [dict(row) for row in rows]


def _verify_stripe_signature(payload: bytes, signature_header: str) -> bool:
    secret = settings.stripe_webhook_secret
    if not secret or not signature_header:
        return False
    parts = {}
    for item in signature_header.split(","):
        if "=" in item:
            key, value = item.split("=", 1)
            parts.setdefault(key.strip(), []).append(value.strip())
    try:
        timestamp = int(parts.get("t", [""])[0])
    except (TypeError, ValueError):
        return False
    if abs(int(time.time()) - timestamp) > 300:
        return False
    signed = str(timestamp).encode("ascii") + b"." + payload
    expected = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, value) for value in parts.get("v1", []))


def _stripe_subscription_snapshot(subscription_id: str, plan_code: str) -> dict:
    if not settings.stripe_secret_key:
        raise HTTPException(503, "billing_not_configured")
    response = httpx.get("https://api.stripe.com/v1/subscriptions/" + subscription_id,
                         auth=(settings.stripe_secret_key, ""), timeout=15)
    if response.status_code >= 400:
        raise HTTPException(502, "payment_provider_subscription_lookup_failed")
    subscription = response.json()
    items = ((subscription.get("items") or {}).get("data") or [])
    price_id = (((items[0].get("price") or {}).get("id")) if items else None)
    if price_id != _stripe_price_id(plan_code):
        raise HTTPException(400, "payment_price_does_not_match_requested_plan")
    ends_epoch = (items[0].get("current_period_end") if items else None) or subscription.get("current_period_end")
    if not ends_epoch:
        raise HTTPException(400, "payment_period_end_missing")
    return {"id": subscription.get("id"), "status": subscription.get("status"),
            "ends_at": datetime.fromtimestamp(int(ends_epoch), timezone.utc).isoformat(),
            "customer": subscription.get("customer")}


@router.post("/billing/checkout")
def create_billing_checkout(plan_code: str, user=Depends(_current_user)):
    _require_role(user, "producer")
    code = (plan_code or "").strip().lower()
    if code not in ("starter", "growth", "premium"):
        raise HTTPException(422, "paid_plan_code_required")
    price_id, price_display = _stripe_price_id(code), _stripe_price_display(code)
    if not all((settings.stripe_secret_key, settings.stripe_webhook_secret,
                price_id, price_display, settings.billing_success_url, settings.billing_cancel_url)):
        raise HTTPException(503, detail={
            "code": "billing_not_configured",
            "required": ["STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET",
                         "STRIPE_PRICE_ID_" + code.upper(), "STRIPE_PRICE_DISPLAY_" + code.upper(),
                         "BILLING_SUCCESS_URL", "BILLING_CANCEL_URL"],
            "message": "قیمت شفاف و شناسه Price باید در Stripe تنظیم شوند؛ خرید هنوز فعال نیست."
        })
    if urlparse(settings.billing_success_url).scheme != "https" or urlparse(settings.billing_cancel_url).scheme != "https":
        raise HTTPException(503, "billing_return_urls_must_use_https")
    form = {
        "mode": "subscription",
        "line_items[0][price]": price_id,
        "line_items[0][quantity]": "1",
        "success_url": settings.billing_success_url,
        "cancel_url": settings.billing_cancel_url,
        "client_reference_id": str(user["id"]),
        "customer_email": user["email"],
        "metadata[user_id]": str(user["id"]),
        "metadata[plan_code]": code,
        "subscription_data[metadata][user_id]": str(user["id"]),
        "subscription_data[metadata][plan_code]": code,
    }
    try:
        response = httpx.post("https://api.stripe.com/v1/checkout/sessions",
                              data=form, auth=(settings.stripe_secret_key, ""),
                              headers={"Idempotency-Key": secrets.token_urlsafe(24)}, timeout=20)
        if response.status_code >= 400:
            raise HTTPException(502, "payment_provider_checkout_failed")
        session = response.json()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "payment_provider_unavailable")
    checkout_url = session.get("url") or ""
    parsed = urlparse(checkout_url)
    if parsed.scheme != "https" or parsed.hostname != "checkout.stripe.com":
        raise HTTPException(502, "payment_provider_returned_invalid_checkout_url")
    return {"checkout_url": checkout_url, "session_id": session.get("id"),
            "price_display": price_display, "activation": "webhook_confirmed_payment_only"}


def _apply_stripe_event(event: dict):
    event_id = str(event.get("id") or "")
    event_type = str(event.get("type") or "")
    obj = ((event.get("data") or {}).get("object") or {})
    if not event_id or not event_type or not isinstance(obj, dict):
        raise HTTPException(400, "invalid_payment_event")
    if event_type == "checkout.session.completed":
        metadata = obj.get("metadata") or {}
        try:
            user_id = int(metadata.get("user_id"))
        except (TypeError, ValueError):
            raise HTTPException(400, "payment_user_reference_missing")
        plan_code = str(metadata.get("plan_code") or "").lower()
        if plan_code not in ("starter", "growth", "premium") or str(obj.get("client_reference_id")) != str(user_id):
            raise HTTPException(400, "payment_metadata_invalid")
        if obj.get("mode") != "subscription" or obj.get("payment_status") not in ("paid", "no_payment_required"):
            raise HTTPException(400, "payment_not_completed")
        subscription_id = obj.get("subscription")
        if not subscription_id:
            raise HTTPException(400, "payment_subscription_missing")
        snapshot = _stripe_subscription_snapshot(str(subscription_id), plan_code)
        if snapshot["status"] not in ("active", "trialing"):
            raise HTTPException(409, "payment_subscription_not_active")
        con = _con()
        try:
            inserted = _execute(con, """INSERT INTO marketplace_billing_events(event_id,event_type)
                VALUES(?,?) ON CONFLICT(event_id) DO NOTHING""", (event_id, event_type))
            if inserted.rowcount != 1:
                con.rollback()
                return {"received": True, "duplicate": True}
            exists = _execute(con, "SELECT id FROM marketplace_users WHERE id=?", (user_id,)).fetchone()
            if not exists:
                raise HTTPException(404, "payment_user_not_found")
            _execute(con, """UPDATE marketplace_subscriptions SET status='superseded'
                WHERE user_id=? AND status='active'""", (user_id,))
            _execute(con, """INSERT INTO marketplace_subscriptions
                (user_id,plan_code,status,starts_at,ends_at,granted_by,external_reference)
                VALUES(?,?,'active',?,?,?,?)""",
                (user_id, plan_code, datetime.now(timezone.utc).isoformat(),
                 snapshot["ends_at"], "stripe", snapshot["id"]))
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()
        add_audit_event("marketplace.subscription_paid", "stripe", str(user_id),
                        "subscription", str(user_id), {"plan": plan_code, "subscription": snapshot["id"]})
        return {"received": True, "activated": True}
    if event_type in ("customer.subscription.updated", "customer.subscription.deleted", "invoice.payment_failed"):
        subscription_id = obj.get("id") if event_type.startswith("customer.subscription.") else obj.get("subscription")
        if not subscription_id:
            return {"received": True, "ignored": True}
        status = str(obj.get("status") or "")
        if event_type == "customer.subscription.deleted":
            status = "revoked"
        elif event_type == "invoice.payment_failed":
            status = "past_due"
        elif status not in ("active", "trialing"):
            status = "past_due" if status in ("past_due", "unpaid", "incomplete") else "revoked"
        ends_epoch = obj.get("current_period_end")
        if not ends_epoch:
            items = ((obj.get("items") or {}).get("data") or [])
            ends_epoch = items[0].get("current_period_end") if items else None
        ends_at = datetime.fromtimestamp(int(ends_epoch), timezone.utc).isoformat() if ends_epoch else None
        con = _con()
        try:
            inserted = _execute(con, """INSERT INTO marketplace_billing_events(event_id,event_type)
                VALUES(?,?) ON CONFLICT(event_id) DO NOTHING""", (event_id, event_type))
            if inserted.rowcount != 1:
                con.rollback()
                return {"received": True, "duplicate": True}
            sql = "UPDATE marketplace_subscriptions SET status=?"
            params = [status]
            if ends_at:
                sql += ",ends_at=?"
                params.append(ends_at)
            sql += " WHERE external_reference=?"
            params.append(str(subscription_id))
            _execute(con, sql, params)
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()
        return {"received": True, "updated": True}
    con = _con()
    try:
        inserted = _execute(con, """INSERT INTO marketplace_billing_events(event_id,event_type)
            VALUES(?,?) ON CONFLICT(event_id) DO NOTHING""", (event_id, event_type))
        con.commit()
        return {"received": True, "ignored": True, "duplicate": inserted.rowcount != 1}
    finally:
        con.close()


@router.post("/billing/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    if not _verify_stripe_signature(payload, request.headers.get("stripe-signature", "")):
        raise HTTPException(400, "invalid_payment_signature")
    try:
        event = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(400, "invalid_payment_payload")
    return _apply_stripe_event(event)
