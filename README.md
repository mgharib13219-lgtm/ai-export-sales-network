# AI Export Sales Network — MVP

AI-native B2B export-sales operating system.

Core flow: Product -> Market -> Buyer -> Verification -> Match -> Outreach -> Follow-up -> RFQ -> Deal -> Repeat.

Human approval is required for binding offers, final price, contracts, payments, compliance exceptions and high-risk transactions.

Local run: copy .env.example to .env, install requirements, then run uvicorn app.main:app.

Production requires PostgreSQL and a strong ADMIN_TOKEN. Email is draft-only by default.
