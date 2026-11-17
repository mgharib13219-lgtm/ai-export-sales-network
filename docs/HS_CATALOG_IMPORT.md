# HS catalogue import and release procedure

## Current implementation

- The public marketplace exposes a searchable catalogue at `/market`.
- The API reads imported rows from `GET /trade/hs-catalog`.
- Administrators can import a CSV at `POST /trade/hs-catalog/import-csv`.
- The admin import workspace is `/admin/hs-catalog`.
- Supported hierarchy widths are 2, 4, 6 and 8 digits. Leading zeroes are preserved.
- The database stores the supplied source, source version and import timestamp per row.

## Important completeness boundary

The application code is not the tariff dataset. A working search endpoint or an empty catalogue table does not mean that every Iranian tariff line is present. No tariff rows are fabricated or bundled as if they were official. The catalogue is only as complete and current as the authorized source file that an administrator imports.

Before production import, obtain a current CSV from an authoritative customs/tariff source and confirm the right to use and republish it. Keep the original source file, publication date/version and a checksum in the organization's controlled records. Do not import a third-party spreadsheet of unknown origin as official data.

## CSV format

Required columns:
- `hs_code` (or `code` / `tariff_code`)
- `description_fa` (or an accepted Persian description header)

Optional columns:
- `description_en`
- `parent_code`
- `digits` (2, 4, 6 or 8)
- `source`

UTF-8 or UTF-8 with BOM is accepted. Maximum upload size is 25 MiB. Duplicate codes within one file are rejected. Existing codes are upserted, not deleted; importing a partial file does not deactivate old rows.

## Controlled import checklist

1. Confirm the source is official or appropriately licensed.
2. Record source publisher, publication/version date and file checksum.
3. Validate the CSV headers, row count, code widths, parent-child hierarchy and leading zeroes.
4. Import through `/admin/hs-catalog` using the administrator token.
5. Compare imported row counts against the source's published counts.
6. Spot-check representative 2/4/6/8-digit rows and Persian/English search.
7. Record the operator, import time, source version and result in the release evidence.
8. Never treat an AI suggestion as a legally binding customs classification. Final classification and declaration must be checked by a qualified customs professional against the destination country's tariff schedule and applicable rules.

## Deployment verification

After a merge and Render deployment, verify independently:
- `/admin/hs-catalog` returns HTTP 200.
- `/trade/hs-catalog?limit=1` returns the expected active row count.
- A known source code and Persian description return the expected exact record.
- The deployed commit/version is confirmed from deployment metadata or a version endpoint.

A passing GitHub Actions workflow does not prove Render has deployed the same commit.
