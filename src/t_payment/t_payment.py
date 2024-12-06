from httpx import AsyncClient
from src.config import settings
import asyncio
import decimal
import json
import hashlib

from src.t_payment.models import StatusCode, Endpoints
from src.t_payment.models import Order

from loguru import logger

# TODO: В будущем скорее всего придется делать возврат средств.
#  Сейчас для этого нет механизма: возвращать деньги и обновлять инфу в бд, нужно вручную.
#  Нужно уточнить процесс и сделать такую функицональность


async def _send_request(endpoint, params=None) -> json:
    """Универсальный внутренний метод для создания асинхронного запроса к API с нужными параметрами"""
    headers = {"Content-Type": "application/json"}
    async with AsyncClient() as async_client:
        async_response = await async_client.post(
            url=settings.t_pay.tpay_url + endpoint,
            headers=headers,
            json=params,
        )
        return async_response.json(parse_float=decimal.Decimal)


class TPay:
    """Класс клиента TPay. Методы:
    create_order_link() — формирует платеж в системе и отдает ссылку для оплаты
    check_order() — разовая проверка статуса платежа
    check_order_polling() — перманентный метод для проверки платежа в формате polling
                            (раз в несколько секунд, определенное количество раз, в зависимости от настроек)
    cancel_payment() — отменяет платеж
    update_order() — обновляет статус-код в инстансе заказа"""

    def __init__(self, tpay_term_key: str, tpay_password: str) -> None:
        self.tpay_term_key = tpay_term_key
        self.tpay_password = tpay_password

    def _generate_token(self, data: dict, mode: str) -> str:
        """Метод для генерации токена, подписывающего запрос
        Mode: init — инициализация платежа, check — проверка, cancel — отмена"""
        params = []
        if mode == Endpoints.init.value:
            # Собираем массив пар Ключ-Значение для создания платежа
            params = [
                ["TerminalKey", data.get("TerminalKey")],
                ["Amount", str(data.get("Amount"))],
                ["OrderId", data.get("OrderId")],
                ["Description", data.get("Description")],
                ["CustomerKey", data.get("CustomerKey")],
            ]
        elif mode in (Endpoints.get_state.value, Endpoints.cancel.value):
            # Собираем массив пар Ключ-Значение
            params = [
                ["TerminalKey", data.get("TerminalKey")],
                ["PaymentId", data.get("PaymentId")],
            ]
        # Добавляем пароль — обязательное требование для формирования нужного токена
        params += [["Password", self.tpay_password]]
        # Сортируем массив по ключам
        sorted_params = sorted(params, key=lambda x: x[0])
        # Конкатенируем значения
        concatenated_values = "".join([value for _, value in sorted_params])
        # Вычисляем SHA-256 хеш
        token = hashlib.sha256(concatenated_values.encode()).hexdigest()
        return token

    async def create_order_link(self, order: Order) -> Order:
        """Метод, который создает заказ в TPay и возвращает объект заказа"""
        endpoint = Endpoints.init.value

        # Заполняем параметры для запроса
        params = {
            "TerminalKey": self.tpay_term_key,
            "Amount": order.amount,  # Сумма в копейках!
            "Description": "Пополнение аккаунта Voicee",
            "OrderId": str(order.id),
            "CustomerKey": str(order.customer_key),
            # Пока только один товар — одно пополнение на какую-то сумму
            "Receipt": {
                # TODO: TPay проверяет почту только по наличию букв и цифр вокруг собаки.
                #  Поэтому нужно дополнительно сделать проверку на нашей стороне
                "Email": order.email,
                "Taxation": settings.t_pay.tax_system,
                "Items": [
                    {
                        "Name": "Пополнение аккаунта Voicee",
                        "Price": order.amount,
                        "Quantity": 1,
                        "Amount": order.amount,
                        "Tax": settings.t_pay.vat,
                    }
                ],
            },
        }
        # Генерируем токен и отправляем запрос
        params["Token"] = await asyncio.to_thread(
            self._generate_token, params, mode=endpoint
        )

        # TODO: Реализовать добавление чека в объект лучше, мб через промежуточную модельку
        order.receipt = params["Receipt"]

        logger.info(f"Sending the request: {params}")
        create_order_response = await _send_request(endpoint, params)
        logger.debug(f"The response: {create_order_response}")

        if create_order_response["Success"]:
            # Выводим id платежа и содержимое ответа для дебага
            logger.info(
                f"The response has been received. Payment id is: {create_order_response['PaymentId']}"
            )
            logger.debug(
                f"The response of {create_order_response['PaymentId']} is: {create_order_response}"
            )

            # Обновляем поля объекта заказа, выводим для дебага
            order.payment_id = create_order_response["PaymentId"]
            order.url = create_order_response["PaymentURL"]
            order.status = create_order_response["Status"]
            logger.debug(f"The order object has been updated: {order}")

            return order

    async def check_order(self, order: Order) -> Order:
        """Метод для разовой проверки платежа.
        Подходит для финальной сверки и полинга, в режиме хуков избыточен"""
        endpoint = Endpoints.get_state.value
        params = {
            "TerminalKey": settings.t_pay.tpay_term_key,
            "PaymentId": order.payment_id,
        }

        # Генерация токена
        params["Token"] = await asyncio.to_thread(
            self._generate_token, params, mode=endpoint
        )

        # Делаем запрос
        checked_order_response = await _send_request(endpoint, params)

        # Обновляем статус платежа в объекте
        order.status = checked_order_response["Status"]
        logger.debug(f"Order has been updated: {checked_order_response}")

        return order

    async def check_order_polling(self, order: Order) -> Order:
        """Метод для проверки платежа в формате polling:
        раз в несколько секунд, какое-то количество раз (в зависимости от настроек).
        Подходит, когда нет возможности работать с хуками и нужно проверять все руками.
        """

        # Проверяем платеж раз в DELAY секунд MAX_ATTEMPTS раз (+1, чтобы начинался с 1 и заканчивался max_attempts)
        for attempt in range(1, settings.t_pay.max_attempts + 1):
            # Вызываем метод разовой проверки статуса заказа
            order = await self.check_order(order)
            logger.info(
                f"Payment {order.payment_id} verification attempt {attempt} "
                f"out of {settings.t_pay.max_attempts} possible: {order.status}"
            )

            # Проверяем на максимальное количество попыток
            if attempt == settings.t_pay.max_attempts:
                logger.info(
                    f"Polling spent the maximum number of attempts ({settings.t_pay.max_attempts})"
                )
                order.status = StatusCode.max_attempts.value
                return order

            elif order.status in (
                StatusCode.rejected.value,
                StatusCode.cancelled.value,
            ):
                logger.info(f"The order has been cancelled. Status: {order.status}")
                return order

            elif order.status == StatusCode.confirmed.value:
                logger.info(f"The order has been confirmed. Status: {order.status}")
                return order

            # Делаем паузу между запросами проверки для polling
            await asyncio.sleep(settings.t_pay.delay)

        return order

    async def cancel_payment(self, order: Order) -> Order:
        """Метод для ручного удаления платежа. Можно удалить платеж после окончания
        попыток проверки в polling-режиме, чтобы точно не пропустить платеж."""
        logger.debug(f"Canceling a payment in the client: {order}")

        endpoint = Endpoints.cancel.value
        params = {
            "TerminalKey": settings.t_pay.tpay_term_key,
            "PaymentId": order.payment_id,
        }
        # Генерируем токен
        params["Token"] = await asyncio.to_thread(
            self._generate_token, params, mode=endpoint
        )

        # Вызываем метод отмены заказа
        checked_order_response = await _send_request(endpoint, params)
        logger.debug(f"The response: {checked_order_response}")

        # Обновляем статус платежа в объекте
        order.status = checked_order_response["Status"]

        logger.info(f"Canceling the payment {order.payment_id}")
        logger.debug(
            f"The response to the cancellation of payment {order.payment_id}: {order}"
        )

        return order
