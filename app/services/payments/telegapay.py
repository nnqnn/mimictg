from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx

from app.config import Settings
from app.services.payments.provider import PaymentLink, PaymentProviderError, PaymentStatusResult


class TelegaPayProvider:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def create_paylink(
        self,
        *,
        telegram_user_id: int,
        amount: Decimal,
        description: str,
        order_id: str,
        return_url: str | None = None,
    ) -> PaymentLink:
        payload = self.build_create_payload(
            telegram_user_id=telegram_user_id,
            amount=amount,
            description=description,
            order_id=order_id,
            return_url=return_url,
        )
        data = await self._post("create_paylink", payload)
        return self.parse_create_response(data)

    async def check_status(self, transaction_id: str) -> PaymentStatusResult:
        data = await self._post("check_status", {"transaction_id": transaction_id})
        return PaymentStatusResult(
            status=str(data.get("status", "")).lower().strip(),
            paid_at=self.parse_provider_datetime(data),
            raw=data,
        )

    def build_create_payload(
        self,
        *,
        telegram_user_id: int,
        amount: Decimal,
        description: str,
        order_id: str,
        return_url: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "amount": float(amount),
            "currency": "RUB",
            "description": description,
            "order_id": order_id,
            "payment_method": "QR_CODE",
            "user_id": str(telegram_user_id),
        }
        if return_url:
            payload["return_url"] = return_url
        return payload

    @staticmethod
    def parse_create_response(data: dict[str, Any]) -> PaymentLink:
        transaction_id = str(data.get("transaction_id", "")).strip()
        payment_url = str(data.get("payment_url", "")).strip()
        if not data.get("success"):
            raise PaymentProviderError("Платёжный шлюз не подтвердил создание ссылки")
        if not transaction_id or not payment_url:
            raise PaymentProviderError("Платёжный шлюз вернул неполные данные платежа")
        return PaymentLink(transaction_id=transaction_id, payment_url=payment_url, raw=data)

    @staticmethod
    def parse_provider_datetime(data: dict[str, Any]) -> datetime | None:
        for key in ("completed_at", "confirmed_at", "processed_at", "created_at"):
            raw = data.get(key)
            if not raw:
                continue
            try:
                return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            except ValueError:
                continue
        return None

    async def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.telegapay_api_key:
            raise PaymentProviderError("Оплата временно недоступна")

        url = f"{self.settings.telegapay_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {
            "X-API-Key": self.settings.telegapay_api_key,
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise PaymentProviderError(f"Ошибка сети при обращении к TelegaPay: {exc}") from exc

        if response.status_code >= 400:
            detail = response.text
            try:
                detail = response.json().get("error") or detail
            except ValueError:
                pass
            raise PaymentProviderError(f"TelegaPay {response.status_code}: {detail}")

        try:
            return response.json()
        except ValueError as exc:
            raise PaymentProviderError("Некорректный JSON от TelegaPay") from exc
