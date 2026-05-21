from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.utils import get_current_user
from app.bot.keyboards.inline import payment_keyboard, subscription_keyboard
from app.bot.keyboards.reply import main_menu_keyboard
from app.config import Settings
from app.db.models import Payment, PaymentStatus, SubscriptionPlan, User
from app.db.session import async_session_factory
from app.services.payments import PaymentProviderError, SubscriptionBillingService, TelegaPayProvider

router = Router(name="subscription")


def _billing(settings: Settings) -> SubscriptionBillingService:
    return SubscriptionBillingService(settings, async_session_factory, TelegaPayProvider(settings))


async def send_subscription_screen(message: Message, user: User) -> None:
    await message.answer(
        SubscriptionBillingService.subscription_overview(user),
        reply_markup=subscription_keyboard(),
    )


@router.message(F.text.in_({"⭐ Подписка", "Подписка"}))
async def subscription_menu(message: Message, session: AsyncSession, settings: Settings) -> None:
    user = await get_current_user(session, message, settings)
    await send_subscription_screen(message, user)


@router.callback_query(F.data == "subscription:open")
async def subscription_open(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    user = await get_current_user(session, callback, settings)
    if callback.message:
        await send_subscription_screen(callback.message, user)
    await callback.answer()


@router.callback_query(F.data.startswith("subscription:buy:"))
async def buy_subscription(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    user = await get_current_user(session, callback, settings)
    raw_plan = callback.data.split(":")[-1] if callback.data else ""
    try:
        plan = SubscriptionPlan(raw_plan)
    except ValueError:
        await callback.answer("Неизвестный тариф.", show_alert=True)
        return

    if callback.message:
        await callback.message.answer("Готовлю ссылку на оплату.", reply_markup=ReplyKeyboardRemove())
    try:
        payment = await _billing(settings).create_plan_payment(session, user=user, plan=plan)
    except PaymentProviderError:
        if callback.message:
            await callback.message.answer("Оплата временно недоступна. Попробуй позже.", reply_markup=main_menu_keyboard())
        await callback.answer()
        return
    except ValueError as exc:
        if callback.message:
            await callback.message.answer(str(exc), reply_markup=main_menu_keyboard())
        await callback.answer()
        return

    offer = SubscriptionBillingService.offer_for(plan)
    title = offer.title if offer else plan.value.title()
    text = (
        f"Ссылка готова.\n\n"
        f"Тариф: <b>{title}</b>\n"
        f"Сумма: <b>{payment.amount:.0f} ₽</b>\n\n"
        "После оплаты я сам активирую подписку. Если уже оплатил, нажми проверку."
    )
    if callback.message:
        await callback.message.answer(
            text,
            reply_markup=payment_keyboard(payment.id, payment.payment_url, payment.target_plan),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("payment:check:"))
async def check_payment(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    payment_id_raw = callback.data.split(":")[-1] if callback.data else ""
    if not payment_id_raw.isdigit():
        await callback.answer("Неизвестный платёж.", show_alert=True)
        return
    payment_id = int(payment_id_raw)
    user = await get_current_user(session, callback, settings)
    payment = await session.get(Payment, payment_id)
    if payment is None or payment.user_id != user.id:
        await callback.answer("Неизвестный платёж.", show_alert=True)
        return

    billing = _billing(settings)
    try:
        result = await billing.check_payment(session, payment_id=payment_id)
    except PaymentProviderError:
        if callback.message:
            await callback.message.answer("Не получилось проверить платёж. Попробуй ещё раз через минуту.")
        await callback.answer()
        return

    if result == "paid":
        if callback.message:
            await callback.message.answer(billing.paid_message(user), reply_markup=main_menu_keyboard())
    elif result == "cancelled":
        if callback.message:
            await callback.message.answer(
                "Платёж не завершён. Можно создать новую ссылку на оплату.",
                reply_markup=subscription_keyboard(),
            )
    elif payment and payment.status == PaymentStatus.FAILED:
        if callback.message:
            await callback.message.answer("Платёж не удалось обработать. Создай новую ссылку на оплату.")
    else:
        if callback.message:
            await callback.message.answer("Платёж пока не подтверждён. Обычно это занимает до минуты.")
    await callback.answer()
