from collections import Counter
from collections.abc import Callable
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from filelock import FileLock, Timeout
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session, sessionmaker
from starlette.middleware.trustedhost import TrustedHostMiddleware

from santa.database import (
    Delivery,
    EventRecord,
    default_database,
    open_database,
    recover_interrupted,
)
from santa.mail import MailResult, make_message, render, send_gmail
from santa.matching import feasibility, matching
from santa.schemas import (
    Confirmation,
    Credentials,
    DrawRequest,
    EventData,
    EventView,
    SaveEvent,
    SendRequest,
)


def get_event(session: Session, event_id: str) -> EventRecord:
    record = session.get(EventRecord, event_id)
    if record is None:
        raise HTTPException(404, "Événement introuvable.")
    return record


def deliveries(session: Session, event_id: str) -> list[Delivery]:
    return list(session.scalars(select(Delivery).where(Delivery.event_id == event_id)))


def view(session: Session, record: EventRecord) -> EventView:
    counts = dict(Counter(item.status for item in deliveries(session, record.id)))
    return EventView(
        id=record.id, revision=record.revision, state=record.state, data=record.data, counts=counts
    )


def create_app(database: Path | None = None, mailer: Callable = send_gmail) -> FastAPI:
    database_path = (database or default_database()).resolve()
    engine = open_database(database_path)
    sessions = sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            with FileLock(str(database_path) + ".lock", timeout=0):
                recover_interrupted(sessions)
                yield
        except Timeout as exc:
            raise RuntimeError(
                "Cette base est déjà utilisée par un serveur Secret Santa. "
                "Arrêtez l'autre serveur avant de continuer."
            ) from exc
        finally:
            engine.dispose()

    app = FastAPI(title="Secret Santa privé", lifespan=lifespan)
    app.state.sessions = sessions
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"]
    )

    @app.middleware("http")
    async def local_requests(request: Request, call_next):
        origin = request.headers.get("origin")
        allowed = {
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        }
        if origin is not None and origin not in allowed:
            return JSONResponse({"detail": "Origine non autorisée."}, status_code=403)
        if request.method in {"POST", "PUT", "DELETE", "PATCH"}:
            if request.headers.get("content-type", "").split(";")[0] != "application/json":
                return JSONResponse({"detail": "Une requête JSON est requise."}, status_code=415)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError):
        errors = [
            {"loc": error["loc"], "msg": error["msg"], "type": error["type"]}
            for error in exc.errors()
        ]
        return JSONResponse({"detail": errors}, status_code=422)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/events", response_model=list[EventView])
    def list_events():
        with sessions() as session:
            return [view(session, record) for record in session.scalars(select(EventRecord))]

    @app.post("/api/events", response_model=EventView, status_code=201)
    def new_event(data: EventData):
        with sessions.begin() as session:
            record = EventRecord(id=str(uuid4()), data=data.model_dump(mode="json"))
            session.add(record)
            session.flush()
            return view(session, record)

    @app.get("/api/events/{event_id}", response_model=EventView)
    def read_event(event_id: str):
        with sessions() as session:
            return view(session, get_event(session, event_id))

    @app.put("/api/events/{event_id}", response_model=EventView)
    def save_event(event_id: str, payload: SaveEvent):
        with sessions.begin() as session:
            get_event(session, event_id)
            result = session.execute(
                update(EventRecord)
                .where(
                    EventRecord.id == event_id,
                    EventRecord.state == "draft",
                    EventRecord.revision == payload.revision,
                )
                .values(data=payload.data.model_dump(mode="json"), revision=payload.revision + 1)
            )
            if result.rowcount != 1:
                raise HTTPException(409, "Brouillon modifié ailleurs ou tirage déjà verrouillé.")
            session.expire_all()
            return view(session, get_event(session, event_id))

    @app.delete("/api/events/{event_id}")
    def remove_event(event_id: str, payload: Confirmation):
        with sessions.begin() as session:
            get_event(session, event_id)
            result = session.execute(
                delete(EventRecord).where(
                    EventRecord.id == event_id, EventRecord.state != "sending"
                )
            )
            if result.rowcount != 1:
                raise HTTPException(409, "Un envoi est en cours.")
        return {"deleted": payload.confirm}

    @app.post("/api/events/{event_id}/duplicate", response_model=EventView, status_code=201)
    def duplicate(event_id: str, _payload: Confirmation):
        with sessions.begin() as session:
            source = get_event(session, event_id)
            data = EventData.model_validate(source.data)
            data.name = data.name[:110] + " (copie)"
            record = EventRecord(id=str(uuid4()), data=data.model_dump(mode="json"))
            session.add(record)
            session.flush()
            return view(session, record)

    @app.post("/api/validate")
    def validate(data: EventData):
        return feasibility(data)

    @app.post("/api/preview")
    def preview(data: EventData):
        return render(data)

    @app.post("/api/events/{event_id}/draw", response_model=EventView)
    def draw(event_id: str, payload: DrawRequest):
        with sessions.begin() as session:
            get_event(session, event_id)
            claimed = session.execute(
                update(EventRecord)
                .where(
                    EventRecord.id == event_id,
                    EventRecord.state == "draft",
                    EventRecord.revision == payload.revision,
                )
                .values(state="drawn", revision=payload.revision + 1)
            )
            if claimed.rowcount != 1:
                raise HTTPException(409, "Brouillon périmé ou tirage déjà effectué.")
            session.expire_all()
            record = get_event(session, event_id)
            data = EventData.model_validate(record.data)
            if data.sender is None:
                raise HTTPException(422, "Renseignez l'adresse Gmail expéditrice avant le tirage.")
            assignments = matching(data, randomize=True)
            if assignments is None:
                raise HTTPException(422, feasibility(data)["message"])
            for giver, recipient in assignments.items():
                session.add(Delivery(event_id=event_id, giver=giver, recipient=recipient))
            session.flush()
            return view(session, record)

    @app.post("/api/events/{event_id}/reveal")
    def reveal(event_id: str, _payload: Confirmation):
        with sessions() as session:
            record = get_event(session, event_id)
            people = {str(person["id"]): person["name"] for person in record.data["participants"]}
            return [
                {"giver": people[item.giver], "recipient": people[item.recipient]}
                for item in deliveries(session, event_id)
            ]

    @app.get("/api/events/{event_id}/deliveries")
    def delivery_status(event_id: str):
        with sessions() as session:
            record = get_event(session, event_id)
            people = {str(person["id"]): person["name"] for person in record.data["participants"]}
            return [
                {"giver": people[item.giver], "status": item.status, "error": item.error}
                for item in deliveries(session, event_id)
            ]

    @app.post("/api/events/{event_id}/test-mail")
    def test_mail(event_id: str, credentials: Credentials):
        with sessions() as session:
            data = EventData.model_validate(get_event(session, event_id).data)
        if data.sender is None:
            raise HTTPException(422, "Renseignez et enregistrez votre adresse Gmail.")
        result: MailResult = mailer(
            str(data.sender),
            credentials.password.get_secret_value(),
            make_message(data, str(data.sender), test=True),
        )
        return {"status": result.status, "error": result.error}

    @app.post("/api/events/{event_id}/send", response_model=EventView)
    def send(event_id: str, credentials: SendRequest):
        with sessions.begin() as session:
            get_event(session, event_id)
            claimed = session.execute(
                update(EventRecord)
                .where(
                    EventRecord.id == event_id,
                    EventRecord.state.in_(["drawn", "partial"]),
                )
                .values(state="sending")
            )
            if claimed.rowcount != 1:
                raise HTTPException(409, "Envoi déjà en cours, terminé, ou tirage non effectué.")
            session.expire_all()
            data = EventData.model_validate(get_event(session, event_id).data)
            items = deliveries(session, event_id)
            if (
                any(item.status == "uncertain" for item in items)
                and not credentials.retry_uncertain
            ):
                raise HTTPException(
                    409, "Confirmez le risque de doublon pour les envois incertains."
                )
            pending_ids = [item.id for item in items if item.status != "accepted"]
        people = {str(person.id): person for person in data.participants}
        try:
            for delivery_id in pending_ids:
                with sessions.begin() as session:
                    item = session.get(Delivery, delivery_id)
                    assert item is not None
                    item.status, item.error = "sending", None
                    message = make_message(
                        data,
                        str(people[item.giver].email),
                        people[item.giver].name,
                        people[item.recipient].name,
                    )
                result = mailer(str(data.sender), credentials.password.get_secret_value(), message)
                with sessions.begin() as session:
                    item = session.get(Delivery, delivery_id)
                    assert item is not None
                    item.status, item.error = result.status, result.error
                if result.status != "accepted":
                    break
        finally:
            with sessions.begin() as session:
                for item in deliveries(session, event_id):
                    if item.status == "sending":
                        item.status = "uncertain"
                        item.error = "Envoi interrompu : vérifiez Gmail avant de réessayer."
                record = get_event(session, event_id)
                record.state = (
                    "sent"
                    if all(item.status == "accepted" for item in deliveries(session, event_id))
                    else "partial"
                )
        with sessions() as session:
            return view(session, get_event(session, event_id))

    dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if dist.is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/")
        def index():
            return FileResponse(dist / "index.html")

    return app
