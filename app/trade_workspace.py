"""Native tenant-scoped inventory and seller price lists."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.db import _con, _execute, _is_postgres, add_audit_event
from app.marketplace import _current_user, _require_role

router = APIRouter(prefix="/trade", tags=["native-trade-workspace"])


# Starter catalogue templates for the raisins pilot. These are product definitions,
# not claims of available stock, certification, origin, or current seller pricing.
STARTER_CATALOG = [
    {"sku_template": "RAISIN-GOLDEN", "name": "Golden raisins", "name_fa": "کشمش طلایی", "hs_code": "080620", "category": "dried_grapes", "unit": "kg"},
    {"sku_template": "RAISIN-GREEN", "name": "Green raisins", "name_fa": "کشمش سبز", "hs_code": "080620", "category": "dried_grapes", "unit": "kg"},
    {"sku_template": "RAISIN-SULTANA", "name": "Sultana raisins", "name_fa": "کشمش سلطانی", "hs_code": "080620", "category": "dried_grapes", "unit": "kg"},
    {"sku_template": "RAISIN-SUNDRIED", "name": "Sun-dried raisins", "name_fa": "کشمش آفتابی", "hs_code": "080620", "category": "dried_grapes", "unit": "kg"},
    {"sku_template": "RAISIN-BLACK", "name": "Black raisins", "name_fa": "کشمش سیاه", "hs_code": "080620", "category": "dried_grapes", "unit": "kg"},
    {"sku_template": "RAISIN-ORGANIC", "name": "Organic raisins (certification required)", "name_fa": "کشمش ارگانیک (نیازمند گواهی معتبر)", "hs_code": "080620", "category": "dried_grapes", "unit": "kg"}
]


def init_trade_workspace():
    con = _con()
    statements = [
        """CREATE TABLE IF NOT EXISTS trade_inventory (
        id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL, sku TEXT NOT NULL,
        product_name TEXT NOT NULL, warehouse_country TEXT NOT NULL,
        quantity DOUBLE PRECISION NOT NULL, unit TEXT NOT NULL,
        reserved_quantity DOUBLE PRECISION NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'active', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(owner_id,sku))""",
        """CREATE TABLE IF NOT EXISTS trade_price_lists (
        id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL, name TEXT NOT NULL,
        currency TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft',
        valid_from TEXT, valid_until TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS trade_price_items (
        id INTEGER PRIMARY KEY, price_list_id INTEGER NOT NULL, owner_id INTEGER NOT NULL,
        product_name TEXT NOT NULL, unit TEXT NOT NULL, unit_price DOUBLE PRECISION NOT NULL,
        minimum_quantity DOUBLE PRECISION NOT NULL DEFAULT 1, incoterm TEXT,
        destination_country TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(price_list_id) REFERENCES trade_price_lists(id))"""
    ]
    if _is_postgres():
        statements = [s.replace("id INTEGER PRIMARY KEY", "id BIGSERIAL PRIMARY KEY") for s in statements]
    for sql in statements:
        _execute(con, sql)
    _execute(con, "CREATE INDEX IF NOT EXISTS idx_trade_inventory_owner_status ON trade_inventory(owner_id,status)")
    _execute(con, "CREATE INDEX IF NOT EXISTS idx_trade_price_lists_owner_status ON trade_price_lists(owner_id,status)")
    _execute(con, "CREATE INDEX IF NOT EXISTS idx_trade_price_items_list_owner ON trade_price_items(price_list_id,owner_id)")
    con.commit()
    con.close()


def _insert_id(con, sql, values):
    cur = _execute(con, sql + (" RETURNING id" if _is_postgres() else ""), values)
    return cur.fetchone()["id"] if _is_postgres() else cur.lastrowid


class InventoryItem(BaseModel):
    sku: str = Field(min_length=1, max_length=80)
    product_name: str = Field(min_length=2, max_length=180)
    warehouse_country: str = Field(min_length=2, max_length=100)
    quantity: float = Field(ge=0)
    unit: str = Field(min_length=1, max_length=24)


class QuantityUpdate(BaseModel):
    quantity: float = Field(ge=0)


class PriceListCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    currency: str = Field(min_length=3, max_length=10)
    valid_from: Optional[str] = Field(default=None, max_length=30)
    valid_until: Optional[str] = Field(default=None, max_length=30)


class PriceItemCreate(BaseModel):
    product_name: str = Field(min_length=2, max_length=180)
    unit: str = Field(min_length=1, max_length=24)
    unit_price: float = Field(gt=0)
    minimum_quantity: float = Field(default=1, gt=0)
    incoterm: Optional[str] = Field(default=None, max_length=12)
    destination_country: Optional[str] = Field(default=None, max_length=100)


@router.get("/catalog/templates")
def list_catalog_templates(user=Depends(_current_user)):
    """Return starter product definitions; no stock or seller claims are implied."""
    return STARTER_CATALOG


@router.post("/inventory")
def create_inventory(data: InventoryItem, user=Depends(_current_user)):
    _require_role(user, "producer")
    con = _con()
    try:
        item_id = _insert_id(con, """INSERT INTO trade_inventory
        (owner_id,sku,product_name,warehouse_country,quantity,unit) VALUES(?,?,?,?,?,?)""",
        (user["id"], data.sku.strip(), data.product_name.strip(),
         data.warehouse_country.strip(), data.quantity, data.unit.strip()))
        con.commit()
    except Exception:
        con.rollback()
        raise HTTPException(409, "sku_already_exists_or_inventory_conflict")
    finally:
        con.close()
    add_audit_event("trade.inventory_created", user["email"], str(item_id),
                    "inventory", str(item_id), {"owner_id": user["id"]})
    return {"inventory_id": item_id, "status": "created"}


@router.get("/inventory")
def list_inventory(status: str = Query(default="active", pattern="^(active|archived|all)$"),
                   limit: int = Query(default=50, ge=1, le=100),
                   user=Depends(_current_user)):
    _require_role(user, "producer")
    con = _con()
    sql = "SELECT id,sku,product_name,warehouse_country,quantity,unit,reserved_quantity,status,created_at,updated_at FROM trade_inventory WHERE owner_id=?"
    params = (user["id"],)
    if status != "all":
        sql += " AND status=?"
        params += (status,)
    rows = _execute(con, sql + " ORDER BY id DESC LIMIT ?", params + (limit,)).fetchall()
    con.close()
    return [dict(row) for row in rows]


@router.patch("/inventory/{item_id}/quantity")
def update_inventory_quantity(item_id: int, data: QuantityUpdate, user=Depends(_current_user)):
    _require_role(user, "producer")
    con = _con()
    cur = _execute(con, """UPDATE trade_inventory SET quantity=?,updated_at=CURRENT_TIMESTAMP
        WHERE id=? AND owner_id=? AND status='active' AND reserved_quantity<=?""",
        (data.quantity, item_id, user["id"], data.quantity))
    con.commit()
    con.close()
    if cur.rowcount != 1:
        raise HTTPException(404, "inventory_item_not_found_or_quantity_below_reserved")
    add_audit_event("trade.inventory_adjusted", user["email"], str(item_id),
                    "inventory", str(item_id), {"owner_id": user["id"]})
    return {"inventory_id": item_id, "quantity": data.quantity, "status": "updated"}


@router.post("/price-lists")
def create_price_list(data: PriceListCreate, user=Depends(_current_user)):
    _require_role(user, "producer")
    if data.valid_from and data.valid_until and data.valid_until < data.valid_from:
        raise HTTPException(422, "valid_until_before_valid_from")
    con = _con()
    list_id = _insert_id(con, """INSERT INTO trade_price_lists
        (owner_id,name,currency,valid_from,valid_until) VALUES(?,?,?,?,?)""",
        (user["id"], data.name.strip(), data.currency.upper(), data.valid_from, data.valid_until))
    con.commit()
    con.close()
    add_audit_event("trade.price_list_created", user["email"], str(list_id),
                    "price_list", str(list_id), {"owner_id": user["id"]})
    return {"price_list_id": list_id, "status": "draft"}


@router.post("/price-lists/{list_id}/items")
def add_price_item(list_id: int, data: PriceItemCreate, user=Depends(_current_user)):
    _require_role(user, "producer")
    con = _con()
    parent = _execute(con, "SELECT id FROM trade_price_lists WHERE id=? AND owner_id=? AND status='draft'",
                      (list_id, user["id"])).fetchone()
    if not parent:
        con.close()
        raise HTTPException(404, "draft_price_list_not_found")
    item_id = _insert_id(con, """INSERT INTO trade_price_items
        (price_list_id,owner_id,product_name,unit,unit_price,minimum_quantity,incoterm,destination_country)
        VALUES(?,?,?,?,?,?,?,?)""",
        (list_id, user["id"], data.product_name.strip(), data.unit.strip(), data.unit_price,
         data.minimum_quantity, data.incoterm, data.destination_country))
    con.commit()
    con.close()
    add_audit_event("trade.price_item_created", user["email"], str(item_id),
                    "price_item", str(item_id), {"owner_id": user["id"], "price_list_id": list_id})
    return {"price_item_id": item_id, "status": "created"}


@router.get("/price-lists")
def list_price_lists(user=Depends(_current_user)):
    _require_role(user, "producer")
    con = _con()
    rows = _execute(con, """SELECT id,name,currency,status,valid_from,valid_until,created_at
        FROM trade_price_lists WHERE owner_id=? ORDER BY id DESC""", (user["id"],)).fetchall()
    result = []
    for row in rows:
        record = dict(row)
        items = _execute(con, """SELECT id,product_name,unit,unit_price,minimum_quantity,incoterm,destination_country
            FROM trade_price_items WHERE price_list_id=? AND owner_id=? ORDER BY id""",
            (row["id"], user["id"])).fetchall()
        record["items"] = [dict(item) for item in items]
        result.append(record)
    con.close()
    return result


@router.post("/price-lists/{list_id}/publish")
def publish_price_list(list_id: int, user=Depends(_current_user)):
    _require_role(user, "producer")
    con = _con()
    count = _execute(con, "SELECT COUNT(*) AS n FROM trade_price_items WHERE price_list_id=? AND owner_id=?",
                     (list_id, user["id"])).fetchone()["n"]
    if not count:
        con.close()
        raise HTTPException(409, "price_list_requires_at_least_one_item")
    cur = _execute(con, """UPDATE trade_price_lists SET status='published',updated_at=CURRENT_TIMESTAMP
        WHERE id=? AND owner_id=? AND status='draft'""", (list_id, user["id"]))
    con.commit()
    con.close()
    if cur.rowcount != 1:
        raise HTTPException(404, "draft_price_list_not_found")
    add_audit_event("trade.price_list_published", user["email"], str(list_id),
                    "price_list", str(list_id), {"owner_id": user["id"], "item_count": count})
    return {"price_list_id": list_id, "status": "published"}
