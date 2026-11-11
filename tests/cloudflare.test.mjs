import assert from "node:assert/strict";
import test from "node:test";

import {
  HttpError,
  getSlotLocks,
  overlaps,
  validateBooking,
  validateBookingDate,
} from "../functions/api/_shared.js";

function nextBusinessDay() {
  const date = new Date();
  date.setUTCDate(date.getUTCDate() + 1);
  while (date.getUTCDay() === 0) date.setUTCDate(date.getUTCDate() + 1);
  return date.toISOString().slice(0, 10);
}

test("reserves each selectable start time that overlaps a service interval", () => {
  assert.deepEqual(getSlotLocks("09:00", 90), ["09:00", "10:00"]);
  assert.deepEqual(getSlotLocks("10:00", 60), ["10:00"]);
  assert.equal(overlaps("09:00", 90, "10:00"), true);
  assert.equal(overlaps("09:00", 90, "11:30"), false);
});

test("validates and normalizes a valid booking", () => {
  const booking = validateBooking({
    customer_name: "  Demo Cliente ",
    customer_email: " cliente@example.com ",
    customer_phone: "  ",
    service_id: "manicure-gel",
    date: nextBusinessDay(),
    time: "10:00",
  });
  assert.equal(booking.customer_name, "Demo Cliente");
  assert.equal(booking.customer_email, "cliente@example.com");
  assert.equal(booking.customer_phone, null);
  assert.deepEqual(booking.slotLocks, ["10:00"]);
});

test("rejects malformed personal details and dates", () => {
  assert.throws(
    () => validateBooking({ customer_name: "x", customer_email: "bad" }),
    error => error instanceof HttpError && error.status === 422,
  );
  assert.throws(
    () => validateBookingDate("not-a-date"),
    error => error instanceof HttpError && error.status === 422,
  );
});
