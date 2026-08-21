# Cin7 Core Connector — Connector Discovery

**Дата discovery:** 2026-08-21
**Статус:** Ярусы 1-3 пройдены (чтение официальной документации Cin7 Core
через help.core.cin7.com и зеркало Apiary-референса dearinventory.docs.apiary.io,
2026-08-21). §6 (решение по объёму) НЕ требует отдельного вопроса Владу —
Влад заявил объём с первого сообщения по этому коннектору ("максимальный
функционал, полный максимум"), что по `CONNECTOR_DISCOVERY_STANDARD.md`
Шаг 5 действует как уже данный ответ. Берём Ярус 1 + Ярус 2 + Ярус 3.

---

## 1. Целевой сервис и источники

Cin7 Core (бывший **DEAR Systems / DEAR Inventory**, бренд сменился после
приобретения Cin7) — облачная платформа управления запасами и заказами
(inventory & order management) для розничных и оптовых продавцов: товары,
остатки по нескольким складам/локациям, продажи, закупки, производство
(сборка по Bill of Materials), базовая бухгалтерская интеграция. В отличие
от Shopify (витрина + продажи как единица e-commerce фронта), Cin7 Core —
это операционный backend склада/производства, часто СТОЯЩИЙ ЗА несколькими
витринами сразу (Shopify + Amazon + розница) и синхронизирующий остатки
между ними. В портфеле Imperal нет ни одного специализированного
inventory/warehouse-management коннектора — ближайшие соседи (Shopify,
WooCommerce через WordPress Hub) управляют витриной, а не многоскладским
учётом и производством.

Источники (прочитаны 2026-08-21):
- `help.core.cin7.com/hc/en-us/articles/9982508120975-API-V1-introduction` —
  V1 введение (легаси)
- `help.core.cin7.com/hc/en-us/articles/10113609017359-API-V2-introduction` —
  V2 введение (актуальная версия)
- `help.core.cin7.com/hc/en-us/articles/<slug>-Connecting-to-the-Cin7-Core-API` —
  подключение, получение Account ID / Application Key
- `dearinventory.docs.apiary.io` (полный REST-референс: Product, Sale,
  Purchase, Customer, Supplier, StockAdjustment, StockTake, Production/BOM,
  Webhooks, Attachments, Tax, Reference Books) — читан через context7.com
  зеркало (`context7.com/websites/dearinventory_apiary_io/llms.txt`), так
  как сам Apiary-сайт отдаёт контент только через JS-рендер/защиту от
  автоматических читателей
- `dearinventory.docs.apiary.io/introduction/api-status-codes` — коды
  ответов, включая точную цифру rate limit
- Сторонние обёртки как перекрёстная проверка модели данных:
  `github.com/CompostNow/cin7core-python`, `github.com/ScreenStaring/cin7-cli`
  (подтверждают состав сущностей: Sale, SaleOrder, Webhook, Product, Stock,
  Location)
- `stacksync.com/connectors/cin7` — источник, явно предупреждающий о
  путанице Cin7 Core vs Cin7 Omni (см. Критично п.1)

## 2. Критично по этому приложению

1. **НАЗВАНИЕ-ЛОВУШКА: под брендом «Cin7» существуют ДВА разных продукта.**
   **Cin7 Core** (бывший DEAR Systems) — API на `inventory.dearsystems.com`,
   документация на `help.core.cin7.com` и Apiary. **Cin7 Omni** — другой
   продукт линейки Cin7, отдельный API на `api.cin7.com` со своей
   документацией и своими rate limit-цифрами. Это два разных продукта с
   разными credentials, разными доменами и разными API-контрактами
   (подтверждено сторонним источником stacksync.com/connectors/cin7).
   Задача явно про **Cin7 Core** — коннектор строится строго на
   `inventory.dearsystems.com/ExternalApi`, `api.cin7.com` не используется
   нигде и не упоминается в схемах, чтобы не создавать путаницу для
   пользователя.
2. **Актуальная версия — V2.** Базовый URL:
   `https://inventory.dearsystems.com/ExternalApi/v2/{endpoint}`. V1 —
   легаси, официально помечен устаревшим (`API-V1-introduction`
   рекомендует миграцию на V2). Коннектор строится целиком на V2.
3. **Модель авторизации — статичная пара ключей, НЕ OAuth.** Каждый запрос
   должен нести два HTTP-заголовка:
   - `api-auth-accountid` — Account ID пользователя
   - `api-auth-applicationkey` — Application Key
   Оба генерируются пользователем внутри самого Cin7 Core на странице
   `https://inventory.dearsystems.com/ExternalAPI` (API setup page). Это
   классический BYOK-паттерн той же формы, что уже применён в портфеле
   (MuleSoft/Power Automate просят готовые credentials без OAuth redirect) —
   `connect_cin7core` просит две строки (account_id + application_key),
   проверяет их одним лёгким GET-запросом (например `/me` или `/Product`
   с `limit=1`), и всё.
4. **Rate limit — жёстко зафиксированная цифра, официально документирована.**
   Официальная страница статус-кодов Apiary прямым текстом: `429 Too Many
   Requests` = **"You reached 60 calls per minute API limit"**. Это НЕ
   Cin7 Omni-цифры (3 req/s / 5000/день), которые относятся к другому
   продукту — важно не перепутать при написании клиента. Коннектор должен
   учитывать этот лимит на уровне клиента (задержки/ретраи при 429),
   аналогично паттерну rate-limit handling в других коннекторах портфеля.
5. **Полный список статус-кодов** (Apiary, `introduction/api-status-codes`):
   `200 OK`, `204 No Content`, `400 Bad Request` (невалидные данные —
   текст ошибки в теле), `403 Forbidden` (ошибка аутентификации),
   `404 Not Found` (несуществующий эндпоинт — важно: путь ЕДИНСТВЕННОГО
   числа, например `/Product`, а не `/Products` — частая ошибка новичков
   согласно самой доке), `405 Not Allowed` (метод не поддержан для этого
   ресурса), `429 Too Many Requests` (см. п.4), `500 Internal Server
   Error`.
6. **Webhooks — есть, но лимитированы и требуют отдельного модуля
   подписки.** До 5 вебхуков одного типа. Retry-логика: несколько попыток
   доставки с нарастающей задержкой, при исчерпании попыток вебхук
   автоматически деактивируется (`IsActive` становится false) — коннектор
   должен уметь это читать и репортить пользователю ("вебхук отключился
   сам, потому что endpoint не отвечал"), а не молчать. Поддерживаемые
   типы авторизации колбэка: `noauth`, `basicauth`, `bearerauth`.
   Официальный список типов событий широкий (≈30), из ключевых:
   `Sale/Created`, `Sale/QuoteAuthorised`, `Sale/OrderAuthorised`,
   `Sale/Voided`, `Sale/Backordered`, `Sale/ShipmentAuthorised`,
   `Sale/InvoiceAuthorised`, `Sale/PickAuthorised`, `Sale/PackAuthorised`,
   `Sale/CreditNoteAuthorised`, `Sale/Undo`, `Sale/PartialPaymentAuthorised`
   и аналогичные для Purchase (`Purchase/Created`, `Purchase/Authorised`
   и т.д.) — точный полный список фиксируется на этапе Дизайна прямым
   зеркалированием документации Webhooks resource.
7. **Требуется отдельный "Automation Module" в подписке Cin7 Core для
   вебхуков** (согласно `Using-the-Automation-Module` статье поддержки) —
   это НЕ гарантированно доступно на любом тарифе клиента. Коннектор
   должен корректно обрабатывать отказ создания вебхука с понятным
   сообщением ("на вашем тарифе Cin7 Core модуль автоматизации/вебхуков
   недоступен"), а не притворяться, что функция всегда работает.
8. **REST-архитектура старой школы: единственное число в путях, XML-подобная
   строгая схема полей с типами/длиной.** Каждый ресурс документирован с
   точными полями (Name, Type, Length, Required) — при валидации на нашей
   стороне следует полагаться на реальные коды ошибок API (400 с деталями
   в теле), а не дублировать валидацию вручную, чтобы не разойтись со
   схемой при её изменении со стороны Cin7.
9. **Производство (Production/BOM) — отдельный полноценный домен,**
   которого нет у большинства коннекторов маркетплейса: Bill of Materials
   (`/production/product-production-bom`), Production Orders, Production
   Runs (со статусами `PLANNED`/`IN PROGRESS`/`OPERATION_COMPLETED`/
   `COMPLETED`/`VOIDED`), Production Resources. Это прямая ценность для
   производственных SMB-клиентов Cin7 Core (не просто перепродавцов).
10. **Постраничный вывод (pagination) — `Page`/`Limit` query-параметры**
    на списочных эндпоинтах (`SaleList`, `PurchaseList` и т.д.), а не
    cursor-based, как у более новых API портфеля (Shopify GraphQL,
    HubSpot). Ответ листингов включает `Total` — коннектор реализует
    собственный удобный листинг (page/limit параметры в схемах), без
    курсоров.

## 3. Карта возможностей (направление на каждую)

| Домен | Возможность | Ingress/Egress/Both | Комментарий |
|---|---|---|---|
| Products | list/get/create/update products, product attachments, availability, pricelist | Both | Ядро каталога |
| Sales | list/get/create/update sale (quote → order → invoice → shipment цикл), sale payments, sale credit notes, void sale | Both | Ядро цикла продаж |
| Sale Fulfilment | SaleList с деталями отгрузки, SaleShip (создание/добавление строк отгрузки) | Both | Отгрузка по продаже |
| Purchases | list/get/create/update purchase (заказ поставщику → получение → счёт), purchase payments | Both | Ядро цикла закупок |
| Customers | list/get/create/update customers, customer addresses, custom fields | Both | CRM-слой |
| Suppliers | list/get/create/update suppliers | Both | Поставщики |
| Stock | stock levels/availability по локациям, stock adjustments (создание/void), stock takes, stock transfers между локациями | Both | Многоскладской учёт — ключевая ценность продукта |
| Locations | list locations | Ingress | Контекст для инвентаря |
| Production | Bill of Materials (get/create/update BOM), production orders, production runs, production resources | Both | Сборка/производство — уникальный домен относительно остальных коннекторов портфеля |
| Webhooks | list/create/update/delete webhook subscriptions | Both | Событийные уведомления (Ярус 2), лимит 5 на тип |
| Tax Rules / Reference Books | tax rates, price tiers, payment terms, carriers, ship zones — справочные данные | Ingress (в основном) | Контекст для валидных значений в других сущностях |
| Attachments | product attachments, sale/purchase attachments (файлы) | Both | Вложения к документам |
| Accounting | Chart of Accounts (справочно), учёт налогов в Sale/Purchase | Ingress | Только чтение — полноценная бухгалтерия вне охвата |

## 4. Ярус 1 — Ключевые функции (P0)

1. `connect_cin7core` / `disconnect_cin7core` / `list_connections` —
   account_id + application_key, проверка лёгким GET-запросом
2. `list_products` / `get_product` / `create_product` / `update_product`
3. `list_customers` / `get_customer` / `create_customer` / `update_customer`
4. `list_suppliers` / `get_supplier` / `create_supplier` / `update_supplier`
5. `list_sales` / `get_sale` / `create_sale` / `update_sale`
6. `list_purchases` / `get_purchase` / `create_purchase` / `update_purchase`
7. `get_stock_levels` (остатки по продукту/локации)
8. `list_locations`

## 5. Ярус 2 — Полное покрытие

| Возможность | Статус | Причина/триггер |
|---|---|---|
| Product CRUD + attachments + availability + pricelist | included | Ярус 1 расширенный |
| Sale полный цикл (quote/order/invoice authorise, void, undo) | included | Реальная операционная последовательность продажи в Cin7 Core |
| Sale payments (create/update/list) | included | Учёт оплат по продаже |
| Sale fulfilment / SaleShip (отгрузки) | included | Прямое продолжение продажи — логистика |
| Sale credit notes | included | Возвраты/кредит-ноты — частый операционный кейс |
| Purchase полный цикл (order/receive/invoice authorise, void) | included | Симметрично Sale-циклу |
| Purchase payments | included | Учёт оплат поставщикам |
| Customer/Supplier CRUD + custom fields | included | Ярус 1 расширенный |
| Stock adjustments (create/void) | included | Ручная корректировка остатков — базовая складская операция |
| Stock takes | included | Инвентаризация |
| Stock transfers между локациями | included | Многоскладской перенос — ключевая ценность продукта |
| Production BOM (get/create/update) | included | Явно заявлено как Ярус максимум — производственный домен |
| Production Orders / Runs (list/get/create/update статус) | included | Полный цикл производства |
| Webhooks (list/create/update/delete) | included | Событийная интеграция, лимит 5/тип учтён в дизайне |
| Attachments (product/sale/purchase) | included | Вложения — частый операционный кейс (накладные, фото) |
| Tax rates / payment terms / carriers / ship zones (read) | included | Справочные данные нужны как контекст при создании Sale/Purchase |
| Полная бухгалтерская синхронизация (Xero/QBO connections внутри Cin7) | not applicable | Настраивается внутри самого Cin7 Core UI, не через внешний API — вне охвата коннектора |
| Cin7 Omni функции (другой продукт) | not applicable | Разные продукт и API — см. Критично п.1, явно не в охвате |
| B2B портал / Customer-facing storefront (если есть в тарифе) | deferred | Нишевая настройка витрины, не основной охват API |

## 6. Ярус 3 — Функции на нашей стороне (value-add)

- **`get_low_stock_report`** — агрегирующий отчёт: товары с остатком по
  всем локациям ниже порога, одним вызовом вместо ручного обхода списка
  продуктов + остатков по каждой локации (по аналогии с
  `get_low_stock_report` в Shopify Connector портфеля)
- **`audit_inventory_health`** — агрегирующий отчёт: продукты без SKU,
  без стоимости, с отрицательным остатком, устаревшие (deprecated)
  продукты всё ещё используемые в открытых Sale/Purchase — по аналогии с
  `audit_store_health`/`audit_cloudhub_environment` в других коннекторах
- **`bulk_update_products`** / **`bulk_create_stock_adjustments`** —
  обёртки по explicit id-списку в одном вызове поверх API, которое
  принимает только один объект за раз на большинстве write-эндпоинтов
- **rate-limit aware retry** на уровне HTTP-клиента коннектора — сам
  API не даёт `Retry-After`, но документированный фиксированный лимит (60/мин)
  позволяет реализовать предсказуемый backoff внутри клиента, а не просто
  бросать 429 пользователю
- **webhook health check** — обёртка, которая явно репортит пользователю
  вебхуки, автоматически деактивированные Cin7 Core после исчерпания
  попыток доставки (см. Критично п.6), вместо того чтобы это осталось
  незамеченным

## 7. Решение по объёму этого захода

Влад заявил объём явно первым же сообщением по этому коннектору:
**"Cin7 Core делай это приложение в максимальной комплектации с
максимумальным функционалом"**. По `CONNECTOR_DISCOVERY_STANDARD.md`
Шаг 5 (исключение) это действует как уже данный ответ — берём **Ярус 1 +
Ярус 2 + Ярус 3** без дополнительного вопроса. Переходим сразу к Фазе 3
(Дизайн) и Фазе 4 (Разработка).
