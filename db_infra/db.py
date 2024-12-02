import peewee_async
from peewee import *
from loguru import logger
from t_payment.models import Order
from datetime import datetime

from config import settings

# Подключение к базе данных PostgreSQL
db = peewee_async.PostgresqlDatabase(database=settings.db_name,
                                     user=settings.db_user, password=settings.db_password,
                                     host=settings.db_host)


class BaseModel(Model):
    order_id = AutoField(column_name='order_id', primary_key=True)
    amount = IntegerField(column_name='amount', null=False)
    customer_key = IntegerField(column_name='customer_key', null=False)
    email = TextField(column_name='email', null=False)
    receipt = TextField(column_name='receipt', null=True)
    description = TextField(column_name='description', null=False)
    status = TextField(column_name='status', null=False)
    url = TextField(column_name='url', null=True)
    payment_id = IntegerField(column_name='payment_id', null=True)
    created = DateTimeField(column_name='created', default=datetime.now, null=False)

    class Meta:
        database = db


class Orders(BaseModel):
    class Meta:
        table_name = 'Orders'


def _get_conn() -> peewee_async.Manager:
    connection_manager = peewee_async.Manager(db)
    return connection_manager


def create_tables(database: peewee_async.PostgresqlDatabase, table: type[Orders]) -> None:
    """Функция для создания таблиц"""
    database.create_tables([table])
    logger.info("Tables created")


async def get_orders() -> list:
    """Функция для получения всех платежей из БД"""
    elements = await _get_conn().execute(Orders.select())
    list_elements = []
    for element in elements:
        list_elements.append(element)
    logger.debug(f"Get all of objects from db: {list_elements}")
    return list_elements


async def get_order_by_number(order_id: str) -> Order:
    """Функция для получения платежа из БД по номеру"""
    try:
        order = await _get_conn().get(Orders, order_id=order_id)
        logger.debug(f"Get order from db: {order.order_id}")
    except Exception as e:
        logger.debug(f"Something went wrong: {e}")
        return None
    else:
        return order


async def add_order(amount, customer_key, description, email, status) -> Order:
    """Функция для создания нового платежа в БД"""
    new_order = await _get_conn().create(Orders,
                                         amount=amount, customer_key=customer_key, email=email,
                                         description=description, status=status)
    return new_order


async def update_order(order: Order) -> Order:
    """Функция для обновления платежа в БД"""
    await _get_conn().execute(Orders.update(status=order.status, url=order.url
                                            ).where(Orders.order_id == order.order_id))
    logger.debug(f"Updating the order in the database.")
    updated_db_object = await get_order_by_number(order.order_id)
    logger.debug(f'Updated order {updated_db_object.order_id} status and url are: {updated_db_object.status}: '
                 f'{updated_db_object.url}')
    return updated_db_object


async def delete_order(order: Order) -> None:
    """Функция для удаления платежа из БД"""
    result = await _get_conn().execute(Orders.delete().where(Orders.number == order.order_id))
    logger.debug(f"Delete order. Result: {result}")
    updated_db_object = await get_order_by_number(order.order_id)
    logger.debug(f'DB object deleted: {updated_db_object.status}')
