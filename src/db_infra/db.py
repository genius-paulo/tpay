import peewee_async
from peewee import *
from loguru import logger
from src.t_payment.models import Order
from datetime import datetime

from src.config import settings

# Подключение к базе данных PostgreSQL
db = peewee_async.PostgresqlDatabase(
    database=settings.db.db_name,
    user=settings.db.db_user,
    password=settings.db.db_password,
    host=settings.db.db_host,
)


class Orders(Model):
    id = AutoField(primary_key=True)
    amount = IntegerField(null=False)
    customer_key = IntegerField(null=False)
    email = TextField(null=False)
    receipt = TextField(null=True)
    description = TextField(null=False)
    status = TextField(null=False)
    url = TextField(null=True)
    payment_id = TextField(null=True)
    created = DateTimeField(default=datetime.now, null=False)

    class Meta:
        database = db
        table_name = "Orders"


def _get_conn() -> peewee_async.Manager:
    return peewee_async.Manager(db)


def _order_mapping(db_order: _get_conn()) -> Order:
    logger.debug(
        f"Mapping an object {db_order}:\n"
        f"amount: {db_order.amount},\n"
        f"customer_key={db_order.customer_key},\n"
        f"email: {db_order.email},\n"
        f"description: {db_order.description},\n"
        f"receipt: {db_order.receipt},\n"
        f"status: {db_order.status},\n"
        f"id: {db_order.id},\n"
        f"url: {db_order.url},\n"
        f"payment_id: {db_order.payment_id},\n"
        f"created: {db_order.created}.\n"
    )

    order = Order(
        amount=db_order.amount,
        customer_key=db_order.customer_key,
        email=db_order.email,
        description=db_order.description,
        receipt=db_order.receipt,
        status=db_order.status,
        id=db_order.id,
        url=db_order.url,
        payment_id=db_order.payment_id,
        created=db_order.created,
    )

    logger.debug(f"The object was mapped successfully: {order}")
    return order


def create_tables(
    database: peewee_async.PostgresqlDatabase, table: type[Orders]
) -> None:
    """Функция для создания таблиц"""
    database.create_tables([table])
    logger.info("Tables created")


async def get_orders() -> list:
    """Функция для получения всех платежей из БД"""
    elements = list(await _get_conn().execute(Orders.select()))
    logger.debug(f"Get all of objects from db: {elements}")
    return elements


async def get_order_by_number(id: int) -> Order:
    """Функция для получения платежа из БД по номеру"""
    try:
        order_db = await _get_conn().get(Orders, id=id)
        logger.debug(f"Get order from db: {order_db.id}")
        return _order_mapping(order_db)
    except Exception as e:
        logger.debug(f"Something went wrong: {e}")


async def add_order(
    amount: int, customer_key: int, description: str, email: str, status: str
) -> Order:
    """Функция для создания нового платежа в БД"""
    new_db_order = await _get_conn().create(
        Orders,
        amount=amount,
        customer_key=customer_key,
        email=email,
        description=description,
        status=status,
    )
    return _order_mapping(new_db_order)


async def update_order(order: Order) -> Order:
    """Функция для обновления платежа в БД"""

    logger.debug(f"Updating the order in the database. The order: {order}")
    try:
        result = await _get_conn().execute(
            Orders.update(
                status=order.status,
                url=order.url,
                receipt=str(order.receipt),
                payment_id=order.payment_id,
            ).where(Orders.id == order.id)
        )
        logger.debug(f"Result of the payment {order.id} update: {result}")
    except Exception as e:
        logger.warning(f"Error updating the payment {order.id} in the database: {e}")

    logger.debug(f"Searching the order in the database: {order}")
    updated_db_object = await get_order_by_number(order.id)
    logger.debug(f"Updated order: {updated_db_object}")
    return updated_db_object
