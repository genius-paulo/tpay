import pytest
from src.t_payment.t_payment import TPay
from src.config import settings
from src.db_infra import db
from loguru import logger
from aiogram.types import Message


@pytest.fixture
def get_client() -> TPay:
    """Создаем клиента T-Pay: передаем ему креды, получаем доступ к методам"""
    return TPay(settings.tpay_term_key, settings.tpay_pass)


@pytest.fixture
def create_tables() -> None:
    """Тесты могут выполняться и без готовых таблиу в БД.
    Нужно проверить, существует ли нужная таблица, и создать ее, если нет"""
    db_name = db.Orders._meta.table_name
    if not db.db.table_exists(db_name):
        db.create_tables(db.db, db.Orders)


@pytest.fixture
def change_polling_setting() -> settings:
    """Для проверки полинга достаточно несколько секунд,
    а по умолчанию он может работать и по полчаса.
    Поэтому на время обновляем настройки полинга."""
    max_attempts_default = settings.t_pay.max_attempts
    settings.t_pay.max_attempts = 3
    logger.info(f"Изменили настройки полинга: {settings.t_pay.max_attempts=}")
    yield settings
    settings.t_pay.max_attempts = max_attempts_default
    logger.info(f"Вернули настройки полинга на место: {settings.t_pay.max_attempts=}")


@pytest.fixture
def create_tg_message() -> Message:
    mock_tg_message = Message(
        # Основные данные сообщения
        message_id=12345,
        from_user={
            "id": 542570177,
            "is_bot": False,
            "first_name": "Иван",
            "last_name": "Иванов",
            "username": "genius_paulo",
            "language_code": "ru",
        },
        chat={
            "id": 542570177,
            "type": "private",  # Возможные типы: private, group, supergroup, channel
            "title": "Мой чат",
            "username": None,
            "first_name": "Иван",
            "last_name": "Иванов",
        },
        date=1600000000,  # Время отправки сообщения (timestamp)
        text="Привет! Как дела?",  # Текст сообщения
    )
    return mock_tg_message
