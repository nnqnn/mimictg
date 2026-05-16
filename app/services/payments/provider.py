from datetime import datetime
from typing import Protocol

from app.db.models import SubscriptionPlan


class PaymentProvider(Protocol):
    async def create_subscription(
        self,
        *,
        user_id: int,
        plan: SubscriptionPlan,
        starts_at: datetime,
        ends_at: datetime | None,
    ) -> dict:
        ...

