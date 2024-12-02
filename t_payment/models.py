class Model(object):
    """Класс для объектов CLoudPayments"""

    @classmethod
    def from_dict(cls, model_dict):
        raise NotImplementedError

    def __repr__(self):
        state = ['%s=%s' % (k, repr(v)) for (k, v) in vars(self).items()]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(state))


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
    — order_id — ID заказа для нас и для TPay
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

    def __init__(self, amount, customer_key, email, description='Пополнение аккаунта Voicee', receipt=None,
                 status='CREATED', order_id=None, url=None, payment_id=None, created=None):
        """Метод инициализации"""
        super(Order, self).__init__()
        self.amount = amount
        self.customer_key = customer_key
        self.email = email
        self.receipt = receipt
        self.payment_id = payment_id
        self.description = description
        self.order_id = order_id
        self.url = url
        self.status = status
        self.created = created

    @classmethod
    def from_dict(cls, order_dict):
        """Преобразует элементы словаря, который передает TPay в атрибуты инстанса"""
        return cls(order_dict['Amount'],
                   order_dict['CustomerKey'],
                   order_dict['Receipt'],
                   order_dict['Description'])
