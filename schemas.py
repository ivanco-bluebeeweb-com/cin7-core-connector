"""Pydantic params models + SDL entity contracts for Cin7 Core Connector.

All params models are module-scope (V17 federal invariant, same rule as
MuleSoft Connector / Shopify Connector / Power Automate Connector's
schemas.py).
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from imperal_sdk import sdl


class NoParams(BaseModel):
    """Explicit empty params model -- V17 disallows untyped handlers."""
    pass


# ──────────────────────────────────────────────────────────────────────────
# Connection
# ──────────────────────────────────────────────────────────────────────────


class ConnectCin7CoreParams(BaseModel):
    account_id: str = Field(
        "",
        description="Cin7 Core Account ID (a GUID) from Settings > Integrations & API > API keys.",
    )
    application_key: str = Field(
        "",
        description="Cin7 Core Application Key (a GUID) from the same API setup page.",
    )
    label: str = Field("", description="Optional friendly name for this account connection.")


class ProviderConnection(sdl.Entity):
    id: str = ""
    title: str = ""
    connected: bool = False
    detail: str = ""
    account_id: str = ""


class ConnectionList(sdl.Entity):
    connections: list[ProviderConnection] = Field(default_factory=list)


class DisconnectCin7CoreParams(BaseModel):
    connection_id: str = Field("", description="Connection id to disconnect, from list_connections.")


class ListConnectionsParams(NoParams):
    pass


# ──────────────────────────────────────────────────────────────────────────
# Products
# ──────────────────────────────────────────────────────────────────────────


class ListProductsParams(BaseModel):
    name: str = Field("", description="Filter: product name starts with this string.")
    sku: str = Field("", description="Filter: SKU starts with this string.")
    include_deprecated: bool = Field(False, description="Include deprecated products in results.")
    page: int = Field(1, ge=1, description="Page number for paginated results.")
    limit: int = Field(100, ge=1, le=1000, description="Items per page (max 1000).")


class GetProductParams(BaseModel):
    product_id: str = Field(..., description="Cin7 Core product ID (GUID).")


class CreateProductParams(BaseModel):
    name: str = Field(..., description="Product name.")
    sku: str = Field(..., description="Stock Keeping Unit -- must be unique.")
    category: str = Field("", description="Product category name.")
    brand: str = Field("", description="Product brand name.")
    product_type: str = Field(
        "Stock",
        description="Product type: Stock, Service, Non-Stock, or Bill of Materials (composite/assembly item).",
    )
    weight: float = Field(0.0, description="Product weight (kg).")
    barcode: str = Field("", description="Product barcode/UPC/EAN.")
    additional_attributes: dict[str, str] = Field(
        default_factory=dict, description="Optional custom field name/value pairs already defined in Cin7 Core."
    )


class UpdateProductParams(BaseModel):
    product_id: str = Field(..., description="Cin7 Core product ID (GUID) to update.")
    name: str = Field("", description="New product name. Omit to keep unchanged.")
    category: str = Field("", description="New product category. Omit to keep unchanged.")
    brand: str = Field("", description="New product brand. Omit to keep unchanged.")
    weight: float | None = Field(None, description="New weight (kg). Omit to keep unchanged.")
    barcode: str = Field("", description="New barcode. Omit to keep unchanged.")


class DeprecateProductParams(BaseModel):
    product_id: str = Field(..., description="Cin7 Core product ID (GUID) to mark deprecated (soft-delete; Cin7 Core has no hard delete for products with transaction history).")


class GetProductAvailabilityParams(BaseModel):
    product_id: str = Field("", description="Filter to one product ID. Omit to read availability for all products.")
    location: str = Field("", description="Filter to one named warehouse/location. Omit for all locations.")


class ListProductPriceTiersParams(BaseModel):
    product_id: str = Field(..., description="Cin7 Core product ID (GUID).")


class SetProductPriceTierParams(BaseModel):
    product_id: str = Field(..., description="Cin7 Core product ID (GUID).")
    price_column: str = Field(..., description="Price tier column name (e.g. 'PriceTier1', 'RRP'), as configured in Cin7 Core Sale Price Lists.")
    price: float = Field(..., description="Price for this tier.")


class GetProductBOMParams(BaseModel):
    product_id: str = Field(..., description="Cin7 Core product ID (GUID) of the assembly/composite product.")


class BOMLine(BaseModel):
    component_sku: str = Field(..., description="SKU of the component product consumed by this BOM.")
    quantity: float = Field(..., description="Quantity of the component required per one unit of the assembly.")
    unit_of_measure: str = Field("", description="Unit of measure for the component quantity.")


class CreateProductBOMParams(BaseModel):
    product_id: str = Field(..., description="Cin7 Core product ID (GUID) of the assembly/composite product.")
    bom_name: str = Field(..., description="Name for this bill of materials.")
    bom_version: str = Field("1.0", description="Version label for this BOM.")
    status: str = Field("DRAFT", description="BOM status: DRAFT, ACTIVE, or OBSOLETE.")
    lines: list[BOMLine] = Field(..., description="Component lines making up this assembly.")


class ListProductCategoriesParams(NoParams):
    pass


class ListPriceListsParams(NoParams):
    pass


# ──────────────────────────────────────────────────────────────────────────
# Customers & Suppliers
# ──────────────────────────────────────────────────────────────────────────


class ListCustomersParams(BaseModel):
    name: str = Field("", description="Filter: customer name starts with this string.")
    page: int = Field(1, ge=1, description="Page number for paginated results.")
    limit: int = Field(100, ge=1, le=1000, description="Items per page (max 1000).")


class GetCustomerParams(BaseModel):
    customer_id: str = Field(..., description="Cin7 Core customer ID (GUID).")


class CreateCustomerParams(BaseModel):
    name: str = Field(..., description="Customer company or individual name.")
    email: str = Field("", description="Primary contact email.")
    phone: str = Field("", description="Primary contact phone number.")
    currency: str = Field("", description="Customer's transaction currency code (e.g. USD). Omit to use account default.")
    price_tier: str = Field("", description="Default price tier/column applied to this customer's sales.")
    payment_term: str = Field("", description="Default payment term name (e.g. 'Net 30').")


class UpdateCustomerParams(BaseModel):
    customer_id: str = Field(..., description="Cin7 Core customer ID (GUID) to update.")
    name: str = Field("", description="New name. Omit to keep unchanged.")
    email: str = Field("", description="New email. Omit to keep unchanged.")
    phone: str = Field("", description="New phone. Omit to keep unchanged.")
    price_tier: str = Field("", description="New default price tier. Omit to keep unchanged.")
    payment_term: str = Field("", description="New default payment term. Omit to keep unchanged.")


class ListSuppliersParams(BaseModel):
    name: str = Field("", description="Filter: supplier name starts with this string.")
    page: int = Field(1, ge=1, description="Page number for paginated results.")
    limit: int = Field(100, ge=1, le=1000, description="Items per page (max 1000).")


class GetSupplierParams(BaseModel):
    supplier_id: str = Field(..., description="Cin7 Core supplier ID (GUID).")


class CreateSupplierParams(BaseModel):
    name: str = Field(..., description="Supplier company name.")
    email: str = Field("", description="Primary contact email.")
    phone: str = Field("", description="Primary contact phone number.")
    currency: str = Field("", description="Supplier's transaction currency code. Omit to use account default.")
    payment_term: str = Field("", description="Default payment term name for purchases from this supplier.")


class UpdateSupplierParams(BaseModel):
    supplier_id: str = Field(..., description="Cin7 Core supplier ID (GUID) to update.")
    name: str = Field("", description="New name. Omit to keep unchanged.")
    email: str = Field("", description="New email. Omit to keep unchanged.")
    phone: str = Field("", description="New phone. Omit to keep unchanged.")
    payment_term: str = Field("", description="New default payment term. Omit to keep unchanged.")


# ──────────────────────────────────────────────────────────────────────────
# Sales
# ──────────────────────────────────────────────────────────────────────────


class SaleLine(BaseModel):
    product_sku: str = Field(..., description="SKU of the product/service line.")
    quantity: float = Field(..., ge=0, description="Quantity sold. Minimum 1 unless a free/kit line.")
    price: float = Field(..., ge=0, description="Unit price in customer currency.")
    discount: float = Field(0.0, ge=0, le=100, description="Line discount percent, 0-100 (100 = free item).")
    tax_rule: str = Field("", description="Tax rule name to apply to this line. Omit to use the customer default.")


class ListSalesParams(BaseModel):
    customer: str = Field("", description="Filter: customer name starts with this string.")
    status: str = Field("", description="Filter: sale status (e.g. DRAFT, ORDERED, INVOICED).")
    updated_since: str = Field("", description="Filter: only sales updated after this ISO-8601 datetime.")
    page: int = Field(1, ge=1, description="Page number for paginated results.")
    limit: int = Field(100, ge=1, le=1000, description="Items per page (max 1000).")


class GetSaleParams(BaseModel):
    sale_id: str = Field(..., description="Cin7 Core sale ID (GUID).")


class CreateSaleQuoteParams(BaseModel):
    customer_id: str = Field(..., description="Cin7 Core customer ID (GUID) this quote is for.")
    location: str = Field("", description="Fulfilment warehouse/location name. Omit to use the account default.")
    lines: list[SaleLine] = Field(..., description="Line items on this quote.")
    memo: str = Field("", description="Internal memo/notes on the quote.")
    currency_rate: float | None = Field(None, description="Currency conversion rate. Omit to use the live rate.")


class AuthoriseSaleOrderParams(BaseModel):
    sale_id: str = Field(..., description="Cin7 Core sale ID (GUID) of the quote to authorise into an order.")


class VoidSaleParams(BaseModel):
    sale_id: str = Field(..., description="Cin7 Core sale ID (GUID) to void. This cannot be undone through the API.")


class CreateSaleShipmentParams(BaseModel):
    sale_id: str = Field(..., description="Cin7 Core sale ID (GUID) being shipped.")
    lines: list[dict] = Field(..., description="Shipment lines: [{'product_sku': str, 'quantity': float}, ...].")
    tracking_number: str = Field("", description="Optional carrier tracking number.")
    carrier: str = Field("", description="Optional carrier name.")


class AuthoriseSaleInvoiceParams(BaseModel):
    sale_id: str = Field(..., description="Cin7 Core sale ID (GUID) to authorise the invoice for.")


class CreateSalePaymentParams(BaseModel):
    sale_id: str = Field(..., description="Cin7 Core sale ID (GUID) the payment applies to.")
    amount: float = Field(..., gt=0, description="Payment amount in customer currency.")
    account: str = Field(..., description="Bank/payment account code from Chart of Accounts.")
    reference: str = Field("", description="Payment reference number.")
    date_paid: str = Field("", description="ISO-8601 date the payment was made. Omit to use now.")


class UpdateSalePaymentParams(BaseModel):
    payment_id: str = Field(..., description="Cin7 Core sale payment ID (GUID) to update.")
    reference: str = Field("", description="New payment reference. Omit to keep unchanged.")
    amount: float | None = Field(None, description="New payment amount. Omit to keep unchanged.")
    account: str = Field("", description="New account code. Omit to keep unchanged.")


class ListSaleCreditNotesParams(BaseModel):
    sale_id: str = Field("", description="Filter to credit notes for one sale. Omit for all.")


# ──────────────────────────────────────────────────────────────────────────
# Purchases
# ──────────────────────────────────────────────────────────────────────────


class PurchaseLine(BaseModel):
    product_sku: str = Field(..., description="SKU of the product/service line.")
    quantity: float = Field(..., ge=0, description="Quantity ordered.")
    price: float = Field(..., ge=0, description="Unit cost in supplier currency.")


class ListPurchasesParams(BaseModel):
    supplier: str = Field("", description="Filter: supplier name starts with this string.")
    status: str = Field("", description="Filter: purchase status (e.g. DRAFT, ORDERED, RECEIVED).")
    updated_since: str = Field("", description="Filter: only purchases updated after this ISO-8601 datetime.")
    page: int = Field(1, ge=1, description="Page number for paginated results.")
    limit: int = Field(100, ge=1, le=1000, description="Items per page (max 1000).")


class GetPurchaseParams(BaseModel):
    purchase_id: str = Field(..., description="Cin7 Core purchase ID (GUID).")


class CreatePurchaseOrderParams(BaseModel):
    supplier_id: str = Field(..., description="Cin7 Core supplier ID (GUID) this order is placed with.")
    location: str = Field("", description="Receiving warehouse/location name. Omit to use the account default.")
    lines: list[PurchaseLine] = Field(..., description="Line items on this purchase order.")
    memo: str = Field("", description="Internal memo/notes on the order.")


class AuthorisePurchaseOrderParams(BaseModel):
    purchase_id: str = Field(..., description="Cin7 Core purchase ID (GUID) of the draft to authorise.")


class VoidPurchaseParams(BaseModel):
    purchase_id: str = Field(..., description="Cin7 Core purchase ID (GUID) to void. This cannot be undone through the API.")


class ReceivePurchaseParams(BaseModel):
    purchase_id: str = Field(..., description="Cin7 Core purchase ID (GUID) being received into stock.")
    lines: list[dict] = Field(..., description="Received lines: [{'product_sku': str, 'quantity': float}, ...].")


class AuthorisePurchaseInvoiceParams(BaseModel):
    purchase_id: str = Field(..., description="Cin7 Core purchase ID (GUID) to authorise the supplier invoice for.")


class CreatePurchasePaymentParams(BaseModel):
    purchase_id: str = Field(..., description="Cin7 Core purchase ID (GUID) the payment applies to.")
    amount: float = Field(..., gt=0, description="Payment amount in supplier currency.")
    account: str = Field(..., description="Bank/payment account code from Chart of Accounts.")
    reference: str = Field("", description="Payment reference number.")


# ──────────────────────────────────────────────────────────────────────────
# Stock & warehouse
# ──────────────────────────────────────────────────────────────────────────


class ListLocationsParams(NoParams):
    pass


class GetStockOnHandParams(BaseModel):
    product_sku: str = Field("", description="Filter to one product SKU. Omit to read all products.")
    location: str = Field("", description="Filter to one named location. Omit for all locations.")


class StockAdjustmentLine(BaseModel):
    product_sku: str = Field(..., description="SKU of the product being adjusted.")
    quantity: float = Field(..., description="Adjustment quantity: positive to add stock, negative to remove.")
    cost: float | None = Field(None, description="Unit cost for this adjustment. Omit to use the product's average cost.")


class CreateStockAdjustmentParams(BaseModel):
    location: str = Field(..., description="Warehouse/location name where the adjustment applies.")
    reason: str = Field(..., description="Adjustment reason (e.g. 'Stocktake correction', 'Damaged goods').")
    lines: list[StockAdjustmentLine] = Field(..., description="Product/quantity lines for this adjustment.")
    memo: str = Field("", description="Internal memo/notes for this adjustment.")


class ListStockAdjustmentsParams(BaseModel):
    location: str = Field("", description="Filter to one named location. Omit for all locations.")
    page: int = Field(1, ge=1, description="Page number for paginated results.")
    limit: int = Field(100, ge=1, le=1000, description="Items per page (max 1000).")


class VoidStockAdjustmentParams(BaseModel):
    adjustment_id: str = Field(..., description="Cin7 Core stock adjustment ID (GUID) to void.")


class CreateStockTransferParams(BaseModel):
    from_location: str = Field(..., description="Source warehouse/location name.")
    to_location: str = Field(..., description="Destination warehouse/location name.")
    lines: list[dict] = Field(..., description="Transfer lines: [{'product_sku': str, 'quantity': float}, ...].")
    memo: str = Field("", description="Internal memo/notes for this transfer.")


class ListStockTransfersParams(BaseModel):
    page: int = Field(1, ge=1, description="Page number for paginated results.")
    limit: int = Field(100, ge=1, le=1000, description="Items per page (max 1000).")


class CreateStockTakeParams(BaseModel):
    location: str = Field(..., description="Warehouse/location name this stocktake covers.")
    name: str = Field(..., description="Name/label for this stocktake session.")


class ListStockTakesParams(BaseModel):
    location: str = Field("", description="Filter to one named location. Omit for all locations.")


class CompleteStockTakeParams(BaseModel):
    stock_take_id: str = Field(..., description="Cin7 Core stocktake ID (GUID) to finalise -- applies counted quantities as stock adjustments.")


# ──────────────────────────────────────────────────────────────────────────
# Production (assembly / BOM runs)
# ──────────────────────────────────────────────────────────────────────────


class ListProductionRunsParams(BaseModel):
    status: str = Field("", description="Filter: run status (PLANNED, IN PROGRESS, OPERATION_COMPLETED, COMPLETED, VOIDED).")
    page: int = Field(1, ge=1, description="Page number for paginated results.")
    limit: int = Field(100, ge=1, le=1000, description="Items per page (max 1000).")


class GetProductionRunParams(BaseModel):
    run_id: str = Field(..., description="Cin7 Core production run ID (GUID).")


class CreateProductionRunParams(BaseModel):
    product_id: str = Field(..., description="Cin7 Core product ID (GUID) of the assembly to produce.")
    bom_id: str = Field("", description="Specific BOM ID (GUID) to use. Omit to use the product's active BOM.")
    quantity: float = Field(..., gt=0, description="Quantity of the finished assembly to produce.")
    location: str = Field(..., description="Warehouse/location where production takes place.")
    planned_date: str = Field("", description="ISO-8601 planned start date. Omit to use now.")


class UpdateProductionRunStatusParams(BaseModel):
    run_id: str = Field(..., description="Cin7 Core production run ID (GUID) to update.")
    status: str = Field(..., description="New status: PLANNED, IN PROGRESS, OPERATION_COMPLETED, COMPLETED, or VOIDED.")


class VoidProductionRunParams(BaseModel):
    run_id: str = Field(..., description="Cin7 Core production run ID (GUID) to void. This cannot be undone through the API.")


# ──────────────────────────────────────────────────────────────────────────
# Webhooks
# ──────────────────────────────────────────────────────────────────────────


class ListWebhooksParams(NoParams):
    pass


class CreateWebhookParams(BaseModel):
    webhook_type: str = Field(
        ...,
        description=(
            "Event type to subscribe to, e.g. 'Sale/Created', 'Sale/OrderAuthorised', "
            "'Sale/InvoiceAuthorised', 'Sale/ShipmentAuthorised', 'Sale/Voided', "
            "'Purchase/Created', 'Purchase/OrderAuthorised', 'Purchase/Voided', "
            "'StockAdjustment/Created', 'Customer/Created', 'Customer/Updated', "
            "'Supplier/Created', 'Product/Created', 'Product/Updated'. "
            "Max 5 webhooks per type are allowed by Cin7 Core."
        ),
    )
    external_url: str = Field(..., description="HTTPS callback URL Cin7 Core will POST the event payload to.")
    auth_type: str = Field("noauth", description="Callback auth type: noauth, basicauth, or bearerauth.")
    username: str = Field("", description="Basic auth username. Required if auth_type is basicauth.")
    password: str = Field("", description="Basic auth password. Required if auth_type is basicauth.")
    bearer_token: str = Field("", description="Bearer token. Required if auth_type is bearerauth.")


class UpdateWebhookParams(BaseModel):
    webhook_id: str = Field(..., description="Cin7 Core webhook ID (GUID) to update.")
    is_active: bool | None = Field(None, description="Enable/disable this webhook. Omit to keep unchanged.")
    external_url: str = Field("", description="New callback URL. Omit to keep unchanged.")


class DeleteWebhookParams(BaseModel):
    webhook_id: str = Field(..., description="Cin7 Core webhook ID (GUID) to permanently remove.")


# ──────────────────────────────────────────────────────────────────────────
# Reference data
# ──────────────────────────────────────────────────────────────────────────


class ListTaxRulesParams(NoParams):
    pass


class ListPaymentTermsParams(NoParams):
    pass


class ListAccountsParams(NoParams):
    """Chart of Accounts, for accounts/reference codes used in payments."""
    pass


class ListCurrenciesParams(NoParams):
    pass


class GetAccountInfoParams(NoParams):
    pass


# ──────────────────────────────────────────────────────────────────────────
# Value-add reports (Tier 3 -- our own aggregations, Cin7 Core has no
# single endpoint for any of these)
# ──────────────────────────────────────────────────────────────────────────


class GetLowStockReportParams(BaseModel):
    threshold: float = Field(10.0, ge=0, description="Flag any SKU whose total on-hand quantity across all locations is at or below this number.")
    location: str = Field("", description="Restrict the scan to one named location. Omit to scan all locations.")


class GetDeadStockReportParams(BaseModel):
    days_without_sale: int = Field(90, ge=1, description="Flag products with on-hand stock but no sale in this many days.")
    location: str = Field("", description="Restrict the scan to one named location. Omit to scan all locations.")


class AuditInventoryHealthParams(NoParams):
    """Aggregated health snapshot: negative-stock SKUs, products missing a
    BOM despite being marked as an assembly type, open purchase orders
    overdue for receipt, and open sale orders overdue for shipment --
    same aggregating-report shape as MuleSoft's audit_cloudhub_environment
    / Salesforce's audit_org."""
    pass


class GetStoreSummaryParams(BaseModel):
    days: int = Field(30, ge=1, le=365, description="Summarise sales/purchases/stock activity over this many trailing days.")


# ──────────────────────────────────────────────────────────────────────────
# Entities -- shared response shapes (SDL, generic dict-friendly)
# ──────────────────────────────────────────────────────────────────────────


class Product(sdl.Entity):
    id: str = ""
    title: str = ""
    name: str = ""
    sku: str = ""
    category: str = ""
    brand: str = ""
    product_type: str = ""
    is_deprecated: bool = False


class ProductList(sdl.Entity):
    title: str = ""
    items: list[Product] = Field(default_factory=list)
    total: int = 0
    page: int = 1


class GenericRecord(sdl.Entity):
    """Thin pass-through wrapper for domains whose full field shape lives
    entirely in Cin7 Core's own schema (dozens of optional fields per
    resource) -- returning the raw dict as `data` avoids re-declaring every
    field twice while still giving chat/panel code a stable entity name.
    Same pattern as MuleSoft/Salesforce connectors' raw passthrough rows."""
    id: str = ""
    data: dict = Field(default_factory=dict)


class GenericRecordList(sdl.Entity):
    title: str = ""
    items: list[GenericRecord] = Field(default_factory=list)
    total: int = 0
    page: int = 1


class ActionResultEntity(sdl.Entity):
    ok: bool = True
    id: str = ""
    message: str = ""


class DeleteResult(sdl.Entity):
    deleted: bool = False
    id: str = ""


class StockLevel(sdl.Entity):
    product_sku: str = ""
    location: str = ""
    on_hand: float = 0.0
    available: float = 0.0
    allocated: float = 0.0


class StockLevelList(sdl.Entity):
    title: str = ""
    items: list[StockLevel] = Field(default_factory=list)


class LowStockRow(sdl.Entity):
    product_sku: str = ""
    product_name: str = ""
    total_on_hand: float = 0.0
    threshold: float = 0.0


class LowStockReport(sdl.Entity):
    title: str = ""
    rows: list[LowStockRow] = Field(default_factory=list)
    threshold: float = 0.0
    scanned_count: int = 0


class DeadStockRow(sdl.Entity):
    product_sku: str = ""
    product_name: str = ""
    on_hand: float = 0.0
    last_sale_date: str = ""


class DeadStockReport(sdl.Entity):
    title: str = ""
    rows: list[DeadStockRow] = Field(default_factory=list)
    days_without_sale: int = 0
    scanned_count: int = 0


class InventoryAuditFinding(sdl.Entity):
    category: str = ""
    severity: str = ""
    reference_id: str = ""
    detail: str = ""


class InventoryAuditReport(sdl.Entity):
    title: str = ""
    findings: list[InventoryAuditFinding] = Field(default_factory=list)
    negative_stock_count: int = 0
    missing_bom_count: int = 0
    overdue_purchase_count: int = 0
    overdue_sale_count: int = 0


class StoreSummary(sdl.Entity):
    title: str = ""
    days: int = 0
    total_sales: int = 0
    total_sales_value: float = 0.0
    total_purchases: int = 0
    total_purchases_value: float = 0.0
    total_products: int = 0
    total_customers: int = 0
    total_suppliers: int = 0


class AccountInfo(sdl.Entity):
    account_id: str = ""
    company_name: str = ""
    base_currency: str = ""
    timezone: str = ""
