from datetime import datetime

from app.db.models import SubscriptionPlan


class MockPaymentProvider:
    async def create_subscription(
        self,
        *,
        user_id: int,
        plan: SubscriptionPlan,
        starts_at: datetime,
        ends_at: datetime | None,
    ) -> dict:
        return {
            "provider": "mock",
            "user_id": user_id,
            "plan": plan.value,
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat() if ends_at else None,
        }

