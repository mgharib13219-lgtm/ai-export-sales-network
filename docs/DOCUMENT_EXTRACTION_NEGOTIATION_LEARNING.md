# Document Extraction, Negotiation Learning, and Follow-up Controls

## Document extraction endpoint

Authenticated operators can upload a single PDF, DOCX, TXT, CSV, TSV, or Markdown file to `POST /crm/documents/extract` using multipart field `file`.

- Files are processed in memory and are not persisted.
- Maximum upload size: 8 MiB.
- PDF: up to 100 pages; embedded text only. Image-only PDFs return an OCR-required warning.
- DOCX: archive entry and uncompressed-size limits are checked before reading paragraphs and tables.
- Text/CSV/TSV: UTF-8 preferred, with Windows-1252 fallback.
- Candidate extraction includes email addresses, possible HS codes, dates, and currency amounts. These are search aids, not validated facts.
- SHA-256 is returned so an operator can identify the exact uploaded bytes.
- The service does not verify signatures, issuers, authenticity, legal validity, or compliance status. Human review remains mandatory.

OCR, image extraction, translation, malware scanning, and external registry checks are not included.

## Negotiation outcome learning

Operators record a won/lost outcome on a lead in the negotiation stage using `POST /crm/leads/{id}/negotiation-outcome`. The admin-only `GET /crm/negotiation/learning` endpoint returns aggregate summaries grouped by currency, Incoterm, and payment terms.

- Segments are hidden until at least three outcome records exist.
- The summary contains win rate and average accepted unit price for wins where a price was recorded.
- No buyer names, emails, or lead IDs are included in the summary.
- The learning agent is deterministic descriptive analytics; it does not train a model or change prices, margins, or approval policy.
- Outcome records are stored as CRM activities and are subject to the application's normal database retention/access controls.

## Follow-up idempotency

A follow-up draft is keyed by lead and attempt number. Repeating the same request returns the prior draft instead of creating a duplicate activity. New attempt numbers are derived from the lead's follow-up activity history. Terminal leads are excluded. Drafts are never sent by this agent; sending still requires a separate explicit approval.

The 3/7/14-day cadence is a default scheduling aid, not a promise that a buyer should be contacted regardless of replies, local rules, or consent.


## Evidence intake and human review ledger

When an operator uploads a document with a CRM `lead_id`, the API records a metadata-only evidence receipt: SHA-256, original filename, extension, size, and extraction length. The uploaded bytes and extracted text are not written to the CRM activity or audit log. The evidence receipt begins in `pending_review`; the original file is not retained by this endpoint, so the operator must preserve the source securely outside the application.

A reviewer must authenticate as an admin and present the separate `AGENT_APPROVER_TOKEN` credential to record a decision. The reviewer also supplies a `reviewer_reference` and a reason. This is an auditable operator reference, **not a verified individual identity**: the current application uses a shared approver credential and does not provide per-user accounts or non-repudiation.

- Decisions are `accepted_for_next_step` or `rejected`; later decisions are appended as new activities and the latest event is shown by the status endpoint.
- An accepted decision means only that a human reviewer recorded a content-review decision for the next workflow step.
- It does **not** establish document authenticity, issuer identity, signature validity, legal validity, or sanctions/export-control clearance.
- Malware scanning is not implemented; the API explicitly reports `malware_scan_performed: false`.
- Files are still processed in memory by the parser; do not upload untrusted documents in production until malware scanning and isolated parsing are deployed.
- Evidence metadata is stored in the existing CRM activity/audit tables. It does not constitute tamper-proof or immutable storage; production needs stronger audit retention and access controls.
