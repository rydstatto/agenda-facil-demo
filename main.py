from __future__ import annotations

import hmac
import os
import re
import sqlite3
from contextlib import asynccontextmanager, closing
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = Path(os.getenv("AGENDA_DB_PATH", BASE_DIR / "agenda.db"))
BUSINESS_CLOSE = time(18, 0)
SLOT_STARTS = (time(9, 0), time(10, 0), time(11, 30), time(13, 0), time(14, 0), time(15, 30), time(16, 30))
MAX_BOOKING_DAYS = 90

SERVICES = {
    "manicure-clasica": {
        "id": "manicure-clasica",
        "name": "Manicure clásica",
        "description": "Limado, cuidado de cutículas y esmaltado",
        "price": 18,
        "duration_minutes": 45,
    },
    "manicure-gel": {
        "id": "manicure-gel",
        "name": "Manicure gel",
        "description": "Color duradero y acabado brillante",
        "price": 28,
        "duration_minutes": 60,
    },
    "manicure-completo": {
        "id": "manicure-completo",
        "name": "Manicure + pedicure",
        "description": "Un cuidado completo de manos y pies",
        "price": 42,
        "duration_minutes": 90,
    },
}

@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Agenda Fácil API", version="1.0.0", lifespan=lifespan)
security = HTTPBasic()
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "https://rydstatto.github.io,http://localhost:8000,http://127.0.0.1:8000",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


def connect_database() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


def initialize_database() -> None:
    with closing(connect_database()) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                customer_email TEXT NOT NULL,
                customer_phone TEXT,
                service_id TEXT NOT NULL,
                service_name TEXT NOT NULL,
                price INTEGER NOT NULL,
                duration_minutes INTEGER NOT NULL,
                booking_date TEXT NOT NULL,
                booking_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'confirmed'
                    CHECK (status IN ('confirmed', 'cancelled')),
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS bookings_date_status ON bookings (booking_date, status)"
        )
        connection.commit()


def authenticate_admin(
    credentials: Annotated[HTTPBasicCredentials, Depends(security)],
) -> str:
    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El acceso de administración no está configurado en el servidor.",
        )
    valid_username = hmac.compare_digest(
        credentials.username.encode("utf-8"), username.encode("utf-8")
    )
    valid_password = hmac.compare_digest(
        credentials.password.encode("utf-8"), password.encode("utf-8")
    )
    if not (valid_username and valid_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas.",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


class BookingRequest(BaseModel):
    customer_name: str = Field(min_length=2, max_length=100)
    customer_email: str = Field(min_length=5, max_length=254)
    customer_phone: str | None = Field(default=None, max_length=30)
    service_id: str
    date: date
    time: str

    @field_validator("customer_name", "customer_email", "service_id", "time", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("customer_email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Ingresa un correo electrónico válido.")
        return value

    @field_validator("customer_phone", mode="before")
    @classmethod
    def normalize_phone(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value


def validate_booking_window(booking_date: date) -> None:
    today = date.today()
    if booking_date < today or booking_date > today + timedelta(days=MAX_BOOKING_DAYS):
        raise HTTPException(
            status_code=422,
            detail=f"Elige una fecha entre hoy y los próximos {MAX_BOOKING_DAYS} días.",
        )
    if booking_date.weekday() == 6:
        raise HTTPException(
            status_code=422,
            detail="El estudio no atiende los domingos.",
        )


def get_requested_slot(slot_value: str) -> time:
    try:
        requested = time.fromisoformat(slot_value)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="El horario seleccionado no es válido.",
        ) from exc
    if requested not in SLOT_STARTS:
        raise HTTPException(
            status_code=422,
            detail="Ese horario no está disponible.",
        )
    return requested


def booking_overlaps(
    connection: sqlite3.Connection,
    booking_date: date,
    start: time,
    duration_minutes: int,
) -> bool:
    requested_start = datetime.combine(booking_date, start)
    requested_end = requested_start + timedelta(minutes=duration_minutes)
    existing_bookings = connection.execute(
        """
        SELECT booking_time, duration_minutes
        FROM bookings
        WHERE booking_date = ? AND status = 'confirmed'
        """,
        (booking_date.isoformat(),),
    ).fetchall()
    for booking in existing_bookings:
        existing_start_time = time.fromisoformat(booking["booking_time"])
        existing_start = datetime.combine(booking_date, existing_start_time)
        existing_end = existing_start + timedelta(minutes=booking["duration_minutes"])
        if requested_start < existing_end and existing_start < requested_end:
            return True
    return False


def serialize_booking(row: sqlite3.Row) -> dict[str, object]:
    return {
        "id": row["id"],
        "customer_name": row["customer_name"],
        "customer_email": row["customer_email"],
        "customer_phone": row["customer_phone"],
        "service_id": row["service_id"],
        "service_name": row["service_name"],
        "price": row["price"],
        "duration_minutes": row["duration_minutes"],
        "date": row["booking_date"],
        "time": row["booking_time"],
        "status": row["status"],
        "created_at": row["created_at"],
    }


@app.get("/api/services")
def list_services() -> list[dict[str, object]]:
    return list(SERVICES.values())


@app.get("/healthz")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/availability")
def get_availability(
    booking_date: Annotated[date, Query(alias="date")],
    service_id: str,
) -> dict[str, object]:
    service = SERVICES.get(service_id)
    if service is None:
        raise HTTPException(status_code=404, detail="El servicio seleccionado no existe.")
    validate_booking_window(booking_date)
    available_slots = []
    with closing(connect_database()) as connection:
        for slot in SLOT_STARTS:
            slot_end = (datetime.combine(booking_date, slot) + timedelta(minutes=service["duration_minutes"])).time()
            if slot_end > BUSINESS_CLOSE:
                continue
            available_slots.append(
                {
                    "time": slot.strftime("%H:%M"),
                    "available": not booking_overlaps(
                        connection, booking_date, slot, service["duration_minutes"]
                    ),
                }
            )
    return {"date": booking_date.isoformat(), "slots": available_slots}


@app.post("/api/bookings", status_code=status.HTTP_201_CREATED)
def create_booking(request: BookingRequest) -> dict[str, object]:
    validate_booking_window(request.date)
    requested_time = get_requested_slot(request.time)
    service = SERVICES.get(request.service_id)
    if service is None:
        raise HTTPException(status_code=404, detail="El servicio seleccionado no existe.")
    end_time = (datetime.combine(request.date, requested_time) + timedelta(minutes=service["duration_minutes"])).time()
    if end_time > BUSINESS_CLOSE:
        raise HTTPException(
            status_code=422,
            detail="Ese servicio no cabe completo en el horario de atención.",
        )

    with closing(connect_database()) as connection:
        connection.execute("BEGIN IMMEDIATE")
        if booking_overlaps(connection, request.date, requested_time, service["duration_minutes"]):
            connection.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ese horario acaba de ocuparse. Elige otro horario disponible.",
            )
        cursor = connection.execute(
            """
            INSERT INTO bookings (
                customer_name, customer_email, customer_phone, service_id,
                service_name, price, duration_minutes, booking_date,
                booking_time, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'confirmed', ?)
            """,
            (
                request.customer_name,
                request.customer_email,
                request.customer_phone,
                service["id"],
                service["name"],
                service["price"],
                service["duration_minutes"],
                request.date.isoformat(),
                requested_time.strftime("%H:%M"),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        connection.commit()
        row = connection.execute("SELECT * FROM bookings WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return serialize_booking(row)


@app.get("/api/admin/bookings", dependencies=[Depends(authenticate_admin)])
def list_bookings() -> list[dict[str, object]]:
    with closing(connect_database()) as connection:
        rows = connection.execute(
            "SELECT * FROM bookings ORDER BY booking_date, booking_time, id"
        ).fetchall()
    return [serialize_booking(row) for row in rows]


@app.post("/api/admin/bookings/{booking_id}/cancel", dependencies=[Depends(authenticate_admin)])
def cancel_booking(booking_id: int) -> dict[str, str]:
    with closing(connect_database()) as connection:
        cursor = connection.execute(
            "UPDATE bookings SET status = 'cancelled' WHERE id = ? AND status = 'confirmed'",
            (booking_id,),
        )
        connection.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="No se encontró una reserva activa con ese número.")
    return {"message": "La reserva fue cancelada."}


@app.get("/admin", include_in_schema=False)
def admin_page() -> FileResponse:
    return FileResponse(BASE_DIR / "admin.html")


app.mount("/", StaticFiles(directory=BASE_DIR, html=True), name="frontend")
