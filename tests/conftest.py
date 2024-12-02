import pytest
from t_payment.t_payment import TPay
from config import settings


@pytest.fixture
def get_client():
    return TPay(settings.tpay_term_key, settings.tpay_pass)
