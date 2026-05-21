# Payment Flow

Документ описывает фактический цикл по исходному коду, а не желаемую архитектуру.

## 1. Пользователь начинает оплату

Есть два входа из Telegram UI:

- Пополнение баланса: `app/bot/handlers/user.py`, callback `topup:<amount>`.
- Покупка тарифа: `app/bot/handlers/user.py`, callback `tariff:<code>`.

Для пополнения обработчик сразу вызывает:

```python
payment, payment_url = await payment_service.create_payment(user=user, amount_rub=amount)
```

Для тарифа обработчик вызывает `BillingService.purchase_tariff(...)`.

- Если баланса хватает, тариф активируется сразу и TelegaPay не вызывается.
- Если баланса не хватает, рассчитывается сумма платежа, создается TelegaPay paylink и создается `DeferredTariffPurchase`, связанная с `payment.id`.

## 2. Создание платежной ссылки

Метод: `TelegaPayService.create_payment(user, amount_rub)`.

Endpoint:

```text
POST {TELEGAPAY_BASE_URL}/create_paylink
```

Headers:

```text
X-API-Key: {TELEGAPAY_API_KEY}
Content-Type: application/json
```

Payload:

```json
{
  "amount": 100.0,
  "currency": "RUB",
  "description": "Balance top-up for TG 123456789",
  "order_id": "ORD123456789-<random_hex>",
  "payment_method": "QR_CODE",
  "user_id": "123456789",
  "return_url": "https://t.me/your_bot"
}
```

`return_url` добавляется только если `TELEGAPAY_RETURN_URL` непустой.

Ожидаемый ответ:

```json
{
  "success": true,
  "transaction_id": "provider_transaction_id",
  "payment_url": "https://..."
}
```

Если `success` не truthy, нет `transaction_id` или нет `payment_url`, код бросает `PaymentProviderError`.

## 3. Сохранение pending-платежа

После успешного ответа TelegaPay создается запись:

- `payments.user_id = user.id`
- `payments.amount = amount`
- `payments.status = pending`
- `payments.provider_label = order_id`
- `payments.external_operation_id = transaction_id`

`provider_label` уникален. `external_operation_id` тоже уникален, если задан.

Пользователю показывается кнопка с `payment_url`.

## 4. Polling статуса

Scheduler вызывает платежную задачу с интервалом `PAYMENT_POLL_INTERVAL_SECONDS`.

Порядок внутри job:

1. `TelegaPayService.poll_pending_payments(bot)`
2. `BillingService.process_deferred_tariff_purchases(bot)`
3. Если были подтвержденные платежи, дополнительно запускаются auto-renew/reconcile в исходном проекте.

Polling выбирает до 60 oldest pending-платежей.

Перед запросом к TelegaPay проверяется локальный TTL:

- если `payment.created_at < now - PAYMENT_TTL_MINUTES`, платеж переводится в `cancelled`;
- статус у провайдера в этом случае уже не запрашивается.

## 5. Проверка статуса в TelegaPay

Endpoint:

```text
POST {TELEGAPAY_BASE_URL}/check_status
```

Headers:

```text
X-API-Key: {TELEGAPAY_API_KEY}
Content-Type: application/json
```

Payload:

```json
{
  "transaction_id": "provider_transaction_id"
}
```

Платеж считается успешным только при:

```text
status == "completed"
```

Платеж отменяется при:

```text
status in {"cancelled", "expired"}
```

Другие статусы оставляют платеж в `pending` до следующего polling.

## 6. Что происходит при `completed`

Для успешного платежа:

1. `PaymentRepository.mark_paid(...)` ставит `status=paid`.
2. `paid_at` берется из первого распознанного поля ответа: `completed_at`, `confirmed_at`, `processed_at`, `created_at`; если не получилось, ставится текущий UTC.
3. Баланс пользователя увеличивается на `payment.amount`.
4. Пользователь получает сообщение о зачислении.
5. Super-admin получает уведомление о пополнении.

Повторное зачисление не происходит, потому что следующий polling уже не выберет этот платеж: он не `pending`.

## 7. Отложенная покупка тарифа

Если пользователь покупал тариф и баланса не хватало, при создании платежа была создана запись `deferred_tariff_purchases`.

После того как платеж стал `paid`, `BillingService.process_deferred_tariff_purchases(bot)`:

- находит pending deferred purchase;
- проверяет связанный `payment.status`;
- если платеж `cancelled` или `failed`, помечает deferred purchase как `cancelled_at`;
- если платеж еще не `paid`, ничего не делает;
- если пользователь забанен, отменяет активацию, но деньги уже остаются на балансе;
- если баланса хватает, списывает `tariff_price`;
- для subscription-тарифа продлевает `expiration_date` на `tariff_days`;
- для instruction-продукта списывает цену и отправляет ссылку на инструкцию;
- ставит `applied_at`.

## 8. Минимальный итоговый цикл

```text
User click -> create_paylink -> save pending payment -> show payment_url
Scheduler -> check_status(transaction_id)
completed -> mark paid -> add balance
Scheduler -> process deferred purchase -> charge balance -> activate product
```
