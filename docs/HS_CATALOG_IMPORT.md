# HS catalogue CSV import

The HS catalogue importer accepts a raw UTF-8 CSV request body. Use the validation
endpoint before importing a new customs file.

## File requirements

- UTF-8 or UTF-8 with BOM; maximum size is 25 MiB.
- Comma, semicolon, and tab delimiters are detected from the sample.
- The header must contain an HS-code column and at least one Persian or English
  description column. Common Persian and English aliases are supported.
- HS codes must represent 2-, 4-, 6-, or 8-digit levels. Persian and Arabic-Indic
  digits are converted to ASCII, and leading zeroes are preserved/padded when a
  digit-level column is supplied.
- A non-empty row needs a code and a Persian or English description. If a parent
  code is supplied, it must equal the immediate two-digit-shorter prefix.
- Duplicate codes within one file are rejected. Validation is all-or-nothing.

## 1. Validate without writing

Send the file as the raw request body, not as multipart form data:

```bash
curl --fail-with-body --silent --show-error \
  -X POST "$BASE_URL/trade/hs-catalog/validate-csv?source=IRICA&source_version=2026" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: text/csv; charset=utf-8" \
  --data-binary @hs.csv
```

The response reports the row count and a preview of up to 10 rows. This endpoint
does not write to the database. Fix any validation error before proceeding.

## 2. Import after validation

Repeat the request using this path:

```text
POST /trade/hs-catalog/import-csv?source=IRICA&source_version=2026
```

The same admin header and raw CSV body are required. The importer runs in a
database transaction and rolls back the import if a database write fails.

**Import behavior is upsert, not full replacement.** Rows supplied in the file
are inserted or updated by HS code. Existing rows missing from a later file are
not deleted or deactivated. This avoids losing catalogue data when a partial
file is uploaded. Back up the production database before importing.

## 3. Verify the imported catalogue

Use the authenticated admin's regular application/API access to query:

```text
GET /trade/hs-catalog?limit=50
GET /trade/hs-catalog?q=0101
GET /trade/hs-catalog?level=4&limit=100
```

The read endpoint returns the active row count and paginated matching records.
Do not treat a successful HTTP response as proof that the source file itself is
the latest official tariff schedule; verify its source and version separately.

Never put the admin token in the URL, commit it to the repository, or paste it
into issue/PR discussions.
