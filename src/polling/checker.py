import asyncio
from src.t_payment.models import Order
from aiogram import Bot
from src.config import settings
from src.t_payment import t_payment
from src.db_infra import db
from src.t_payment.models import StatusCode

from loguru import logger

# Создаем клиента для TPay
client = t_payment.TPay(settings.t_pay.tpay_term_key, settings.t_pay.tpay_pass)


async def check_order_status(order: Order, bot) -> Order:
    """Запускаем проверку статуса заказа в TPay и реагируем на изменения статусов.
    Если лимит проверок закончился, получили ошибку или платеж отменился, руками отменяем платеж,
    чтобы не наткнуться на ошибку."""
    checked_order = await client.check_order_polling(order)
    logger.debug(f"The order id: {checked_order.id}, status: {checked_order.status}")

    if checked_order.status == StatusCode.confirmed.value:
        checked_order = await payment_received(checked_order, bot)

    elif checked_order.status in (
        StatusCode.rejected.value,
        StatusCode.cancelled.value,
        StatusCode.max_attempts.value,
    ):
        checked_order = await cancel_payment(checked_order, bot)

    return checked_order


async def payment_received(order: Order, bot) -> Order:
    """Действия при удачной оплате: обновляем объект заказа в БД, отсылаем подробности юзеру"""

    # Обновляем заказ в бд
    updated_order = await db.update_order(order)
    logger.info(
        f"The payment {updated_order.id} received. Status: {updated_order.status}"
    )

    # Сообщение для понимания, что платеж прошел успешно
    await bot.send_message(
        order.customer_key,
        f"The payment {updated_order.id} was successful."
        f"\nThe amount: {updated_order.amount}.",
    )
    return updated_order
    # TODO: Реализовать получение чека


async def cancel_payment(order: Order, bot) -> Order:
    """Действия при неудачной оплате: отменяем платеж в TPay,
    обновляем статус платежа в БД, отправляем инфу юзеру"""
    logger.debug("Canceling a TPay payment")
    try:
        order = await client.cancel_payment(order)
    except Exception as e:
        logger.debug(
            f"Не получилось отменить платеж в TPay. Возможно, он уже отменен: {e}"
        )

    logger.debug("Updating the payment in DB")
    updated_order = await db.update_order(order)

    logger.info(f"The payment {updated_order.id} canceled")

    # Сообщение для понимания, что платеж прошел с ошибкой
    await bot.send_message(
        updated_order.customer_key,
        f"The payment {updated_order.id} was made with an error."
        f"\nThe amount of {updated_order.amount} has not been credited."
        f"\nStatus code: {updated_order.status}",
    )
    return updated_order


async def run_checker() -> None:
    """Запускаем постоянную проверку новых платежей.
    Актуально при перезапуске или в случае сбоев"""
    bot = Bot(token=settings.tg.tg_token)
    while True:
        new_orders = await db.get_all_orders_by_status(StatusCode.new.value)
        logger.debug(f"All of new orders: {new_orders}")
        tasks = [check_order_status(order, bot) for order in new_orders]
        logger.info(f"Listening to changes in NEW orders")
        await asyncio.gather(*tasks)
        await asyncio.sleep(5)
