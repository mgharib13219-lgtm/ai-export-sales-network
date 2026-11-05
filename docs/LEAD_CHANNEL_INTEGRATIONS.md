# Lead channel integrations and n8n workflow

## Purpose
Importable n8n workflow skeleton for receiving business leads from approved discovery sources and controlled outreach. It is a template, not proof external accounts are connected or running.

## Integration approach
- Gmail: create an outreach draft for human review; send only after operator approval.
- Telegram: Bot API for chats where the contact initiated or authorized communication. Configure a bot credential and eligible chat ID.
- WhatsApp: WhatsApp Business Platform / Cloud API only; approved templates and opt-in are required where applicable.
- LinkedIn and X: use official APIs, account permissions, or approved exports/partner connectors. No scraping logged-in pages, circumventing limits, or bulk unsolicited DMs.
- Buyer/manufacturer/order signals: use permitted public sources, licensed business-data providers, marketplace APIs, inbound RFQs, or human-curated leads. Preserve source URL, timestamp, evidence, and lawful contact basis.

## Import and setup
1. Import n8n/workflows/lead-intake-review.json in n8n.
2. Configure authentication/secret header for the webhook and start in test mode.
3. Set up Gmail and Telegram credentials in n8n. Credentials are not embedded in the JSON.
4. Gmail stays in draft mode. Telegram node is gated by outreach_approved=true and opt_in=true.
5. Test with dummy data; inspect execution logs and verify no secrets are written to source control.
6. Configure persistent deduplication, opt-out/unsubscribe handling, rate limits, retention, and role-based access before production.

## Webhook payload
company_name, contact_name, contact_email, telegram_chat_id, product_or_order_signal, source_url, source_name, evidence, contact_basis, opt_in (boolean), outreach_approved (boolean), message.

Records missing company name, source URL, or contact basis are rejected. Gmail draft is generated only if contact_email exists. Telegram send requires chat ID plus operator approval and opt-in. External discovery feeds, credentials, and account permissions must be configured by the owner.

## Status boundary
This workflow template can be versioned in Git. Activating it requires a user-owned n8n instance, credentials, webhook configuration, and provider permissions. Do not commit secrets.
