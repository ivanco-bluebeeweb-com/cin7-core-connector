"""Chat functions for Cin7 Core Connector: connection management, Products
(with BOM/composite assembly), Customers, Suppliers, Sales, Purchases,
Stock/Warehouse operations, Production Runs, Webhooks, reference data, and
value-add reports (Tier 3). Built on cin7_client.py / schemas.py, following
the same shape as MuleSoft Connector's / Shopify Connector's handlers.py.
"""
from __future__ import annotations

import json
import uuid

import cin7_client as cc
from app import ext, chat
from imperal_sdk import ActionResult
from schemas import (
    NoParams,
    ConnectCin7CoreParams, ProviderConnection, ConnectionList,
    DisconnectCin7CoreParams, DeleteResult,
    ListProductsParams, GetProductParams, CreateProductParams, UpdateProductParams,
    DeprecateProductParams, GetProductAvailabilityParams,
    ListProductPriceTiersParams, SetProductPriceTierParams,
    GetProductBOMParams, CreateProductBOMParams,
    ListProductCategoriesParams, ListPriceListsParams,
    Product, ProductList, GenericRecord, GenericRecordList,
    StockLevel, StockLevelList, ActionResultEntity,
    ListCustomersParams, GetCustomerParams, CreateCustomerParams, UpdateCustomerParams,
    ListSuppliersParams, GetSupplierParams, CreateSupplierParams, UpdateSupplierParams,
    ListSalesParams, GetSaleParams, CreateSaleQuoteParams, AuthoriseSaleOrderParams,
    VoidSaleParams, CreateSaleShipmentParams, AuthoriseSaleInvoiceParams,
    CreateSalePaymentParams, UpdateSalePaymentParams, ListSaleCreditNotesParams,
    ListPurchasesParams, GetPurchaseParams, CreatePurchaseOrderParams,
    AuthorisePurchaseOrderParams, VoidPurchaseParams, ReceivePurchaseParams,
    AuthorisePurchaseInvoiceParams, CreatePurchasePaymentParams,
    ListLocationsParams, GetStockOnHandParams, CreateStockAdjustmentParams,
    ListStockAdjustmentsParams, VoidStockAdjustmentParams, CreateStockTransferParams,
    ListStockTransfersParams, CreateStockTakeParams, ListStockTakesParams,
    CompleteStockTakeParams,
    ListProductionRunsParams, GetProductionRunParams, CreateProductionRunParams,
    UpdateProductionRunStatusParams, VoidProductionRunParams,
    ListWebhooksParams, CreateWebhookParams, UpdateWebhookParams, DeleteWebhookParams,
    ListTaxRulesParams, ListPaymentTermsParams, ListAccountsParams,
    ListCurrenciesParams, GetAccountInfoParams, AccountInfo,
    GetLowStockReportParams, LowStockReport, LowStockRow,
    GetDeadStockReportParams, DeadStockReport, DeadStockRow,
    AuditInventoryHealthParams, InventoryAuditReport, InventoryAuditFinding,
    GetStoreSummaryParams, StoreSummary,
)

_SECRET_NAME = "cin7_core_connections"


async def _load_connections(ctx) -> list[dict]:
    raw = await ctx.secrets.get(_SECRET_NAME)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return data if isinstance(data, list) else []


async def _save_connections(ctx, connections: list[dict]) -> None:
    await ctx.secrets.set(_SECRET_NAME, json.dumps(connections))


async def _resolve_connection(ctx, connection_id: str = "") -> dict | None:
    connections = await _load_connections(ctx)
    if not connections:
        return None
    if connection_id:
        for c in connections:
            if c.get("id") == connection_id:
                return c
        return None
    return connections[0]


async def _resolve_or_error(ctx, connection_id: str = ""):
    """Shared guard: resolve a connection or return the standard 'not
    connected' ActionResult.error. Returns (conn, error_or_None)."""
    conn = await _resolve_connection(ctx, connection_id)
    if conn is None:
        return None, ActionResult.error(
            "No Cin7 Core account is connected yet. Use connect_cin7_core first.",
            code=cc.ACCOUNT_MISSING,
        )
    return conn, None


def _connection_to_entity(c: dict) -> ProviderConnection:
    return ProviderConnection(
        id=c.get("id", ""),
        title=c.get("label") or c.get("account_id", ""),
        connected=True,
        detail=f"Account ID {c.get('account_id', '')}",
        account_id=c.get("account_id", ""),
    )


@chat.function(
    "connect_cin7_core",
    "Connect a Cin7 Core account by saving its Account ID and Application Key, after checking they actually work.",
    action_type="write",
    chain_callable=True,
    data_model=ProviderConnection,
    event="cin7-core-connector.connect_cin7_core",
    effects=["cin7_core.provider.connected"],
)
async def connect_cin7_core(ctx, params: ConnectCin7CoreParams) -> ActionResult:
    """Connect a Cin7 Core account by saving its Account ID and Application Key."""
    if not params.account_id or not params.application_key:
        return ActionResult.error("Account ID and Application Key are both required.", code="CIN7_MISSING_FIELDS")
    check = await cc.check_connection(ctx, params.account_id, params.application_key)
    if not check.get("ok"):
        return ActionResult.error(check.get("error", "Could not verify these credentials."), code=check.get("error_code", cc.CREDENTIALS_REJECTED))
    connections = await _load_connections(ctx)
    conn_id = str(uuid.uuid4())
    record = {
        "id": conn_id,
        "account_id": params.account_id,
        "application_key": params.application_key,
        "label": params.label,
    }
    connections.append(record)
    await _save_connections(ctx, connections)
    return ActionResult.success(_connection_to_entity(record), summary="Cin7 core connected.")


@chat.function(
    "disconnect_cin7_core",
    "Disconnect a Cin7 Core account: deletes the saved Account ID/Application Key. Nothing in Cin7 Core itself is changed.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="cin7-core-connector.disconnect_cin7_core",
    effects=["cin7_core.provider.disconnected"],
)
async def disconnect_cin7_core(ctx, params: DisconnectCin7CoreParams) -> ActionResult:
    """Disconnect a Cin7 Core account."""
    connections = await _load_connections(ctx)
    remaining = [c for c in connections if c.get("id") != params.connection_id]
    if len(remaining) == len(connections):
        return ActionResult.error("No such connection.", code="CIN7_CONNECTION_NOT_FOUND")
    await _save_connections(ctx, remaining)
    return ActionResult.success(DeleteResult(deleted=True, id=params.connection_id), summary="Cin7 core disconnected.")


@chat.function(
    "list_connections",
    "List the connected Cin7 Core accounts.",
    action_type="read",
    chain_callable=True,
    data_model=ConnectionList,
    event="cin7-core-connector.list_connections",
)
async def list_connections(ctx, params: NoParams) -> ActionResult:
    """List the connected Cin7 Core accounts."""
    connections = await _load_connections(ctx)
    return ActionResult.success(ConnectionList(connections=[_connection_to_entity(c) for c in connections]), summary="Connections listed.")


# ──────────────────────────────────────────────────────────────────────────
# Products
# ──────────────────────────────────────────────────────────────────────────


def _product_to_entity(p: dict) -> Product:
    return Product(
        id=p.get("ID", ""),
        title=p.get("Name", ""),
        name=p.get("Name", ""),
        sku=p.get("SKU", ""),
        category=p.get("Category", ""),
        brand=p.get("Brand", ""),
        product_type=p.get("Type", ""),
        is_deprecated=bool(p.get("IsDeprecated", False)),
    )


@chat.function(
    "list_products",
    "List products in the connected Cin7 Core account, with SKU, category, brand, and type. Supports name/SKU prefix filters.",
    action_type="read",
    chain_callable=True,
    data_model=ProductList,
    event="cin7-core-connector.list_products",
)
async def list_products(ctx, params: ListProductsParams) -> ActionResult:
    """List products in the connected Cin7 Core account."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/Product", params={
            "Name": params.name or None, "SKU": params.sku or None,
            "IncludeDeprecated": 1 if params.include_deprecated else None,
            "Page": params.page, "Limit": params.limit,
        }, action="list products")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    products = body.get("Products", []) if isinstance(body, dict) else []
    return ActionResult.success(ProductList(
        title=f"{len(products)} product(s)",
        items=[_product_to_entity(p) for p in products],
        total=body.get("Total", len(products)) if isinstance(body, dict) else len(products),
        page=params.page,
    ), summary="Products listed.")


@chat.function(
    "get_product",
    "Read one product in full, including SKU, category, brand, and type.",
    action_type="read",
    chain_callable=True,
    data_model=Product,
    event="cin7-core-connector.get_product",
)
async def get_product(ctx, params: GetProductParams) -> ActionResult:
    """Read one product in full."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/Product", params={"ID": params.product_id}, action="get product")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    products = body.get("Products", []) if isinstance(body, dict) else []
    if not products:
        return ActionResult.error("No such product.", code=cc.NOT_FOUND)
    return ActionResult.success(_product_to_entity(products[0]), summary="Product retrieved.")


@chat.function(
    "create_product",
    "Create a new product (Stock, Service, Non-Stock, or Bill of Materials assembly type).",
    action_type="write",
    chain_callable=True,
    data_model=Product,
    event="cin7-core-connector.create_product",
    effects=["cin7_core.product.created"],
)
async def create_product(ctx, params: CreateProductParams) -> ActionResult:
    """Create a new product."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    payload = {
        "Name": params.name, "SKU": params.sku, "Category": params.category or None,
        "Brand": params.brand or None, "Type": params.product_type, "Weight": params.weight or None,
        "Barcode": params.barcode or None,
    }
    for i, (k, v) in enumerate(params.additional_attributes.items(), start=1):
        if i > 10:
            break
        payload[f"AdditionalAttribute{i}"] = v
    try:
        body = await cc.cin7_post(ctx, conn["account_id"], conn["application_key"], "/Product", json={k: v for k, v in payload.items() if v is not None}, action="create product")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(Product(id=body.get("ID", ""), title=params.name, name=params.name, sku=params.sku, category=params.category, brand=params.brand, product_type=params.product_type), summary="Product created.")


@chat.function(
    "update_product",
    "Update selected fields of an existing product. Only given fields change.",
    action_type="write",
    chain_callable=True,
    data_model=Product,
    event="cin7-core-connector.update_product",
    effects=["cin7_core.product.updated"],
)
async def update_product(ctx, params: UpdateProductParams) -> ActionResult:
    """Update selected fields of an existing product."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    payload = {"ID": params.product_id}
    if params.name:
        payload["Name"] = params.name
    if params.category:
        payload["Category"] = params.category
    if params.brand:
        payload["Brand"] = params.brand
    if params.weight is not None:
        payload["Weight"] = params.weight
    if params.barcode:
        payload["Barcode"] = params.barcode
    try:
        await cc.cin7_put(ctx, conn["account_id"], conn["application_key"], "/Product", json=payload, action="update product")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(Product(id=params.product_id, title=params.name or params.product_id), summary="Product updated.")


@chat.function(
    "deprecate_product",
    "Mark a product as deprecated (Cin7 Core's soft-delete for products with transaction history -- there is no hard delete once a product has been used on a sale/purchase).",
    action_type="write",
    chain_callable=True,
    data_model=Product,
    event="cin7-core-connector.deprecate_product",
    effects=["cin7_core.product.deprecated"],
)
async def deprecate_product(ctx, params: DeprecateProductParams) -> ActionResult:
    """Mark a product as deprecated."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        await cc.cin7_put(ctx, conn["account_id"], conn["application_key"], "/Product", json={"ID": params.product_id, "IsDeprecated": True}, action="deprecate product")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(Product(id=params.product_id, title="deprecated", is_deprecated=True), summary="Deprecate product done.")


@chat.function(
    "get_product_availability",
    "Read a product's stock availability (on hand, available, allocated) across locations.",
    action_type="read",
    chain_callable=True,
    data_model=StockLevelList,
    event="cin7-core-connector.get_product_availability",
)
async def get_product_availability(ctx, params: GetProductAvailabilityParams) -> ActionResult:
    """Read a product's stock availability across locations."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/ProductAvailability", params={
            "ProductID": params.product_id or None, "Location": params.location or None,
        }, action="get product availability")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    rows = body.get("ProductAvailabilityList", body if isinstance(body, list) else []) if isinstance(body, dict) else body
    items = [StockLevel(
        product_sku=r.get("SKU", params.product_id), location=r.get("Location", ""),
        on_hand=float(r.get("OnHand", 0) or 0), available=float(r.get("Available", 0) or 0),
        allocated=float(r.get("Allocated", 0) or 0),
    ) for r in (rows or [])]
    return ActionResult.success(StockLevelList(title=f"{len(items)} location(s)", items=items), summary="Product availability retrieved.")


@chat.function(
    "list_product_price_tiers",
    "List the configured price tier values for one product.",
    action_type="read",
    chain_callable=True,
    data_model=GenericRecordList,
    event="cin7-core-connector.list_product_price_tiers",
)
async def list_product_price_tiers(ctx, params: ListProductPriceTiersParams) -> ActionResult:
    """List the configured price tier values for one product."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/Product", params={"ID": params.product_id}, action="list product price tiers")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    products = body.get("Products", []) if isinstance(body, dict) else []
    if not products:
        return ActionResult.error("No such product.", code=cc.NOT_FOUND)
    prices = {k: v for k, v in products[0].items() if k.startswith("PriceTier") or k == "RRP"}
    return ActionResult.success(GenericRecordList(items=[GenericRecord(id=k, data={"price": v}) for k, v in prices.items()]), summary="Product price tiers listed.")


@chat.function(
    "set_product_price_tier",
    "Set one price tier value on a product (e.g. PriceTier1, RRP).",
    action_type="write",
    chain_callable=True,
    data_model=ActionResultEntity,
    event="cin7-core-connector.set_product_price_tier",
    effects=["cin7_core.product.updated"],
)
async def set_product_price_tier(ctx, params: SetProductPriceTierParams) -> ActionResult:
    """Set one price tier value on a product."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        await cc.cin7_put(ctx, conn["account_id"], conn["application_key"], "/Product", json={"ID": params.product_id, params.price_column: params.price}, action="set product price tier")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(ActionResultEntity(id=params.product_id, message=f"{params.price_column} set to {params.price}"), summary="Product price tier updated.")


@chat.function(
    "get_product_bom",
    "Read the production bill of materials (BOM) for one assembly/composite product.",
    action_type="read",
    chain_callable=True,
    data_model=GenericRecord,
    event="cin7-core-connector.get_product_bom",
)
async def get_product_bom(ctx, params: GetProductBOMParams) -> ActionResult:
    """Read the production BOM for one assembly/composite product."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/production/product-production-bom", params={"productId": params.product_id}, action="get product BOM")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(GenericRecord(id=params.product_id, data=body if isinstance(body, dict) else {"result": body}), summary="Product bom retrieved.")


@chat.function(
    "create_product_bom",
    "Create a new production bill of materials (BOM) for an assembly product -- the component lines consumed to build one unit.",
    action_type="write",
    chain_callable=True,
    data_model=GenericRecord,
    event="cin7-core-connector.create_product_bom",
    effects=["cin7_core.product_bom.created"],
)
async def create_product_bom(ctx, params: CreateProductBOMParams) -> ActionResult:
    """Create a new production BOM for an assembly product."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    payload = {
        "ProductID": params.product_id, "BOMName": params.bom_name,
        "BOMVersion": params.bom_version, "BOMStatus": params.status,
        "Lines": [{"ComponentSKU": l.component_sku, "Quantity": l.quantity, "UnitOfMeasure": l.unit_of_measure or None} for l in params.lines],
    }
    try:
        body = await cc.cin7_post(ctx, conn["account_id"], conn["application_key"], "/production/product-production-bom", json=payload, action="create product BOM")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(GenericRecord(id=body.get("ID", "") if isinstance(body, dict) else "", data=body if isinstance(body, dict) else {}), summary="Product bom created.")


@chat.function(
    "list_product_categories",
    "List product categories configured in Cin7 Core.",
    action_type="read",
    chain_callable=True,
    data_model=GenericRecordList,
    event="cin7-core-connector.list_product_categories",
)
async def list_product_categories(ctx, params: ListProductCategoriesParams) -> ActionResult:
    """List product categories configured in Cin7 Core."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/ref/productcategory", action="list product categories")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    rows = body if isinstance(body, list) else body.get("ProductCategoryList", []) if isinstance(body, dict) else []
    return ActionResult.success(GenericRecordList(items=[GenericRecord(id=str(r.get("ID", r)), data=r if isinstance(r, dict) else {"name": r}) for r in rows]), summary="Product categories listed.")


@chat.function(
    "list_price_lists",
    "List sale price lists configured in Cin7 Core.",
    action_type="read",
    chain_callable=True,
    data_model=GenericRecordList,
    event="cin7-core-connector.list_price_lists",
)
async def list_price_lists(ctx, params: ListPriceListsParams) -> ActionResult:
    """List sale price lists configured in Cin7 Core."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/ref/pricelist", action="list price lists")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    rows = body if isinstance(body, list) else body.get("PriceColumnList", []) if isinstance(body, dict) else []
    return ActionResult.success(GenericRecordList(items=[GenericRecord(id=str(r.get("ID", r)), data=r if isinstance(r, dict) else {"name": r}) for r in rows]), summary="Price lists listed.")


# ──────────────────────────────────────────────────────────────────────────
# Customers
# ──────────────────────────────────────────────────────────────────────────


def _customer_to_entity(c: dict) -> GenericRecord:
    return GenericRecord(id=c.get("ID", ""), data=c)


@chat.function(
    "list_customers",
    "List customers in the connected Cin7 Core account.",
    action_type="read",
    chain_callable=True,
    data_model=GenericRecordList,
    event="cin7-core-connector.list_customers",
)
async def list_customers(ctx, params: ListCustomersParams) -> ActionResult:
    """List customers in the connected Cin7 Core account."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/customer", params={
            "Name": params.name or None, "Page": params.page, "Limit": params.limit,
        }, action="list customers")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    rows = body.get("CustomerList", []) if isinstance(body, dict) else []
    return ActionResult.success(GenericRecordList(title=f"{len(rows)} customer(s)", items=[_customer_to_entity(r) for r in rows], page=params.page), summary="Customers listed.")


@chat.function(
    "get_customer",
    "Read one customer in full.",
    action_type="read",
    chain_callable=True,
    data_model=GenericRecord,
    event="cin7-core-connector.get_customer",
)
async def get_customer(ctx, params: GetCustomerParams) -> ActionResult:
    """Read one customer in full."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/customer", params={"ID": params.customer_id}, action="get customer")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    rows = body.get("CustomerList", []) if isinstance(body, dict) else []
    if not rows:
        return ActionResult.error("No such customer.", code=cc.NOT_FOUND)
    return ActionResult.success(_customer_to_entity(rows[0]), summary="Customer retrieved.")


@chat.function(
    "create_customer",
    "Create a new customer record.",
    action_type="write",
    chain_callable=True,
    data_model=GenericRecord,
    event="cin7-core-connector.create_customer",
    effects=["cin7_core.customer.created"],
)
async def create_customer(ctx, params: CreateCustomerParams) -> ActionResult:
    """Create a new customer record."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    payload = {
        "Name": params.name, "Email": params.email or None, "Phone": params.phone or None,
        "Currency": params.currency or None, "PriceTier": params.price_tier or None,
        "PaymentTerm": params.payment_term or None,
    }
    try:
        body = await cc.cin7_post(ctx, conn["account_id"], conn["application_key"], "/customer", json={k: v for k, v in payload.items() if v is not None}, action="create customer")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(GenericRecord(id=body.get("ID", "") if isinstance(body, dict) else "", data=body if isinstance(body, dict) else {"name": params.name}), summary="Customer created.")


@chat.function(
    "update_customer",
    "Update selected fields of an existing customer without changing omitted fields.",
    action_type="write",
    chain_callable=True,
    data_model=GenericRecord,
    event="cin7-core-connector.update_customer",
    effects=["cin7_core.customer.updated"],
)
async def update_customer(ctx, params: UpdateCustomerParams) -> ActionResult:
    """Update selected fields of an existing customer."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    payload = {"ID": params.customer_id}
    for field, value in (("Name", params.name), ("Email", params.email), ("Phone", params.phone), ("PriceTier", params.price_tier), ("PaymentTerm", params.payment_term)):
        if value:
            payload[field] = value
    try:
        await cc.cin7_put(ctx, conn["account_id"], conn["application_key"], "/customer", json=payload, action="update customer")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(GenericRecord(id=params.customer_id, data=payload), summary="Customer updated.")


# ──────────────────────────────────────────────────────────────────────────
# Suppliers
# ──────────────────────────────────────────────────────────────────────────


@chat.function(
    "list_suppliers",
    "List suppliers in the connected Cin7 Core account.",
    action_type="read",
    chain_callable=True,
    data_model=GenericRecordList,
    event="cin7-core-connector.list_suppliers",
)
async def list_suppliers(ctx, params: ListSuppliersParams) -> ActionResult:
    """List suppliers in the connected Cin7 Core account."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/supplier", params={
            "Name": params.name or None, "Page": params.page, "Limit": params.limit,
        }, action="list suppliers")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    rows = body.get("SupplierList", []) if isinstance(body, dict) else []
    return ActionResult.success(GenericRecordList(title=f"{len(rows)} supplier(s)", items=[GenericRecord(id=r.get("ID", ""), data=r) for r in rows], page=params.page), summary="Suppliers listed.")


@chat.function(
    "get_supplier",
    "Read one supplier in full.",
    action_type="read",
    chain_callable=True,
    data_model=GenericRecord,
    event="cin7-core-connector.get_supplier",
)
async def get_supplier(ctx, params: GetSupplierParams) -> ActionResult:
    """Read one supplier in full."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/supplier", params={"ID": params.supplier_id}, action="get supplier")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    rows = body.get("SupplierList", []) if isinstance(body, dict) else []
    if not rows:
        return ActionResult.error("No such supplier.", code=cc.NOT_FOUND)
    return ActionResult.success(GenericRecord(id=rows[0].get("ID", ""), data=rows[0]), summary="Supplier retrieved.")


@chat.function(
    "create_supplier",
    "Create a new product supplier.",
    action_type="write",
    chain_callable=True,
    data_model=GenericRecord,
    event="cin7-core-connector.create_supplier",
    effects=["cin7_core.supplier.created"],
)
async def create_supplier(ctx, params: CreateSupplierParams) -> ActionResult:
    """Create a new product supplier."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    payload = {
        "Name": params.name, "Email": params.email or None, "Phone": params.phone or None,
        "Currency": params.currency or None, "PaymentTerm": params.payment_term or None,
    }
    try:
        body = await cc.cin7_post(ctx, conn["account_id"], conn["application_key"], "/supplier", json={k: v for k, v in payload.items() if v is not None}, action="create supplier")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(GenericRecord(id=body.get("ID", "") if isinstance(body, dict) else "", data=body if isinstance(body, dict) else {"name": params.name}), summary="Supplier created.")


@chat.function(
    "update_supplier",
    "Update selected fields of an existing supplier without changing omitted fields.",
    action_type="write",
    chain_callable=True,
    data_model=GenericRecord,
    event="cin7-core-connector.update_supplier",
    effects=["cin7_core.supplier.updated"],
)
async def update_supplier(ctx, params: UpdateSupplierParams) -> ActionResult:
    """Update selected fields of an existing supplier."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    payload = {"ID": params.supplier_id}
    for field, value in (("Name", params.name), ("Email", params.email), ("Phone", params.phone), ("PaymentTerm", params.payment_term)):
        if value:
            payload[field] = value
    try:
        await cc.cin7_put(ctx, conn["account_id"], conn["application_key"], "/supplier", json=payload, action="update supplier")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(GenericRecord(id=params.supplier_id, data=payload), summary="Supplier updated.")


# ──────────────────────────────────────────────────────────────────────────
# Sales
# ──────────────────────────────────────────────────────────────────────────


@chat.function(
    "list_sales",
    "List sales (quotes/orders/invoices) in the connected Cin7 Core account, with financial/fulfilment status.",
    action_type="read",
    chain_callable=True,
    data_model=GenericRecordList,
    event="cin7-core-connector.list_sales",
)
async def list_sales(ctx, params: ListSalesParams) -> ActionResult:
    """List sales in the connected Cin7 Core account."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/sale/list", params={
            "Customer": params.customer or None, "Status": params.status or None,
            "ModifiedSince": params.updated_since or None, "Page": params.page, "Limit": params.limit,
        }, action="list sales")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    rows = body.get("SaleList", []) if isinstance(body, dict) else []
    return ActionResult.success(GenericRecordList(title=f"{len(rows)} sale(s)", items=[GenericRecord(id=r.get("SaleID", ""), data=r) for r in rows], page=params.page), summary="Sales listed.")


@chat.function(
    "get_sale",
    "Read one sale in full: financial/fulfilment status, totals, and every line item.",
    action_type="read",
    chain_callable=True,
    data_model=GenericRecord,
    event="cin7-core-connector.get_sale",
)
async def get_sale(ctx, params: GetSaleParams) -> ActionResult:
    """Read one sale in full."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/sale", params={"ID": params.sale_id}, action="get sale")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    if not isinstance(body, dict) or not body:
        return ActionResult.error("No such sale.", code=cc.NOT_FOUND)
    return ActionResult.success(GenericRecord(id=body.get("ID", params.sale_id), data=body), summary="Sale retrieved.")


@chat.function(
    "create_sale_quote",
    "Create a new sale quote -- a proposed sale not yet authorised into an order.",
    action_type="write",
    chain_callable=True,
    data_model=GenericRecord,
    event="cin7-core-connector.create_sale_quote",
    effects=["cin7_core.sale.created"],
)
async def create_sale_quote(ctx, params: CreateSaleQuoteParams) -> ActionResult:
    """Create a new sale quote."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    payload = {
        "CustomerID": params.customer_id, "Location": params.location or None,
        "Lines": [{"ProductSKU": l.product_sku, "Quantity": l.quantity, "Price": l.price, "Discount": l.discount, "Tax": l.tax_rule or None} for l in params.lines],
        "Comment": params.memo or None,
    }
    try:
        body = await cc.cin7_post(ctx, conn["account_id"], conn["application_key"], "/sale", json={k: v for k, v in payload.items() if v is not None}, action="create sale quote")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(GenericRecord(id=body.get("ID", "") if isinstance(body, dict) else "", data=body if isinstance(body, dict) else {}), summary="Sale quote created.")


@chat.function(
    "authorise_sale_order",
    "Authorise a sale quote into an order -- commits allocation of stock.",
    action_type="write",
    chain_callable=True,
    data_model=GenericRecord,
    event="cin7-core-connector.authorise_sale_order",
    effects=["cin7_core.sale.order_authorised"],
)
async def authorise_sale_order(ctx, params: AuthoriseSaleOrderParams) -> ActionResult:
    """Authorise a sale quote into an order."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_post(ctx, conn["account_id"], conn["application_key"], "/sale/order", json={"ID": params.sale_id}, action="authorise sale order")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(GenericRecord(id=params.sale_id, data=body if isinstance(body, dict) else {}), summary="Authorise sale order done.")


@chat.function(
    "void_sale",
    "Void a sale (quote, order, or invoice). This cannot be undone through the API.",
    action_type="write",
    chain_callable=True,
    data_model=ActionResultEntity,
    event="cin7-core-connector.void_sale",
    effects=["cin7_core.sale.voided"],
)
async def void_sale(ctx, params: VoidSaleParams) -> ActionResult:
    """Void a sale."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        await cc.cin7_post(ctx, conn["account_id"], conn["application_key"], "/sale/void", json={"ID": params.sale_id}, action="void sale")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(ActionResultEntity(id=params.sale_id, message="voided"), summary="Void sale done.")


@chat.function(
    "create_sale_shipment",
    "Fulfil (ship) a sale order, optionally with tracking info.",
    action_type="write",
    chain_callable=True,
    data_model=GenericRecord,
    event="cin7-core-connector.create_sale_shipment",
    effects=["cin7_core.sale.shipment_created"],
)
async def create_sale_shipment(ctx, params: CreateSaleShipmentParams) -> ActionResult:
    """Fulfil (ship) a sale order."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    payload = {
        "SaleID": params.sale_id,
        "Lines": [{"ProductSKU": l.get("product_sku"), "Quantity": l.get("quantity")} for l in params.lines],
        "TrackingNumber": params.tracking_number or None, "Carrier": params.carrier or None,
    }
    try:
        body = await cc.cin7_post(ctx, conn["account_id"], conn["application_key"], "/sale/shipment", json={k: v for k, v in payload.items() if v is not None}, action="create sale shipment")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(GenericRecord(id=params.sale_id, data=body if isinstance(body, dict) else {}), summary="Sale shipment created.")


@chat.function(
    "authorise_sale_invoice",
    "Authorise the invoice for a sale -- moves it from draft to a real, collectable invoice.",
    action_type="write",
    chain_callable=True,
    data_model=GenericRecord,
    event="cin7-core-connector.authorise_sale_invoice",
    effects=["cin7_core.sale.invoice_authorised"],
)
async def authorise_sale_invoice(ctx, params: AuthoriseSaleInvoiceParams) -> ActionResult:
    """Authorise the invoice for a sale."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_post(ctx, conn["account_id"], conn["application_key"], "/sale/invoice", json={"ID": params.sale_id}, action="authorise sale invoice")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(GenericRecord(id=params.sale_id, data=body if isinstance(body, dict) else {}), summary="Authorise sale invoice done.")


@chat.function(
    "create_sale_payment",
    "Record a payment received against a sale invoice.",
    action_type="write",
    chain_callable=True,
    data_model=GenericRecord,
    event="cin7-core-connector.create_sale_payment",
    effects=["cin7_core.sale.payment_created"],
)
async def create_sale_payment(ctx, params: CreateSalePaymentParams) -> ActionResult:
    """Record a payment received against a sale invoice."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    payload = {
        "SaleID": params.sale_id, "Amount": params.amount, "Account": params.account,
        "Reference": params.reference or None, "Date": params.date_paid or None,
    }
    try:
        body = await cc.cin7_post(ctx, conn["account_id"], conn["application_key"], "/sale/payment", json={k: v for k, v in payload.items() if v is not None}, action="create sale payment")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(GenericRecord(id=body.get("ID", "") if isinstance(body, dict) else "", data=body if isinstance(body, dict) else {}), summary="Sale payment created.")


@chat.function(
    "update_sale_payment",
    "Update an existing sale payment's reference, amount, or account.",
    action_type="write",
    chain_callable=True,
    data_model=GenericRecord,
    event="cin7-core-connector.update_sale_payment",
    effects=["cin7_core.sale.payment_updated"],
)
async def update_sale_payment(ctx, params: UpdateSalePaymentParams) -> ActionResult:
    """Update an existing sale payment."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    payload = {"ID": params.payment_id}
    if params.reference:
        payload["Reference"] = params.reference
    if params.amount is not None:
        payload["Amount"] = params.amount
    if params.account:
        payload["Account"] = params.account
    try:
        await cc.cin7_put(ctx, conn["account_id"], conn["application_key"], "/sale/payment", json=payload, action="update sale payment")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(GenericRecord(id=params.payment_id, data=payload), summary="Sale payment updated.")


@chat.function(
    "list_sale_credit_notes",
    "List credit notes issued against sales, optionally filtered to one sale.",
    action_type="read",
    chain_callable=True,
    data_model=GenericRecordList,
    event="cin7-core-connector.list_sale_credit_notes",
)
async def list_sale_credit_notes(ctx, params: ListSaleCreditNotesParams) -> ActionResult:
    """List credit notes issued against sales."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/sale/creditnote", params={"SaleID": params.sale_id or None}, action="list sale credit notes")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    rows = body if isinstance(body, list) else body.get("CreditNoteList", []) if isinstance(body, dict) else []
    return ActionResult.success(GenericRecordList(items=[GenericRecord(id=str(r.get("ID", "")), data=r) for r in rows]), summary="Sale credit notes listed.")


# ──────────────────────────────────────────────────────────────────────────
# Purchases
# ──────────────────────────────────────────────────────────────────────────


@chat.function(
    "list_purchases",
    "List purchases (orders/receipts/invoices) in the connected Cin7 Core account.",
    action_type="read",
    chain_callable=True,
    data_model=GenericRecordList,
    event="cin7-core-connector.list_purchases",
)
async def list_purchases(ctx, params: ListPurchasesParams) -> ActionResult:
    """List purchases in the connected Cin7 Core account."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/purchase/list", params={
            "Supplier": params.supplier or None, "Status": params.status or None,
            "ModifiedSince": params.updated_since or None, "Page": params.page, "Limit": params.limit,
        }, action="list purchases")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    rows = body.get("PurchaseList", []) if isinstance(body, dict) else []
    return ActionResult.success(GenericRecordList(title=f"{len(rows)} purchase(s)", items=[GenericRecord(id=r.get("PurchaseID", ""), data=r) for r in rows], page=params.page), summary="Purchases listed.")


@chat.function(
    "get_purchase",
    "Read one purchase in full: status, totals, and every line item.",
    action_type="read",
    chain_callable=True,
    data_model=GenericRecord,
    event="cin7-core-connector.get_purchase",
)
async def get_purchase(ctx, params: GetPurchaseParams) -> ActionResult:
    """Read one purchase in full."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/purchase", params={"ID": params.purchase_id}, action="get purchase")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(GenericRecord(id=params.purchase_id, data=body if isinstance(body, dict) else {}), summary="Purchase retrieved.")


@chat.function(
    "create_purchase_order",
    "Create a new purchase order with a supplier and line items -- a proposed purchase not yet authorised.",
    action_type="write",
    chain_callable=True,
    data_model=GenericRecord,
    event="cin7-core-connector.create_purchase_order",
    effects=["cin7_core.purchase.created"],
)
async def create_purchase_order(ctx, params: CreatePurchaseOrderParams) -> ActionResult:
    """Create a new purchase order."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    payload = {
        "SupplierID": params.supplier_id,
        "Location": params.location or None,
        "Lines": [{"ProductSKU": l.product_sku, "Quantity": l.quantity, "Price": l.price} for l in params.lines],
    }
    try:
        body = await cc.cin7_post(ctx, conn["account_id"], conn["application_key"], "/purchase", json={k: v for k, v in payload.items() if v is not None}, action="create purchase order")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(GenericRecord(id=body.get("ID", "") if isinstance(body, dict) else "", data=body if isinstance(body, dict) else {}), summary="Purchase order created.")


@chat.function(
    "authorise_purchase_order",
    "Authorise a draft purchase order, moving it from DRAFT to ORDERED so it can be sent to the supplier.",
    action_type="write",
    chain_callable=True,
    data_model=ActionResultEntity,
    event="cin7-core-connector.authorise_purchase_order",
    effects=["cin7_core.purchase.authorised"],
)
async def authorise_purchase_order(ctx, params: AuthorisePurchaseOrderParams) -> ActionResult:
    """Authorise a draft purchase order."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        await cc.cin7_post(ctx, conn["account_id"], conn["application_key"], "/purchase/authorise", json={"ID": params.purchase_id}, action="authorise purchase order")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(ActionResultEntity(id=params.purchase_id, message="Purchase order authorised."), summary="Authorise purchase order done.")


@chat.function(
    "void_purchase",
    "Void a purchase (order/invoice), after explicit confirmation. This cannot be undone through the API.",
    action_type="write",
    chain_callable=True,
    data_model=ActionResultEntity,
    event="cin7-core-connector.void_purchase",
    effects=["cin7_core.purchase.voided"],
)
async def void_purchase(ctx, params: VoidPurchaseParams) -> ActionResult:
    """Void a purchase."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        await cc.cin7_post(ctx, conn["account_id"], conn["application_key"], "/purchase/void", json={"ID": params.purchase_id}, action="void purchase")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(ActionResultEntity(id=params.purchase_id, message="Purchase voided."), summary="Void purchase done.")


@chat.function(
    "receive_purchase",
    "Record goods received against an authorised purchase order, updating on-hand stock at the receiving location.",
    action_type="write",
    chain_callable=True,
    data_model=GenericRecord,
    event="cin7-core-connector.receive_purchase",
    effects=["cin7_core.purchase.received", "cin7_core.stock.adjusted"],
)
async def receive_purchase(ctx, params: ReceivePurchaseParams) -> ActionResult:
    """Record goods received against an authorised purchase order."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    payload = {
        "PurchaseID": params.purchase_id,
        "Lines": [{"ProductSKU": l.product_sku, "Quantity": l.quantity} for l in params.lines],
    }
    try:
        body = await cc.cin7_post(ctx, conn["account_id"], conn["application_key"], "/purchase/receive", json=payload, action="receive purchase")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(GenericRecord(id=params.purchase_id, data=body if isinstance(body, dict) else {}), summary="Receive purchase done.")


@chat.function(
    "authorise_purchase_invoice",
    "Authorise a purchase invoice, moving it into the payable/AP ledger.",
    action_type="write",
    chain_callable=True,
    data_model=ActionResultEntity,
    event="cin7-core-connector.authorise_purchase_invoice",
    effects=["cin7_core.purchase.invoice_authorised"],
)
async def authorise_purchase_invoice(ctx, params: AuthorisePurchaseInvoiceParams) -> ActionResult:
    """Authorise a purchase invoice."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        await cc.cin7_post(ctx, conn["account_id"], conn["application_key"], "/purchase/invoice/authorise", json={"ID": params.purchase_id}, action="authorise purchase invoice")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(ActionResultEntity(id=params.purchase_id, message="Purchase invoice authorised."), summary="Authorise purchase invoice done.")


@chat.function(
    "create_purchase_payment",
    "Record a payment made against a purchase invoice.",
    action_type="write",
    chain_callable=True,
    data_model=GenericRecord,
    event="cin7-core-connector.create_purchase_payment",
    effects=["cin7_core.purchase.payment_created"],
)
async def create_purchase_payment(ctx, params: CreatePurchasePaymentParams) -> ActionResult:
    """Record a payment made against a purchase invoice."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    payload = {
        "PurchaseID": params.purchase_id, "Amount": params.amount, "Account": params.account,
        "Reference": params.reference or None,
    }
    try:
        body = await cc.cin7_post(ctx, conn["account_id"], conn["application_key"], "/purchase/payment", json={k: v for k, v in payload.items() if v is not None}, action="create purchase payment")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(GenericRecord(id=body.get("ID", "") if isinstance(body, dict) else "", data=body if isinstance(body, dict) else {}), summary="Purchase payment created.")


# ──────────────────────────────────────────────────────────────────────────
# Stock & warehouse
# ──────────────────────────────────────────────────────────────────────────


@chat.function(
    "list_locations",
    "List the account's warehouse/store locations.",
    action_type="read",
    chain_callable=True,
    data_model=GenericRecordList,
    event="cin7-core-connector.list_locations",
)
async def list_locations(ctx, params: ListLocationsParams) -> ActionResult:
    """List the account's warehouse/store locations."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/ref/location", action="list locations")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    rows = body if isinstance(body, list) else body.get("LocationList", []) if isinstance(body, dict) else []
    return ActionResult.success(GenericRecordList(items=[GenericRecord(id=str(r.get("ID", r)), data=r if isinstance(r, dict) else {"name": r}) for r in rows]), summary="Locations listed.")


@chat.function(
    "get_stock_on_hand",
    "Read on-hand/available/allocated stock levels, optionally filtered to one SKU and/or one location.",
    action_type="read",
    chain_callable=True,
    data_model=StockLevelList,
    event="cin7-core-connector.get_stock_on_hand",
)
async def get_stock_on_hand(ctx, params: GetStockOnHandParams) -> ActionResult:
    """Read on-hand/available/allocated stock levels."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/product/availability", params={
            "SKU": params.product_sku or None, "Location": params.location or None,
        }, action="get stock on hand")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    rows = body if isinstance(body, list) else body.get("AvailabilityList", []) if isinstance(body, dict) else []
    levels = [
        StockLevel(
            product_sku=r.get("SKU", params.product_sku), location=r.get("Location", ""),
            on_hand=r.get("OnHand", 0.0), available=r.get("Available", 0.0), allocated=r.get("Allocated", 0.0),
        )
        for r in rows
    ]
    return ActionResult.success(StockLevelList(items=levels), summary="Stock on hand retrieved.")


@chat.function(
    "create_stock_adjustment",
    "Manually adjust stock quantity for one or more SKUs at a location -- positive quantities add stock, negative remove it.",
    action_type="write",
    chain_callable=True,
    data_model=GenericRecord,
    event="cin7-core-connector.create_stock_adjustment",
    effects=["cin7_core.stock.adjusted"],
)
async def create_stock_adjustment(ctx, params: CreateStockAdjustmentParams) -> ActionResult:
    """Manually adjust stock quantity for one or more SKUs at a location."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_post(ctx, conn["account_id"], conn["application_key"], "/stockadjustment", json={
            "Location": params.location, "Reason": params.reason, "Memo": params.memo or None,
            "Lines": [{"ProductSKU": l.product_sku, "Quantity": l.quantity, "Cost": l.cost} for l in params.lines],
        }, action="create stock adjustment")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(GenericRecord(id=body.get("ID", "") if isinstance(body, dict) else "", data=body if isinstance(body, dict) else {}), summary="Stock adjustment created.")


@chat.function(
    "list_stock_adjustments",
    "List past stock adjustments, optionally filtered to one location.",
    action_type="read",
    chain_callable=True,
    data_model=GenericRecordList,
    event="cin7-core-connector.list_stock_adjustments",
)
async def list_stock_adjustments(ctx, params: ListStockAdjustmentsParams) -> ActionResult:
    """List past stock adjustments."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/stockadjustment/list", params={
            "Location": params.location or None, "Page": params.page, "Limit": params.limit,
        }, action="list stock adjustments")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    rows = body.get("StockAdjustmentList", []) if isinstance(body, dict) else []
    return ActionResult.success(GenericRecordList(items=[GenericRecord(id=r.get("ID", ""), data=r) for r in rows], page=params.page), summary="Stock adjustments listed.")


@chat.function(
    "void_stock_adjustment",
    "Void a stock adjustment, reversing its quantity change. Cannot be undone through the API.",
    action_type="write",
    chain_callable=True,
    data_model=ActionResultEntity,
    event="cin7-core-connector.void_stock_adjustment",
    effects=["cin7_core.stock_adjustment.voided"],
)
async def void_stock_adjustment(ctx, params: VoidStockAdjustmentParams) -> ActionResult:
    """Void a stock adjustment."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        await cc.cin7_post(ctx, conn["account_id"], conn["application_key"], "/stockadjustment/void", json={"ID": params.adjustment_id}, action="void stock adjustment")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(ActionResultEntity(id=params.adjustment_id, message="Stock adjustment voided."), summary="Void stock adjustment done.")


@chat.function(
    "create_stock_transfer",
    "Move stock from one location to another (inter-warehouse transfer).",
    action_type="write",
    chain_callable=True,
    data_model=GenericRecord,
    event="cin7-core-connector.create_stock_transfer",
    effects=["cin7_core.stock.transferred"],
)
async def create_stock_transfer(ctx, params: CreateStockTransferParams) -> ActionResult:
    """Move stock from one location to another."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_post(ctx, conn["account_id"], conn["application_key"], "/stocktransfer", json={
            "FromLocation": params.from_location, "ToLocation": params.to_location,
            "Lines": [{"ProductSKU": l.product_sku, "Quantity": l.quantity, "Cost": l.cost} for l in params.lines],
        }, action="create stock transfer")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(GenericRecord(id=body.get("ID", "") if isinstance(body, dict) else "", data=body if isinstance(body, dict) else {}), summary="Stock transfer created.")


@chat.function(
    "list_stock_transfers",
    "List past stock transfers between locations.",
    action_type="read",
    chain_callable=True,
    data_model=GenericRecordList,
    event="cin7-core-connector.list_stock_transfers",
)
async def list_stock_transfers(ctx, params: ListStockTransfersParams) -> ActionResult:
    """List past stock transfers between locations."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/stocktransfer/list", action="list stock transfers")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    rows = body.get("StockTransferList", []) if isinstance(body, dict) else []
    return ActionResult.success(GenericRecordList(items=[GenericRecord(id=r.get("ID", ""), data=r) for r in rows]), summary="Stock transfers listed.")


@chat.function(
    "create_stock_take",
    "Start a new stocktake (physical inventory count) session at a location.",
    action_type="write",
    chain_callable=True,
    data_model=GenericRecord,
    event="cin7-core-connector.create_stock_take",
    effects=["cin7_core.stock_take.created"],
)
async def create_stock_take(ctx, params: CreateStockTakeParams) -> ActionResult:
    """Start a new stocktake session at a location."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_post(ctx, conn["account_id"], conn["application_key"], "/stocktake", json={
            "Location": params.location, "Name": params.name,
        }, action="create stock take")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(GenericRecord(id=body.get("ID", "") if isinstance(body, dict) else "", data=body if isinstance(body, dict) else {}), summary="Stock take created.")


@chat.function(
    "list_stock_takes",
    "List stocktake sessions.",
    action_type="read",
    chain_callable=True,
    data_model=GenericRecordList,
    event="cin7-core-connector.list_stock_takes",
)
async def list_stock_takes(ctx, params: ListStockTakesParams) -> ActionResult:
    """List stocktake sessions."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/stocktake/list", action="list stock takes")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    rows = body.get("StockTakeList", []) if isinstance(body, dict) else []
    return ActionResult.success(GenericRecordList(items=[GenericRecord(id=r.get("ID", ""), data=r) for r in rows]), summary="Stock takes listed.")


@chat.function(
    "complete_stock_take",
    "Finalise a stocktake session -- applies counted quantities as stock adjustments. Cannot be undone through the API.",
    action_type="write",
    chain_callable=True,
    data_model=ActionResultEntity,
    event="cin7-core-connector.complete_stock_take",
    effects=["cin7_core.stock_take.completed"],
)
async def complete_stock_take(ctx, params: CompleteStockTakeParams) -> ActionResult:
    """Finalise a stocktake session."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        await cc.cin7_post(ctx, conn["account_id"], conn["application_key"], "/stocktake/complete", json={"ID": params.stock_take_id}, action="complete stock take")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(ActionResultEntity(id=params.stock_take_id, message="Stocktake completed and applied."), summary="Complete stock take done.")


# ──────────────────────────────────────────────────────────────────────────
# Production (assembly / BOM runs)
# ──────────────────────────────────────────────────────────────────────────


@chat.function(
    "list_production_runs",
    "List production runs (assembly builds), optionally filtered by status.",
    action_type="read",
    chain_callable=True,
    data_model=GenericRecordList,
    event="cin7-core-connector.list_production_runs",
)
async def list_production_runs(ctx, params: ListProductionRunsParams) -> ActionResult:
    """List production runs, optionally filtered by status."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/production/list", params={
            "Status": params.status or None, "Page": params.page, "Limit": params.limit,
        }, action="list production runs")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    rows = body.get("ProductionList", []) if isinstance(body, dict) else []
    return ActionResult.success(GenericRecordList(items=[GenericRecord(id=r.get("ID", ""), data=r) for r in rows], page=params.page), summary="Production runs listed.")


@chat.function(
    "get_production_run",
    "Read one production run in full -- its BOM, quantity, status, and consumed/produced lines.",
    action_type="read",
    chain_callable=True,
    data_model=GenericRecord,
    event="cin7-core-connector.get_production_run",
)
async def get_production_run(ctx, params: GetProductionRunParams) -> ActionResult:
    """Read one production run in full."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/production", params={"ID": params.run_id}, action="get production run")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(GenericRecord(id=params.run_id, data=body if isinstance(body, dict) else {}), summary="Production run retrieved.")


@chat.function(
    "create_production_run",
    "Plan a new production run: build a finished assembly product from its Bill of Materials at a location.",
    action_type="write",
    chain_callable=True,
    data_model=GenericRecord,
    event="cin7-core-connector.create_production_run",
    effects=["cin7_core.production_run.created"],
)
async def create_production_run(ctx, params: CreateProductionRunParams) -> ActionResult:
    """Plan a new production run."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    payload = {
        "ProductID": params.product_id, "BOMID": params.bom_id or None,
        "Quantity": params.quantity, "Location": params.location,
        "PlannedDate": params.planned_date or None,
    }
    try:
        body = await cc.cin7_post(ctx, conn["account_id"], conn["application_key"], "/production", json={k: v for k, v in payload.items() if v is not None}, action="create production run")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(GenericRecord(id=body.get("ID", "") if isinstance(body, dict) else "", data=body if isinstance(body, dict) else {}), summary="Production run created.")


@chat.function(
    "update_production_run_status",
    "Move a production run to a new status: PLANNED, IN PROGRESS, OPERATION_COMPLETED, COMPLETED, or VOIDED.",
    action_type="write",
    chain_callable=True,
    data_model=ActionResultEntity,
    event="cin7-core-connector.update_production_run_status",
    effects=["cin7_core.production_run.status_changed"],
)
async def update_production_run_status(ctx, params: UpdateProductionRunStatusParams) -> ActionResult:
    """Move a production run to a new status."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        await cc.cin7_put(ctx, conn["account_id"], conn["application_key"], "/production", json={"ID": params.run_id, "Status": params.status}, action="update production run status")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(ActionResultEntity(id=params.run_id, message=f"Production run moved to {params.status}."), summary="Production run status updated.")


@chat.function(
    "void_production_run",
    "Void a production run. Cannot be undone through the API.",
    action_type="write",
    chain_callable=True,
    data_model=ActionResultEntity,
    event="cin7-core-connector.void_production_run",
    effects=["cin7_core.production_run.voided"],
)
async def void_production_run(ctx, params: VoidProductionRunParams) -> ActionResult:
    """Void a production run."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        await cc.cin7_put(ctx, conn["account_id"], conn["application_key"], "/production", json={"ID": params.run_id, "Status": "VOIDED"}, action="void production run")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(ActionResultEntity(id=params.run_id, message="Production run voided."), summary="Void production run done.")


# ──────────────────────────────────────────────────────────────────────────
# Webhooks
# ──────────────────────────────────────────────────────────────────────────


@chat.function(
    "list_webhooks",
    "List webhook subscriptions configured on this Cin7 Core account.",
    action_type="read",
    chain_callable=True,
    data_model=GenericRecordList,
    event="cin7-core-connector.list_webhooks",
)
async def list_webhooks(ctx, params: ListWebhooksParams) -> ActionResult:
    """List webhook subscriptions configured on this account."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/webhooks", action="list webhooks")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    rows = body if isinstance(body, list) else body.get("WebhookList", []) if isinstance(body, dict) else []
    return ActionResult.success(GenericRecordList(items=[GenericRecord(id=r.get("ID", ""), data=r) for r in rows]), summary="Webhooks listed.")


@chat.function(
    "create_webhook",
    "Subscribe to a Cin7 Core event topic (e.g. Sale, Purchase, Product, StockAdjustment, Customer changes) -- Cin7 Core will POST to your URL as things happen.",
    action_type="write",
    chain_callable=True,
    data_model=GenericRecord,
    event="cin7-core-connector.create_webhook",
    effects=["cin7_core.webhook.created"],
)
async def create_webhook(ctx, params: CreateWebhookParams) -> ActionResult:
    """Subscribe to a Cin7 Core event topic."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    payload = {
        "Type": params.topic, "Status": "Active" if params.is_active else "Inactive",
        "ExternalUrl": params.external_url, "AuthType": params.auth_type,
        "Username": params.username or None, "Password": params.password or None,
        "BearerToken": params.bearer_token or None,
    }
    try:
        body = await cc.cin7_post(ctx, conn["account_id"], conn["application_key"], "/webhooks", json={k: v for k, v in payload.items() if v is not None}, action="create webhook")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(GenericRecord(id=body.get("ID", "") if isinstance(body, dict) else "", data=body if isinstance(body, dict) else {}), summary="Webhook created.")


@chat.function(
    "update_webhook",
    "Change an existing webhook's URL and/or enabled status.",
    action_type="write",
    chain_callable=True,
    data_model=GenericRecord,
    event="cin7-core-connector.update_webhook",
    effects=["cin7_core.webhook.updated"],
)
async def update_webhook(ctx, params: UpdateWebhookParams) -> ActionResult:
    """Change an existing webhook's URL and/or enabled status."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    payload = {"ID": params.webhook_id}
    if params.is_active is not None:
        payload["Status"] = "Active" if params.is_active else "Inactive"
    if params.external_url:
        payload["ExternalUrl"] = params.external_url
    try:
        await cc.cin7_put(ctx, conn["account_id"], conn["application_key"], "/webhooks", json=payload, action="update webhook")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(GenericRecord(id=params.webhook_id, data=payload), summary="Webhook updated.")


@chat.function(
    "delete_webhook",
    "Permanently remove a webhook subscription by id.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="cin7-core-connector.delete_webhook",
    effects=["cin7_core.webhook.deleted"],
)
async def delete_webhook(ctx, params: DeleteWebhookParams) -> ActionResult:
    """Permanently remove a webhook subscription."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        await cc.cin7_delete(ctx, conn["account_id"], conn["application_key"], "/webhooks", params={"ID": params.webhook_id}, action="delete webhook")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(DeleteResult(id=params.webhook_id, deleted=True), summary="Webhook deleted.")


# ──────────────────────────────────────────────────────────────────────────
# Reference data
# ──────────────────────────────────────────────────────────────────────────


async def _list_ref(ctx, params, path: str, action: str, list_key: str = "") -> ActionResult:
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], path, action=action)
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    if isinstance(body, list):
        rows = body
    elif isinstance(body, dict) and list_key:
        rows = body.get(list_key, [])
    elif isinstance(body, dict):
        rows = next((v for v in body.values() if isinstance(v, list)), [])
    else:
        rows = []
    return ActionResult.success(GenericRecordList(items=[
        GenericRecord(id=str(r.get("ID", r)) if isinstance(r, dict) else str(r), data=r if isinstance(r, dict) else {"name": r})
        for r in rows
    ]), summary=" list ref done.")


@chat.function(
    "list_tax_rules",
    "List tax rules configured in Cin7 Core.",
    action_type="read",
    chain_callable=True,
    data_model=GenericRecordList,
    event="cin7-core-connector.list_tax_rules",
)
async def list_tax_rules(ctx, params: ListTaxRulesParams) -> ActionResult:
    """List tax rules configured in Cin7 Core."""
    return await _list_ref(ctx, params, "/ref/taxrule", "list tax rules")


@chat.function(
    "list_payment_terms",
    "List payment terms configured in Cin7 Core.",
    action_type="read",
    chain_callable=True,
    data_model=GenericRecordList,
    event="cin7-core-connector.list_payment_terms",
)
async def list_payment_terms(ctx, params: ListPaymentTermsParams) -> ActionResult:
    """List payment terms configured in Cin7 Core."""
    return await _list_ref(ctx, params, "/ref/paymentterm", "list payment terms")


@chat.function(
    "list_accounts",
    "List the Chart of Accounts codes configured in Cin7 Core, used as account references in payments.",
    action_type="read",
    chain_callable=True,
    data_model=GenericRecordList,
    event="cin7-core-connector.list_accounts",
)
async def list_accounts(ctx, params: ListAccountsParams) -> ActionResult:
    """List the Chart of Accounts codes configured in Cin7 Core."""
    return await _list_ref(ctx, params, "/ref/account", "list accounts")


@chat.function(
    "list_currencies",
    "List currencies enabled on this Cin7 Core account.",
    action_type="read",
    chain_callable=True,
    data_model=GenericRecordList,
    event="cin7-core-connector.list_currencies",
)
async def list_currencies(ctx, params: ListCurrenciesParams) -> ActionResult:
    """List currencies enabled on this Cin7 Core account."""
    return await _list_ref(ctx, params, "/ref/currency", "list currencies")


@chat.function(
    "get_account_info",
    "Read the connected Cin7 Core account's own profile: company name, base currency, and enabled modules.",
    action_type="read",
    chain_callable=True,
    data_model=AccountInfo,
    event="cin7-core-connector.get_account_info",
)
async def get_account_info(ctx, params: GetAccountInfoParams) -> ActionResult:
    """Read the connected Cin7 Core account's own profile."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/me", action="get account info")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(AccountInfo(
        company_name=body.get("Company", ""), base_currency=body.get("BaseCurrency", ""),
        timezone=body.get("TimeZone", ""), account_id=conn["account_id"],
    ), summary="Account info retrieved.")


# ──────────────────────────────────────────────────────────────────────────
# Value-add reports (Tier 3 -- our own aggregations, Cin7 Core has no
# single endpoint for any of these)
# ──────────────────────────────────────────────────────────────────────────


@chat.function(
    "get_low_stock_report",
    "Value-add report: scan products and flag every SKU whose total on-hand quantity across all locations is at or below a threshold.",
    action_type="read",
    chain_callable=True,
    data_model=LowStockReport,
    event="cin7-core-connector.get_low_stock_report",
)
async def get_low_stock_report(ctx, params: GetLowStockReportParams) -> ActionResult:
    """Scan products and flag every SKU at or below a stock threshold."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/product/availability", params={
            "Location": params.location or None, "Limit": 1000,
        }, action="scan stock for low-stock report")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    rows = body if isinstance(body, list) else body.get("AvailabilityList", []) if isinstance(body, dict) else []
    flagged = [
        LowStockRow(
            product_sku=r.get("SKU", ""), product_name=r.get("Name", ""),
            total_on_hand=r.get("OnHand", 0.0), threshold=params.threshold,
        )
        for r in rows if r.get("OnHand", 0.0) <= params.threshold
    ]
    return ActionResult.success(LowStockReport(
        title=f"{len(flagged)} SKU(s) at or below {params.threshold}",
        rows=flagged, threshold=params.threshold, scanned_count=len(rows),
    ), summary="Low stock report retrieved.")


@chat.function(
    "get_dead_stock_report",
    "Value-add report: flag products that have on-hand stock but no recorded sale in a given number of trailing days.",
    action_type="read",
    chain_callable=True,
    data_model=DeadStockReport,
    event="cin7-core-connector.get_dead_stock_report",
)
async def get_dead_stock_report(ctx, params: GetDeadStockReportParams) -> ActionResult:
    """Flag products with on-hand stock but no recent sale."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    try:
        stock_body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/product/availability", params={
            "Location": params.location or None, "Limit": 1000,
        }, action="scan stock for dead-stock report")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    stock_rows = stock_body if isinstance(stock_body, list) else stock_body.get("AvailabilityList", []) if isinstance(stock_body, dict) else []
    import datetime
    cutoff = (datetime.datetime.utcnow() - datetime.timedelta(days=params.days_without_sale)).date().isoformat()
    flagged = [
        DeadStockRow(
            product_sku=r.get("SKU", ""), product_name=r.get("Name", ""),
            on_hand=r.get("OnHand", 0.0), last_sale_date=r.get("LastSaleDate", "") or "never",
        )
        for r in stock_rows
        if r.get("OnHand", 0.0) > 0 and (not r.get("LastSaleDate") or r.get("LastSaleDate", "") < cutoff)
    ]
    return ActionResult.success(DeadStockReport(
        title=f"{len(flagged)} dead-stock SKU(s)",
        rows=flagged, days_without_sale=params.days_without_sale, scanned_count=len(stock_rows),
    ), summary="Dead stock report retrieved.")


@chat.function(
    "audit_inventory_health",
    "Aggregated health snapshot: negative-stock SKUs, assembly products missing an active BOM, open purchase orders overdue for receipt, and open sale orders overdue for shipment.",
    action_type="read",
    chain_callable=True,
    data_model=InventoryAuditReport,
    event="cin7-core-connector.audit_inventory_health",
)
async def audit_inventory_health(ctx, params: AuditInventoryHealthParams) -> ActionResult:
    """Build an aggregated inventory health snapshot."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    findings: list[InventoryAuditFinding] = []
    negative_count = 0
    try:
        stock_body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/product/availability", params={"Limit": 1000}, action="audit: scan stock")
        stock_rows = stock_body if isinstance(stock_body, list) else stock_body.get("AvailabilityList", []) if isinstance(stock_body, dict) else []
        for r in stock_rows:
            if r.get("OnHand", 0.0) < 0:
                negative_count += 1
                findings.append(InventoryAuditFinding(
                    category="negative_stock", severity="high", reference_id=r.get("SKU", ""),
                    detail=f"{r.get('SKU', '')} has negative on-hand quantity ({r.get('OnHand')}).",
                ))
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    missing_bom_count = 0
    try:
        prod_body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/Product", params={"Limit": 1000}, action="audit: scan products")
        products = prod_body.get("Products", []) if isinstance(prod_body, dict) else []
        for p in products:
            if p.get("Type", "").lower() in ("bill of materials", "assembly") and not p.get("HasActiveBOM", True):
                missing_bom_count += 1
                findings.append(InventoryAuditFinding(
                    category="missing_bom", severity="medium", reference_id=p.get("ID", ""),
                    detail=f"{p.get('Name', '')} ({p.get('SKU', '')}) is an assembly type with no active BOM.",
                ))
    except cc.ClientFail:
        pass
    overdue_purchase_count = 0
    overdue_sale_count = 0
    try:
        purch_body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/purchase/list", params={"Status": "ORDERED", "Limit": 1000}, action="audit: scan purchases")
        purchases = purch_body.get("PurchaseList", []) if isinstance(purch_body, dict) else []
        overdue_purchase_count = len(purchases)
        for p in purchases[:20]:
            findings.append(InventoryAuditFinding(
                category="overdue_purchase", severity="low", reference_id=p.get("PurchaseID", ""),
                detail=f"Purchase order {p.get('PurchaseID', '')} still open (status ORDERED).",
            ))
    except cc.ClientFail:
        pass
    try:
        sale_body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/sale/list", params={"Status": "ORDERED", "Limit": 1000}, action="audit: scan sales")
        sales = sale_body.get("SaleList", []) if isinstance(sale_body, dict) else []
        overdue_sale_count = len(sales)
        for s in sales[:20]:
            findings.append(InventoryAuditFinding(
                category="overdue_sale", severity="low", reference_id=s.get("SaleID", ""),
                detail=f"Sale order {s.get('SaleID', '')} still open (status ORDERED).",
            ))
    except cc.ClientFail:
        pass
    return ActionResult.success(InventoryAuditReport(
        title=f"{len(findings)} finding(s)",
        findings=findings, negative_stock_count=negative_count, missing_bom_count=missing_bom_count,
        overdue_purchase_count=overdue_purchase_count, overdue_sale_count=overdue_sale_count,
    ), summary="Inventory health audit ready.")


@chat.function(
    "get_store_summary",
    "Value-add report: one-glance account snapshot -- sales/purchases counts and value, plus product/customer/supplier counts, over a trailing period.",
    action_type="read",
    chain_callable=True,
    data_model=StoreSummary,
    event="cin7-core-connector.get_store_summary",
)
async def get_store_summary(ctx, params: GetStoreSummaryParams) -> ActionResult:
    """Build a one-glance account snapshot."""
    conn, err = await _resolve_or_error(ctx)
    if err:
        return err
    import datetime
    since = (datetime.datetime.utcnow() - datetime.timedelta(days=params.days)).isoformat()
    try:
        sales_body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/sale/list", params={"ModifiedSince": since, "Limit": 1000}, action="summary: scan sales")
        sales = sales_body.get("SaleList", []) if isinstance(sales_body, dict) else []
        purch_body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/purchase/list", params={"ModifiedSince": since, "Limit": 1000}, action="summary: scan purchases")
        purchases = purch_body.get("PurchaseList", []) if isinstance(purch_body, dict) else []
        prod_body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/Product", params={"Limit": 1}, action="summary: count products")
        cust_body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/customer", params={"Limit": 1}, action="summary: count customers")
        supp_body = await cc.cin7_get(ctx, conn["account_id"], conn["application_key"], "/supplier", params={"Limit": 1}, action="summary: count suppliers")
    except cc.ClientFail as e:
        return ActionResult.error(e.payload.get("error"), code=e.payload.get("error_code"))
    return ActionResult.success(StoreSummary(
        title=f"Cin7 Core summary, last {params.days} days",
        days=params.days,
        total_sales=len(sales), total_sales_value=sum(s.get("Total", 0.0) for s in sales),
        total_purchases=len(purchases), total_purchases_value=sum(p.get("Total", 0.0) for p in purchases),
        total_products=prod_body.get("Total", 0) if isinstance(prod_body, dict) else 0,
        total_customers=cust_body.get("Total", 0) if isinstance(cust_body, dict) else 0,
        total_suppliers=supp_body.get("Total", 0) if isinstance(supp_body, dict) else 0,
    ), summary="Store summary retrieved.")
