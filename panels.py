"""Panel UI -- connections list/connect form + a live products snapshot.

SIDEBAR CONTENT -- NO CARDS ANYWHERE, per ~/UI_INTERFACE_STANDARD.md's
"left sidebar, no decorated cards" rule (same convention as MuleSoft
Connector's / Shopify Connector's panels.py).

Every section (connections, connect form, products) is a plain ui.Stack,
content stacked vertically and left-aligned, sections separated by
ui.Divider() -- no Card border/background/shadow anywhere in this slot.
Disconnect lives only in the "App settings" screen (panels_settings.py).
The one secondary "App settings" button is always the LAST element at the
bottom of the sidebar.

FORM CONTRACT (per Vlad's UI_INTERFACE_STANDARD.md instruction, 2026-08-21):
every input carries its own visible label (a ui.Text caption above it,
never a bare placeholder standing in for a label), and the placeholder text
itself is contextually specific to what belongs in that field -- never a
generic restatement of the label. The form container is forced to the
sidebar's full width (align="stretch" on every wrapping Stack) and its own
content stretches to fill it in turn.

WHY A 2-FIELD FORM, NOT A TOKEN LIKE n8n/Make.com/Slack.

Cin7 Core's External API v2 uses static per-account header auth -- an
Account ID (GUID) plus an Application Key (GUID), both issued together
from the same Settings > Integrations & API > API keys screen (see
app.py's module docstring for the full reasoning). There is no OAuth
token exchange and no separate org/environment selector the way
MuleSoft's Connected Apps flow needs -- just the two paired credentials.
"""
from __future__ import annotations

from imperal_sdk import ui

import cin7_client as cc
from app import ext
import handlers as h


def _settings_button() -> ui.UINode:
    """The one required secondary entry point into the settings screen --
    always the last element at the bottom of the sidebar."""
    return ui.Button(
        "App settings", variant="secondary", size="sm", full_width=True,
        icon="settings", on_click=ui.Call("__panel__cin7_core_settings"),
    )


def _connection_row(c: dict) -> ui.UINode:
    label = c.get("label") or c.get("account_id", "")
    return ui.Stack(direction="v", gap=1, children=[
        ui.Text(label, variant="body"),
        ui.Text(f"Account ID {c.get('account_id', '')}", variant="caption"),
    ])


def _connections_section(connections: list[dict]) -> ui.UINode:
    if not connections:
        return ui.Text("No Cin7 Core accounts connected yet.", variant="caption")
    children: list[ui.UINode] = []
    for i, c in enumerate(connections):
        if i > 0:
            children.append(ui.Divider())
        children.append(_connection_row(c))
    return ui.Stack(direction="v", gap=2, children=children)


def _product_row(p: dict) -> ui.UINode:
    subtitle = p.get("SKU", "") + (f" · {p.get('Category', '')}" if p.get("Category") else "")
    return ui.Stack(direction="v", gap=1, children=[
        ui.Text(p.get("Name", ""), variant="body"),
        ui.Text(subtitle, variant="caption"),
    ])


def _products_section(products: list[dict]) -> ui.UINode:
    if not products:
        return ui.Text("No products found yet.", variant="caption")
    children: list[ui.UINode] = []
    for i, p in enumerate(products):
        if i > 0:
            children.append(ui.Divider())
        children.append(_product_row(p))
    return ui.Stack(direction="v", gap=2, children=children)


def _connect_section() -> ui.UINode:
    """Plain content, no Card wrapper. Stretched full-width per
    UI_INTERFACE_STANDARD.md (2026-08-21). No intro heading/description
    text here -- the setup walkthrough lives ONLY in cin7_core_connect_help's
    modal (button below opens it); repeating it here would duplicate that
    instruction."""
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Button("How do I set this up?", variant="ghost", size="sm",
                  icon="HelpCircle",
                  on_click=ui.Call("__panel__cin7_core_connect_help")),
        ui.Form(
            action="connect_cin7_core",
            submit_label="Verify and connect",
            children=[
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Account ID", variant="caption"),
                    ui.Input(param_name="account_id",
                             placeholder="e.g. a1b2c3d4-e5f6-7890-abcd-ef1234567890"),
                ]),
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Application Key", variant="caption"),
                    ui.Password(param_name="application_key",
                                placeholder="Application Key from the same API setup page"),
                ]),
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Label (optional)", variant="caption"),
                    ui.Input(param_name="label", placeholder="e.g. Production warehouse"),
                ]),
            ],
        ),
    ])


@ext.panel("cin7_core_connect", slot="left", title="Cin7 Core", icon="📦",
           default_width=320, min_width=260, max_width=420)
async def cin7_core_connect_panel(ctx, **kwargs) -> object:
    connections = await h._load_connections(ctx)
    connected = bool(connections)

    header = ui.Header(text="Cin7 Core", level=2,
                        subtitle="Manage your Cin7 Core inventory, sales, and purchases from Imperal")

    if not connected:
        return ui.Stack(direction="v", gap=4, align="stretch", children=[
            header,
            _connect_section(),
            ui.Divider(),
            _settings_button(),
        ])

    products: list[dict] = []
    first = connections[0]
    try:
        body = await cc.cin7_get(ctx, first["account_id"], first["application_key"], "/Product", params={"Limit": 10}, action="load sidebar products")
        products = body.get("Products", []) if isinstance(body, dict) else []
    except cc.ClientFail:
        products = []

    return ui.Stack(direction="v", gap=4, align="stretch", children=[
        header,
        ui.Text("Connected accounts", variant="subtitle"),
        _connections_section(connections),
        ui.Divider(),
        _connect_section(),
        ui.Divider(),
        ui.Text(f"Products -- {first.get('label') or first.get('account_id', '')}", variant="subtitle"),
        _products_section(products),
        ui.Divider(),
        _settings_button(),
    ])


@ext.panel("cin7_core_connect_help", slot="center",
           title="How to connect Cin7 Core", center_overlay=True)
async def cin7_core_connect_help(ctx, **kwargs) -> object:
    content = ui.Stack(direction="v", gap=3, children=[
        ui.Text("1. In Cin7 Core, open Settings > Integrations & API > API keys."),
        ui.Text("2. Click \"Add API application\" (or use an existing one) to generate credentials."),
        ui.Text("3. Copy the Account ID (a GUID) shown at the top of that page."),
        ui.Text("4. Copy the Application Key (a GUID) generated for your API application."),
        ui.Text("5. Paste both into the form -- Cin7 Core checks them immediately on connect."),
        ui.Divider(),
        ui.Alert(
            title="Cin7 Core, not Cin7 Omni",
            message=(
                "This connects Cin7 Core (formerly DEAR Systems) -- "
                "inventory.dearsystems.com. Cin7 Omni is a separate product "
                "with its own different API and is not supported here."
            ),
            type="warning",
        ),
        ui.Divider(),
        ui.Link(
            label="Open Cin7 Core's official API documentation",
            href="https://help.core.cin7.com/",
        ),
    ])
    return ui.Dialog(
        title="How to connect Cin7 Core",
        content=content,
        confirm_label="",
        cancel_label="Close",
    )


@ext.panel("cin7_core_center", slot="center", title="Cin7 Core", icon="📦", center_overlay=True)
async def cin7_core_center_panel(ctx, **kwargs) -> object:
    """Base center panel -- per UI_INTERFACE_STANDARD.md (2026-08-20).
    This app has no list/detail content of its own to show in the center
    by default (everything lives in the sidebar). MUST carry
    center_overlay=True: per docs.imperal.io/en/concepts/panels, a plain
    slot="center" panel is registered but the Panel app never fetches it
    at session-init without that flag. Text is the shared canonical
    wording -- must stay identical across every app in this situation."""
    return ui.Empty(
        message="Nothing to show here -- this app is managed entirely from the sidebar.",
        icon="👈",
    )
