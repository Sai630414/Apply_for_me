import os
import pytest
from starlette.testclient import TestClient

os.environ["APP_ENV"] = "test"
os.environ["DEBUG"] = "true"
os.environ["JWT_SECRET_KEY"] = "test_secret_key_applyforme_12345"

from app.core.config import settings
settings.APP_ENV = "test"

from app.main import app
from app.core.security import create_access_token


@pytest.fixture
def client():
    test_client = TestClient(app, raise_server_exceptions=True)
    yield test_client


@pytest.fixture
def test_user():
    return {
        "_id": "test_user_id_42",
        "email": "applicant@test.com",
        "name": "Alex Applicant",
        "picture": "https://example.com/avatar.png"
    }


@pytest.fixture
def auth_headers(test_user):
    token = create_access_token({
        "sub": test_user["_id"],
        "email": test_user["email"],
        "name": test_user["name"],
        "picture": test_user["picture"]
    })
    return {"Authorization": f"Bearer {token}"}
