import re
from datetime import date
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

DEFAULT_BODY = """Bonjour {{participant_nom}},

Pour {{evenement_nom}}, tu offres un cadeau à : {{destinataire_nom}} !

Budget : {{budget}}
Date : {{date}}

Garde le secret et amuse-toi bien !"""
TAGS = ("participant_nom", "destinataire_nom", "evenement_nom", "budget", "date")
TOKEN = re.compile(r"\{\{([a-z_]+)\}\}")
Name = Annotated[str, Field(min_length=1, max_length=120, pattern=r"^[^\r\n]+$")]


def validate_template(value: str) -> str:
    unknown = set(TOKEN.findall(value)) - set(TAGS)
    remainder = TOKEN.sub("", value)
    if unknown or "{" in remainder or "}" in remainder:
        raise ValueError("Balise inconnue ou invalide. Utilisez les balises proposées.")
    return value


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


class Participant(StrictModel):
    id: UUID
    name: Name
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()


class Group(StrictModel):
    id: UUID
    name: Name
    members: list[UUID] = Field(min_length=2, max_length=200)


class EventData(StrictModel):
    name: Name = "Mon Secret Santa"
    budget: float | None = Field(default=None, gt=0, le=1_000_000)
    currency: Literal["EUR", "USD", "GBP", "CHF", "CAD"] = "EUR"
    gift_date: date | None = None
    sender: EmailStr | None = None
    participants: list[Participant] = Field(default_factory=list, max_length=200)
    groups: list[Group] = Field(default_factory=list, max_length=200)
    subject: str = Field(
        default="Ton Secret Santa : {{evenement_nom}}", min_length=1, max_length=300
    )
    body: str = Field(default=DEFAULT_BODY, min_length=1, max_length=20_000)

    @field_validator("sender")
    @classmethod
    def gmail_sender(cls, value: str | None) -> str | None:
        if value is not None and value.lower().split("@")[1] not in ("gmail.com", "googlemail.com"):
            raise ValueError("Utilisez une adresse Gmail personnelle (@gmail.com).")
        return value.lower() if value else None

    @field_validator("subject")
    @classmethod
    def safe_subject(cls, value: str) -> str:
        if "\r" in value or "\n" in value:
            raise ValueError("L'objet doit tenir sur une seule ligne.")
        return validate_template(value)

    @field_validator("body")
    @classmethod
    def safe_body(cls, value: str) -> str:
        return validate_template(value)

    @model_validator(mode="after")
    def valid_members(self) -> Self:
        ids = {person.id for person in self.participants}
        emails = {person.email for person in self.participants}
        if len(ids) != len(self.participants) or len(emails) != len(self.participants):
            raise ValueError(
                "Les identifiants et adresses mail des participants doivent être uniques."
            )
        if len({group.id for group in self.groups}) != len(self.groups):
            raise ValueError("Les identifiants de groupes doivent être uniques.")
        for group in self.groups:
            if len(set(group.members)) != len(group.members) or not set(group.members) <= ids:
                raise ValueError("Un groupe contient un membre absent ou en double.")
        return self


class SaveEvent(StrictModel):
    revision: int = Field(ge=1)
    data: EventData


class DrawRequest(StrictModel):
    revision: int = Field(ge=1)


class Confirmation(StrictModel):
    confirm: Literal[True]


class Credentials(StrictModel):
    password: SecretStr

    @field_validator("password")
    @classmethod
    def app_password(cls, value: SecretStr) -> SecretStr:
        secret = value.get_secret_value().replace(" ", "")
        if not re.fullmatch(r"[a-zA-Z]{16}", secret):
            raise ValueError("Saisissez le mot de passe d'application Google de 16 lettres.")
        return SecretStr(secret)


class SendRequest(Credentials):
    retry_uncertain: bool = False


class EventView(StrictModel):
    id: str
    revision: int
    state: str
    data: EventData
    counts: dict[str, int]
