# Iran Raisins Export Pilot — Operating Brief

## Confirmed commercial inputs
- Origin: Iran.
- Product scope: golden, green, sun-dried and other Iranian raisin varieties.
- Available volume: 20–100 metric tonnes (user-stated; not independently inspected).
- Packaging: bulk bags of 10–12.5 kg and export cartons.
- Price: not yet supplied. Do not publish a firm price or indicative offer until grade, specification, packing, quantity, destination and Incoterms are known.

Machine-readable configuration: `config/raisins_export_pilot.json`.

## Market evidence and initial priorities
The World Bank WITS/UN Comtrade page for HS 080620 reports 2024 imports of Iranian dried grapes:
- European Union: USD 34.68m / 13.86m kg
- Türkiye: USD 26.70m / 11.43m kg
- Germany: USD 6.04m / 2.25m kg
- Azerbaijan: USD 5.15m / 2.79m kg
- Algeria: USD 4.41m / 1.69m kg
- Kazakhstan: USD 4.16m / 8.45m kg

Source: https://wits.worldbank.org/trade/comtrade/en/country/All/year/2024/tradeflow/Imports/partner/IRN/product/080620

These are historical bilateral trade values, not evidence that a named company is currently buying. The EU market-entry guide identifies Türkiye as the dominant dried-grape supplier to Europe and discusses competition and market requirements:
https://www.cbi.eu/market-information/processed-fruit-vegetables-edible-nuts/dried-grapes/market-entry

Trade-data lead discovery (commercial databases; verify each record independently):
- Germany buyer directory: https://www.trademo.com/germany/buyers/raisins
- Türkiye buyer directory: https://www.trademo.com/turkey/buyers/raisins
- Global raisin buyer directory: https://www.trademo.com/buyers/raisins
- Iran-origin shipment lead page: https://www.volza.com/p/yellow-or-raisins/buyers-directory/sourcing-from-iran/

A commercial shipment-data page indexed in October 2026 reports Iran-origin raisin buyer leads including Al Jannat Traders (Pakistan), Ecofruits LLP (Kazakhstan), TOO Altyin Badam and IP Isakov. These are research leads only: verify legal identity, current activity, product match, official contact, sanctions/payment/logistics feasibility and buyer intent before outreach. The source may be subscription-gated and its claims have not been independently audited:
https://www.volza.com/p/yellow-or-raisins/buyers-directory/sourcing-from-iran/

## Lead qualification workflow
1. Discover candidate importers, processors, wholesalers and food distributors.
2. Resolve each candidate to a legal entity and official domain.
3. Confirm raisin/dried-fruit business activity from official pages or reliable shipment records.
4. Seek evidence of Iranian-origin sourcing separately; never infer it from general raisin imports.
5. Capture only publicly listed business contact channels and cite the source URL and access date.
6. Check product fit: variety, grade, moisture, size, color, oil treatment, SO2/additives, defects, microbiology, pesticide residues, packaging and certificates.
7. Check whether Iran origin, payment rails, insurance, carriers and destination customs are lawful and practically available. Escalate uncertainty to a qualified trade/compliance professional.
8. Score with the weights in the JSON profile. Mark missing evidence as unknown, not zero-confidence fact.
9. Draft a tailored inquiry; do not send until the user approves.
10. Do not issue a firm quotation until supplier cost, quality spec, packing, quantity, destination and Incoterms are confirmed.

## Minimum supplier data still required
- City/region and producer/exporter legal name.
- Variety-specific available tonnes (not just total capacity).
- Representative current photos and recent batch samples.
- Grade/specification sheet and lab results (moisture, SO2, pesticide residues, microbiology and relevant contaminants).
- Sorting/processing capability and certifications actually held.
- Packaging dimensions/materials, net/gross weights and palletization.
- Monthly supply capacity and readiness date.
- Ex-works/FOB cost basis and loading port; freight quote can be obtained later.
- Export documentation and customs eligibility.

## Safety and approval boundaries
- Research, evidence collection, deduplication, lead scoring and draft preparation may run automatically.
- No automated emails, WhatsApp messages, calls, RFQs, firm prices, exclusivity, contracts, payment instructions or shipping commitments.
- Human approval is required for outreach, price, contracts, payment, logistics commitments and any compliance exception.
- Do not claim a buyer is verified, interested or ready to purchase without direct evidence.
- Do not claim live agent execution or database insertion unless the deployed service and records are checked.

## Deployment and operational blockers
- The scheduled GitHub Actions workflow calls `POST /agent/cron/run` every six hours, but it is inert until the same `AGENT_CRON_TOKEN` is set in Render and GitHub Actions repository secrets.
- At least one search provider key and at least one AI provider key are required for live discovery/analysis. Paid services must not be enabled without explicit budget approval.
- Render deployment/health has not been independently verified.
- Render Free services may sleep; GitHub Actions is the external trigger, not an always-on worker.
- The linked free Postgres database was previously reported to expire on 2026-11-27. Back up and plan migration before that date.
- Rotate the database password because it was previously exposed in chat; update Render `DATABASE_URL` securely and redeploy.
- CI success is not proof of production readiness. Run health, readiness, auth, cron and end-to-end pilot checks after deployment.

## Immediate pilot sequence
1. Complete supplier facts and product specification.
2. Confirm current export eligibility and destination/payment route with official customs/bank/compliance sources.
3. Build a shortlist from the trade directories and verify candidates from official websites.
4. Ask the user to approve outreach drafts and a spending ceiling before activating external APIs or sending messages.
5. Run one profile, inspect the lead evidence and logs, then increase cadence only after quality is acceptable.
