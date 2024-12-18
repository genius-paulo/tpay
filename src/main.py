import asyncio

from aiogram import Bot, Dispatcher, executor, types
from src.config import settings
from src.t_payment import t_payment
from src.db_infra import db
from src.t_payment.models import StatusCode
from src.polling import checker

import sys
from loguru import logger

logger.remove()
logger.add(sys.stderr, level=settings.logger_level)

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


@dp.message_handler(commands=["get_payment"])
async def get_payment_link(message: types.Message) -> None:
    """Создаем платеж в БД, а потом в TPay,
    отправляем юзеру ссылку, запускаем polling-проверку"""

    try:
        # Создаем платеж в базе
        order = await db.add_order(
            amount=1000,  # Сумма передается в копейках, нужно «очеловечивать» — например, у себя делить на 100
            customer_key=message.from_id,
            email="fedorenko-pavel@mail.ru",
            description="Услуги по транскрибации аудио и видео файлов путем предоставления доступа к "
            "Программному комплексу распознавания и синтеза речи Voicee (Войси)",
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
        await checker.check_order_status(updated_order, bot)

    except Exception as e:
        logger.error(f"Somethings went wrong: {e}")


@dp.message_handler()
async def echo(message: types.Message):
    await message.answer(
        "This bot demonstrates the possibilities of interacting with the TPay API."
        " To receive a test payment, click /get_payment"
    )


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(checker.run_checker())
    executor.start_polling(dp, skip_updates=settings.tg.skip_updates)
