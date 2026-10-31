"""Product-agnostic public marketplace MVP.

Account credentials are stored as salted PBKDF2 hashes. Sessions are bearer tokens
stored only as SHA-256 hashes. Verification is a review workflow, not an automatic
claim that a company or its products are verified.
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.db import _con, _execute, _is_postgres, add_audit_event
from app.auth import require_admin
from app.marketplace_matching import rank_listings_for_request

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


def init_marketplace():
    con = _con()
    statements = [
        """CREATE TABLE IF NOT EXISTS marketplace_users (
            id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE, company_name TEXT NOT NULL,
            country TEXT NOT NULL, role TEXT NOT NULL, password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS marketplace_sessions (
            token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL,
            expires_at TIMESTAMP NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS marketplace_login_attempts (
            attempt_key TEXT PRIMARY KEY, failures INTEGER NOT NULL DEFAULT 0,
            window_started_at TIMESTAMP NOT NULL, locked_until TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS marketplace_products (
            id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL, name TEXT NOT NULL,
            category TEXT NOT NULL, description TEXT NOT NULL, origin TEXT NOT NULL,
            capacity TEXT, moq TEXT, target_markets TEXT, status TEXT NOT NULL DEFAULT 'published',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS marketplace_requests (
            id INTEGER PRIMARY KEY, buyer_id INTEGER NOT NULL, title TEXT NOT NULL,
            category TEXT NOT NULL, specification TEXT NOT NULL, destination TEXT NOT NULL,
            quantity TEXT, status TEXT NOT NULL DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS marketplace_verifications (
            id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, verification_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending', notes TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, reviewed_at TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS marketplace_reviews (
            id INTEGER PRIMARY KEY, author_id INTEGER NOT NULL, subject_user_id INTEGER NOT NULL,
            transaction_reference TEXT, rating INTEGER NOT NULL, body TEXT NOT NULL,
            verification_status TEXT NOT NULL DEFAULT 'unverified',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"""
    ]
    if _is_postgres():
        statements = [s.replace("id INTEGER PRIMARY KEY", "id BIGSERIAL PRIMARY KEY") for s in statements]
    statements.extend([
        "CREATE INDEX IF NOT EXISTS idx_marketplace_products_status_category ON marketplace_products(status,category)",
        "CREATE INDEX IF NOT EXISTS idx_marketplace_products_owner_status ON marketplace_products(owner_id,status)",
        "CREATE INDEX IF NOT EXISTS idx_marketplace_requests_status_category ON marketplace_requests(status,category)",
        "CREATE INDEX IF NOT EXISTS idx_marketplace_requests_buyer_status ON marketplace_requests(buyer_id,status)",
        "CREATE INDEX IF NOT EXISTS idx_marketplace_sessions_user_expiry ON marketplace_sessions(user_id,expires_at)",
        "CREATE INDEX IF NOT EXISTS idx_marketplace_reviews_subject_created ON marketplace_reviews(subject_user_id,created_at)",
        "CREATE INDEX IF NOT EXISTS idx_marketplace_verifications_user_status ON marketplace_verifications(user_id,status)",
    ])
    for statement in statements:
        _execute(con, statement)
    now = datetime.now(timezone.utc).isoformat()
    _execute(con, "DELETE FROM marketplace_sessions WHERE expires_at<=?", (now,))
    _execute(con, "DELETE FROM marketplace_login_attempts WHERE window_started_at<=? AND (locked_until IS NULL OR locked_until<=?)",
             ((datetime.now(timezone.utc) - timedelta(days=1)).isoformat(), now))
    con.commit()
    con.close()


def _id_insert(con, sql, values):
    if _is_postgres():
        sql += " RETURNING id"
    cur = _execute(con, sql, values)
    return cur.fetchone()["id"] if _is_postgres() else cur.lastrowid


def _hash_password(password: str, salt: Optional[bytes] = None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310000)
    return salt.hex() + "$" + digest.hex()


def _verify_password(password: str, stored: str):
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 310000)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


DUMMY_PASSWORD_HASH = _hash_password("constant-dummy-password-not-for-login")


class Register(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    company_name: str = Field(min_length=2, max_length=180)
    country: str = Field(min_length=2, max_length=100)
    role: str
    password: str = Field(min_length=12, max_length=200)


class Login(BaseModel):
    email: str
    password: str


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=12, max_length=200)


class ProductListing(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    category: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=10, max_length=8000)
    origin: str = Field(min_length=2, max_length=100)
    capacity: Optional[str] = Field(default=None, max_length=200)
    moq: Optional[str] = Field(default=None, max_length=200)
    target_markets: Optional[str] = Field(default=None, max_length=1000)


class BuyRequest(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    category: str = Field(min_length=2, max_length=120)
    specification: str = Field(min_length=10, max_length=8000)
    destination: str = Field(min_length=2, max_length=100)
    quantity: Optional[str] = Field(default=None, max_length=200)


class VerificationRequest(BaseModel):
    verification_type: str = Field(min_length=3, max_length=80)
    notes: str = Field(default="", max_length=2000)


class VerificationDecision(BaseModel):
    status: str = Field(min_length=5, max_length=30)
    notes: str = Field(default="", max_length=2000)


class ReviewCreate(BaseModel):
    subject_user_id: int = Field(gt=0)
    transaction_reference: Optional[str] = Field(default=None, max_length=200)
    rating: int = Field(ge=1, le=5)
    body: str = Field(min_length=10, max_length=3000)


def _current_user(authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "login_required")
    token = authorization[7:].strip()
    if len(token) < 32:
        raise HTTPException(401, "invalid_session")
    con = _con()
    row = _execute(con, """SELECT u.id,u.email,u.company_name,u.country,u.role
        FROM marketplace_sessions s JOIN marketplace_users u ON u.id=s.user_id
        WHERE s.token_hash=? AND s.expires_at>?""",
        (hashlib.sha256(token.encode()).hexdigest(), datetime.now(timezone.utc).isoformat())).fetchone()
    con.close()
    if not row:
        raise HTTPException(401, "session_expired")
    return dict(row)


def _require_role(user, role):
    if user["role"] != role:
        raise HTTPException(403, "role_not_permitted")


@router.post("/register")
def register(data: Register):
    role = data.role.strip().lower()
    if role not in ("producer", "buyer"):
        raise HTTPException(422, "role_must_be_producer_or_buyer")
    email = data.email.strip().lower()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise HTTPException(422, "invalid_email")
    con = _con()
    try:
        user_id = _id_insert(con,
            "INSERT INTO marketplace_users(email,company_name,country,role,password_hash) VALUES(?,?,?,?,?)",
            (email, data.company_name.strip(), data.country.strip(), role, _hash_password(data.password)))
        con.commit()
    except Exception:
        con.rollback()
        raise HTTPException(409, "email_already_registered")
    finally:
        con.close()
    add_audit_event("marketplace.account_registered", email, str(user_id), "user", str(user_id), {"role": role})
    return {"status": "registered", "user_id": user_id, "role": role,
            "next_step": "Login to publish listings or submit buyer requests. Company verification is separate."}


def _login_attempt_keys(email: str, client_host: str):
    normalized_email = email.strip().lower()
    return (
        hashlib.sha256(("email|" + normalized_email).encode("utf-8")).hexdigest(),
        hashlib.sha256(("client|" + client_host).encode("utf-8")).hexdigest(),
    )

def _check_login_lock(con, attempt_key: str, now: datetime):
    row = _execute(con, "SELECT failures,window_started_at,locked_until FROM marketplace_login_attempts WHERE attempt_key=?", (attempt_key,)).fetchone()
    if not row:
        return
    locked_until = row["locked_until"]
    if locked_until and str(locked_until) > now.isoformat():
        raise HTTPException(429, "login_temporarily_locked")
    started = datetime.fromisoformat(str(row["window_started_at"]).replace("Z", "+00:00"))
    if (now - started).total_seconds() > 900:
        _execute(con, "DELETE FROM marketplace_login_attempts WHERE attempt_key=?", (attempt_key,))

def _record_login_failure(con, attempt_key: str, now: datetime):
    row = _execute(con, "SELECT failures,window_started_at FROM marketplace_login_attempts WHERE attempt_key=?", (attempt_key,)).fetchone()
    if not row:
        _execute(con, "INSERT INTO marketplace_login_attempts(attempt_key,failures,window_started_at,locked_until) VALUES(?,?,?,?)", (attempt_key, 1, now.isoformat(), None))
        return
    started = datetime.fromisoformat(str(row["window_started_at"]).replace("Z", "+00:00"))
    if (now - started).total_seconds() > 900:
        _execute(con, "UPDATE marketplace_login_attempts SET failures=1,window_started_at=?,locked_until=NULL WHERE attempt_key=?", (now.isoformat(), attempt_key))
        return
    failures = int(row["failures"]) + 1
    locked = (now + timedelta(minutes=15)).isoformat() if failures >= 5 else None
    _execute(con, "UPDATE marketplace_login_attempts SET failures=?,locked_until=? WHERE attempt_key=?", (failures, locked, attempt_key))

@router.post("/login")
def login(data: Login, request: Request):
    email = data.email.strip().lower()
    now = datetime.now(timezone.utc)
    client_host = request.client.host if request.client else "unknown"
    attempt_keys = _login_attempt_keys(email, client_host)
    con = _con()
    try:
        for attempt_key in attempt_keys:
            _check_login_lock(con, attempt_key, now)
        row = _execute(con, "SELECT * FROM marketplace_users WHERE email=?", (email,)).fetchone()
        stored_hash = row["password_hash"] if row else DUMMY_PASSWORD_HASH
        password_valid = _verify_password(data.password, stored_hash)
        if not row or not password_valid:
            for attempt_key in attempt_keys:
                _record_login_failure(con, attempt_key, now)
            con.commit()
            raise HTTPException(401, "invalid_credentials")
        for attempt_key in attempt_keys:
            _execute(con, "DELETE FROM marketplace_login_attempts WHERE attempt_key=?", (attempt_key,))
        token = secrets.token_urlsafe(40)
        expires = now + timedelta(days=7)
        _execute(con, "INSERT INTO marketplace_sessions(token_hash,user_id,expires_at) VALUES(?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), row["id"], expires.isoformat()))
        con.commit()
        user = {"id": row["id"], "email": row["email"], "company_name": row["company_name"], "country": row["country"], "role": row["role"]}
    finally:
        con.close()
    return {"access_token": token, "token_type": "bearer", "expires_at": expires.isoformat(), "user": user}

@router.get("/me")
def me(user=Depends(_current_user)):
    return user


@router.post("/password")
def change_password(data: PasswordChange, user=Depends(_current_user)):
    con = _con()
    row = _execute(con, "SELECT password_hash FROM marketplace_users WHERE id=?", (user["id"],)).fetchone()
    if not row or not _verify_password(data.current_password, row["password_hash"]):
        con.close()
        raise HTTPException(401, "current_password_incorrect")
    _execute(con, "UPDATE marketplace_users SET password_hash=? WHERE id=?", (_hash_password(data.new_password), user["id"]))
    _execute(con, "DELETE FROM marketplace_sessions WHERE user_id=?", (user["id"],))
    con.commit()
    con.close()
    add_audit_event("marketplace.password_changed", user["email"], str(user["id"]), "user", str(user["id"]), {"sessions_revoked": True})
    return {"status": "password_changed", "sessions_revoked": True, "next_step": "Log in again on each device."}

@router.post("/logout")
def logout(authorization: Optional[str] = Header(default=None), user=Depends(_current_user)):
    token = authorization[7:].strip()
    con = _con()
    _execute(con, "DELETE FROM marketplace_sessions WHERE token_hash=?",
             (hashlib.sha256(token.encode()).hexdigest(),))
    con.commit()
    con.close()
    add_audit_event("marketplace.session_revoked", user["email"], str(user["id"]),
                    "user", str(user["id"]), {"reason": "user_logout"})
    return {"status": "logged_out"}


@router.post("/products")
def create_product(data: ProductListing, user=Depends(_current_user)):
    _require_role(user, "producer")
    con = _con()
    product_id = _id_insert(con, """INSERT INTO marketplace_products
        (owner_id,name,category,description,origin,capacity,moq,target_markets)
        VALUES(?,?,?,?,?,?,?,?)""",
        (user["id"], data.name, data.category, data.description, data.origin,
         data.capacity, data.moq, data.target_markets))
    con.commit()
    con.close()
    add_audit_event("marketplace.product_published", user["email"], str(product_id),
                    "product", str(product_id), {"owner_id": user["id"]})
    return {"product_id": product_id, "status": "published"}


@router.patch("/products/{product_id}")
def update_product(product_id: int, data: ProductListing, user=Depends(_current_user)):
    _require_role(user, "producer")
    con = _con()
    cur = _execute(con, """UPDATE marketplace_products SET name=?,category=?,description=?,
        origin=?,capacity=?,moq=?,target_markets=? WHERE id=? AND owner_id=? AND status='published'""",
        (data.name, data.category, data.description, data.origin, data.capacity, data.moq,
         data.target_markets, product_id, user["id"]))
    con.commit()
    con.close()
    if cur.rowcount != 1:
        raise HTTPException(404, "published_product_not_found_or_not_owned")
    add_audit_event("marketplace.product_updated", user["email"], str(product_id),
                    "product", str(product_id), {"owner_id": user["id"]})
    return {"product_id": product_id, "status": "updated"}


@router.delete("/products/{product_id}")
def archive_product(product_id: int, user=Depends(_current_user)):
    _require_role(user, "producer")
    con = _con()
    cur = _execute(con, """UPDATE marketplace_products SET status='archived'
        WHERE id=? AND owner_id=? AND status='published'""", (product_id, user["id"]))
    con.commit()
    con.close()
    if cur.rowcount != 1:
        raise HTTPException(404, "published_product_not_found_or_not_owned")
    add_audit_event("marketplace.product_archived", user["email"], str(product_id),
                    "product", str(product_id), {"owner_id": user["id"]})
    return {"product_id": product_id, "status": "archived"}


@router.get("/products")
def list_products(q: Optional[str] = Query(default=None, max_length=120),
                  category: Optional[str] = Query(default=None, max_length=120),
                  limit: int = Query(default=50, ge=1, le=100)):
    limit = max(1, min(limit, 100))
    clauses = ["p.status='published'"]
    values = []
    if q:
        clauses.append("(LOWER(p.name) LIKE ? OR LOWER(p.description) LIKE ?)")
        values.extend([f"%{q.lower()}%", f"%{q.lower()}%"])
    if category:
        clauses.append("LOWER(p.category)=?")
        values.append(category.lower())
    con = _con()
    rows = _execute(con, """SELECT p.id,p.name,p.category,p.description,p.origin,p.capacity,p.moq,
        p.target_markets,p.created_at,u.company_name,u.country
        FROM marketplace_products p JOIN marketplace_users u ON u.id=p.owner_id
        WHERE """ + " AND ".join(clauses) + " ORDER BY p.id DESC LIMIT ?", values + [limit]).fetchall()
    con.close()
    return [dict(r) for r in rows]


@router.post("/requests")
def create_request(data: BuyRequest, user=Depends(_current_user)):
    _require_role(user, "buyer")
    con = _con()
    request_id = _id_insert(con, """INSERT INTO marketplace_requests
        (buyer_id,title,category,specification,destination,quantity) VALUES(?,?,?,?,?,?)""",
        (user["id"], data.title, data.category, data.specification, data.destination, data.quantity))
    con.commit()
    con.close()
    add_audit_event("marketplace.buy_request_created", user["email"], str(request_id),
                    "buy_request", str(request_id), {"buyer_id": user["id"]})
    return {"request_id": request_id, "status": "open"}


@router.patch("/requests/{request_id}")
def update_buy_request(request_id: int, data: BuyRequest, user=Depends(_current_user)):
    _require_role(user, "buyer")
    con = _con()
    cur = _execute(con, """UPDATE marketplace_requests SET title=?,category=?,specification=?,
        destination=?,quantity=? WHERE id=? AND buyer_id=? AND status='open'""",
        (data.title, data.category, data.specification, data.destination, data.quantity,
         request_id, user["id"]))
    con.commit()
    con.close()
    if cur.rowcount != 1:
        raise HTTPException(404, "open_buy_request_not_found_or_not_owned")
    add_audit_event("marketplace.buy_request_updated", user["email"], str(request_id),
                    "buy_request", str(request_id), {"buyer_id": user["id"]})
    return {"request_id": request_id, "status": "updated"}


@router.delete("/requests/{request_id}")
def close_buy_request(request_id: int, user=Depends(_current_user)):
    _require_role(user, "buyer")
    con = _con()
    cur = _execute(con, """UPDATE marketplace_requests SET status='closed'
        WHERE id=? AND buyer_id=? AND status='open'""", (request_id, user["id"]))
    con.commit()
    con.close()
    if cur.rowcount != 1:
        raise HTTPException(404, "open_buy_request_not_found_or_not_owned")
    add_audit_event("marketplace.buy_request_closed", user["email"], str(request_id),
                    "buy_request", str(request_id), {"buyer_id": user["id"]})
    return {"request_id": request_id, "status": "closed"}


@router.get("/requests")
def list_requests(category: Optional[str] = Query(default=None, max_length=120),
                  limit: int = Query(default=50, ge=1, le=100), user=Depends(_current_user)):
    _require_role(user, "producer")
    clauses, values = ["status='open'"], []
    if category:
        clauses.append("LOWER(category)=?")
        values.append(category.lower())
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    con = _con()
    rows = _execute(con, "SELECT id,title,category,specification,destination,quantity,status,created_at "
                   "FROM marketplace_requests" + where + " ORDER BY id DESC LIMIT ?",
                   values + [max(1, min(limit, 100))]).fetchall()
    con.close()
    return [dict(r) for r in rows]


@router.post("/verification")
def request_verification(data: VerificationRequest, user=Depends(_current_user)):
    allowed_types = {
        "company_identity", "company_registration", "representative_authority",
        "product_certificate", "quality_certificate", "export_license",
        "bank_account_ownership", "facility_audit"
    }
    verification_type = data.verification_type.strip().lower()
    if verification_type not in allowed_types:
        raise HTTPException(422, "unsupported_verification_type")
    con = _con()
    verification_id = _id_insert(con, """INSERT INTO marketplace_verifications
        (user_id,verification_type,notes) VALUES(?,?,?)""",
        (user["id"], verification_type, data.notes))
    con.commit()
    con.close()
    add_audit_event("marketplace.verification_requested", user["email"], str(verification_id),
                    "verification", str(verification_id), {"status": "pending"})
    return {"verification_id": verification_id, "status": "pending",
            "note": "No verification badge is granted until evidence is reviewed by an authorized reviewer."}


@router.get("/verification/pending", dependencies=[Depends(require_admin)])
def pending_verifications(limit: int = Query(default=100, ge=1, le=300)):
    con = _con()
    rows = _execute(con, """SELECT v.id,v.user_id,v.verification_type,v.status,v.notes,v.created_at,
        u.email,u.company_name,u.country FROM marketplace_verifications v
        JOIN marketplace_users u ON u.id=v.user_id WHERE v.status='pending'
        ORDER BY v.id ASC LIMIT ?""", (limit,)).fetchall()
    con.close()
    return [dict(row) for row in rows]

@router.patch("/verification/{verification_id}", dependencies=[Depends(require_admin)])
def review_verification(verification_id: int, data: VerificationDecision):
    status = data.status.strip().lower()
    if status not in {"approved", "rejected", "more_info_required"}:
        raise HTTPException(422, "invalid_verification_decision")
    con = _con()
    row = _execute(con, "SELECT id,user_id,status FROM marketplace_verifications WHERE id=?", (verification_id,)).fetchone()
    if not row:
        con.close()
        raise HTTPException(404, "verification_request_not_found")
    if row["status"] != "pending":
        con.close()
        raise HTTPException(409, "verification_request_already_reviewed")
    cur = _execute(con, "UPDATE marketplace_verifications SET status=?,notes=?,reviewed_at=? WHERE id=? AND status='pending'",
                   (status, data.notes, datetime.now(timezone.utc).isoformat(), verification_id))
    if cur.rowcount != 1:
        con.rollback()
        con.close()
        raise HTTPException(409, "verification_request_already_reviewed")
    con.commit()
    con.close()
    add_audit_event("marketplace.verification_reviewed", "admin", str(verification_id),
                    "verification", str(verification_id), {"status": status, "user_id": row["user_id"]})
    return {"verification_id": verification_id, "status": status,
            "note": "This decision applies only to the submitted verification type; it is not blanket company or product certification."}

@router.get("/profiles/{user_id}/verification")
def profile_verification_status(user_id: int):
    con = _con()
    exists = _execute(con, "SELECT id FROM marketplace_users WHERE id=?", (user_id,)).fetchone()
    if not exists:
        con.close()
        raise HTTPException(404, "profile_not_found")
    rows = _execute(con, "SELECT verification_type,status,reviewed_at,created_at FROM marketplace_verifications WHERE user_id=? ORDER BY id DESC LIMIT 100",
                    (user_id,)).fetchall()
    con.close()
    return {"user_id": user_id, "verification_items": [dict(row) for row in rows],
            "blanket_verified": False}

@router.post("/reviews")
def create_review(data: ReviewCreate, user=Depends(_current_user)):
    if data.subject_user_id == user["id"]:
        raise HTTPException(400, "self_review_not_allowed")
    con = _con()
    exists = _execute(con, "SELECT id FROM marketplace_users WHERE id=?", (data.subject_user_id,)).fetchone()
    if not exists:
        con.close()
        raise HTTPException(404, "review_subject_not_found")
    # Reviews are never labelled transaction-verified merely because a reference was supplied.
    review_id = _id_insert(con, """INSERT INTO marketplace_reviews
        (author_id,subject_user_id,transaction_reference,rating,body,verification_status)
        VALUES(?,?,?,?,?,'unverified')""",
        (user["id"], data.subject_user_id, data.transaction_reference, data.rating, data.body))
    con.commit()
    con.close()
    add_audit_event("marketplace.review_created", user["email"], str(review_id),
                    "review", str(review_id), {"verification_status": "unverified"})
    return {"review_id": review_id, "verification_status": "unverified"}


@router.get("/profiles/{user_id}/reviews")
def profile_reviews(user_id: int):
    con = _con()
    rows = _execute(con, """SELECT r.id,r.rating,r.body,r.verification_status,r.created_at,
        u.company_name AS reviewer_company FROM marketplace_reviews r
        JOIN marketplace_users u ON u.id=r.author_id
        WHERE r.subject_user_id=? ORDER BY r.id DESC LIMIT 100""", (user_id,)).fetchall()
    con.close()
    return [dict(r) for r in rows]


@router.get("/matches/requests/{request_id}")
def match_request_to_products(request_id: int, user=Depends(_current_user)):
    """Return explainable discovery candidates; never represents a match as verified."""
    _require_role(user, "producer")
    con = _con()
    request_row = _execute(con, "SELECT * FROM marketplace_requests WHERE id=? AND status='open'",
                           (request_id,)).fetchone()
    if not request_row:
        con.close()
        raise HTTPException(404, "open_buy_request_not_found")
    listings = _execute(con, """SELECT p.id,p.name,p.category,p.description,p.origin,p.capacity,p.moq,
        p.target_markets,u.company_name,u.country
        FROM marketplace_products p JOIN marketplace_users u ON u.id=p.owner_id
        WHERE p.status='published' ORDER BY p.id DESC LIMIT 500""").fetchall()
    con.close()
    matches = rank_listings_for_request(dict(request_row), [dict(row) for row in listings])
    return {"request_id": request_id, "matches": matches,
            "note": "Discovery ranking only. Identity, product claims, certificates and destination compliance remain unverified."}
