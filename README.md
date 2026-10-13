# AI Export Sales Network — MVP

AI-native B2B export-sales operating system.

Core flow: Product -> Market -> Buyer -> Verification -> Match -> Outreach -> Follow-up -> RFQ -> Deal -> Repeat.

Human approval is required for binding offers, final price, contracts, payments, compliance exceptions and high-risk transactions.

## Run locally

1. Copy `.env.example` to `.env`.
2. Install dependencies: `pip install -r requirements.txt`.
3. Start the app: `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
4. Open `/docs` for the API or `/` for the dashboard.

## Deploy to Render

The repository includes `render.yaml` for the web service and PostgreSQL database. In Render, create a Blueprint from this repository and set the requested environment variables before expecting live integrations:

- `ADMIN_TOKEN`: a long, unique random value.
- `AI_API_KEY`: OpenAI API key with access to the configured model.
- `SEARCH_API_KEY`: SerpAPI key for buyer discovery.
- `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`: credentials for an authorized SMTP mailbox. Confirm the SMTP port/provider requirements.
- `AI_BASE_URL`: leave blank unless using a compatible custom endpoint.

Never commit API keys, SMTP passwords, or the production admin token. The integration status endpoint `/system/integrations` is admin-protected and reports whether the providers are configured. A configured provider does not guarantee that credentials are valid; verify with a controlled test.

## Current limitations

- Email sending requires configured SMTP credentials and explicit human confirmation for each send.
- Buyer discovery requires a configured search provider; AI analysis requires a valid AI API key and model access.
- Website/contact evidence is not proof of a buyer's legal identity. Validate important prospects before commercial commitments.
- Production deployment and live delivery must be verified in the hosting environment; repository CI alone does not prove a live service is running.
