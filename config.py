from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv

load_dotenv()


class AuthData(BaseModel):
    Authorization: str = Field(description="Authorization data")


class Settings(BaseModel):
    # Креды Telegram
    tg_token: str = os.getenv('API_TOKEN')
    skip_updates: str = True

    # Авторизация для TPay
    tpay_term_key: str = os.getenv('TPAY_TERMINAL_KEY')
    tpay_pass: str = os.getenv('TPAY_PASSWORD')

    # Креды организации
    inn: str = os.getenv('INN')
    vat: str = os.getenv('TAX_VAT')
    tax_system: str = os.getenv('TAX_SYS')

    # Креды для бд
    db_name: str = os.getenv('DB_NAME')
    db_user: str = os.getenv('DB_USER')
    db_password: str = os.getenv('DB_PASSWORD')
    db_host: str = os.getenv('DB_HOST')

    # Задержка между проверками платежа и максимальное число попыток
    # Итоговое время ожидания платежа = delay * max_attempts
    delay: int = 3
    max_attempts: int = 100

    # Количество уже существующих заказов в системе TPay
    orders_count: int = int(os.getenv('ORDERS_COUNT'))

    # Уровень отображения логов
    logger_level: str = os.getenv('LOGGER_LEVEL')


settings = Settings()
