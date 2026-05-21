# Integration Notes

Этот документ предназначен для ИИ-агента, который будет встраивать платежи в другой проект.

## Обязательные таблицы и поля

Минимально нужны следующие модели или их аналоги.

`User`:

- `id`
- `telegram_id`
- `username`
- `balance Numeric(10, 2)`
- для подписки: `expiration_date`, `status`, `vpn_enabled`, `device_limit_blocked`, `uuid`

`PaymentStatus`:

- `pending`
- `paid`
- `cancelled`
- `failed`

`Payment`:

- `id`
- `user_id`
- `amount Numeric(10, 2)`
- `status`
- `provider_label String(128)`, unique
- `external_operation_id String(128)`, nullable unique
- `created_at`
- `paid_at`

`DeferredTariffPurchase`:

- `id`
- `user_id`
- `payment_id`, unique
- `tariff_code`
- `tariff_price Numeric(10, 2)`
- `tariff_days`
- `created_at`
- `applied_at`
- `cancelled_at`

Если переносится логика оплаченных подписок и реферальных paid-событий, нужен `SubscriptionCharge`:

- `id`
- `user_id`
- `source`
- `created_at`

## Обязательные репозитории

`PaymentRepository`:

- `create_pending(user_id, amount, provider_label)`
- `get_by_id(payment_id)`
- `pending(limit)`
- `mark_paid(payment, operation_id, paid_at=None)`
- `mark_cancelled(payment)`

`DeferredTariffPurchaseRepository`:

- `create(user_id, payment_id, tariff_code, tariff_price, tariff_days)`
- `list_pending(limit)`

Для `BillingService` также нужны методы получения пользователя по `id` и создания `SubscriptionCharge`.

## Обязательные настройки

Из `env.payment.example` перенести:

```text
TELEGAPAY_BASE_URL=https://secure.telegapay.link/api/v1
TELEGAPAY_API_KEY=NEW_PROJECT_API_KEY
TELEGAPAY_RETURN_URL=https://t.me/your_new_bot
PAYMENT_MIN_AMOUNT=100
PAYMENT_TTL_MINUTES=60
PAYMENT_POLL_INTERVAL_SECONDS=60
```

В новом проекте заменить:

- `TELEGAPAY_API_KEY` на новый API-ключ;
- `TELEGAPAY_RETURN_URL` на ссылку нового бота или страницы возврата;
- `DATABASE_URL` на БД нового проекта.

## Зависимости

Минимально для платежного сервиса:

- `httpx`
- `SQLAlchemy`
- `asyncpg`, если используется PostgreSQL async URL
- `pydantic-settings`, если переносится текущий `Settings`

Для scheduler:

- `apscheduler`

Для Telegram UI и уведомлений:

- `aiogram`

Если новый проект не Telegram-бот, замените `bot.send_message(...)` на локальный notification adapter или no-op.

## Точки адаптации

- `TelegaPayService` ожидает объект `settings` с полями `telegapay_base_url`, `telegapay_api_key`, `telegapay_return_url`, `payment_min_amount`, `payment_ttl_minutes`, `super_admin_id`.
- `TelegaPayService` ожидает `async_sessionmaker`.
- `create_payment()` принимает ORM-объект пользователя с `id` и `telegram_id`.
- `poll_pending_payments()` принимает `Bot`, но `Bot` нужен только для уведомлений.
- `BillingService` зависит от VPN/Xray-логики исходного проекта. Если в новом проекте другой продукт, оставьте платежную часть и замените `_charge_subscription()` на активацию своего продукта.
- `payment_method` сейчас жестко задан как `QR_CODE`. Не менять на другое значение без проверки договора с TelegaPay.

## Scheduler

Сохранить порядок:

```python
processed = await payment_service.poll_pending_payments(bot)
applied, cancelled = await billing_service.process_deferred_tariff_purchases(bot)
```

Почему порядок важен: сначала pending-платеж должен стать `paid` и пополнить баланс, только потом deferred purchase может списать деньги и активировать тариф.

## Приемочные проверки после переноса

1. Создание платежа возвращает `payment_url` и создает запись `payments.status=pending`.
2. В запрос `create_paylink` уходит `X-API-Key` нового проекта.
3. Ответ TelegaPay `completed` переводит платеж в `paid`, заполняет `paid_at`, увеличивает баланс ровно на `payment.amount`.
4. Ответ `cancelled` или `expired` переводит платеж в `cancelled`.
5. Платеж старше `PAYMENT_TTL_MINUTES` отменяется локально.
6. Покупка тарифа при нехватке баланса создает `DeferredTariffPurchase`.
7. После успешной оплаты deferred purchase списывает баланс и активирует продукт.
8. Повторный polling не начисляет деньги второй раз.
9. Ошибка сети или невалидный JSON от TelegaPay не ломает весь job, а оставляет платеж pending для следующей проверки.
10. Реальный `.env` исходного проекта нигде не был перенесен.

## Webhook

Webhook в исходной реализации отсутствует. Подтверждение оплаты выполняется только server-side polling-ом через `check_status`.
