# AI Export Trade Network — Product & Delivery Blueprint

> Status: proposal for staged implementation. This document does not authorize production deployment, payments, legal representation, or external outreach.

## Product promise

A simple, guided B2B trade workspace where suppliers can list goods and buy visibility/leads, buyers can describe demand, and platform-operated AI agents discover matches and coordinate trade workflows. The platform earns recurring subscription revenue and transparent, contractually agreed transaction fees.

## UX principles (non-negotiable)

1. One primary action per screen; no dashboard overloaded with competing widgets.
2. Use plain language, explain trade jargon inline, and show progressive disclosure.
3. A first-time user should complete profile, product/RFQ, and first chat through a guided checklist.
4. Always show deal stage, next action, responsible party, and fees before commitment.
5. Locale is user-selectable; persist language and directionality. Arabic and Persian need RTL; other locales LTR.
6. AI actions are preview-first: show intended message, recipient, source, and rationale before any external send.
7. Never disguise an AI/platform representative as the actual buyer/supplier. Clearly label “Platform trade agent acting on behalf of …”; reveal legal counterparty identity at contract/KYC milestones with consent and applicable law.
8. Accessible responsive layout, readable typography, consistent navigation, and friendly empty states.
9. Keep sensitive buyer/contact data gated by role, purpose, consent, subscription entitlement, and deal stage.
10. Avoid dark patterns: cancellation, fees, dispute route, and data controls remain discoverable.

## Core personas and jobs

- Supplier/exporter: publish goods, receive qualified RFQs, understand export readiness, obtain buyer discovery and deal support.
- Buyer/importer: specify demand, compare vetted supplier offers, understand risk and landed-cost factors, negotiate in their language.
- Platform sourcing agent: discover public/compliant buyer demand and suppliers, qualify leads, coordinate RFQ and follow-up.
- Deal coordinator: assemble quotes, manage milestones, escalate blockers, keep an auditable deal record.
- Trade/legal specialist: provide jurisdiction-specific, human-reviewed advice and document review within professional scope.
- Platform operations/compliance: approve suppliers, investigate abuse, oversee permissions, audit events and disputes.

## Revenue model (configurable, not hard-coded)

- Supplier plans: Free / Starter / Growth / Premium with explicit limits for listing count, lead access, visibility boosts, analytics and agent-assisted sourcing.
- Paid qualified-lead access, only where terms and buyer consent permit.
- Success fee/commission on platform-originated deals, defined in signed supplier terms and deal attribution rules.
- Paid expert services: legal, customs, inspection, logistics and export-readiness consultations.
- Enterprise contracts for organizations with multiple seats and workflows.
- Advertising/boosting only as a labeled option; ranking must not misrepresent relevance or verification.

## Product domains

### 1. Identity, organization and trust
- Accounts, organization memberships, roles, invitation and verified business profile.
- Verification status is granular (identity, company registration, product evidence, capability, certificates); no blanket “verified” claim.
- KYC/beneficial-owner review and sanctions/export-control screening are provider- and jurisdiction-dependent.
- Least-privilege access, tenant isolation, audit trail and account recovery.

### 2. Catalog and supplier listing
- Product data: title, HS candidate (not authoritative until expert/customs validation), origin, specifications, capacity, MOQ, lead time, Incoterms version/place, certifications, photos and availability.
- Listing quality score with actionable fixes; never imply a score is a legal certification.
- Dormant-listing agent: configurable inactivity thresholds (e.g. 7/30 days), diagnose price/data/market/lead-time issues, propose edits and new market targets. Supplier approves material changes.

### 3. Buyer discovery / supplier discovery agents
- Sources: public company websites, public trade directories, public RFQs and licensed datasets; use only permitted access.
- Source registry records URL, collection timestamp, access basis, permitted purpose, retention and confidence.
- Extract organization/product/need signals; deduplicate; score fit, freshness, geography, compliance and confidence.
- Respect robots, platform terms, privacy, anti-spam, rate limits, opt-outs, and local marketing laws. No credential bypass, CAPTCHA bypass, private-data scraping, or unsolicited bulk messaging.
- Outreach pipeline: candidate → researched → qualified → draft → human review (configurable) → permitted send → response → opportunity → closed/lost.
- Messages are individualized, truthful, and clearly identify platform/agent and why recipient is contacted. Provide opt-out and suppression lists.
- Start with human-approved outreach; expand automation only after legal/compliance review and monitored pilot.

### 4. RFQ and matching
- Buyer RFQ captures product, quantity, target price (optional), destination, delivery window, standards, packaging, payment preferences and required documents.
- Matching ranks supplier capacity, specifications, region, readiness, price range, trust evidence and response history.
- Explain why a match was recommended; allow filters and manual correction.
- Supplier offers normalized into comparable fields; buyer sees differences and assumptions, not a misleading single “best” label.

### 5. Agent-assisted conversation
- Separate buyer-facing and supplier-facing threads, linked by internal opportunity/deal ID.
- Agent translates, summarizes, extracts structured terms and proposes replies.
- AI does not claim to be the counterparty or fabricate approval, quotes, certificates, legal advice, or commitments.
- Contact data filtering before entitlement is an anti-circumvention layer, not a guarantee. Apply multilingual and obfuscation-aware detection; flag rather than silently destroy context; provide safe, policy-compliant appeal.
- Block external contact disclosure until permitted by deal state, consent, policy and contract. Do not prohibit legally required disclosures.
- Attachments initially restricted or quarantined pending malware scan and appropriate OCR/DLP pipeline.

### 6. Deal lifecycle and attribution
- Opportunity has stable ID, origin/source, agent actions, participants, quote revisions and evidence.
- State machine: new → qualified → RFQ → offers → negotiation → buyer-approved terms → contract/KYC → payment arrangement → fulfillment → delivered → closed; separate disputed/cancelled/expired paths.
- No agent may bind either party, accept terms, release funds, or create legal obligations without explicit authorized human approval.
- Attribution rules define sourced-by-platform, commission window, excluded pre-existing relationships, deal amendments, refunds, disputes and audit procedure.
- Ledger is append-only for fees, adjustments and payment-provider events; idempotency keys and signed webhooks required.
- Payment provider, escrow, trade finance, tax and cross-border payout integrations remain out of scope until legal and provider approval.

### 7. Trade readiness and expert network
- Country/product-specific checklists with source date, jurisdiction, applicability and confidence.
- AI research is informational; specialist review required for legal opinions, customs classification, sanctions, licenses, contract enforceability and destination-market compliance.
- Expert directory: jurisdiction, languages, practice area, professional qualification, verification date, engagement terms, conflicts check and fee.
- Avoid representing platform as a law firm unless licensed. Scope and liability must be reviewed by counsel in each operating jurisdiction.
- Export readiness wizard: entity capability, product data, certificates, packaging/labeling, logistics, payment, customs and buyer documentation.
- When a supplier lacks export authorization, refer to a lawful qualified exporter/merchant exporter where available; never suggest evasion.

### 8. Subscription entitlements
- Plan catalog and entitlements stored as versioned configuration.
- Enforcement on server, not only UI: listing limits, buyer/RFQ visibility, lead unlock, boost, analytics and agent sourcing quota.
- Clear renewal, cancellation, refunds, billing currency, taxes, and downgrade effects.
- No exposure of private buyer identity merely because a supplier purchased a plan; use consent, purpose and stage gates.

### 9. Trust, disputes and safety
- Evidence-backed verification, review moderation, complaint reporting, fraud signals and escalation queue.
- Dispute workflow records chronology, submitted evidence, policy, reviewer and outcome.
- Clearly state any protection is limited to eligible transactions and is not a universal guarantee.
- Security: tenant isolation tests, rate limits, abuse detection, secrets management, retention/deletion policy, backups, incident response and access review.

## Simplified user journeys

### Supplier onboarding
1. Choose “I sell / supply”.
2. Create account and organization.
3. Guided company/product profile (save progress).
4. Show export-readiness gaps in plain language.
5. Select free or paid plan with comparison and exact limits.
6. Publish listing after required review.
7. Supplier home: “Your next best action” and a single primary CTA.

### Buyer onboarding
1. Choose “I need to buy”.
2. Guided RFQ, including optional voice/text in chosen language.
3. Show RFQ preview and visibility/consent settings.
4. Match suppliers and explain fit.
5. Compare offers in normalized table.
6. Chat with clearly labeled platform trade agent.
7. Approve terms, then proceed through legal identity/contract/payment gates.

### Navigation model (keep simple)
- Home / Workspace
- Products (supplier) or Buy Requests (buyer)
- Opportunities
- Messages
- Deals
- Services (experts, export readiness, logistics)
- Plan & Billing
- Help / Disputes
Admin/compliance tools remain separate from customer navigation.

## Delivery sequence and acceptance gates

### Phase 0 — Baseline and safety (first)
- Inspect current routes, schema, auth, migrations and tests.
- Identify current behavior and avoid duplicate routes/models.
- Establish migration rollback strategy and tenant-bound access checks.
- Document supported locales and UI direction.
- No production deployment or external outreach.

### Phase 1 — Usable marketplace MVP
- Clean guided onboarding and role-based workspace.
- Supplier listing and buyer RFQ with core fields.
- Server-enforced subscription entitlements (initially mock/provider-neutral billing interface).
- Internal chat threads with translated message drafts and contact-sharing controls.
- Deal IDs, offer history, event audit and attribution.
- Tests for permissions, tenant isolation, entitlements, lifecycle transitions and abuse signals.

### Phase 2 — Agent discovery pilot
- Source registry and compliant public-source search connectors.
- Candidate lead queue with source, timestamp, evidence, fit score and opt-out state.
- Human-reviewed outreach drafts and replies.
- Dormant listing analysis and seller-approved recommendations.
- Pilot metrics: qualified leads, reply rate, RFQ conversion, sourced deals, complaint/opt-out rate.

### Phase 3 — Experts and export-readiness
- Expert profile verification and booking/consult request.
- Country/product checklist with cited current sources and human-review status.
- Legal/customs consult workflow, scoped engagement and secure document handling.

### Phase 4 — Payments, fulfillment and scale
- Payment provider, commission ledger and signed webhook processing.
- Inspection, logistics, dispute and eligible transaction-protection partners.
- Distributed rate limiting, background queues, monitoring, backups and retention automation.
- Security and legal review before activation.

## Minimum test/acceptance checklist

- Unauthorized user cannot read another organization's RFQ, messages, leads or deal.
- Subscription limits are enforced in API endpoints and are not bypassable by direct requests.
- No external outreach occurs without valid permission and configured policy.
- Opt-out/suppression takes precedence over all lead scoring.
- AI draft cannot be sent as a false identity or claim unverified credentials.
- Contact gate considers entitlement, consent and deal stage; legal disclosure exceptions are explicit.
- Deal transitions reject invalid state changes and log actor/source/time.
- Commission calculation is deterministic, versioned, auditable and idempotent.
- Payment events are signature-verified and duplicate-safe before real provider integration.
- UI locale switching preserves content and RTL/LTR behavior.
- Key workflows are usable on mobile and have understandable error/empty/loading states.
- Human expert advice is clearly distinguished from AI-generated information.

## Metrics

North-star: completed, platform-attributed deals with positive contribution margin and low complaint rate.

Track:
- qualified buyer leads per active listing / time-to-first-qualified-lead
- RFQ-to-offer, offer-to-deal, and deal-to-fulfilled conversion
- active suppliers with at least one meaningful opportunity
- supplier subscription retention and plan upgrade/downgrade
- sourced-deal commission revenue and contribution margin
- buyer/supplier response time
- outreach reply, opt-out and complaint rates
- verification coverage and dispute incidence
- task completion, onboarding drop-off, support contacts, and usability feedback

## Explicit exclusions until separately approved

- Deceptive impersonation of buyer/supplier.
- Unreviewed autonomous legal advice or binding negotiation.
- Scraping behind login, bypassing access controls, or bulk spam.
- Guaranteed payment, escrow, certification, legal compliance, or fraud prevention without an actual eligible provider/process.
- Production billing, external outbound campaigns, or deployment without explicit authorization.
