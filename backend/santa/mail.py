import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from typing import Literal

from santa.mail_theme import CHRISTMAS_GIFS, render_html
from santa.schemas import TOKEN, EventData

Status = Literal["accepted", "failed", "uncertain"]


@dataclass(frozen=True)
class MailResult:
    status: Status
    error: str | None = None


def render(data: EventData, giver: str = "Camille", recipient: str = "Alex") -> dict[str, str]:
    values = {
        "participant_nom": giver,
        "destinataire_nom": recipient,
        "evenement_nom": data.name,
        "budget": f"{data.budget:g} {data.currency}" if data.budget else "Non précisé",
        "date": data.gift_date.strftime("%d/%m/%Y") if data.gift_date else "Non précisée",
    }

    def replace(template: str) -> str:
        return TOKEN.sub(lambda match: values[match.group(1)], template)

    body = replace(data.body)
    return {"subject": replace(data.subject), "body": body, "html": render_html(body)}


def make_message(
    data: EventData, to: str, giver: str = "Camille", recipient: str = "Alex", *, test: bool = False
) -> EmailMessage:
    rendered = render(data, giver, recipient)
    message = EmailMessage()
    message["From"] = formataddr(("Secret Santa", str(data.sender)))
    message["To"] = to
    message["Subject"] = ("[TEST - données fictives] " if test else "") + rendered["subject"]
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid()
    message.set_content(rendered["body"])
    image_ids = {name: make_msgid() for name in CHRISTMAS_GIFS}
    message.add_alternative(
        render_html(
            rendered["body"], {name: f"cid:{cid[1:-1]}" for name, cid in image_ids.items()}
        ),
        subtype="html",
    )
    html_part = message.get_body(preferencelist=("html",))
    assert isinstance(html_part, EmailMessage)
    for name, content in CHRISTMAS_GIFS.items():
        html_part.add_related(
            content,
            maintype="image",
            subtype="gif",
            cid=image_ids[name],
            disposition="inline",
            filename=f"noel-{name}.gif",
        )
    return message


def send_gmail(sender: str, password: str, message: EmailMessage) -> MailResult:
    client: smtplib.SMTP_SSL | None = None
    submitting = False
    try:
        client = smtplib.SMTP_SSL(
            "smtp.gmail.com", 465, timeout=20, context=ssl.create_default_context()
        )
        client.login(sender, password)
        submitting = True
        client.send_message(message)
        return MailResult("accepted")
    except smtplib.SMTPAuthenticationError:
        return MailResult(
            "failed", "Authentification Gmail refusée : vérifiez le mot de passe d'application."
        )
    except smtplib.SMTPRecipientsRefused:
        return MailResult("failed", "Gmail a refusé l'adresse du destinataire.")
    except smtplib.SMTPResponseException:
        return MailResult("failed", "Gmail a refusé l'envoi : vérifiez les quotas et le compte.")
    except (OSError, smtplib.SMTPServerDisconnected):
        return MailResult(
            "uncertain" if submitting else "failed",
            "Connexion Gmail interrompue. "
            "Vérifiez les messages envoyés avant toute nouvelle tentative."
            if submitting
            else "Connexion Gmail impossible : vérifiez le réseau.",
        )
    except smtplib.SMTPException:
        return MailResult(
            "uncertain" if submitting else "failed",
            "Erreur de protocole Gmail. Vérifiez le compte et les messages envoyés.",
        )
    finally:
        if client is not None:
            client.close()
