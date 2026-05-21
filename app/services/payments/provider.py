from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol


class PaymentProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class PaymentLink:
    transaction_id: str
    payment_url: str
    raw: dict[str, Any]


@dataclass(frozen=True)
class PaymentStatusResult:
    status: str
    paid_at: datetime | None
    raw: dict[str, Any]


class PaymentProvider(Protocol):
    async def create_paylink(
        self,
        *,
        telegram_user_id: int,
        amount: Decimal,
        description: str,
        order_id: str,
        return_url: str | None = None,
    ) -> PaymentLink:
        ...

    async def check_status(self, transaction_id: str) -> PaymentStatusResult:
        ...
