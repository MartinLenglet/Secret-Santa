from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Event
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from santa.app import create_app
from santa.database import Delivery, EventRecord
from santa.mail import MailResult

SECRET = {"password": "abcdefghijklmnop"}


def create(client, data):
    response = client.post("/api/events", json=data)
    assert response.status_code == 201, response.text
    return response.json()


def draw(client, data):
    event = create(client, data)
    response = client.post(f"/api/events/{event['id']}/draw", json={"revision": event["revision"]})
    assert response.status_code == 200, response.text
    return response.json()


def test_crud_revision_duplicate_and_no_leaks(client, data):
    event = create(client, data)
    path = f"/api/events/{event['id']}"
    data["budget"] = 20
    updated = client.put(path, json={"revision": 1, "data": data})
    assert updated.status_code == 200
    assert updated.json()["revision"] == 2
    assert client.put(path, json={"revision": 1, "data": data}).status_code == 409
    assert client.post(path + "/draw", json={"revision": 1}).status_code == 409
    assert client.post(path + "/draw", json={"revision": 2}).status_code == 200
    assert client.post(path + "/draw", json={"revision": 3}).status_code == 409
    assert client.put(path, json={"revision": 3, "data": data}).status_code == 409
    public = client.get(path).json()
    assert public["state"] == "drawn"
    assert public["counts"] == {"pending": 4}
    assert "recipient" not in client.get(path).text
    assert "recipient" not in client.get(path + "/deliveries").text
    assert client.post(path + "/reveal", json={}).status_code == 422
    assert client.post(path + "/reveal", json={"confirm": False}).status_code == 422
    revealed = client.post(path + "/reveal", json={"confirm": True}).json()
    assert len(revealed) == 4
    assert all(item["giver"] != item["recipient"] for item in revealed)
    copied = client.post(path + "/duplicate", json={"confirm": True}).json()
    assert copied["state"] == "draft"
    assert copied["counts"] == {}
    assert copied["data"]["participants"] == data["participants"]
    assert client.request("DELETE", path, json={"confirm": True}).status_code == 200
    assert client.get(path).status_code == 404
    assert len(client.get("/api/events").json()) == 1


@pytest.mark.parametrize(
    "kind",
    [
        "duplicate_email",
        "duplicate_id",
        "missing_member",
        "bad_group",
        "bad_sender",
        "unknown_tag",
        "bad_braces",
        "header_newline",
        "name_newline",
        "negative_budget",
        "too_many",
    ],
)
def test_invalid_config(client, data, kind):
    if kind == "duplicate_email":
        data["participants"][1]["email"] = data["participants"][0]["email"].upper()
    elif kind == "duplicate_id":
        data["participants"][1]["id"] = data["participants"][0]["id"]
    elif kind == "missing_member":
        data["groups"] = [
            {
                "id": str(uuid4()),
                "name": "Couple",
                "members": [data["participants"][0]["id"], str(uuid4())],
            }
        ]
    elif kind == "bad_group":
        data["groups"] = [{"id": str(uuid4()), "name": "Couple", "members": []}]
    elif kind == "bad_sender":
        data["sender"] = "organisateur@example.com"
    elif kind == "unknown_tag":
        data["body"] = "Bonjour {{inconnu}}"
    elif kind == "bad_braces":
        data["body"] = "Bonjour {{participant_nom}"
    elif kind == "header_newline":
        data["subject"] = "Bonjour\r\nBcc: other@example.com"
    elif kind == "name_newline":
        data["participants"][0]["name"] = "Camille\nBcc: other@example.com"
    elif kind == "negative_budget":
        data["budget"] = -1
    elif kind == "too_many":
        data["participants"] = [
            {"id": str(uuid4()), "name": f"p{i}", "email": f"p{i}@example.com"} for i in range(201)
        ]
    assert client.post("/api/events", json=data).status_code == 422


def test_impossible_draw_rolls_back(client, data):
    data["groups"] = [
        {
            "id": str(uuid4()),
            "name": "Tout le monde",
            "members": [p["id"] for p in data["participants"]],
        }
    ]
    event = create(client, data)
    path = f"/api/events/{event['id']}"
    assert not client.post("/api/validate", json=data).json()["possible"]
    assert client.post(path + "/draw", json={"revision": 1}).status_code == 422
    assert client.get(path).json()["state"] == "draft"
    data["groups"] = []
    assert client.post("/api/validate", json=data).json()["possible"]


def test_preview_test_and_successful_delivery(client, data, sent):
    preview = client.post("/api/preview", json=data).json()
    assert "Camille" in preview["body"]
    assert "Alex" in preview["body"]
    assert "Non précisé" in preview["body"]
    assert "HO ! HO ! HOOO !" in preview["html"]
    assert "data:image/gif;base64," in preview["html"]
    event = draw(client, data)
    path = f"/api/events/{event['id']}"
    assert client.post(path + "/test-mail", json=SECRET).json()["status"] == "accepted"
    assert sent[0]["To"] == data["sender"]
    assert sent[0]["Subject"].startswith("[TEST")
    assert "Camille" in sent[0].get_body(preferencelist=("html",)).get_content()
    assert "Alex" in sent[0].get_body(preferencelist=("html",)).get_content()
    response = client.post(path + "/send", json=SECRET)
    assert response.json()["state"] == "sent"
    assert response.json()["counts"] == {"accepted": 4}
    assert len(sent) == 5
    assert len({message["To"] for message in sent[1:]}) == 4
    assert all(len(message.get_all("To")) == 1 for message in sent)
    assert all(message.get_body(preferencelist=("html",)) is not None for message in sent)
    assert client.post(path + "/send", json=SECRET).status_code == 409
    assert client.get(path).headers["cache-control"] == "no-store"
    assert "abcdefghijklmnop" not in client.get("/api/events").text


def test_partial_retry_without_redraw(tmp_path, data):
    calls = []

    def mailer(sender, password, message):
        calls.append(message)
        return MailResult("failed", "Quota Gmail") if len(calls) == 2 else MailResult("accepted")

    with TestClient(create_app(tmp_path / "partial.sqlite3", mailer)) as client:
        event = draw(client, data)
        path = f"/api/events/{event['id']}"
        original = client.post(path + "/reveal", json={"confirm": True}).json()
        assert client.post(path + "/send", json=SECRET).json()["state"] == "partial"
        result = client.post(path + "/send", json=SECRET).json()
        assert result["state"] == "sent"
        assert len(calls) == 5
        assert calls[0]["To"] not in [message["To"] for message in calls[2:]]
        assert client.post(path + "/reveal", json={"confirm": True}).json() == original


def test_uncertain_needs_confirmation(tmp_path, data):
    calls = []

    def mailer(*args):
        calls.append(args[-1])
        return (
            MailResult("uncertain", "Connexion perdue")
            if len(calls) == 1
            else MailResult("accepted")
        )

    with TestClient(create_app(tmp_path / "uncertain.sqlite3", mailer)) as client:
        event = draw(client, data)
        path = f"/api/events/{event['id']}"
        first = client.post(path + "/send", json=SECRET).json()
        assert first["counts"]["uncertain"] == 1
        assert client.post(path + "/send", json=SECRET).status_code == 409
        assert len(calls) == 1
        assert client.get(path).json()["state"] == "partial"
        result = client.post(path + "/send", json={**SECRET, "retry_uncertain": True}).json()
        assert result["state"] == "sent"


def test_recovery_and_persistence(tmp_path, data):
    database = tmp_path / "persist.sqlite3"
    application = create_app(database)
    with TestClient(application) as client:
        event = draw(client, data)
        with application.state.sessions.begin() as session:
            session.get(EventRecord, event["id"]).state = "sending"
            session.query(Delivery).filter_by(event_id=event["id"]).first().status = "sending"
    with TestClient(create_app(database)) as client:
        result = client.get(f"/api/events/{event['id']}").json()
        assert result["state"] == "partial"
        assert result["counts"]["uncertain"] == 1


def test_concurrent_send_and_delete_blocked(tmp_path, data):
    started, release = Event(), Event()

    def mailer(*_args):
        started.set()
        assert release.wait(5)
        return MailResult("accepted")

    with TestClient(create_app(tmp_path / "concurrent.sqlite3", mailer)) as client:
        event = draw(client, data)
        path = f"/api/events/{event['id']}"
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(client.post, path + "/send", json=SECRET)
            try:
                assert started.wait(5)
                assert client.post(path + "/send", json=SECRET).status_code == 409
                assert client.request("DELETE", path, json={"confirm": True}).status_code == 409
                assert client.get(path).json()["state"] == "sending"
            finally:
                release.set()
            assert future.result(timeout=5).json()["state"] == "sent"


def test_unexpected_error_is_visible_and_recoverable(tmp_path, data):
    def broken_mailer(*_args):
        raise RuntimeError("Failure during submission")

    with TestClient(create_app(tmp_path / "broken.sqlite3", broken_mailer)) as client:
        event = draw(client, data)
        path = f"/api/events/{event['id']}"
        with pytest.raises(RuntimeError, match="Failure during submission"):
            client.post(path + "/send", json=SECRET)
        assert client.get(path).json()["counts"]["uncertain"] == 1
        assert client.get(path).json()["state"] == "partial"


def test_origin_content_type_and_password_redaction(client, data):
    assert (
        client.post(
            "/api/events", json=data, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    assert client.post("/api/events", content="{}").status_code == 415
    assert client.get("/api/health", headers={"Host": "evil.example"}).status_code == 400
    event = create(client, data)
    password = "do-not-echo-this-password"
    response = client.post(f"/api/events/{event['id']}/test-mail", json={"password": password})
    assert response.status_code == 422
    assert password not in response.text


def test_no_password_in_database_or_logs(client, data, tmp_path, caplog):
    event = draw(client, data)
    client.post(f"/api/events/{event['id']}/send", json=SECRET)
    assert "abcdefghijklmnop" not in caplog.text
    for suffix in ("", "-wal", "-shm"):
        path = tmp_path / ("test.sqlite3" + suffix)
        if path.exists():
            assert b"abcdefghijklmnop" not in path.read_bytes()


def test_draw_requires_sender(client, data):
    data = deepcopy(data)
    data["sender"] = None
    event = create(client, data)
    assert client.post(f"/api/events/{event['id']}/draw", json={"revision": 1}).status_code == 422


def test_second_server_cannot_recover_active_database(tmp_path, data):
    database = tmp_path / "exclusive.sqlite3"
    first = create_app(database)
    with TestClient(first) as client:
        event = draw(client, data)
        with first.state.sessions.begin() as session:
            session.get(EventRecord, event["id"]).state = "sending"
        with pytest.raises(RuntimeError, match="déjà utilisée"):
            with TestClient(create_app(database)):
                pass
        assert client.get(f"/api/events/{event['id']}").json()["state"] == "sending"


def test_concurrent_draw_has_one_winner(client, data):
    event = create(client, data)
    path = f"/api/events/{event['id']}"
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(client.post, path + "/draw", json={"revision": 1}) for _ in range(2)]
    assert sorted(future.result().status_code for future in futures) == [200, 409]
    assert client.get(path).json()["counts"] == {"pending": 4}
