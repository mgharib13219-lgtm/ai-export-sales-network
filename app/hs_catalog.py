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
SOURCE_KEYS = ("source", "منبع")


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
            code = re.sub(r"\s+", "", _pick(row, CODE_KEYS))
            fa = _pick(row, FA_KEYS)
            en = _pick(row, EN_KEYS)
            parent = _pick(row, PARENT_KEYS)
            row_source = _pick(row, SOURCE_KEYS) or source
            if not code and not fa:
                continue
            if not re.fullmatch(r"\d{2}(?:\d{2}){0,3}", code):
                raise ValueError(f"invalid_hs_code_at_line_{line_no}")
            if not fa:
                raise ValueError(f"missing_persian_description_at_line_{line_no}")
            if parent and not re.fullmatch(r"\d{2}(?:\d{2}){0,3}", parent):
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
                      level: int | None = Query(default=None, ge=2, le=8),
                      limit: int = Query(default=50, ge=1, le=100),
                      offset: int = Query(default=0, ge=0, le=100000)):
    """Search imported Iranian HS rows by code or Persian/English description."""
    con = _con()
    sql = """SELECT hs_code,description_fa,description_en,parent_code,source,
             source_version,imported_at FROM iran_hs_catalog WHERE is_active=1"""
    params = []
    if q.strip():
        term = q.strip()[:160]
        sql += " AND (hs_code LIKE ? OR description_fa LIKE ? OR description_en LIKE ?)"
        params.extend((f"%{term}%", f"%{term}%", f"%{term}%"))
    if level is not None:
        sql += " AND LENGTH(hs_code)=?"
        params.append(level)
    rows = _execute(con, sql + " ORDER BY hs_code LIMIT ? OFFSET ?",
                    tuple(params) + (limit, offset)).fetchall()
    count = _execute(con, "SELECT COUNT(*) AS n FROM iran_hs_catalog WHERE is_active=1").fetchone()["n"]
    con.close()
    return {"items": [dict(row) for row in rows], "active_catalog_rows": count,
            "limit": limit, "offset": offset}
