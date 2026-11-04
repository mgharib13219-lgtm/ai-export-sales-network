# Specialist Agent Operating Guide

## What is now wired into the live opportunity pipeline

The orchestrator runs the following bounded specialist sequence:

1. **Compliance Gatekeeper** — runs first, checks whether product/origin/HS/destination data is present and records explicit risk flags. An explicit risk flag stops discovery and returns a compliance hold.
2. **Supplier Onboarding Specialist** — checks the producer/product profile for missing business facts and evidence gaps. It never verifies identity or certificates.
3. **Catalogue Editor** — creates a seller-fact-only catalogue draft. It does not add quality claims, change HS codes, verify certificates, or publish.
4. **Market Intelligence** — prepares market research for target countries.
5. **Buyer Discovery** — discovers public business candidates. Provider diagnostics are not leads.
6. **Verification and Matching** — collect public website/contact evidence and rank fit. Automated scores are not identity verification.
7. **Outreach Writer and Deal Intelligence** — create drafts and non-binding calculations only.
8. **Independent Quality Auditor** — checks output gates, identity claims, compliance flags and outreach status.

## Important operating semantics

- A missing product field produces `INSUFFICIENT_EVIDENCE`; it does not imply the product is prohibited.
- Explicit compliance risk flags produce `BLOCKED` and stop buyer discovery.
- A completed preflight is never legal clearance. Live sanctions, export-control, beneficial-owner, end-use, licence and import-rule screening are not connected by this change.
- Every discovered match carries `compliance_clearance=false` and `human_compliance_review_required=true` until a qualified human review process exists.
- Catalogue and outreach outputs are drafts. No external message, publication, quotation, contract, shipment, purchase or payment is sent or committed.
- Supplier onboarding statuses describe completeness only; they do not authenticate a company or representative.

## Agent activation

1. Configure one approved search provider and a usage cap.
2. Configure one AI provider initially; enable ensemble only after cost review.
3. Create one agent profile with one product and one or two destination countries.
4. Run one manual cycle and inspect the compliance review, supplier evidence gaps, catalogue draft, discovered evidence, and quality audit.
5. Keep all external actions behind named human approval.
6. Expand to more products only after reviewing cost, lead quality, duplicate rates and provider terms.

## Acceptance tests

Run `python -m pytest -q`. The specialist-agent tests cover missing information, explicit compliance blocks, seller-claim preservation, evidence gaps, and audit failures. Integration tests verify the compliance gate executes before buyer discovery and that compliance holds remain attached to matches.

## Not yet implemented

- Live sanctions/restricted-party and beneficial-owner data integrations.
- Product-specific export-control classification and official customs rule feeds.
- Document upload, OCR, tamper detection, evidence hashing and human adjudication workflow.
- Supplier/representative identity verification and certificate validation.
- Persistent task queue, worker leases and retry/dead-letter handling for long-running specialist tasks.
- Per-provider dollar budgets, usage metering and circuit breakers.
- MFA, distributed rate limiting, and production-grade abuse controls.
