import smtplib
from unittest.mock import Mock, patch

import pytest

from santa.mail import make_message, render, send_gmail
from santa.schemas import EventData


def test_optional_values_and_non_recursive_substitution(data):
    data.update(budget=25, gift_date="2026-12-24", name="{{destinataire_nom}}")
    rendered = render(EventData.model_validate(data), "Léa", "Zoé")
    assert "25 EUR" in rendered["body"]
    assert "24/12/2026" in rendered["body"]
    assert "{{destinataire_nom}}" in rendered["subject"]
    assert "Léa" in rendered["body"]


@pytest.mark.parametrize(
    ("stage", "exception", "expected"),
    [
        ("connect", OSError("private"), "failed"),
        ("login", smtplib.SMTPAuthenticationError(535, b"private"), "failed"),
        ("send_message", smtplib.SMTPRecipientsRefused({}), "failed"),
        ("send_message", smtplib.SMTPDataError(550, b"quota"), "failed"),
        ("send_message", smtplib.SMTPServerDisconnected("private"), "uncertain"),
        ("send_message", TimeoutError("private"), "uncertain"),
    ],
)
def test_smtp_failures(data, stage, exception, expected):
    client = Mock()
    with patch("santa.mail.smtplib.SMTP_SSL", return_value=client) as factory:
        if stage == "connect":
            factory.side_effect = exception
        else:
            getattr(client, stage).side_effect = exception
        result = send_gmail(
            data["sender"],
            "abcdefghijklmnop",
            make_message(EventData.model_validate(data), "person@example.com"),
        )
    assert result.status == expected
    assert "private" not in result.error
    if stage != "connect":
        client.close.assert_called_once()


def test_tls_host_and_single_recipient(data):
    client = Mock()
    with patch("santa.mail.smtplib.SMTP_SSL", return_value=client) as factory:
        result = send_gmail(
            data["sender"],
            "abcdefghijklmnop",
            make_message(EventData.model_validate(data), "person@example.com"),
        )
    assert result.status == "accepted"
    assert factory.call_args.args == ("smtp.gmail.com", 465)
    context = factory.call_args.kwargs["context"]
    assert context.check_hostname
    assert factory.call_args.kwargs["timeout"] == 20
    client.login.assert_called_once_with(data["sender"], "abcdefghijklmnop")
