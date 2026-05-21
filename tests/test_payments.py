from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from app.bot.keyboards.reply import main_menu_keyboard
from app.config import Settings
from app.db.models import Payment, SubscriptionPlan, User
from app.services.payments import MockPaymentProvider, PaymentProviderError, SubscriptionBillingService, TelegaPayProvider


def _service() -> SubscriptionBillingService:
    return SubscriptionBillingService(Settings(_env_file=None), None, MockPaymentProvider())


def test_telegapay_create_payload_shape():
    provider = TelegaPayProvider(Settings(_env_file=None, TELEGAPAY_API_KEY="key"))

    payload = provider.build_create_payload(
        telegram_user_id=123,
        amount=Decimal("990"),
        description="Mimic Pro subscription",
        order_id="MIMIC123-test",
        return_url="https://t.me/bot",
    )

    assert payload == {
        "amount": 990.0,
        "currency": "RUB",
        "description": "Mimic Pro subscription",
        "order_id": "MIMIC123-test",
        "payment_method": "QR_CODE",
        "user_id": "123",
        "return_url": "https://t.me/bot",
    }


def test_telegapay_create_response_validation():
    link = TelegaPayProvider.parse_create_response(
        {"success": True, "transaction_id": "tx_1", "payment_url": "https://pay"}
    )
    assert link.transaction_id == "tx_1"
    assert link.payment_url == "https://pay"

    with pytest.raises(PaymentProviderError):
        TelegaPayProvider.parse_create_response({"success": True, "transaction_id": "tx_1"})


def test_activate_subscription_extends_active_until_once():
    service = _service()
    now = datetime(2026, 5, 21, tzinfo=timezone.utc)
    user = User(
        id=1,
        telegram_id=100,
        subscription_plan=SubscriptionPlan.FREE,
        subscription_until=now + timedelta(days=10),
    )
    payment = Payment(id=7, user_id=1, amount=Decimal("990"), target_plan=SubscriptionPlan.PRO)

    subscription = service.activate_subscription(user=user, payment=payment, now=now)
    second_subscription = service.activate_subscription(user=user, payment=payment, now=now)

    assert subscription is not None
    assert second_subscription is None
    assert user.subscription_plan == SubscriptionPlan.PRO
    assert user.subscription_until == now + timedelta(days=40)
    assert payment.activated_at == now


def test_activate_subscription_from_now_for_expired_subscription():
    service = _service()
    now = datetime(2026, 5, 21, tzinfo=timezone.utc)
    user = User(
        id=1,
        telegram_id=100,
        subscription_plan=SubscriptionPlan.START,
        subscription_until=now - timedelta(days=1),
    )
    payment = Payment(id=8, user_id=1, amount=Decimal("1990"), target_plan=SubscriptionPlan.BUSINESS)

    service.activate_subscription(user=user, payment=payment, now=now)

    assert user.subscription_plan == SubscriptionPlan.BUSINESS
    assert user.subscription_until == now + timedelta(days=30)


def test_pending_payment_expires_by_ttl():
    service = _service()
    now = datetime(2026, 5, 21, tzinfo=timezone.utc)
    payment = Payment(
        id=1,
        user_id=1,
        amount=Decimal("499"),
        target_plan=SubscriptionPlan.START,
        created_at=now - timedelta(minutes=61),
    )

    assert service.is_expired(payment, now=now)


def test_main_menu_has_marketing_subscription_button():
    keyboard = main_menu_keyboard()
    texts = [[button.text for button in row] for row in keyboard.keyboard]

    assert texts[0] == ["⭐ Подписка"]


def test_env_example_contains_telegapay_settings():
    env_text = Path(".env.example").read_text(encoding="utf-8")

    assert "TELEGAPAY_API_KEY=" in env_text
    assert "TELEGAPAY_BASE_URL=" in env_text
    assert "PAYMENT_POLL_INTERVAL_SECONDS=" in env_text
