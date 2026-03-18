import pytest

from rota_connector.client import RotaConnector
from rota_connector.configs import ROTA_BASE_URL


@pytest.fixture
def connector():
    with RotaConnector(base_url=ROTA_BASE_URL) as client:
        client.set_credentials("test-client-id", "test-client-secret")
        yield client
