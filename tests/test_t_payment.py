import asyncio

# TODO: Нужно проверить создание платежа на разные типы данных: строка, число и т.д. Я точно проверил их не все


def test_create_order(get_client):
    order_obj = asyncio.run(get_client.create_order_link(amount=1000, customer_key=12345))
    final_order = asyncio.run(get_client.check_order_polling(order_obj))
    print(f'The final order is: {final_order}')
