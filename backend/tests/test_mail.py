import smtplib
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
from unittest.mock import Mock, patch

import pytest

from santa.mail import make_message, render, send_gmail
from santa.schemas import EventData


class Images(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sources = []

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            self.sources.append(dict(attrs)["src"])


def test_festive_preview_escapes_custom_text_and_keeps_line_breaks(data):
    data.update(
        body='Bonjour {{participant_nom}}\n{{evenement_nom}}\n<script>alert("non")</script>',
        name='<img src="https://example.com/tracker">',
    )
    rendered = render(EventData.model_validate(data), "Léa & Zoé", "Alex")
    assert "Léa & Zoé\n<img src=" in rendered["body"]
    html = rendered["html"]
    assert "Léa &amp; Zoé<br>" in html
    assert "&lt;img src=" in html
    assert "&lt;script&gt;" in html
    assert "<script>" not in html
    images = Images()
    images.feed(html)
    assert len(images.sources) == 2
    assert all(source.startswith("data:image/gif;base64,") for source in images.sources)
    assert "HO ! HO ! HOOO !" in html


@pytest.mark.parametrize("test", [False, True])
def test_festive_mime_message_with_embedded_animated_gifs(data, test):
    event = EventData.model_validate(data)
    message = make_message(event, "person@example.com", "Léa", "Zoé", test=test)
    parsed = BytesParser(policy=policy.default).parsebytes(message.as_bytes())
    assert parsed.get_content_type() == "multipart/alternative"
    text = parsed.get_body(preferencelist=("plain",)).get_content()
    assert text.rstrip() == render(event, "Léa", "Zoé")["body"]
    html = parsed.get_body(preferencelist=("html",)).get_content()
    assert "Léa" in html and "Zoé" in html
    assert "Camille" not in html and "Alex" not in html
    assert str(parsed["Subject"]).startswith("[TEST") == test
    images = Images()
    images.feed(html)
    parts = [part for part in parsed.walk() if part.get_content_type() == "image/gif"]
    assert len(parts) == len(images.sources) == 2
    assert {f"cid:{part['Content-ID'][1:-1]}" for part in parts} == set(images.sources)
    for part in parts:
        assert part.get_content_disposition() == "inline"
        gif = part.get_payload(decode=True)
        assert gif.startswith(b"GIF89a")
        assert b"NETSCAPE2.0" in gif
        assert gif.count(b"\x21\xf9\x04") == 6
    assert "data:image/" not in html
    assert "https://" not in html and "http://" not in html


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
