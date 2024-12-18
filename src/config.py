from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Extra


class BaseSettingsWithConfig(BaseSettings):
    """Родительский класс с настройками .env и экстра-атрибутов.
    Нужен, чтобы унаследовать эти настройки для всех классов настроек дальше"""

    model_config = SettingsConfigDict(
        env_file="../.env", env_file_encoding="utf-8", extra="allow"
    )


class TgSettings(BaseSettingsWithConfig):
    """Модель настроек телеги"""

    # Креды Telegram
    tg_token: str
    skip_updates: bool = True


class DBSettings(BaseSettingsWithConfig):
    """Модель настроек БД"""

    # Креды для бд
    db_name: str
    db_user: str
    db_password: str
    db_host: str


class TPaySettings(BaseSettingsWithConfig):
    """Модель настроек для TPay"""

    # Авторизация для TPay
    # URL для обращения к API TPay
    tpay_url: str
    tpay_term_key: str
    tpay_pass: str
    # Креды организации
    vat: str
    tax_system: str
    # Задержка между проверками платежа и максимальное число попыток
    # Итоговое время ожидания платежа = delay * max_attempts
    delay: int
    max_attempts: int


class Settings(BaseSettingsWithConfig):
    """Все настройки в одной точке входа"""

    # Уровень отображения логов
    logger_level: str

    tg: TgSettings = TgSettings()
    db: DBSettings = DBSettings()
    t_pay: TPaySettings = TPaySettings()


settings = Settings()
