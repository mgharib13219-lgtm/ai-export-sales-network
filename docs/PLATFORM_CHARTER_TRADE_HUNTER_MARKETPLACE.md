# Platform Charter: Iran Trade Discovery & Trust Marketplace

## Product identity
This is not a raisin-only exporter dashboard. It is a product-agnostic, two-sided trade marketplace and continuously operating trade-intelligence agent. Raisins are only the first pilot category.

The platform serves:
- Iranian manufacturers, farms, cooperatives, exporters and SMEs that may have no export knowledge.
- International buyers, importers, distributors, retailers, processors and sourcing teams looking for Iranian suppliers.
- Platform trust and compliance operations.

## Core user promise
A producer should be able to create an account, complete identity/business verification, list a product in plain language or upload a catalogue, photos and specifications, and receive guided help. The system should turn incomplete product information into a structured draft, explain missing fields in the user's language, and never invent certifications, capacity, prices or claims.

A buyer should be able to describe a need in plain language, search and discover relevant suppliers/products, compare evidence-backed supplier profiles, request information and catalogue, and leave a review only after a verifiable transaction or platform-mediated interaction.

## Continuous trade-hunter agent
The agent operates on a schedule and on relevant events:
1. Monitor permitted trade news, customs/tariff updates, sanctions notices, market reports, tenders, trade fairs, price indicators, freight signals and competitor activity.
2. Identify product/country demand signals and map them to listed Iranian products and supplier capabilities.
3. Discover potential buyers from lawful public sources and approved data providers.
4. Resolve candidate companies to legal entities; deduplicate and collect official-domain evidence.
5. Score buyer-product fit, market attractiveness, route feasibility, evidence quality and confidence.
6. Explain why an opportunity is recommended, show source URLs and timestamps, and distinguish fact from inference.
7. Match international buyer requests to verified Iranian suppliers.
8. Draft localized product introductions, catalogues, RFQs and follow-ups.
9. Track outcomes and learn from approved user feedback and genuine transaction outcomes.
10. Alert users about high-value opportunities, risks, stale information and actions requiring approval.

The agent must not autonomously send unsolicited outreach, make binding offers, negotiate final prices, accept orders, commit stock, sign contracts, direct payments or promise shipment. These require explicit authorized human approval and auditable records.

## Two-sided marketplace capabilities
### Producer side
- Guided onboarding with Persian-first UX and optional multilingual profile.
- Product listing wizard: product category, HS code suggestion (never treated as customs advice), origin, varieties/specifications, available volume, monthly capacity, seasonality, MOQ, packaging, photos, catalogue, sample availability, certificates and indicative price status.
- AI-assisted translation and catalogue generation with producer review.
- Supplier profile with verified legal identity status, facility evidence where appropriate, product-level verification, response rate, fulfillment history and review summary.
- Lead inbox, buyer requests, quote drafts, sample requests and order pipeline.

### Buyer side
- Buyer onboarding and legal-entity verification.
- Natural-language sourcing request: product, grade, quantity, frequency, destination, packaging, target delivery and required documents.
- Search/filter and AI matching across verified suppliers.
- Evidence-based supplier comparison and request-for-quotation workflow.
- Catalogue downloads and secure messaging after access controls.
- Buyer reputation and transaction history, with privacy and lawful disclosure controls.

## Identity, trust and anti-fraud architecture
Verification must be tiered, not a single badge:
- Email/phone control verification.
- Individual identity verification for account controllers and beneficial owners where legally required.
- Business legal-entity verification against authoritative registries or qualified verification vendors.
- Authority verification: confirm that the user may represent the business.
- Bank-account beneficiary name matching through a regulated provider or documented manual review; never collect banking passwords or one-time codes.
- Product evidence checks: facility, samples, lab reports, certificates and traceability documents, each with issuer, scope, expiry and verification status.
- Transaction verification before a review can be marked as a verified transaction review.

Badges must state exactly what was checked, by whom, and when. No badge may imply a guarantee of quality, solvency or future performance. Expired, disputed or revoked checks must be visible.

### Reviews and reputation
- Only authenticated accounts can review.
- Label review type: verified transaction, verified sample/order interaction, or unverified platform feedback.
- A verified-transaction review requires a platform order/transaction record or robust evidence reviewed by an authorized moderator.
- Prevent duplicate reviews, self-reviews, paid reviews, retaliation and review manipulation.
- Provide right of reply, dispute/appeal, moderation audit trail and correction process.
- Display review count, recency and confidence; do not reduce trust to an opaque single score.
- Separate identity verification, product verification, delivery performance and buyer/seller conduct.

### Fraud prevention
- Risk signals: mismatched company/domain/beneficiary names, newly created domains, copied catalogues, suspicious price deviations, inconsistent documents, repeated devices/accounts, unusual messaging/payment patterns and complaint clusters.
- Risk scores are triage signals, not proof of fraud.
- Hold risky listings or transactions for review; preserve evidence and provide an appeal path.
- Never publish sensitive identity documents or private personal data.
- Minimize collected data, encrypt sensitive fields, restrict staff access, log every privileged action, define retention/deletion policies and conduct security reviews.
- Establish incident reporting, account recovery and impersonation takedown processes.

## Compliance by design
- Country/product-specific screening for sanctions, export controls, import restrictions, customs, food safety, labeling, phytosanitary requirements and payment/logistics availability.
- Maintain source, timestamp, jurisdiction and confidence for every compliance assertion.
- Escalate ambiguity to qualified legal/customs/compliance professionals.
- Do not facilitate prohibited transactions or advise users to evade restrictions.
- Verify applicable privacy, consumer, marketplace, KYC/AML and data-protection obligations before launch in each jurisdiction.

## Agent governance and transparency
- Separate public facts, user-provided claims, model inference and unverified leads.
- Every material lead and market insight must have source URL, observed date, retrieval date and evidence excerpt/hash where lawful.
- Show confidence and missing evidence; do not fabricate buyer intent, contact details, shipment history, ratings or certifications.
- Provide user-visible activity logs, agent pause controls, notification preferences and data export/correction channels.
- Human approval gates for external messages, quotes, contracts, payments, orders and logistics commitments.
- No paid API, data subscription or verification vendor activation without approved budget and user consent.

## Suggested product modules
1. Identity & Business Verification
2. Producer Product Studio
3. Buyer Sourcing Desk
4. Trade Hunter / Market Radar
5. Buyer & Supplier Discovery
6. Matching and Recommendation Engine
7. Trust, Reviews & Disputes
8. RFQ, Catalogue and Messaging Workspace
9. Quote, Order and Shipment Workflow
10. Compliance & Risk Monitor
11. Admin, Moderation and Audit Center
12. Analytics, Alerts and Learning Loop

## Phased delivery
### Phase 1 — Safe foundation
- Multi-tenant roles and permissions: producer, buyer, verifier, moderator, admin.
- Product-agnostic catalog and supplier/buyer profiles.
- Evidence-backed lead schema and agent activity log.
- Manual verification workflow and transparent status labels.
- Admin review queue, report/appeal handling and audit logs.
- Raisins pilot as sample category, not a hard-coded product limitation.

### Phase 2 — Discovery and matching
- Scheduled news/trade signal ingestion.
- Buyer discovery and company resolution.
- Product-to-buyer and buyer-to-supplier matching.
- Localized catalogue and RFQ drafts.
- Human-approved outreach and response tracking.

### Phase 3 — Trust and transaction workflow
- Qualified identity/business verification integrations.
- Verified interaction/transaction reviews.
- Secure messaging, quote comparison, sample and order records.
- Fraud detection triage and dispute resolution.

### Phase 4 — Scalable intelligence
- Country/category opportunity forecasting.
- Supplier performance insights based on verified outcomes.
- Multilingual assistant and guided onboarding for non-experts.
- Measured learning loop with evaluation, feedback and model monitoring.

## Non-negotiable acceptance criteria
- A novice producer can publish a draft product listing without knowing export terminology.
- A buyer can find and compare suppliers using transparent evidence.
- A user can tell what exactly is verified and what is not.
- No review is called transaction-verified without a verifiable transaction.
- Every surfaced buyer lead has provenance and freshness metadata.
- No autonomous external commercial commitment occurs.
- The platform supports arbitrary product categories; raisins are only initial sample data.
