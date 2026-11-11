import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import main


class BookingApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "test-agenda.db"
        self.database_patch = patch.object(main, "DATABASE_PATH", self.database_path)
        self.database_patch.start()
        main.initialize_database()
        self.client = TestClient(main.app)
        self.client.__enter__()
        self.booking_date = self.next_business_day()
        self.payload = {
            "customer_name": "María Demo",
            "customer_email": "maria@example.com",
            "customer_phone": None,
            "service_id": "manicure-completo",
            "date": self.booking_date.isoformat(),
            "time": "09:00",
        }

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.database_patch.stop()
        self.temp_dir.cleanup()

    @staticmethod
    def next_business_day() -> date:
        candidate = date.today() + timedelta(days=1)
        while candidate.weekday() == 6:
            candidate += timedelta(days=1)
        return candidate

    def test_creates_booking_and_marks_overlapping_slots_unavailable(self) -> None:
        response = self.client.post("/api/bookings", json=self.payload)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["service_name"], "Manicure + pedicure")
        self.assertEqual(response.json()["status"], "confirmed")

        availability = self.client.get(
            "/api/availability",
            params={"date": self.booking_date.isoformat(), "service_id": "manicure-clasica"},
        )
        slots = {slot["time"]: slot["available"] for slot in availability.json()["slots"]}
        self.assertFalse(slots["09:00"])
        self.assertFalse(slots["10:00"])

    def test_health_check_and_pages_origin_cors(self) -> None:
        self.assertEqual(self.client.get("/healthz").json(), {"status": "ok"})
        response = self.client.options(
            "/api/services",
            headers={
                "Origin": "https://rydstatto.github.io",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "https://rydstatto.github.io",
        )

    def test_rejects_duplicate_booking(self) -> None:
        self.assertEqual(self.client.post("/api/bookings", json=self.payload).status_code, 201)
        duplicate = self.client.post("/api/bookings", json=self.payload)

        self.assertEqual(duplicate.status_code, 409)

    def test_rejects_invalid_email_and_closed_sunday(self) -> None:
        invalid_email = {**self.payload, "customer_email": "not-an-email"}
        self.assertEqual(self.client.post("/api/bookings", json=invalid_email).status_code, 422)

        invalid_name = {**self.payload, "customer_name": 23}
        self.assertEqual(self.client.post("/api/bookings", json=invalid_name).status_code, 422)

        sunday = self.booking_date
        while sunday.weekday() != 6:
            sunday += timedelta(days=1)
        closed_day = {**self.payload, "date": sunday.isoformat()}
        self.assertEqual(self.client.post("/api/bookings", json=closed_day).status_code, 422)

    def test_admin_requires_credentials_and_can_cancel_booking(self) -> None:
        self.assertEqual(self.client.get("/api/admin/bookings").status_code, 401)
        with patch.dict(os.environ, {"ADMIN_USERNAME": "", "ADMIN_PASSWORD": ""}):
            unauthorized = self.client.get(
                "/api/admin/bookings",
                auth=("owner", "test-only-password"),
            )
            self.assertEqual(unauthorized.status_code, 503)
        with patch.dict(os.environ, {"ADMIN_USERNAME": "owner", "ADMIN_PASSWORD": "test-only-password"}):
            self.assertEqual(self.client.get("/api/admin/bookings").status_code, 401)
            booking = self.client.post("/api/bookings", json=self.payload).json()
            auth = ("owner", "test-only-password")
            bookings = self.client.get("/api/admin/bookings", auth=auth)
            self.assertEqual(bookings.status_code, 200)
            self.assertEqual(len(bookings.json()), 1)

            cancelled = self.client.post(
                f"/api/admin/bookings/{booking['id']}/cancel",
                auth=auth,
            )
            self.assertEqual(cancelled.status_code, 200)

        availability = self.client.get(
            "/api/availability",
            params={"date": self.booking_date.isoformat(), "service_id": "manicure-gel"},
        )
        slots = {slot["time"]: slot["available"] for slot in availability.json()["slots"]}
        self.assertTrue(slots["09:00"])


if __name__ == "__main__":
    unittest.main()
