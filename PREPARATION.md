# Cin7 Core Connector — Preparation

**Статус:** Фаза 1 (Discovery + архитектурные решения) завершена. Влад
подтвердил объём релиза с первого сообщения по этому коннектору —
«максимальная комплектация с максимумальным функционалом» (Ярус 1+2+3),
без отдельного запроса подтверждения (см. `CONNECTOR_DISCOVERY.md` шапка).

**Владелец продукта:** vlad@bluebeeweb.com
**Дата подготовки:** 2026-08-21, v0.1
**Vikunja task:** #2215 (BBW Imperal Apps), [App Development].

**Почему сейчас:** Cin7 Core (бывший DEAR Systems) — устоявшаяся облачная
платформа управления запасами и заказами (inventory & order management)
для розничных/оптовых продавцов. В портфеле Imperal есть Shopify (витрина
и продажи) и WooCommerce через WordPress Hub, но нет ни одного
специализированного inventory/warehouse-management коннектора —
многоскладской учёт, закупки, производство (BOM) — самостоятельный
операционный домен, часто СТОЯЩИЙ ЗА несколькими витринами сразу.

---

## 1. Паспорт приложения

**Название в Marketplace (display_name): «Cin7 Core»**. Внутренний
app_id/папка: `cin7-core-connector`.

**Cin7 Core Connector** — коннектор к Cin7 Core External API v2 (REST,
`inventory.dearsystems.com/ExternalApi/v2`) для управления запасами и
заказами: продукты (с BOM/composite-структурой), остатки по локациям,
продажи (котировки/заказы/счета/отгрузки/платежи), закупки (заказы
поставщику/получения/счета), клиенты и поставщики, производство (BOM +
Production Runs), справочники (Chart of Accounts, налоги, зоны
доставки), вебхуки (события Sale/Purchase/StockAdjustment/Customer).
BYOK: пользователь подключает свой собственный Cin7 Core аккаунт через
пару статичных ключей (Account ID + Application Key), созданных в самом
Cin7 Core (Settings → Integrations & API → API keys). Imperal ничего не
хостит и не проксирует, кроме самого запроса.

---

## 2. Ключевые архитектурные решения (см. `CONNECTOR_DISCOVERY.md` §1-2)

### 2.1 Жёсткая фиксация на Cin7 Core, НЕ Cin7 Omni

Под брендом «Cin7» существуют два разных продукта с разными API
(`inventory.dearsystems.com` для Core vs `api.cin7.com` для Omni). Задача
явно про Core — весь код, все заголовки в схемах, всё именование
(app_id, docstrings) явно говорят «Cin7 Core», чтобы у пользователя не
было иллюзии, что коннектор подходит для Cin7 Omni-аккаунта. Это
единственная развилка, где спутать источники значило бы построить
нерабочий продукт — зафиксировано первым пунктом Discovery.

### 2.2 Авторизация — статичная пара ключей, НЕ OAuth

В отличие от Shopify/Salesforce/HubSpot (OAuth или custom-app token
через redirect/dashboard), Cin7 Core использует простейшую модель:
`api-auth-accountid` (Guid) + `api-auth-applicationkey` (Guid) — оба
статичных значения, полученных один раз на странице API setup внутри
Cin7 Core UI, передаются HTTP-заголовками на КАЖДЫЙ запрос. Нет redirect
flow, нет refresh token, нет expiry. Коннектор просит у пользователя:
**Account ID** + **Application Key** + опциональный **label** — форма
из 2 обязательных полей, аналог модели MuleSoft/Power Automate (готовые
credentials, не OAuth redirect).

### 2.3 API V2 как единственная поддерживаемая версия

Cin7 Core официально поддерживает V1 (легаси) и V2 (актуальная,
рекомендованная к миграции). Коннектор строится целиком на V2
(`https://inventory.dearsystems.com/ExternalApi/v2/{endpoint}`), V1 не
используется нигде — тот же принцип "одна зафиксированная версия",
что применён в Shopify Connector (`API_VERSION` константа), только тут
выбор уже сделан самим Cin7 Core (V1 официально устаревший).

### 2.4 Rate limiting — фиксированный count-based лимит, простой backoff

В отличие от Shopify (cost-based leaky bucket с непредсказуемой
"стоимостью" каждого запроса), Cin7 Core использует простую и
задокументированную цифру: **60 запросов/минуту**, превышение отдаёт
HTTP `429 Too Many Requests` (официально подтверждено на странице
API Status Codes). Это упрощает реализацию клиента относительно
Shopify — предсказуемый sleep/backoff на 429 без парсинга
`extensions.cost`, но чувствительность к лимиту одинаково реальна:
многошаговые операции (например, создание Sale построчно) должны быть
готовы к 429 и делать backoff, а не считать одну ошибку фатальной.

### 2.5 Multi-account, как multi-org у MuleSoft/Power Automate/Shopify

Пользователь может подключить несколько Cin7 Core аккаунтов (агентство
ведёт несколько клиентов) — хранится список подключений
(`cin7core_connections` secret), каждый вызов принимает опциональный
`connection_id` (по умолчанию первый/единственный), тот же паттерн, что
уже применён во всех недавних BYOK-коннекторах портфеля.

### 2.6 Вебхуки требуют Automation Module — явное предупреждение в UI

Cin7 Core документирует до 5 вебхуков одного типа и retry-логику с
несколькими попытками и увеличивающимися задержками перед автоматической
деактивацией вебхука при провале доставки. Функции `create_webhook` /
`list_webhooks` реализуются как обычно, но docstring/схема явно
предупреждают: если у аккаунта не подключён Automation Module в тарифе
Cin7 Core, вызов вернёт ошибку самого Cin7 Core (не наша сторона) — тот
же принцип "честно объяснить внешнее ограничение", что уже применён для
других коннекторов с платными модулями сторонних сервисов.

### 2.7 Именованные сущности вместо GraphQL GID

В отличие от Shopify (все id — строки `gid://shopify/...`), Cin7 Core
использует классические GUID-идентификаторы и REST endpoints по
одному ресурсу на сущность (`/Product`, `/SaleList`, `/PurchaseList`,
`/Customer`, `/Supplier`, `/StockAdjustment`, `/StockTake`,
`/production/*`, `/webhooks`). Схемы коннектора проектируются вокруг
плоских REST-эндпоинтов, а не единой GraphQL-точки — ближе по духу к
WordPress Hub/HubSpot, чем к Shopify/Salesforce.

---

## 3. Три яруса функций (по `CONNECTOR_DISCOVERY_STANDARD.md`)

### Ярус 1 — управление подключением + базовый CRUD по ядру домена

- `connect_cin7core` / `disconnect_cin7core` / `list_connections`
- Products: `list_products`, `get_product`, `create_product`,
  `update_product`, `delete_product` (deprecate, т.к. Cin7 Core не
  жёстко удаляет продукты — помечает `IsDeprecated`)
- Stock: `get_stock_levels`, `list_stock_adjustments`,
  `create_stock_adjustment`
- Sales: `list_sales`, `get_sale`, `create_sale`, `update_sale`,
  `authorise_sale_order`, `void_sale`
- Purchases: `list_purchases`, `get_purchase`, `create_purchase`,
  `update_purchase`, `authorise_purchase_order`, `void_purchase`
- Customers: `list_customers`, `get_customer`, `create_customer`,
  `update_customer`
- Suppliers: `list_suppliers`, `get_supplier`, `create_supplier`,
  `update_supplier`

### Ярус 2 — полнота охвата домена

- Sale lifecycle: `create_sale_quote`, `create_sale_shipment`,
  `create_sale_invoice`, `create_sale_payment`, `update_sale_payment`,
  `void_sale_payment`, `list_sale_credits`
- Purchase lifecycle: `create_purchase_receipt`,
  `create_purchase_invoice`, `create_purchase_payment`,
  `void_purchase_payment`
- Stock: `list_stock_locations`, `create_stock_transfer`,
  `list_stock_takes`, `create_stock_take`, `authorise_stock_take`
- Production: `get_product_bom`, `create_product_bom`,
  `update_product_bom`, `list_production_runs`,
  `create_production_run`, `update_production_run_status`
- Reference data: `list_price_tiers`, `list_tax_rules`,
  `list_locations`, `list_payment_terms`, `list_carriers`
- Attachments: `list_product_attachments`, `upload_product_attachment`,
  `delete_product_attachment`
- Webhooks: `list_webhooks`, `create_webhook`, `update_webhook`,
  `delete_webhook`

### Ярус 3 — value-add поверх нативных возможностей

- `get_low_stock_report` — товары с суммарным остатком по всем
  локациям ниже порога, одним вызовом
- `audit_inventory_health` — health-скан: продукты без SKU/стоимости,
  отрицательные остатки, deprecated продукты всё ещё используемые в
  открытых Sale/Purchase
- `bulk_update_products` / `bulk_create_stock_adjustments` — explicit
  батч на 1-100 ids (тот же паттерн `apply_bulk_*` у WordPress Hub)
- Rate-limit aware retry внутри HTTP-клиента коннектора (см. §2.4) —
  предсказуемый backoff на 429 вместо голой ошибки пользователю
- `check_webhook_health` — явный отчёт о вебхуках, автоматически
  деактивированных Cin7 Core после исчерпания попыток доставки

---

## 4. Что решено НЕ включать в этот заход (явный вырез, не забывчивость)

- **Cin7 Omni функции** — другой продукт, другой API, вне охвата
  (см. §2.1) — специально исключено, чтобы не создавать путаницу.
- **CRM/Lead-модуль Cin7 Core** (Opportunity/Lead API) — примыкающий,
  но менее востребованный домен для inventory-ориентированного
  коннектора, добавить по явному запросу.
- **B2B customer-facing портал** — конфигурация витрины внутри самого
  Cin7 Core UI, не управляется через внешний API.
- **Отчёты/дашборды Cin7 Core** (встроенная аналитика) — не выставлены
  как отдельный API-ресурс в документации, нет предмета для функции.
