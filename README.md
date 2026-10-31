# AI Export Sales Network — MVP

AI-native B2B export-sales operating system.

Core flow: Product -> Market -> Buyer -> Verification -> Match -> Outreach -> Follow-up -> RFQ -> Deal -> Repeat.

Human approval is required for binding offers, final price, contracts, payments, compliance exceptions and high-risk transactions.

## Run locally

1. Copy `.env.example` to `.env`.
2. Install dependencies: `pip install -r requirements.txt`.
3. Start the app: `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
4. Open `/docs` for the API, `/` for the operations dashboard, or `/market` for the public producer/buyer marketplace.

## Deploy to Render

The repository includes `render.yaml` for the web service and PostgreSQL database. In Render, create a Blueprint from this repository and set the requested environment variables before expecting live integrations:

- `ADMIN_TOKEN`: a long, unique random value.
- `AI_API_KEY`: OpenAI API key with access to the configured model.
- `SEARCH_API_KEY`: SerpAPI key for buyer discovery.
- `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`: credentials for an authorized SMTP mailbox. Confirm the SMTP port/provider requirements.
- `AI_BASE_URL`: leave blank unless using a compatible custom endpoint.

Never commit API keys, SMTP passwords, or the production admin token. The integration status endpoint `/system/integrations` is admin-protected and reports whether the providers are configured. A configured provider does not guarantee that credentials are valid; verify with a controlled test.

## Current limitations

- Email sending requires configured SMTP credentials and explicit human confirmation for each send.
- Buyer discovery requires a configured search provider; AI analysis requires a valid AI API key and model access.
- Website/contact evidence is not proof of a buyer's legal identity. Validate important prospects before commercial commitments.
- Production deployment and live delivery must be verified in the hosting environment; repository CI alone does not prove a live service is running.


## Product-agnostic marketplace (MVP)

The public `/market` page supports producer/buyer registration, login, product discovery, producer listings, and buyer sourcing requests. Authenticated producers can browse open requests and request an explainable match ranking. A match is only a discovery candidate: supplier identity, product claims/certificates, and destination compliance are not automatically verified. Users can edit/archive their own listings, edit/close their own requests, change their password (revoking all sessions), and revoke their current session. Repeated invalid login attempts trigger account- and client-address lockouts. Administrators can review scoped verification requests; a review never creates a blanket company/product certification.

The specialist runtime is an admin-only, bounded research workflow. It has no model tool execution or automatic external side effects. Provider outputs are schema-checked and require human review. Approval records do not execute actions. Set a separate `AGENT_APPROVER_TOKEN` in the deployment environment if approval-ledger decisions are needed; do not reuse `ADMIN_TOKEN`.

Marketplace authentication and verification remain MVP-grade: email verification, MFA, password recovery, shared-secret approver identity, independent document review, verified-transaction adjudication, sanctions-screening integrations, and full abuse/rate-limit controls remain launch blockers. Do not treat registration, listing, or match scores as trust certification.


## Release readiness and final-test gate

The admin-only `GET /system/readiness` endpoint returns a secret-free checklist
for required deployment configuration. It distinguishes missing configuration
from actual provider verification: a configured key is not proof that a provider
accepts it, and readiness does not prove the deployed service, DNS/TLS, email
delivery, or scheduled jobs are healthy.

Before the final end-to-end test:

1. Set unique `ADMIN_TOKEN`, `AGENT_APPROVER_TOKEN`, and `AGENT_CRON_TOKEN`
   secrets in the hosting environment. The approver token must not reuse the
   admin token. Set the identical cron token in the scheduler's secret store.
2. Configure a supported AI provider and search provider only if those live
   capabilities are required for the test. Configure SMTP only for a controlled
   mailbox test.
3. Confirm the production database is PostgreSQL and take a restorable backup.
4. Deploy, then check `/health`, `/ready`, `/system/readiness`, and
   `/system/integrations` using an authorized admin session.
5. Run CI and the documented API/UI smoke tests against the deployed release.
   Verify registration, login, role boundaries, session revocation, listing and
   RFQ flows, verification review, agent task creation, compliance hold behavior,
   and approval-ledger immutability.
6. Use synthetic test companies and a controlled mailbox. Do not contact real
   buyers/suppliers, issue firm quotes, sign contracts, or move funds during
   acceptance testing.

A release is not considered production-ready until the deployment checks and
end-to-end tests have passed. Missing secrets, external-provider validation,
legal/compliance screening, email verification/MFA/password recovery, evidence
upload and independent review, and abuse controls remain explicit launch gates.
