CREATE TABLE IF NOT EXISTS bookings (
    id TEXT PRIMARY KEY,
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
);

CREATE INDEX IF NOT EXISTS bookings_date_status
    ON bookings (booking_date, status);

CREATE TABLE IF NOT EXISTS booking_slots (
    booking_date TEXT NOT NULL,
    slot_time TEXT NOT NULL,
    booking_id TEXT NOT NULL REFERENCES bookings(id),
    PRIMARY KEY (booking_date, slot_time)
);

CREATE INDEX IF NOT EXISTS booking_slots_booking_id
    ON booking_slots (booking_id);
