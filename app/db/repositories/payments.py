from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Payment, PaymentStatus, SubscriptionPlan


class PaymentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_pending(
        self,
        *,
        user_id: int,
        amount: Decimal,
        target_plan: SubscriptionPlan,
        provider_order_id: str,
        provider_transaction_id: str,
        payment_url: str,
        raw_payload: dict[str, Any],
    ) -> Payment:
        payment = Payment(
            user_id=user_id,
            amount=amount,
            currency="RUB",
            target_plan=target_plan,
            status=PaymentStatus.PENDING,
            provider_order_id=provider_order_id,
            provider_transaction_id=provider_transaction_id,
            payment_url=payment_url,
            raw_payload=raw_payload,
        )
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def get_by_id(self, payment_id: int) -> Payment | None:
        return await self.session.get(Payment, payment_id)

    async def pending(self, *, limit: int = 60) -> list[Payment]:
        result = await self.session.execute(
            select(Payment)
            .where(Payment.status == PaymentStatus.PENDING)
            .order_by(Payment.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_paid(
        self,
        payment: Payment,
        *,
        paid_at: datetime | None = None,
        status_payload: dict[str, Any] | None = None,
    ) -> None:
        payment.status = PaymentStatus.PAID
        payment.paid_at = paid_at or datetime.now(timezone.utc)
        if status_payload is not None:
            payment.raw_payload = {**(payment.raw_payload or {}), "status": status_payload}
        await self.session.flush()

    async def mark_cancelled(
        self,
        payment: Payment,
        *,
        status_payload: dict[str, Any] | None = None,
    ) -> None:
        payment.status = PaymentStatus.CANCELLED
        payment.cancelled_at = datetime.now(timezone.utc)
        if status_payload is not None:
            payment.raw_payload = {**(payment.raw_payload or {}), "status": status_payload}
        await self.session.flush()

    async def mark_failed(self, payment: Payment, *, error: str) -> None:
        payment.status = PaymentStatus.FAILED
        payment.raw_payload = {**(payment.raw_payload or {}), "error": error}
        await self.session.flush()
