# Cin7 Core Connector — UI component plan

Источники: `Docs/session-notes/UI_COMPONENT_VOCABULARY.md`, `UI_INTERFACE_STANDARD.md`,
`concepts/panels.md`. Основано на функционале `cin7-core-connector`.

## 1. Компоненты

| Экран | Примитивы | Почему именно эти |
|---|---|---|
| Sidebar (left) | `ui.Column`(align="start") + `ui.Text`(company) + `ui.Divider` + navigation `ui.ListItem`(Products/Sale Orders/Purchase Orders/Stock) + `ui.Button`("App settings") | Без карточек по стандарту. |
| Product List (center, `center_overlay=True`) | `ui.Stats`(SKUs/Low stock alerts/Out of stock) + `ui.Input`(param_name="query", placeholder="Найти товар по SKU или названию...", on_submit=Call) + `ui.DataTable`(image via `ui.Image` в ячейке, sku, name, available qty, status Badge low/ok/out; sortable) | Поиск + табличный обзор каталога с индикатором остатков. |
| Product Detail | Back-button + `ui.KeyValue`(cost/price/barcode/supplier) + `ui.DataTable`(stock by location/warehouse; sortable) + `ui.Timeline`(stock movements: received→sold→adjusted) | `Timeline` отражает историю движения запасов конкретного товара. |
| Sale Order List | `ui.Select`(status_filter) + `ui.DataTable`(order#, customer, total, status Badge draft/authorised/fulfilled/invoiced; sortable) | Табличный поток заказов на продажу. |
| Sale Order Detail | Back-button + `ui.KeyValue`(customer/shipping/payment) + `ui.DataTable`(line items: product/qty/price, read-only) + `ui.Timeline`(created→authorised→picked→packed→shipped→invoiced) + `ui.Row`(Button "Authorise", "Fulfil", "Invoice") | `Timeline` — прямое отражение стадий фулфилмента Cin7. |
| Purchase Order List | `ui.DataTable`(po#, supplier, total, status Badge; sortable) | Табличный поток заказов поставщикам. |
| Purchase Order Detail | Back-button + `ui.KeyValue`(supplier/expected date) + `ui.DataTable`(line items) + `ui.Row`(Button "Authorise", "Receive Stock") | Симметрично Sale Order — приёмка товара как явное действие. |
| Stock Adjustment | `ui.Form`(action="adjust_stock") + `ui.Select`(product) + `ui.Select`(location) + `ui.Input`(type="number", quantity_delta) + `ui.TextArea`(reason) | Корректировка остатков — форма с обязательной причиной для аудита. |
| Low Stock Report | `ui.DataTable`(sku, name, available, reorder point; sortable) | Табличный отчёт по товарам ниже reorder point. |
| App Settings | `ui.Accordion`([Connections+Disconnect, Default Location/Warehouse, Webhooks CRUD]) | Централизованные настройки по стандарту. |

## 2. User flow (валидно по panel lifecycle)

1. **SESSION INIT** → `__panel__cin7_sidebar` рендерит company + разделы,
   `auto_action` открывает Product List.
2. Product List: `Input`(query) → `on_submit` → `search_products` →
   `refresh_panels`.
3. Клик по товару → `ui.Call(product_id=...)` → Product Detail — DataTable
   по локациям + Timeline движений.
4. Sale Order List → клик по заказу → Sale Order Detail; "Authorise"/"Fulfil"/
   "Invoice" — каждое действие меняет статус необратимо в учётной системе →
   обёрнуто `ui.Dialog` с подтверждением.
5. Purchase Order Detail: "Receive Stock" открывает `ui.Dialog` с формой
   количества по каждой позиции (реализовано как N×`ui.Input` внутри Dialog
   content, сгенерированных по числу строк заказа) → подтверждение →
   `ui.Call` → `refresh_panels` обновляет остатки.
6. Stock Adjustment: отдельная Form, доступна из Product Detail или из
   sidebar напрямую.
7. Low Stock Report: read-only, ссылка на товар ведёт в Product Detail.
8. App Settings: доступен из sidebar в любой момент.

## 3. Экраны/карточки (конкретно для этого приложения)

- **Screen: Sidebar** — ListItem секции: Products, Sale Orders, Purchase
  Orders, Stock (с Badge low-stock count).
- **Screen: Product List** — Stats(3) + Input(search) + DataTable(5 колонок).
- **Screen: Product Detail** — KeyValue + DataTable(по локациям) + Timeline.
- **Screen: Sale Order List** — Select(фильтр) + DataTable(4 колонки).
- **Screen: Sale Order Detail** — KeyValue + DataTable(line items) + Timeline
  + Row(3 Button).
- **Screen: Purchase Order List** — DataTable(4 колонки).
- **Screen: Purchase Order Detail** — KeyValue + DataTable + Row(2 Button).
- **Screen: Stock Adjustment** — Form(4 поля).
- **Screen: Low Stock Report** — DataTable(4 колонки).
- **Screen: App Settings** — Accordion(3 секции).

Ограничение SDK, учтённое в плане: нет отдельного barcode-scanner примитива —
штрихкод вводится/ищется через обычный `Input`.
