# Autonomous Export Agent — Activation Runbook

## What is already in the repository

- Admin dashboard for CRM and persistent agent profiles.
- Agent profile API and bounded scheduled cycle (up to 3 due profiles per cycle).
- GitHub Actions schedule configured for every 6 hours.
- Scheduled execution is intentionally opt-in: without `AGENT_CRON_TOKEN`, the workflow exits without calling the app.
- Research and drafts only. The agent does not automatically send emails, issue final quotations, sign contracts, purchase services, or make payments.

## Required deployment configuration

Configure these in the Render service's Environment page. Never commit their values to the repository.

Required to protect the dashboard:
- `ADMIN_TOKEN`: strong, unique random secret.

Required to enable scheduled execution:
- `AGENT_CRON_TOKEN`: a different strong, unique random secret. Use the same value in Render and the GitHub repository secret named `AGENT_CRON_TOKEN`.

Required for buyer discovery and AI analysis:
- `SEARCH_PROVIDER=serpapi`
- `SEARCH_API_KEY`: a valid key for the selected search provider.
- `AI_PROVIDER=ensemble` (or select one provider to control costs).
- At least one AI key: `AI_API_KEY`, `ANTHROPIC_API_KEY`, or `GEMINI_API_KEY`.

The app can run without AI/search credentials, but buyer discovery will not be fully operational. Do not configure paid keys until the expected spending limit and usage monitoring have been agreed.

## Turn on the schedule safely

1. In Render, add `AGENT_CRON_TOKEN` and save the environment changes. Allow the service to redeploy.
2. In GitHub, open Settings → Secrets and variables → Actions → New repository secret. Create `AGENT_CRON_TOKEN` with exactly the same value. Do not paste the value into issues, chat, logs, or code.
3. Confirm the Render service has deployed the current `main` branch and that `/health` and `/ready` respond successfully.
4. Open the dashboard, authenticate with `ADMIN_TOKEN`, and create one product profile with a realistic target-country list and an interval of at least 6 hours.
5. Run a manual cycle once, review buyer evidence and the run history, and verify API usage/cost before enabling a wider set of products.
6. Inspect the scheduled-agent GitHub Actions run. If the secret is missing, the workflow intentionally reports that it skipped execution.

## Cost and approval controls

- The scheduled endpoint processes no more than three due profiles per cycle, but this is not a monetary budget. Search and AI providers may bill per request/token.
- Start with one profile and one configured AI provider. Enable multi-model ensemble only after checking the incremental cost.
- Keep outbound email in draft mode until SMTP is configured and the user explicitly approves sending.
- Require human approval for prices, final quotations, contracts, payments, purchases, and compliance exceptions.
- Use provider dashboards or usage caps to limit spending; the app does not yet enforce a provider-level dollar budget.

## Database and secret hygiene

- Back up the PostgreSQL database before major schema or deployment changes.
- The current free database is subject to its provider's expiration/retention terms; arrange a backup or migration before the displayed expiration date.
- If a database password or API key was ever pasted into chat, logs, or source control, rotate it at the provider and update the deployment secret. Do not reuse exposed credentials.

## Current limitations

- A successful CI run verifies tests, not the availability of external providers or the production deployment.
- The schedule cannot discover buyers until provider credentials are configured.
- The agent records research results and run history; it does not guarantee that discovered companies are active importers or that contact details are current. Verify evidence before outreach.
