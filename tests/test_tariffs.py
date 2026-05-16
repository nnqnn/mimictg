from app.config import Settings
from app.db.models import SubscriptionPlan
from app.services.tariffs.service import TariffService


def test_workspace_limits_by_plan():
    tariffs = TariffService(Settings(_env_file=None))

    assert tariffs.can_add_workspace(SubscriptionPlan.FREE, 0)
    assert not tariffs.can_add_workspace(SubscriptionPlan.FREE, 1)

    assert tariffs.can_add_workspace(SubscriptionPlan.PRO, 1)
    assert not tariffs.can_add_workspace(SubscriptionPlan.PRO, 2)

    assert tariffs.can_add_workspace(SubscriptionPlan.BUSINESS, 4)
    assert not tariffs.can_add_workspace(SubscriptionPlan.BUSINESS, 5)


def test_feature_gates():
    tariffs = TariffService(Settings(_env_file=None))

    assert not tariffs.limits_for(SubscriptionPlan.FREE).publication
    assert tariffs.limits_for(SubscriptionPlan.PRO).publication
    assert tariffs.limits_for(SubscriptionPlan.BUSINESS).priority

