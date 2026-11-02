from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from santa.app import create_app
from santa.mail import MailResult
from santa.schemas import EventData


@pytest.fixture
def data():
    return EventData(
        name="Noël entre amis",
        sender="organisateur@gmail.com",
        participants=[
            {"id": str(uuid4()), "name": name, "email": f"person{index}@example.com"}
            for index, name in enumerate(["Camille", "Alex", "Sam", "Lou"])
        ],
    ).model_dump(mode="json")


@pytest.fixture
def sent():
    return []


@pytest.fixture
def client(tmp_path, sent):
    def mailer(sender, password, message):
        assert sender == "organisateur@gmail.com"
        assert password == "abcdefghijklmnop"
        sent.append(message)
        return MailResult("accepted")

    with TestClient(create_app(tmp_path / "test.sqlite3", mailer)) as test_client:
        yield test_client
