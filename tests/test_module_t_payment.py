from src.t_payment.models import Order
from src.t_payment import models
import pytest
from unittest.mock import patch
from loguru import logger
import json


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.parametrize(
    "amount, customer_key, email, id",
    [(100, 542570177, "test@test", "test06762673-4a6a-7a2a-8000-e7f50d0bf386")],
)
async def test_create_order(get_client, amount, customer_key, email, id):
    """Тестируем создание заказа в TPay. Ответ API заменяем на мок"""
    with patch("src.t_payment.t_payment._send_request") as mock_create_order_link:
        mock_response_data = f"""
        {{
                "Success": true,
                "ErrorCode": "0",
                "TerminalKey": "123456DEMO",
                "Status": "NEW",
                "PaymentId": "123456",
                "OrderId": "{id}",
                "Amount": "{amount}",
                "PaymentURL": "https://securepayments.tinkoff.ru/testCM63WT"
        }}
        """
        mock_create_order_link.return_value = json.loads(mock_response_data)

        # Создаем заказ в системе и проверяем, что он создался, по наличию ссылки
        test_order = Order(amount=amount, customer_key=customer_key, email=email, id=id)
        order = await get_client.create_order_link(test_order)
        logger.info(f"The mock object url: {order.url}")
        assert order.url is not None


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.parametrize(
    "amount, customer_key, email, id, payment_id",
    [
        (
            100,
            542570177,
            "test@test",
            "test06761d58-139d-71c3-8000-d17cc1fd2289",
            "5516169993",
        )
    ],
)
async def test_once_check_order(
    get_client, amount, customer_key, email, id, payment_id
):
    with patch("src.t_payment.t_payment._send_request") as mock_check_order:
        #  Создаем мок реального овтета на запрос проверки платежа
        mock_response_data = f"""
        {{
          "Success": true,
          "ErrorCode": "0",
          "Message": "OK",
          "TerminalKey": "12345DEMO",
          "Status": "NEW",
          "PaymentId": "{payment_id}",
          "OrderId": "{id}",
          "Params": [
            {{
              "Key": "Route",
              "Value": "ACQ"
            }}
          ],
          "Amount": "{amount}"
        }}
        """
        mock_check_order.return_value = json.loads(mock_response_data)

        # Создаем объект заказа
        test_order = Order(
            amount=amount,
            customer_key=customer_key,
            email=email,
            id=id,
            payment_id=payment_id,
        )

        # Отправляем запрос, который должен отработать с моком
        checked_order = await get_client.check_order(test_order)
        # Проверяем совпадение id изначального и возвращенного заказов
        assert checked_order.id == test_order.id


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.parametrize(
    "amount, customer_key, email, id, payment_id, status",
    [
        (
            100,
            542570177,
            "test@test",
            "test06761d58-139d-71c3-8000-d17cc1fd2289",
            "5516169993",
            models.StatusCode.new.value,
        ),
        (
            100,
            542570177,
            "test@test",
            "test06761d58-139d-71c3-8000-d17cc1fd2289",
            "5516169993",
            models.StatusCode.confirmed.value,
        ),
        (
            100,
            542570177,
            "test@test",
            "test06761d58-139d-71c3-8000-d17cc1fd2289",
            "5516169993",
            models.StatusCode.max_attempts.value,
        ),
        (
            100,
            542570177,
            "test@test",
            "test06761d58-139d-71c3-8000-d17cc1fd2289",
            "5516169993",
            models.StatusCode.cancelled.value,
        ),
    ],
)
async def test_polling_check_order(
    get_client,
    change_polling_setting,
    amount,
    customer_key,
    email,
    id,
    payment_id,
    status,
):
    with patch("src.t_payment.t_payment._send_request") as mock_check_order:
        #  Создаем мок реального ответа на запрос проверки платежа
        mock_response_data = f"""
        {{
          "Success": true,
          "ErrorCode": "0",
          "Message": "OK",
          "TerminalKey": "12345DEMO",
          "Status": "{status}",
          "PaymentId": "{payment_id}",
          "OrderId": "{id}",
          "Params": [
            {{
              "Key": "Route",
              "Value": "ACQ"
            }}
          ],
          "Amount": "{amount}"
        }}
        """
        mock_check_order.return_value = json.loads(mock_response_data)

        # Создаем объект заказа
        test_order = Order(
            amount=amount,
            customer_key=customer_key,
            email=email,
            id=id,
            payment_id=payment_id,
        )

        # Отправляем запрос, который должен отработать с моком
        checked_order = await get_client.check_order_polling(test_order)
        assert checked_order.status in (
            models.StatusCode.max_attempts.value,
            models.StatusCode.confirmed.value,
            models.StatusCode.cancelled.value,
        )


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.parametrize(
    "amount, customer_key, email, id, payment_id",
    [
        (
            100,
            542570177,
            "test@test",
            "test06761d58-139d-71c3-8000-d17cc1fd2289",
            "5516169993",
        )
    ],
)
async def test_cancel_order(get_client, amount, customer_key, email, id, payment_id):
    with patch("src.t_payment.t_payment._send_request") as mock_cancel_order:
        # Создаем мок реального ответа на запрос отмены платежа
        mock_response_data = f"""
        {{
                "Success": true,
                "ErrorCode": "0",
                "TerminalKey": "12345DEMO",
                "Status": "CANCELED",
                "PaymentId": "{payment_id}",
                "OrderId": "{id}",
                "OriginalAmount": {amount},
                "NewAmount": 0
                }}
        """
        mock_cancel_order.return_value = json.loads(mock_response_data)

        # Создаем объект заказа
        test_order = Order(
            amount=amount,
            customer_key=customer_key,
            email=email,
            id=id,
            payment_id=payment_id,
        )
        # Отменяем заказ после теста и проверяем совпадение статусов изначального и возвращенного заказов
        canceled_order = await get_client.cancel_payment(test_order)
        assert canceled_order.status is not models.StatusCode.cancelled.value
