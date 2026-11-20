# Production recovery and launch runbook

Last reviewed: 2026-11-20

## Current production inventory

- Web service: `ai-export-sales-network`, Render service `srv-db78v92d0e5s73fn2mm0`.
- Live URL: https://ai-export-sales-network.onrender.com
- Database: `ai-export-sales-db`, Render Postgres `dpg-dbgttdvb9u1s73985si0-a`.
- Database engine: PostgreSQL 18, Oregon, Free plan.
- Render-reported database expiration: **2026-11-27 11:38:31 UTC**.
- At the review on 2026-11-20, all 27 application tables were present and all 27 had zero rows, including users, products, requests, leads, deals, agent runs, audit events and `iran_hs_catalog`.
- No production customer/trade records were found in those tables during this read-only inspection. The database still contains the application schema and must not be deleted until its replacement is verified.

Render Free Postgres expires 30 days after creation, is inaccessible after expiry unless upgraded, and is deleted after a further 14-day grace period. Free Postgres has no Render-managed backups or PITR. See https://render.com/docs/free and https://render.com/docs/postgresql-backups.

## P0 — Preserve the database before 2026-11-27

1. Do not delete the current database.
2. In Render Dashboard, open the database and copy its **External Database URL**. Do not put it in Git, tickets, chat, shell scripts, or command history.
3. Add `?sslmode=require` (or `&sslmode=require` if query parameters already exist) to the external URL.
4. From a trusted machine with PostgreSQL client tools installed, run:

   ```bash
   export DATABASE_URL='(paste the external URL into this shell only)'
   bash scripts/backup_render_postgres.sh
   unset DATABASE_URL
   ```

5. Copy the generated `.dump` and `.sha256` files to encrypted storage separate from the machine and Render account. Confirm the checksum after copying.
6. Restore the dump into a **separate, empty, non-production PostgreSQL database** using `pg_restore --no-owner --no-privileges --dbname="$TARGET_DATABASE_URL" backup.dump`. Never use `--clean` against a database containing data.
7. Run schema and row-count checks on the restored database. Keep the original database until the new target is validated and the app's connection is switched.
8. For continuity, choose either (a) upgrade the existing Render database in the Dashboard, or (b) create a paid/new managed PostgreSQL instance and restore the dump. Confirm exact plan price and downtime in the Dashboard before approving any charge. A new database requires changing the web service's `DATABASE_URL` to the new internal URL (same Render region/workspace where possible), then redeploying and checking `/ready`.

**Current limitation:** the existing free database has no Render-managed export/PITR, and this environment cannot run `pg_dump` against the secret external URL or save a dump into an owner-controlled encrypted destination. Therefore no backup is claimed as completed. The live database was inspected read-only; all 27 application tables were empty at inspection time, so the migration payload appears to be schema only, but a verified dump is still required before deletion or cutover.

## P1 — Data catalogue (no fabricated trade data)

- `iran_hs_catalog` currently has zero records.
- The existing admin-only `POST /trade/hs-catalog/import-csv` endpoint accepts a source CSV and stores source, version and import timestamp.
- Do not import generated or guessed codes, duty rates, or product descriptions.
- The World Customs Organization's HS-based tariff/nomenclature directory lists Iran Customs' official tariff portal: https://www.wcoomd.org/-/media/wco/public/global/pdf/topics/nomenclature/overview/hs-contracting-parties/positions-of-cp/situation_hs.pdf?la=en . Obtain the current national schedule directly from IRICA and preserve the edition/effective date. The 1405 tariff amendments reported in April 2026 cover 268 tariff lines, which is a warning that an older static file can be stale; secondary news summaries are not a substitute for the official schedule.
- Obtain an official, dated customs/tariff source for the relevant jurisdiction and year. Preserve the source file and licence/usage terms. Validate code widths, hierarchy, effective dates, destination country, and rates with a qualified customs broker before showing landed-cost figures.
- Import first into staging; compare row counts and sample codes against the source; only then import to production. The current catalogue schema stores descriptions/source provenance but is not a complete multi-country tariff-rate model.

## P2 — Controlled buyer/supplier acceptance test

Use staging or an isolated test database only, synthetic company names and `.invalid` email addresses. Never create fake production users or contact real businesses.

- Register separate buyer and producer accounts; test duplicate registration and login failure handling.
- Publish a producer listing; confirm public search visibility.
- Create a buyer RFQ; confirm producer can see it and request explainable candidate matches.
- Confirm tenant/role isolation, edit/archive ownership, contact-sharing consent, session expiry/revocation and buyer inventory restrictions.
- Confirm every match remains an unverified candidate and does not claim supplier identity, certification, customs compliance or commercial availability.
- Archive the listing and close the RFQ; confirm they disappear from active feeds.
- Run CI and retain the workflow result/commit SHA. The latest previously recorded CI result was 139 passed; this is not a substitute for a production end-to-end run.

## P3 — Security and trust launch gates

The repository README and acceptance plan explicitly identify these as remaining blockers. Before unrestricted public trading, implement and independently test:

- email verification, MFA and secure password recovery;
- verified company/representative identity and independently reviewed certificates;
- private evidence upload, access control, malware scanning, retention and deletion;
- sanctions/export-control screening and destination-specific product compliance;
- dispute handling and verified-transaction adjudication;
- distributed rate limiting and abuse monitoring;
- a robust named approver identity process and audit-log review.

Until these gates are met, keep the product in a restricted pilot. Do not describe account registration, a listing, or an AI match score as verification.

## P4 — Operations and release checks

After database continuity is secured:

1. Confirm deployed commit and Render deployment status.
2. Verify `/health` and `/ready`; verify admin-only `/system/readiness` and `/system/integrations` with an authorized admin session. Do not expose tokens in URLs or logs.
3. Validate AI/search providers with controlled test inputs. Keep email draft-only unless SMTP is configured and an operator explicitly approves a test to a controlled mailbox.
4. Check TLS/custom domain, error logs, resource usage, restart behavior, and monthly usage.
5. Establish encrypted off-site backups and a recurring restore drill before accepting customer data.
6. Record an operator sign-off and rollback plan.

## Rollback principles

- Keep the previous database and app deployment until the new connection has passed `/ready` and the acceptance suite.
- Never point production at a test database.
- Never run destructive schema/data changes without a verified backup and an explicit change window.
- If a cutover fails, restore the previous `DATABASE_URL` and redeploy; do not delete either database during incident response.
