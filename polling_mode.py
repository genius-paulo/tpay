from aiogram import Bot, Dispatcher, executor, types
from loguru import logger
from config import settings
from t_payment import t_payment
from t_payment.models import Order
from db_infra import db

# Запускаем бота
bot = Bot(token=settings.tg_token)
dp = Dispatcher(bot)

# Создаем клиента для TPay
client = t_payment.TPay(settings.tpay_term_key, settings.tpay_pass)

# Создаем бд
db.create_tables(db.db, db.Orders)


# TODO: Нужно реализовать проверку незавершенных платежей при перезапуске

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    """Проверяем, что все ок и что бот работает"""
    await message.reply("Hi!\nThe bot is working.")
    await message.reply(f"Available tables in db: {db.db.get_tables()}")


@dp.message_handler(commands=['get_mock_payments'])
async def create_mock_orders(message: types.Message):
    """Создаем фейковые заказы в БД, чтобы закрыть количество существующих заказов в TPay"""
    for _ in range(settings.orders_count):
        await get_payment_link(message)

    await message.reply(f"{settings.orders_count} orders have been created in the database."
                        f"\nThese are all orders from the database: {await db.get_orders()}")


@dp.message_handler(commands=["get_payment"])
async def get_payment_link(message: types.Message) -> None:
    """Создаем платеж в БД, а потом в TPay,
    отправляем юзеру ссылку, запускаем polling-проверку"""

    try:
        # Создаем платеж в базе
        order_db = await db.add_order(amount=1000, customer_key=message.from_id, email='test@test',
                                      description='Пополнение аккаунта Voicee', status='CREATED')
        logger.debug(f'The order was created in the DB: {type(order_db)}: {order_db}')

        # TODO: Можно ли реализовать распаковку из объекта БД в объект заказа лучше?
        # Создаем объект заказа
        order_obj = Order(order_id=order_db.order_id, amount=order_db.amount, customer_key=order_db.customer_key,
                          email=order_db.email, description=order_db.description, status=order_db.status,
                          created=order_db.created)
        logger.debug(f'The order object was created: {type(order_obj)}: {order_obj}')

        # Создаем платеж в TPay
        order = await client.create_order_link(order_obj)
        logger.debug(f'The TPay order was created: {type(order)}, {order}')

        # Обновляем заказа в базе
        order_obj = await db.update_order(order)

        # Отправляем сообщение юзеру
        await message.answer(f'Link to your order: {order_obj.url}. Payment status: {order_obj.status}')

        # Запускаем polling-проверку статуса платежа
        result_order = await check_order_status(order)

    except Exception as e:
        logger.info(f'Somethings went wrong: {e}')


async def check_order_status(order: Order) -> Order:
    """Запускаем проверку статуса заказа в TPay и реагируем на изменения статусов.
    Если лимит проверок закончился, получили ошибку или платеж отменился, руками отменяем платеж,
    чтобы не наткнуться на ошибку."""
    order = await client.check_order_polling(order)
    logger.debug(f"The order id: {order.order_id}, status: {order.status}")

    if order.status == 'CONFIRMED':
        order = await payment_received(order)

    elif order.status in ('REJECTED', 'CANCELLED', 'MAX_ATTEMPTS'):
        order = await cancel_payment(order)

    return order


async def payment_received(order: Order) -> None:
    """Действия при удачной оплате: обновляем объект заказа в БД, отсылаем подрообности юзеру"""

    # Обновляем заказ в бд
    order = await db.update_order(order)
    logger.info(f"The payment {order.order_id} received. Status: {order.status}")

    # Сообщение для понимания, что платеж прошел успешно
    await bot.send_message(order.customer_key,
                           f'The payment {order.order_id} was successful.'
                           f'\nThe amount: {order.amount}.')
    return order
    # TODO: Реализовать получение чека


async def cancel_payment(order: Order) -> None:
    """Действия при неудачной оплате: отменяем платеж в TPay,
    обновляем статус платежа в БД, отправляем инфу юзеру"""
    logger.debug('Canceling a TPay payment')
    try:
        await client.cancel_payment(order)
    except Exception as e:
        logger.debug(f'Не получилось отменить платеж в TPay. Возможно, он уже отменен: {e}')

    logger.debug('Updating the payment in DB')
    order = await db.update_order(order)

    logger.info(f"The payment {order.order_id} canceled")

    # Сообщение для понимания, что платеж прошел с ошибкой
    await bot.send_message(order.customer_key,
                           f'The payment {order.order_id} was made with an error.'
                           f'\nThe amount of {order.amount} has not been credited.'
                           f'\nStatus code: {order.status}')
    return order


@dp.message_handler()
async def echo(message: types.Message):
    await message.answer('This bot demonstrates the possibilities of interacting with the TPay API.'
                         ' To receive a test payment, click /get_payment')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=settings.skip_updates)
