# ERP and commerce connector architecture

## Decision

Keep the AI Export Sales Network as the system of engagement and trade discovery. Do not replace its marketplace, CRM, matching or trade-intelligence functions with a third-party ERP or shop platform.

Add a vendor-neutral integration boundary so a producer or buyer can optionally connect an existing ERP, inventory system or B2B shop. CosmoShop and Forterro are candidate ecosystems, not dependencies and not approved/active integrations.

No vendor account, subscription, API credential or paid module is required for this architecture work.

## Target architecture

```text
CosmoShop / other B2B shops       Forterro / other ERP
           |                              |
           +-------- vendor adapters -----+
                          |
                Integration gateway
             (tenant isolation, auth, logs)
                          |
                Canonical trade model
       products | inventory | price lists | orders
                          |
       AI Export Sales Network core platform
       buyer discovery | RFQs | matching | CRM
       trade intelligence | compliance holds
```

The platform remains the source of truth for leads, buyer discovery, marketplace identity, match explanations, compliance decisions and agent approvals. A connected ERP remains authoritative for the specific data objects its customer designates (for example stock, SKU, production capacity or order fulfilment status).

## Canonical objects and ownership

| Object | Canonical fields | Default owner | Sync policy |
|---|---|---|---|
| Product/SKU | external_id, SKU, title, description, HS code candidate, origin, unit, packaging | ERP or seller | ERP -> platform; seller-approved publication |
| Inventory | SKU, location, available quantity, unit, observed_at | ERP | read-only pull/webhook; show freshness |
| Price list | SKU, currency, unit price, MOQ, validity | ERP/seller | read-only; never treat as binding quote |
| Buyer/RFQ | buyer reference, product, grade, quantity, destination, requested date | Marketplace | platform -> ERP only after seller approval |
| Order | external order ID, line items, quantities, status, timestamps | agreed per tenant | explicit state mapping and idempotent sync |
| Shipment | carrier, tracking reference, status, event time | ERP/logistics provider | read-only status updates |

All external IDs must be namespaced by tenant and connector. Never merge records across tenants based only on matching names or email addresses.

## Connector contract

Every future adapter must implement these capabilities independently; unsupported capabilities must be reported rather than simulated:

1. Authenticate using the vendor's documented OAuth/API-token mechanism and least-privilege scopes.
2. Validate the remote tenant/company identity before enabling sync.
3. Pull products and inventory with pagination, incremental cursors and rate-limit handling.
4. Push an approved RFQ/order only when the tenant has explicitly enabled that direction.
5. Receive webhooks with signature verification, replay protection and idempotency.
6. Map vendor states to the canonical state model without discarding the original vendor payload.
7. Record sync cursor, source, external ID, observed time, result and retry status.
8. Support disconnect, credential rotation and tenant-scoped deletion/export.

Never store credentials in source control, logs, browser code or ordinary audit payloads. Store secrets in the deployment secret manager, encrypt at rest, redact from diagnostics and permit rotation/revocation.

## Initial vendor assessment

### CosmoShop

CosmoShop publicly documents B2B shop capabilities, APIs and a catalogue of integration modules. Its public materials describe ERP/shop interfaces and integrations including SAP/OCI, JTL, Reybex and other merchandise-management systems. This suggests two possible paths, subject to vendor confirmation:

- Prefer the customer's existing ERP as the inventory/order system of record, and connect that ERP to our platform.
- If the customer only has CosmoShop, evaluate its supported API/export/import or a vendor-supported connector for products, stock and order events.

Do not assume every CosmoShop installation has the same API, modules, permissions or subscription. Confirm the exact product version, API documentation, available events, sandbox, costs and data-processing terms before implementation.

### Forterro

Forterro is a portfolio of ERP products rather than one universal ERP API. Public MyForterro documentation describes tenant-scoped APIs and OAuth-based access for selected services (including AI, e-invoicing and FX); this is not evidence that every Forterro ERP exposes a common inventory/order API.

Before building an adapter, identify the exact Forterro product used by the customer, its version, deployment model, integration interface, tenant model, licensed modules and partner approval requirements. Do not send data to MyForterro endpoints unless the relevant customer tenant and permissions are provisioned.

## Safe rollout

### Phase 0 — current repository change
- Document the vendor-neutral architecture and data ownership.
- Keep integrations disabled by default.
- Do not create fake connected status or sample live data.

### Phase 1 — read-only pilot
- Choose one consenting pilot company and one system of record.
- Use a sandbox or synthetic data first.
- Import product catalogue and stock snapshots only.
- Display source system and last-synced timestamp.
- Reconcile counts and quantities against the source before enabling users.

### Phase 2 — approved workflow handoff
- Let a seller review and approve an RFQ/order export.
- Use idempotency keys and an outbox/retry queue.
- Require a second confirmation for any action that changes stock, price, order acceptance, invoice or shipment commitment.
- Keep all commercial commitments under the existing human-approval policy.

### Phase 3 — operational sync
- Add webhooks, conflict handling, monitoring, retries, dead-letter review and tenant-level disconnect.
- Run backup/restore, access-control and data-protection tests.
- Obtain legal, security and vendor approval before production rollout.

## Mandatory controls

- Tenant isolation at every query, credential, queue, log and external-ID boundary.
- Least privilege and separate credentials per customer tenant.
- TLS in transit; encrypted secret storage; no secrets in logs.
- Schema validation, payload size limits, allowlisted fields and safe HTML/text handling.
- Webhook signature verification, timestamp tolerance, replay prevention and idempotency.
- Rate limits, bounded retries with backoff and dead-letter handling.
- Data minimisation, retention/deletion/export policy and documented lawful basis.
- Audit trail for sync and all write operations.
- Compliance screening remains a separate gate; an ERP connection does not verify a company, product certificate, buyer or transaction.
- No automated unsolicited outreach, firm quotes, contracts, payments, stock commitments or order acceptance.

## Go/no-go checklist for a real connector

Do not start vendor-specific implementation until all are known:
- Customer's exact vendor product/version and hosting model.
- Written customer authorisation and named technical owner.
- Vendor API documentation and permission to integrate.
- Sandbox/test tenant and synthetic dataset.
- Auth flow, scopes, rate limits, pagination and webhook contract.
- Field mapping, source-of-truth decisions and conflict policy.
- Data residency, privacy/security terms and retention requirements.
- Commercial costs and support/SLA expectations.

## Public references reviewed

- CosmoShop interfaces and connector catalogue: https://store.cosmoshop.de/interfaces/
- CosmoShop modules and partners: https://www.cosmoshop.de/cosmoshop/module/
- CosmoShop ePRO and ERP integration overview: https://store.cosmoshop.de/Shopsoftware-ePRO.htm
- MyForterro API usage and tenant-scoped authentication: https://forterro-fwe.atlassian.net/wiki/spaces/MFT/pages/1685717006/How+to+use+the+MyForterro+API
- MyForterro tenant setup: https://forterro-fwe.atlassian.net/wiki/spaces/MFT/pages/2077065329/Tenant+Setup

These are discovery references, not confirmation of a commercial partnership or compatibility with a specific customer installation.
