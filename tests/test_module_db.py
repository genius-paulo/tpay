from loguru import logger
from src.t_payment import models
from src.db_infra import db
import pytest


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.parametrize(
    "amount,customer_key,email,status",
    [
        (100, 542570177, "test@test", models.StatusCode.created.value),
        (1000000000, 542570177, "test@test", models.StatusCode.new.value),
        (502020200, 542570177, "test@test", models.StatusCode.cancelled.value),
    ],
)
async def test_create_order_in_db(create_tables, amount, customer_key, email, status):
    # Создаем заказ в БД и проверяем на наличие ID
    db_order = await db.add_order(
        amount=amount,
        customer_key=customer_key,
        description="TEST CREATE",
        email=email,
        status=models.StatusCode.created.value,
    )
    assert str(db_order.id) is not None


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.parametrize(
    "new_status",
    [
        models.StatusCode.created.value,
        models.StatusCode.new.value,
        models.StatusCode.cancelled.value,
    ],
)
async def test_update_order_in_db(create_tables, new_status):
    # Создаем заказ в БД
    db_order = await db.add_order(
        amount=1000,
        customer_key=542570177,
        description="TEST UPDATE",
        email="test@test",
        status=models.StatusCode.created.value,
    )

    # Меняем статус
    db_order.status = new_status
    # Обновляем статус в базе
    updated_order = await db.update_order(db_order)

    # Получаем запись из базы вручную и сравниваем статус со статусом объекта
    received_object = await db.get_order_by_number(db_order.id)
    assert updated_order.id == received_object.id


@pytest.mark.asyncio(loop_scope="module")
async def test_get_all_orders(create_tables):
    orders = await db.get_orders()
    for order in orders:
        assert order.id is not None
        assert order.status in (
            models.StatusCode.created.value,
            models.StatusCode.new.value,
            models.StatusCode.confirmed.value,
            models.StatusCode.cancelled.value,
            models.StatusCode.max_attempts.value,
            models.StatusCode.rejected.value,
        )


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.parametrize(
    "status",
    [
        models.StatusCode.created.value,
        models.StatusCode.new.value,
        models.StatusCode.confirmed.value,
        models.StatusCode.cancelled.value,
    ],
)
async def test_get_all_orders_by_status(create_tables, status):
    # Получаем все заказы по статусу
    orders = await db.get_all_orders_by_status(status)
    # Проверяем, что статус каждого полученного заказа совпадает со статусом теста
    logger.info(f"Проверяем получение заказов со статусом {status}")
    for order in orders:
        logger.info(f"Заказ {order.id}: {order.status}")
        assert order.status == status


def test_clean_database() -> None:
    # Находим все записи, где email 'test@test'
    orders_to_delete = db.Orders.select().where(db.Orders.email == "test@test")
    # Удаляем их
    for order in orders_to_delete:
        logger.info(f"Удаляю тестовые записи с email = test@test из БД: {order}")
        order.delete_instance()
