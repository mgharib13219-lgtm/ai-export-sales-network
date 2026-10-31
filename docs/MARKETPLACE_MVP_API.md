# Marketplace MVP API

This first product-agnostic marketplace slice adds producer and buyer accounts,
public product discovery, buyer requests, verification requests, and feedback.

## Endpoints

- `POST /marketplace/register` — create a producer or buyer account.
- `POST /marketplace/login` — obtain a seven-day bearer session.
- `GET /marketplace/me` — inspect the authenticated account.
- `POST /marketplace/logout` — revoke the current bearer session.
- `POST /marketplace/products` — producers publish a product.
- `GET /marketplace/products?q=&category=` — public product search.
- `POST /marketplace/requests` — buyers publish a sourcing request.
- `GET /marketplace/requests` — authenticated producers browse requests.
- `POST /marketplace/verification` — request a review of company credentials.
- `POST /marketplace/reviews` — leave feedback; it is always marked unverified
  until a future evidence-review process confirms an underlying transaction.
- `GET /marketplace/profiles/{user_id}/reviews` — public profile feedback.

## Security and current limitations

Passwords use salted PBKDF2-HMAC-SHA256; bearer tokens are stored as SHA-256
hashes and expire after seven days. Producer-only and buyer-only actions are
role-gated. Important events are written to the existing audit log.

This is an MVP, not a complete production marketplace. It does not yet provide
email verification, password reset, rate limiting, MFA, document upload/storage,
human verification review UI, transaction escrow, sanctions screening, dispute
handling, or verified-transaction review adjudication. Do not treat account
registration or a pending verification request as proof of company identity.


## Buyer-to-supplier discovery matching

`GET /marketplace/matches/requests/{request_id}` (producer session required) ranks published listings for an open buyer request. The deterministic score uses exact category agreement and Jaccard overlap of normalized title/specification terms against listing name/description. Results include reasons, information gaps, and mandatory holds. This is discovery assistance only: supplier identity, product claims/certificates, and destination compliance are never auto-cleared. No supplier is contacted and no offer or commitment is created.
