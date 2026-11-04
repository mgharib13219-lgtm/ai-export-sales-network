# Commercial Deal and Document Evidence Controls

## Document evidence review

The document evidence agent accepts supplier-provided references or metadata for:
- business registration
- representative authority
- product specification
- certificate evidence
- facility or production evidence

It reports missing items, malformed expiry dates, expired items, and documents expiring within the configured warning window. It does not open files, extract contents, authenticate issuers, verify signatures, or establish legal/compliance clearance. A complete metadata checklist is only ready for human review.

## Deal builder

The deal builder fails closed until an operator explicitly records both compliance review and buyer identity review. Once those gates are supplied, it delegates to the quotation agent, which requires every landed-cost input and returns a draft only. It does not send offers, create contracts, accept counteroffers, initiate payments, or bind the parties.

## Quotation input rules

- Currency must be a three-letter alphabetic code.
- Base price and all cost inputs must be finite, non-negative numbers.
- Every configured cost component must be supplied; zero is valid and is not treated as missing.
- Margin must be finite and between 0 and 100 percent (exclusive upper bound).
- Validity must be an integer from 1 to 365 days.
- Final price, margin, Incoterm, payment terms, document requirements, and offer publication remain subject to human approval.

## Operational limitation

The current evidence workflow is metadata-only. File upload, malware scanning, OCR, translation, signature/issuer validation, sanctions screening, and regulatory determination require separate integrations and must not be implied by a successful checklist.
