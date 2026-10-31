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

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from app.db import _con, _execute, _is_postgres, add_audit_event

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
    for statement in statements:
        _execute(con, statement)
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


class Register(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    company_name: str = Field(min_length=2, max_length=180)
    country: str = Field(min_length=2, max_length=100)
    role: str
    password: str = Field(min_length=12, max_length=200)


class Login(BaseModel):
    email: str
    password: str


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


@router.post("/login")
def login(data: Login):
    con = _con()
    row = _execute(con, "SELECT * FROM marketplace_users WHERE email=?", (data.email.strip().lower(),)).fetchone()
    if not row or not _verify_password(data.password, row["password_hash"]):
        con.close()
        raise HTTPException(401, "invalid_credentials")
    token = secrets.token_urlsafe(40)
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    _execute(con, "INSERT INTO marketplace_sessions(token_hash,user_id,expires_at) VALUES(?,?,?)",
             (hashlib.sha256(token.encode()).hexdigest(), row["id"], expires.isoformat()))
    con.commit()
    user = {"id": row["id"], "email": row["email"], "company_name": row["company_name"],
            "country": row["country"], "role": row["role"]}
    con.close()
    return {"access_token": token, "token_type": "bearer", "expires_at": expires.isoformat(), "user": user}


@router.get("/me")
def me(user=Depends(_current_user)):
    return user


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


@router.get("/products")
def list_products(q: Optional[str] = None, category: Optional[str] = None, limit: int = 50):
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


@router.get("/requests")
def list_requests(category: Optional[str] = None, limit: int = 50, user=Depends(_current_user)):
    _require_role(user, "producer")
    clauses, values = [], []
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
    con = _con()
    verification_id = _id_insert(con, """INSERT INTO marketplace_verifications
        (user_id,verification_type,notes) VALUES(?,?,?)""",
        (user["id"], data.verification_type, data.notes))
    con.commit()
    con.close()
    add_audit_event("marketplace.verification_requested", user["email"], str(verification_id),
                    "verification", str(verification_id), {"status": "pending"})
    return {"verification_id": verification_id, "status": "pending",
            "note": "No verification badge is granted until evidence is reviewed by an authorized reviewer."}


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
