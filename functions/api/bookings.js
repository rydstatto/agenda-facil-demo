import {
  HttpError,
  errorResponse,
  readJson,
  serializeBooking,
  validateBooking,
} from "./_shared.js";

export async function onRequestPost({ request, env }) {
  try {
    const booking = validateBooking(await readJson(request));
    const id = crypto.randomUUID();
    const createdAt = new Date().toISOString();
    const statements = [
      env.DB.prepare(
        `INSERT INTO bookings (
          id, customer_name, customer_email, customer_phone, service_id,
          service_name, price, duration_minutes, booking_date, booking_time,
          status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'confirmed', ?)`,
      ).bind(
        id,
        booking.customer_name,
        booking.customer_email,
        booking.customer_phone,
        booking.service.id,
        booking.service.name,
        booking.service.price,
        booking.service.duration_minutes,
        booking.date,
        booking.time,
        createdAt,
      ),
      ...booking.slotLocks.map(slot =>
        env.DB.prepare(
          "INSERT INTO booking_slots (booking_date, slot_time, booking_id) VALUES (?, ?, ?)",
        ).bind(booking.date, slot, id),
      ),
    ];

    try {
      await env.DB.batch(statements);
    } catch (error) {
      if (String(error).includes("booking_slots.booking_date, booking_slots.slot_time")) {
        throw new HttpError(409, "Ese horario acaba de ocuparse. Elige otro horario.");
      }
      throw error;
    }

    const row = await env.DB.prepare("SELECT * FROM bookings WHERE id = ?").bind(id).first();
    return Response.json(serializeBooking(row), { status: 201 });
  } catch (error) {
    return errorResponse(error);
  }
}
