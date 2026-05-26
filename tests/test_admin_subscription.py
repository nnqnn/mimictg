from datetime import datetime, timezone

from app.bot.handlers.utils import ADMIN_SUBSCRIPTION_UNTIL, grant_admin_subscription_if_needed
from app.config import Settings
from app.db.models import SubscriptionPlan, User


def test_admin_telegram_id_gets_business_subscription():
    settings = Settings(_env_file=None, ADMIN_TELEGRAM_IDS="100,200")
    user = User(
        telegram_id=100,
        subscription_plan=SubscriptionPlan.FREE,
        subscription_until=None,
    )

    changed = grant_admin_subscription_if_needed(user, settings)

    assert changed
    assert user.subscription_plan == SubscriptionPlan.BUSINESS
    assert user.subscription_until == ADMIN_SUBSCRIPTION_UNTIL


def test_non_admin_keeps_current_subscription():
    settings = Settings(_env_file=None, ADMIN_TELEGRAM_IDS="100,200")
    until = datetime(2026, 6, 1, tzinfo=timezone.utc)
    user = User(
        telegram_id=300,
        subscription_plan=SubscriptionPlan.FREE,
        subscription_until=until,
    )

    changed = grant_admin_subscription_if_needed(user, settings)

    assert not changed
    assert user.subscription_plan == SubscriptionPlan.FREE
    assert user.subscription_until == until


def test_admin_subscription_grant_is_idempotent():
    settings = Settings(_env_file=None, ADMIN_TELEGRAM_IDS="100")
    user = User(
        telegram_id=100,
        subscription_plan=SubscriptionPlan.BUSINESS,
        subscription_until=ADMIN_SUBSCRIPTION_UNTIL,
    )

    changed = grant_admin_subscription_if_needed(user, settings)

    assert not changed
