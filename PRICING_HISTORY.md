# Pricing history — Cin7 Core Connector

## 2026-08-29 — Initial mandatory per-action pricing

Applied before release under the canonical `Docs/PRICING_POLICY.md`. The map covers every one of the 69 manifest functions exactly once.

- **0 tokens:** `connect_cin7_core`, `disconnect_cin7_core`, and locally stored `list_connections`; charging for credential setup/removal or local connection inventory would be unfair.
- **8 tokens:** each external single-resource read (`list_*`, `get_*`), reflecting a real Cin7 Core API request.
- **16 tokens:** ordinary single-record create/update/delete/configuration actions, including customer, supplier, product, order, stock, and webhook changes.
- **20 tokens:** consequential lifecycle actions: authorising sales/purchases/invoices, receiving goods, completing stocktakes, shipping sales, creating production runs, and irreversible voids.
- **40 tokens:** cross-resource diagnostics and inventory/business roll-ups: `audit_inventory_health`, `get_dead_stock_report`, `get_low_stock_report`, and `get_store_summary`.
- **60 tokens:** bulk actions (none are currently exposed; the policy remains enforced by the map generator).

Platform application: `developer.update_pricing` must use `per_action` and the explicit Partner revenue split of 95 before Marketplace review.
