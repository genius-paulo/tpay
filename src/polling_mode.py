from aiogram import Bot, Dispatcher, executor, types
from loguru import logger
from config import settings
from t_payment import t_payment
from t_payment.models import Order
from db_infra import db
from t_payment.models import StatusCode

# Запускаем бота
bot = Bot(token=settings.tg.tg_token)
dp = Dispatcher(bot)

# Создаем клиента для TPay
client = t_payment.TPay(settings.t_pay.tpay_term_key, settings.t_pay.tpay_pass)

# Создаем бд
db.create_tables(db.db, db.Orders)


# TODO: Нужно реализовать проверку незавершенных платежей при перезапуске


@dp.message_handler(commands=["start"])
async def send_welcome(message: types.Message):
    """Проверяем, что все ок и что бот работает"""
    await message.reply("Hi!\nThe bot is working.")
    await message.reply(f"Available tables in db: {db.db.get_tables()}")


@dp.message_handler(commands=["get_mock_payments"])
async def create_mock_orders(message: types.Message):
    """Создаем фейковые заказы в БД, чтобы закрыть количество существующих заказов в TPay"""
    for _ in range(settings.t_pay.orders_count):
        await get_payment_link(message)

    await message.reply(
        f"{settings.t_pay.orders_count} orders have been created in the database."
        f"\nThese are all orders from the database: {await db.get_orders()}"
    )


@dp.message_handler(commands=["get_payment"])
async def get_payment_link(message: types.Message) -> None:
    """Создаем платеж в БД, а потом в TPay,
    отправляем юзеру ссылку, запускаем polling-проверку"""

    try:
        # Создаем платеж в базе
        order = await db.add_order(
            amount=1000,
            customer_key=message.from_id,
            email="test@test",
            description="Покупка секунд Voicee",
            status=StatusCode.created.value,
        )

        logger.debug(f"The order object was created: {type(order)}: {order}")

        # Создаем платеж в TPay
        order = await client.create_order_link(order)
        logger.debug(f"The TPay order was created: {type(order)}, {order}")
        # Обновляем заказа в базе
        updated_order = await db.update_order(order)

        # Отправляем сообщение юзеру
        await message.answer(
            f"Link to your order: {updated_order.url}. Payment status: {updated_order.status}"
        )

        # Запускаем polling-проверку статуса платежа
        await check_order_status(updated_order)

    except Exception as e:
        logger.info(f"Somethings went wrong: {e}")


async def check_order_status(order: Order) -> Order:
    """Запускаем проверку статуса заказа в TPay и реагируем на изменения статусов.
    Если лимит проверок закончился, получили ошибку или платеж отменился, руками отменяем платеж,
    чтобы не наткнуться на ошибку."""
    checked_order = await client.check_order_polling(order)
    logger.debug(f"The order id: {checked_order.id}, status: {checked_order.status}")

    if checked_order.status == StatusCode.confirmed.value:
        checked_order = await payment_received(checked_order)

    elif checked_order.status in (
        StatusCode.rejected.value,
        StatusCode.cancelled.value,
        StatusCode.max_attempts.value,
    ):
        checked_order = await cancel_payment(checked_order)

    return checked_order


async def payment_received(order: Order) -> Order:
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


async def cancel_payment(order: Order) -> Order:
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


@dp.message_handler()
async def echo(message: types.Message):
    await message.answer(
        "This bot demonstrates the possibilities of interacting with the TPay API."
        " To receive a test payment, click /get_payment"
    )


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=settings.tg.skip_updates)
