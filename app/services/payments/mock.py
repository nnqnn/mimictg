from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.services.payments.provider import PaymentLink, PaymentStatusResult


class MockPaymentProvider:
    def __init__(self, *, status: str = "completed"):
        self.status = status
        self.created_payloads: list[dict[str, Any]] = []

    async def create_paylink(
        self,
        *,
        telegram_user_id: int,
        amount: Decimal,
        description: str,
        order_id: str,
        return_url: str | None = None,
    ) -> PaymentLink:
        payload = {
            "telegram_user_id": telegram_user_id,
            "amount": str(amount),
            "description": description,
            "order_id": order_id,
            "return_url": return_url,
        }
        self.created_payloads.append(payload)
        return PaymentLink(
            transaction_id=f"mock-{order_id}",
            payment_url=f"https://pay.example/{order_id}",
            raw={"success": True, "mock": True, **payload},
        )

    async def check_status(self, transaction_id: str) -> PaymentStatusResult:
        return PaymentStatusResult(
            status=self.status,
            paid_at=datetime.now(timezone.utc) if self.status == "completed" else None,
            raw={"status": self.status, "transaction_id": transaction_id, "mock": True},
        )
