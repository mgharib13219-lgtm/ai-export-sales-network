"""Iranian customs HS master catalogue with controlled CSV ingestion.

The importer accepts the source file as UTF-8 CSV in the request body. It does
not fabricate tariff rows: only supplied source rows are persisted, with source
and import timestamp recorded. Supports 2/4/6/8 digit HS hierarchy codes.
"""
import csv
import io
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.auth import require_admin
from app.db import _con, _execute, _is_postgres

router = APIRouter(prefix="/trade/hs-catalog", tags=["iran-hs-catalog"])

MAX_CSV_BYTES = 25 * 1024 * 1024
CODE_KEYS = ("hs_code", "code", "tariff_code", "کد", "کدتعرفه", "کد تعرفه")
FA_KEYS = ("description_fa", "name_fa", "description", "نام", "شرح", "شرح تعرفه", "شرح کالا")
EN_KEYS = ("description_en", "name_en", "english_description", "نام انگلیسی", "شرح انگلیسی")
PARENT_KEYS = ("parent_code", "parent")
DIGITS_KEYS = ("digits", "length", "رقم")
SOURCE_KEYS = ("source", "source_id", "منبع")


def init_hs_catalog():
    con = _con()
    sql = """CREATE TABLE IF NOT EXISTS iran_hs_catalog (
        hs_code TEXT PRIMARY KEY,
        description_fa TEXT NOT NULL,
        description_en TEXT NOT NULL DEFAULT '',
        parent_code TEXT,
        source TEXT NOT NULL,
        source_version TEXT NOT NULL DEFAULT '',
        imported_at TIMESTAMP NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1
    )"""
    _execute(con, sql)
    _execute(con, "CREATE INDEX IF NOT EXISTS idx_iran_hs_fa ON iran_hs_catalog(description_fa)")
    _execute(con, "CREATE INDEX IF NOT EXISTS idx_iran_hs_parent ON iran_hs_catalog(parent_code)")
    con.commit()
    con.close()


def _pick(row, keys):
    normalized = {str(k).strip().lower(): (v or "").strip() for k, v in row.items() if k is not None}
    for key in keys:
        value = normalized.get(key.lower())
        if value:
            return value
    return ""


def _normalize_code(value, digits=None):
    raw = str(value or "").strip().replace(",", "").replace(" ", "")
    if raw.endswith(".0"):
        raw = raw[:-2]
    if not raw.isdigit():
        return ""
    width = int(digits) if str(digits or "").isdigit() else len(raw)
    if width not in (2, 4, 6, 8):
        return ""
    return raw.zfill(width)


@router.post("/import-csv", dependencies=[Depends(require_admin)])
async def import_hs_csv(request: Request,
                        source: str = Query(min_length=3, max_length=300),
                        source_version: str = Query(default="", max_length=100)):
    """Replace/upsert tariff descriptions from an explicitly supplied source CSV."""
    raw = await request.body()
    if not raw or len(raw) > MAX_CSV_BYTES:
        raise HTTPException(413 if len(raw) > MAX_CSV_BYTES else 400, "csv_missing_or_too_large")
    try:
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise ValueError("missing_csv_header")
        now = datetime.now(timezone.utc).isoformat()
        prepared = []
        seen = set()
        for line_no, row in enumerate(reader, start=2):
            raw_code = re.sub(r"\s+", "", _pick(row, CODE_KEYS))
            digits = _pick(row, DIGITS_KEYS)
            code = _normalize_code(raw_code, digits or None)
            fa = _pick(row, FA_KEYS)
            en = _pick(row, EN_KEYS)
            raw_parent = _pick(row, PARENT_KEYS)
            row_source = _pick(row, SOURCE_KEYS) or source
            if not raw_code and not fa:
                continue
            if not code:
                raise ValueError(f"invalid_hs_code_at_line_{line_no}")
            parent = ""
            if raw_parent:
                parent = _normalize_code(raw_parent, len(code) - 2 if len(code) > 2 else None)
                if not parent or len(code) <= 2:
                    raise ValueError(f"invalid_parent_code_at_line_{line_no}")
            if code in seen:
                raise ValueError(f"duplicate_hs_code_at_line_{line_no}")
            seen.add(code)
            prepared.append((code, fa[:1000], en[:1000], parent or (code[:-2] if len(code) > 2 else None),
                             row_source[:300], source_version, now, 1))
        if not prepared:
            raise ValueError("no_valid_rows_found")
    except (UnicodeDecodeError, csv.Error, ValueError) as exc:
        raise HTTPException(422, str(exc)[:180])

    con = _con()
    try:
        for values in prepared:
            _execute(con, """INSERT INTO iran_hs_catalog
                (hs_code,description_fa,description_en,parent_code,source,source_version,imported_at,is_active)
                VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(hs_code) DO UPDATE SET
                description_fa=excluded.description_fa,
                description_en=excluded.description_en,
                parent_code=excluded.parent_code,
                source=excluded.source,
                source_version=excluded.source_version,
                imported_at=excluded.imported_at,
                is_active=1""", values)
        con.commit()
        total = _execute(con, "SELECT COUNT(*) AS n FROM iran_hs_catalog WHERE is_active=1").fetchone()["n"]
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
    return {"status": "imported", "rows_received": len(prepared),
            "active_catalog_rows": total, "source": source,
            "source_version": source_version, "imported_at": now}


@router.get("")
def search_hs_catalog(q: str = Query(default="", max_length=160),
                      level: int | None = Query(default=None),
                      limit: int = Query(default=50, ge=1, le=100),
                      offset: int = Query(default=0, ge=0, le=100000)):
    """Search imported Iranian HS rows by code or Persian/English description."""
    if level is not None and level not in (2, 4, 6, 8):
        raise HTTPException(422, "invalid_hs_level")
    con = _con()
    sql = """SELECT hs_code,description_fa,description_en,parent_code,source,
             source_version,imported_at FROM iran_hs_catalog WHERE is_active=1"""
    count_sql = "SELECT COUNT(*) AS n FROM iran_hs_catalog WHERE is_active=1"
    params = []
    count_params = []
    if q.strip():
        term = q.strip()[:160]
        sql += " AND (hs_code LIKE ? OR description_fa LIKE ? OR description_en LIKE ?)"
        like_params = (f"%{term}%", f"%{term}%", f"%{term}%")
        params.extend(like_params)
        count_sql += " AND (hs_code LIKE ? OR description_fa LIKE ? OR description_en LIKE ?)"
        count_params.extend(like_params)
    if level is not None:
        sql += " AND LENGTH(hs_code)=?"
        params.append(level)
        count_sql += " AND LENGTH(hs_code)=?"
        count_params.append(level)
    try:
        rows = _execute(con, sql + " ORDER BY hs_code LIMIT ? OFFSET ?",
                        tuple(params) + (limit, offset)).fetchall()
        count = _execute(con, count_sql, tuple(count_params)).fetchone()["n"]
    finally:
        con.close()
    return {"items": [dict(row) for row in rows], "active_catalog_rows": count,
            "limit": limit, "offset": offset}
