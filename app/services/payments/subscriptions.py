from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.db.models import Payment, PaymentStatus, Subscription, SubscriptionPlan, SubscriptionStatus, User
from app.db.repositories.payments import PaymentRepository
from app.services.payments.provider import PaymentProvider, PaymentProviderError

logger = logging.getLogger(__name__)

PAID_PROVIDER_STATUSES = {"completed"}
CANCELLED_PROVIDER_STATUSES = {"cancelled", "expired"}


@dataclass(frozen=True)
class SubscriptionOffer:
    plan: SubscriptionPlan
    title: str
    price: Decimal
    days: int
    short_features: tuple[str, ...]


PAYMENT_PENDING = "pending"
PAYMENT_PAID = "paid"
PAYMENT_CANCELLED = "cancelled"
PAYMENT_FAILED = "failed"
PaymentCheckResult = Literal["pending", "paid", "cancelled", "failed"]


class SubscriptionBillingService:
    def __init__(
        self,
        settings: Settings,
        session_maker: async_sessionmaker[AsyncSession],
        provider: PaymentProvider,
    ):
        self.settings = settings
        self.session_maker = session_maker
        self.provider = provider

    @staticmethod
    def offers() -> tuple[SubscriptionOffer, ...]:
        return (
            SubscriptionOffer(
                plan=SubscriptionPlan.START,
                title="Start",
                price=Decimal("499"),
                days=30,
                short_features=("50 генераций в месяц", "идеи постов", "улучшение черновиков"),
            ),
            SubscriptionOffer(
                plan=SubscriptionPlan.PRO,
                title="Pro",
                price=Decimal("990"),
                days=30,
                short_features=("ежедневный пост", "медиа-план", "публикация в канал", "полный аудит"),
            ),
            SubscriptionOffer(
                plan=SubscriptionPlan.BUSINESS,
                title="Business",
                price=Decimal("1990"),
                days=30,
                short_features=("5 каналов", "приоритетная генерация", "расширенный задел под агентский режим"),
            ),
        )

    @classmethod
    def offer_for(cls, plan: SubscriptionPlan | str) -> SubscriptionOffer | None:
        value = plan.value if isinstance(plan, SubscriptionPlan) else plan
        for offer in cls.offers():
            if offer.plan.value == value:
                return offer
        return None

    @classmethod
    def subscription_overview(cls, user: User) -> str:
        current = user.subscription_plan.value if isinstance(user.subscription_plan, SubscriptionPlan) else user.subscription_plan
        until = cls.format_date(user.subscription_until) if user.subscription_until else "без даты окончания"
        lines = [
            "⭐ <b>Подписка Mimic</b>",
            "",
            f"Текущий тариф: <b>{current}</b>",
            f"Действует до: <b>{until}</b>",
            "",
            "Free подходит, чтобы попробовать стиль и базовую генерацию.",
            "Pro открывает ежедневный пост, медиа-план, полный аудит и публикацию в канал.",
            "",
            "<b>Тарифы</b>",
        ]
        for offer in cls.offers():
            features = ", ".join(offer.short_features)
            lines.append(f"• {offer.title} — {offer.price:.0f} ₽ / 30 дней: {features}")
        return "\n".join(lines)

    async def create_plan_payment(
        self,
        session: AsyncSession,
        *,
        user: User,
        plan: SubscriptionPlan,
    ) -> Payment:
        offer = self.offer_for(plan)
        if offer is None:
            raise ValueError("Неизвестный тариф")
        if not self.settings.telegapay_api_key:
            raise PaymentProviderError("Оплата временно недоступна")
        if offer.price < Decimal(str(self.settings.payment_min_amount)):
            raise ValueError(f"Минимальная сумма платежа: {self.settings.payment_min_amount} ₽")

        order_id = self.generate_order_id(user.telegram_id)
        description = f"Mimic {offer.title} subscription for TG {user.telegram_id}"
        link = await self.provider.create_paylink(
            telegram_user_id=user.telegram_id,
            amount=offer.price,
            description=description,
            order_id=order_id,
            return_url=self.settings.telegapay_return_url or None,
        )
        payment = await PaymentRepository(session).create_pending(
            user_id=user.id,
            amount=offer.price,
            target_plan=offer.plan,
            provider_order_id=order_id,
            provider_transaction_id=link.transaction_id,
            payment_url=link.payment_url,
            raw_payload={"create": link.raw},
        )
        return payment

    async def check_payment(
        self,
        session: AsyncSession,
        *,
        payment_id: int,
        bot: Bot | None = None,
    ) -> PaymentCheckResult:
        repo = PaymentRepository(session)
        payment = await repo.get_by_id(payment_id)
        if payment is None:
            return PAYMENT_FAILED
        if payment.status == PaymentStatus.PAID:
            return PAYMENT_PAID
        if payment.status == PaymentStatus.CANCELLED:
            return PAYMENT_CANCELLED
        if payment.status == PaymentStatus.FAILED:
            return PAYMENT_FAILED
        if self.is_expired(payment):
            await repo.mark_cancelled(payment, status_payload={"reason": "local_ttl"})
            return PAYMENT_CANCELLED
        if not payment.provider_transaction_id:
            await repo.mark_failed(payment, error="missing provider_transaction_id")
            return PAYMENT_FAILED

        try:
            result = await self.provider.check_status(payment.provider_transaction_id)
        except PaymentProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise PaymentProviderError(str(exc)) from exc

        if result.status in PAID_PROVIDER_STATUSES:
            await repo.mark_paid(payment, paid_at=result.paid_at, status_payload=result.raw)
            user = await session.get(User, payment.user_id)
            if user is not None:
                subscription = self.activate_subscription(user=user, payment=payment, now=payment.paid_at)
                if subscription is not None:
                    session.add(subscription)
                if bot is not None:
                    await self.safe_send(bot, user.telegram_id, self.paid_message(user))
            await session.flush()
            return PAYMENT_PAID

        if result.status in CANCELLED_PROVIDER_STATUSES:
            await repo.mark_cancelled(payment, status_payload=result.raw)
            return PAYMENT_CANCELLED

        payment.raw_payload = {**(payment.raw_payload or {}), "status": result.raw}
        await session.flush()
        return PAYMENT_PENDING

    async def poll_pending_payments(self, bot: Bot) -> int:
        processed = 0
        async with self.session_maker() as session:
            pending = await PaymentRepository(session).pending(limit=60)
            for payment in pending:
                try:
                    result = await self.check_payment(session, payment_id=payment.id, bot=bot)
                    if result == PAYMENT_PAID:
                        processed += 1
                except PaymentProviderError as exc:
                    logger.warning("Payment check failed for payment_id=%s: %s", payment.id, exc)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Unexpected payment polling error for payment_id=%s: %s", payment.id, exc)
            await session.commit()
        return processed

    def activate_subscription(
        self,
        *,
        user: User,
        payment: Payment,
        now: datetime | None = None,
    ) -> Subscription | None:
        if payment.activated_at is not None:
            return None
        now = self.ensure_aware(now or datetime.now(timezone.utc))
        offer = self.offer_for(payment.target_plan)
        if offer is None:
            return None
        current_until = self.ensure_aware(user.subscription_until) if user.subscription_until else None
        starts_at = current_until if current_until and current_until > now else now
        ends_at = starts_at + timedelta(days=offer.days)
        user.subscription_plan = offer.plan
        user.subscription_until = ends_at
        payment.activated_at = now
        return Subscription(
            user_id=user.id,
            plan=offer.plan,
            status=SubscriptionStatus.ACTIVE,
            starts_at=now,
            ends_at=ends_at,
            metadata_json={"source": "telegapay", "payment_id": payment.id},
        )

    def is_expired(self, payment: Payment, *, now: datetime | None = None) -> bool:
        now = self.ensure_aware(now or datetime.now(timezone.utc))
        created_at = self.ensure_aware(payment.created_at)
        return created_at < now - timedelta(minutes=self.settings.payment_ttl_minutes)

    @staticmethod
    def generate_order_id(telegram_id: int) -> str:
        return f"MIMIC{telegram_id}-{secrets.token_hex(8)}"

    @staticmethod
    def ensure_aware(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def format_date(value: datetime) -> str:
        return SubscriptionBillingService.ensure_aware(value).strftime("%d.%m.%Y")

    @classmethod
    def paid_message(cls, user: User) -> str:
        current = user.subscription_plan.value if isinstance(user.subscription_plan, SubscriptionPlan) else user.subscription_plan
        until = cls.format_date(user.subscription_until) if user.subscription_until else "—"
        return f"Готово. Подписка {current.title()} активна до {until}."

    @staticmethod
    async def safe_send(bot: Bot, telegram_id: int, text: str) -> None:
        try:
            await bot.send_message(telegram_id, text)
        except Exception:  # noqa: BLE001
            logger.warning("Cannot deliver payment notification to %s", telegram_id)
