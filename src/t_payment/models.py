import datetime
import enum
from uuid_extensions import uuid7


def _create_uuidv7():
    return str(uuid7())


class Model:
    """Класс для объектов TPay"""

    @classmethod
    def from_dict(cls, model_dict):
        raise NotImplementedError

    def __repr__(self):
        state = ["%s=%s" % (k, repr(v)) for (k, v) in vars(self).items()]
        return "%s(%s)" % (self.__class__.__name__, ", ".join(state))


class StatusCode(enum.Enum):
    """Класс статус-кодов, чтобы передавать их в более явном виде.
    Статусы:
    — CREATED — платеж создан у нас, но не в TPay
    — NEW — платеж создан у нас и в TPay
    — CONFIRMED — платеж совершен успешно
    — REJECTED — платеж отклонен пользователем или со стороны TPay
    — CANCELLED — платеж отменен у нас и в TPay
    — MAX_ATTEMPTS — мы закончили проверять платеж, но его статус неизвестен, нужно уточнять вручную
    """

    created: str = "CREATED"
    new: str = "NEW"
    confirmed: str = "CONFIRMED"
    rejected: str = "REJECTED"
    cancelled: str = "CANCELED"
    max_attempts: str = "MAX_ATTEMPTS"


class Order(Model):
    """Класс заказа. Используется для:
    формирования заказа на стороне клиента, создания заказа в TPay,
    синхронизации данных транзакции в TPay с заказом на нашей стороне и в БД.
    Заполняется из словаря с помощью метода from_dict().

    Атрибуты:
    — customer_key — ID в телеге
    — email — почта
    — receipt — позиции чека
    — payment_id — ID платежа в системе TPay
    — description — Описание платежа
    — id — ID заказа для нас и для TPay
    — url — ссылка на платежную форму
    — status — статус заказа
    — created — дата и время создания

    Статусы заказа/платежа:
    — CREATED: заказ создан у нас, но его пока нет в TPay,
    — NEW: заказ успешно создан в TPay,
    — FORM_SHOWED: пользователь открыл и посмотрел форму оплаты,
    — CONFIRMED: платеж успешно оплачен
    — REJECTED: платеж отклонен системой
    — MAX_ATTEMPTS: достигнуто максимальное число проверок
    — CANCELLED: заказ отклонен нами"""

    def __init__(
        self,
        amount: int,
        customer_key: int,
        email: str,
        description: str = "Пополнение аккаунта Voicee",
        receipt: str | None = None,
        status: str = StatusCode.created.value,
        id: str = _create_uuidv7(),
        url: str | None = None,
        payment_id: str | None = None,
        created: datetime.datetime | None = None,
    ):
        self.amount = amount
        self.customer_key = customer_key
        self.email = email
        self.receipt = receipt
        self.payment_id = payment_id
        self.description = description
        self.id = id
        self.url = url
        self.status = status
        self.created = created


class Endpoints(enum.Enum):
    """Модель эндпоинтов для отправки запросов.
    Эндпоинты:
    — Init — инициализация платежа
    — GetState — проверка платежа
    — Cancel — отмена платежа
    """

    init: str = "Init"
    get_state: str = "GetState"
    cancel: str = "Cancel"
