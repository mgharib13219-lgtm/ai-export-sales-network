# Final acceptance test plan

This plan is a controlled, non-commercial acceptance test. Use a staging deployment,
synthetic company names, synthetic product data, and a mailbox controlled by the
operator. Never use real buyer/supplier contact data in the test.

## 1. Release identity and service health

Record the Git commit SHA, Render deployment ID, Python version, and database
engine/version. Confirm the deployed SHA is the intended release.

- `GET /health` returns HTTP 200.
- `GET /ready` returns HTTP 200 and reports the database check as successful.
- An unauthenticated request to `GET /system/readiness` is rejected.
- An authorized admin request to `GET /system/readiness` returns a checklist
  without secret values. Resolve every blocker for the capabilities under test.
- `GET /system/integrations` reports the expected configured providers. Then
  perform a controlled provider call; configuration alone is not validation.

## 2. Marketplace user journeys

1. Register a synthetic producer and a separate synthetic buyer.
2. Confirm duplicate email registration is rejected without leaking account data.
3. Log in with each role and confirm role-specific UI/actions.
4. Publish a synthetic listing as producer; search it while logged out.
5. Create a synthetic sourcing request as buyer.
6. Confirm producer can view open requests and request candidate matches.
7. Confirm match output includes reasons/holds and never marks a supplier
   automatically verified or compliant.
8. Confirm buyer cannot edit producer listings and producer cannot edit buyer RFQs.
9. Archive the listing, close the RFQ, and confirm both disappear from active feeds.
10. Change a password; confirm all prior sessions are revoked. Test logout.

## 3. Abuse, trust and compliance boundaries

- Test invalid login attempts and confirm lockout behavior; verify no raw email/IP
  limiter identifiers are persisted.
- Submit a scoped verification request; confirm it is pending by default.
- Confirm non-admin reviewers cannot approve/reject it.
- Admin may record only a scoped status; confirm no global verified badge appears.
- Confirm public reviews remain explicitly unverified.
- Submit an agent task with compliance first and a synthetic destination.
- Confirm missing/invalid AI evidence yields an evidence hold, not a fabricated
  market conclusion or buyer lead.
- Confirm sensitive agent roles cannot run before compliance.
- Confirm approval decisions are immutable and do not trigger external side effects.

## 4. Controlled integrations

- Search: run one narrow, documented query and inspect source URLs and retrieval dates.
- AI: submit synthetic data and verify schema validation, provider error handling,
  provenance, and human-review requirements.
- Email: use only an operator-controlled mailbox; test draft generation first.
  Send only after explicit operator approval and record the message ID.
- Scheduler: trigger one controlled cron run and confirm authentication, idempotency,
  audit history, and bounded execution. Do not run concurrent duplicate jobs.

## 5. Data and recovery

- Verify database backups exist and restore one to an isolated test database.
- Verify session expiry and cleanup.
- Verify logs/audit records contain no passwords, bearer tokens, API keys, or
  full database connection strings.
- Confirm retention/deletion procedures and privacy notices before public launch.

## Acceptance criteria

The release passes only when all tests for the enabled capabilities pass on the
deployed commit, no critical/high security issue remains open, backup restore is
proven, and an operator signs off. Any unconfigured integration is marked disabled
or draft-only; it must not be described as operational.

## Explicit launch blockers outside this MVP

Email verification, MFA, password recovery, independent company/representative
and certificate verification, secure evidence upload/storage and retention,
independent sanctions/export-control screening, destination-specific product
compliance, dispute handling, transaction verification, distributed rate limiting,
and a robust named approver identity process require additional implementation
and/or specialist review before unrestricted public trading.
