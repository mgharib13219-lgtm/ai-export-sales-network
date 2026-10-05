# AI Export Sales Network — Project State Checkpoint

Last verified: 2026-10-05

## Canonical repository
- GitHub: mgharib13219-lgtm/ai-export-sales-network
- Branch: main

## Product
AI-powered B2B export sales network for Iranian manufacturers.
Core flow:
Product -> Market -> Buyer -> Verification -> Match -> Outreach -> Follow-up -> RFQ -> Deal -> Repeat Deal

The platform is not intended to be a generic marketplace, B2C store, or simple lead directory.

## Current engineering state
Completed and committed:
- FastAPI application structure and existing agent modules
- provider abstraction for AI/search/email
- SSRF protection for buyer-site fetching, including redirect re-validation
- sessionStorage instead of localStorage for dashboard admin token
- HTML escaping for CRM rendering
- production guard rejecting SQLite when ENVIRONMENT=production
- Docker runtime with non-root app user
- startup migration hook via app/migrations.py
- Render Blueprint (render.yaml) with Docker runtime, readiness check and managed Postgres definition
- CI workflow for compile + pytest
- production/deployment documentation
- draft-only email provider; real email sending is intentionally disabled

## Verified tests
Historical local verification before the latest GitHub-only commits:
- compileall: passed
- pytest: 7 passed
- /health: HTTP 200
- /ready: HTTP 200
- database smoke check: ok

Current GitHub Actions status at this checkpoint:
- latest workflow runs were still queued; current main commit CI has NOT been declared passing.

## Not completed / must not be claimed as completed
- Render deployment
- live production URL
- live OpenAI/AI provider test
- live search provider test
- production PostgreSQL persistence test
- high-volume distributed rate limiting/idempotency
- Alembic/transactional schema migration system
- full audit/event store
- jurisdiction-specific legal/privacy review
- commercial anti-circumvention contract review

## Security rule
Never store API keys, passwords, tokens, database credentials, or other secrets in this checkpoint or in chat.
Never claim an external integration is live without an actual successful verification.

## Next engineering priorities
1. Verify latest CI result.
2. Audit current source against the original MVP source; do not overwrite richer source with simplified versions.
3. Harden rate limiting, idempotency and audit/event handling.
4. Verify PostgreSQL compatibility and migration strategy.
5. Add/expand tests for security, failure modes and approval gates.
6. Prepare Render deployment only after the above is sufficiently safe.
