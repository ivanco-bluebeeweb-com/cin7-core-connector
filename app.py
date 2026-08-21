"""Extension declaration, secrets, lifecycle hooks.

WHY BYOK (bring-your-own-key), same reasoning as Shopify Connector /
MuleSoft Connector / Power Automate Connector. The user's Cin7 Core
account is THEIR OWN inventory account -- Imperal cannot and should not
broker access to someone else's Cin7 Core organization centrally.

WHY STATIC ACCOUNT ID + APPLICATION KEY, NOT OAUTH.

Cin7 Core's External API v2 (inventory.dearsystems.com/ExternalApi/v2,
confirmed during Discovery 2026-08-21, CONNECTOR_DISCOVERY.md) does not
offer an OAuth authorization flow at all -- authentication is a static
pair of GUIDs (`api-auth-accountid` + `api-auth-applicationkey`) issued
once on the account's own API setup page inside the Cin7 Core UI
(Settings > Integrations & API), sent as HTTP headers on every request.
There is no redirect dance, no refresh token, no expiry -- the same
"paste your own ready-made credentials" shape already used by MuleSoft
Connector (Connected App client id/secret) and Power Automate Connector
(Azure AD App Registration), just with a simpler two-field pair here
because Cin7 Core itself doesn't scope keys per-permission the way those
platforms do.

WHY write_mode="both", SAME REASONING AS EVERY OTHER BYOK CONNECTOR IN
THE PORTFOLIO (Shopify/MuleSoft/n8n/Make.com/Power Automate).

Declaring write_mode="user" would mean only the platform's generic
Secrets screen could write these -- leaving a first-time user with no
in-app screen explaining what an Account ID / Application Key even are
or where to find them. "both" keeps the generic Secrets screen as a
fallback while letting `connect_cin7_core` be the friendly guided path.

WHY SCOPE IS PER-ACCOUNT, NOT APP-LEVEL, SAME AS EVERY OTHER BYOK
CONNECTOR IN THE PORTFOLIO.

Different Imperal users must never see each other's Cin7 Core
connections. Secrets are stored per-account, and a user may connect
MULTIPLE Cin7 Core accounts (e.g. an agency/bookkeeper managing several
clients' inventory) -- `cin7_core_connections` holds a JSON array,
matching the multi-connection shape of every other BYOK connector in
the portfolio.

NAME TRAP GUARDED EXPLICITLY (see CONNECTOR_DISCOVERY.md Critical #1):
Cin7 Core and Cin7 Omni are two DIFFERENT products with different APIs
and different credentials (inventory.dearsystems.com vs api.cin7.com).
This extension is Cin7 Core ONLY -- every user-facing string says so
explicitly to avoid a user pasting Cin7 Omni credentials here by mistake.
"""
from __future__ import annotations

from imperal_sdk import ChatExtension, Extension

ext = Extension(
    "cin7-core-connector",
    version="0.1.0",
    display_name="Cin7 Core",
    description=(
        "Connect your own Cin7 Core (formerly DEAR Systems) inventory "
        "account via its Account ID + Application Key. Manage products "
        "and Bills of Materials, multi-location stock, sales (quotes, "
        "orders, invoices, shipments, payments), purchases (orders, "
        "receipts, invoices, payments), customers and suppliers, "
        "production runs, stock adjustments and stocktakes, and webhooks "
        "-- through the Cin7 Core External API v2. Not compatible with "
        "Cin7 Omni, a different product with a different API."
    ),
    icon="icon.svg",
    capabilities=[
        "cin7_core:read",
        "cin7_core:write",
    ],
    actions_explicit=True,
    system=False,
)

chat = ChatExtension(
    ext,
    tool_name="cin7_core",
    description=(
        "Cin7 Core Connector -- connect your own Cin7 Core (formerly DEAR "
        "Systems) inventory account via Account ID + Application Key, then "
        "manage products/BOMs, multi-location stock, sales, purchases, "
        "customers, suppliers, production runs, stock adjustments/"
        "stocktakes, webhooks, and run value-add inventory reports."
    ),
)

ext.secret(
    "cin7_core_connections",
    (
        "Your connected Cin7 Core accounts -- stored as a JSON array, one "
        "entry per account, each with its Account ID and Application Key. "
        "Managed through connect_cin7_core / disconnect_cin7_core -- you "
        "should not need to edit this directly."
    ),
    required=True,
    write_mode="both",
    max_bytes=65536,
    rotation_hint_days=180,
)(lambda: None)


@ext.health_check
async def health_check(ctx) -> dict:
    """Fast configuration health; no third-party call -- just confirms at
    least one account connection is stored, same shape as Shopify's/
    MuleSoft's health_check."""
    import json as _json
    raw = await ctx.secrets.get("cin7_core_connections")
    try:
        count = len(_json.loads(raw)) if raw else 0
    except Exception:
        count = 0
    return {
        "healthy": True,
        "detail": (
            f"{count} Cin7 Core account(s) connected." if count
            else "Not connected yet -- run connect_cin7_core."
        ),
    }
