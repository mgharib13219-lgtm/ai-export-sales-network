# Lead channel integrations and n8n workflow

## Purpose
Importable n8n workflow template for receiving business leads from approved discovery sources and preparing controlled outreach. It is not proof that external accounts are connected or running.

## Integration approach
- Gmail: create a draft for human review when a valid lead has a contact email. Creating the draft does not send the email.
- Telegram: send only when the lead has a valid evidence record, a Telegram chat ID, `opt_in=true`, and `outreach_approved=true`.
- WhatsApp: use WhatsApp Business Platform / Cloud API only; approved templates and opt-in are required where applicable.
- LinkedIn and X: use official APIs, account permissions, or approved exports/partner connectors. Do not scrape logged-in pages, circumvent limits, or send bulk unsolicited DMs.
- Buyer/manufacturer/order signals: use permitted public sources, licensed business-data providers, marketplace APIs, inbound RFQs, or human-curated leads. Preserve source URL, timestamp, evidence, and lawful contact basis.

## Import and setup
1. Import `n8n/workflows/lead-intake-review.json` in n8n.
2. Configure **Header Auth** on the `Lead Intake Webhook` node using a strong, private header credential. Do not activate the workflow while webhook authentication is unset.
3. Configure Gmail and Telegram credentials in n8n. Credentials are not embedded in the JSON.
4. Keep the workflow inactive while configuring and testing. Gmail remains draft-only; Telegram has a separate opt-in and operator-approval gate.
5. Test with synthetic data. Verify that invalid evidence creates no downstream action, a valid email lead creates only a Gmail draft, and Telegram sends only with both explicit booleans true and a chat ID.
6. Configure persistent deduplication, opt-out/unsubscribe handling, rate limits, retention, and role-based access before production.
7. Activate only after negative tests confirm that missing authentication, missing contact basis, missing opt-in, or missing operator approval cannot trigger an external message.

## Webhook payload
Expected fields include `company_name`, `contact_name`, `contact_email`, `telegram_chat_id`, `product_or_order_signal`, `source_url`, `source_name`, `evidence`, `contact_basis`, `opt_in` (boolean), `outreach_approved` (boolean), and `message`.

Records without a company name, valid HTTP/HTTPS source URL, or contact basis are marked invalid and do not reach either channel. A valid record with a contact email can create a Gmail draft without being approved for sending. Telegram requires a chat ID plus both `opt_in=true` and `outreach_approved=true`.

## Status boundary
The workflow is a version-controlled template and is inactive by default. Activating it requires a user-owned n8n instance, webhook authentication, provider credentials, external discovery feeds, persistent deduplication/opt-out controls, and provider account permissions. The repository does not contain those credentials or prove any provider is connected. Never commit secrets.
