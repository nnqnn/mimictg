# TelegaPay Payment Handoff

Этот пакет - срез платежной реализации из проекта `tgvpn`. Его можно отдать другому ИИ-агенту, чтобы перенести платежный цикл в новый проект с теми же TelegaPay endpoints и другим API-ключом.

## Что внутри

- `source/` - исходные файлы, скопированные с сохранением путей из проекта.
- `env.payment.example` - безопасный env-шаблон для нового проекта. Реальный `.env` не копировался.
- `PAYMENT_FLOW.md` - полный фактический цикл создания и подтверждения платежа.
- `INTEGRATION_NOTES.md` - таблицы, методы, зависимости и приемочные проверки для интеграции.

## Главные файлы в `source/`

- `app/services/payment_service.py` - TelegaPay API client, создание paylink, polling статусов, зачисление баланса.
- `app/services/billing_service.py` - тарифы, покупка за баланс, создание отложенной покупки при нехватке баланса, автоактивация после оплаты.
- `app/services/scheduler_service.py` - фоновая задача: сначала проверяет платежи, затем применяет отложенные покупки.
- `app/db/models.py` - ORM-модели, включая `Payment`, `DeferredTariffPurchase`, `SubscriptionCharge`, `User`.
- `app/db/repositories.py` - методы доступа к платежам и отложенным покупкам.
- `app/bot/handlers/user.py` - Telegram UI-flow для пополнения и покупки тарифа.
- `app/bot/keyboards.py` - кнопки выбора суммы, тарифа и перехода по платежной ссылке.
- `app/config.py` - env-настройки TelegaPay и polling.
- `app/logging_config.py` - отдельный логгер `payments`.
- `app/utils/security.py` - генерация уникального `order_id`.
- `app/utils/time.py` - UTC-время и форматирование сроков.
- `requirements.txt` - зависимости исходного проекта.
- `.env.example` - полный env-шаблон исходного проекта без секретов.

## Как переносить

1. Сначала перенести или адаптировать модели `Payment`, `DeferredTariffPurchase`, `PaymentStatus` и поля пользователя `balance`, `telegram_id`, `username`.
2. Перенести репозитории `PaymentRepository` и `DeferredTariffPurchaseRepository`.
3. Перенести `TelegaPayService` и заменить зависимости на локальные аналоги нового проекта.
4. Перенести нужную часть `BillingService`, если новый проект должен автоматически активировать тариф после оплаты.
5. Подключить scheduler job: `poll_pending_payments()` -> `process_deferred_tariff_purchases()`.
6. Настроить env из `env.payment.example`, обязательно заменить `TELEGAPAY_API_KEY` на ключ нового проекта.

## Важные ограничения

- Webhook сейчас не используется. Подтверждение оплаты идет polling-ом через `check_status`.
- `payment_method` в коде установлен как `QR_CODE`.
- Повторное начисление предотвращается тем, что polling выбирает только `payments.status=pending`.
- Просроченный pending-платеж отменяется локально после `PAYMENT_TTL_MINUTES` до запроса статуса.
