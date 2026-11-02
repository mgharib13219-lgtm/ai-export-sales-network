# Native Trade Workspace

The platform will own its core trade operations and will not require CosmoShop, Forterro, or another ERP vendor.

## Build sequence

1. Tenant-scoped inventory owned by each producer account.
2. Seller-managed price lists with currency, validity dates, unit prices, minimum quantities, Incoterms, and destination scope.
3. Buyer purchase orders and seller order acknowledgements, with explicit human approval gates.
4. Reservation and fulfilment state tracking without payment custody or automatic contractual commitments.

## Non-negotiable controls

- Every record is scoped to its owning account; cross-tenant access is denied by query predicates, not UI filtering.
- Inventory quantities cannot be reduced below reserved quantities.
- Published prices are seller-provided indicative/commercial data, not a binding offer unless separately approved.
- No automatic emails, external writes, payments, or contracts.
- External connectors remain optional adapters; the native data model is canonical.
- Every material mutation is audit logged.
