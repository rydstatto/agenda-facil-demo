import {
  SLOT_STARTS,
  errorResponse,
  getService,
  validateBookingDate,
} from "./_shared.js";

export async function onRequestGet({ request, env }) {
  try {
    const url = new URL(request.url);
    const bookingDate = url.searchParams.get("date");
    const service = getService(url.searchParams.get("service_id"));
    validateBookingDate(bookingDate);

    const reserved = await env.DB.prepare(
      "SELECT slot_time FROM booking_slots WHERE booking_date = ?",
    )
      .bind(bookingDate)
      .all();
    const reservedTimes = new Set((reserved.results || []).map(row => row.slot_time));
    const closingTime = 18 * 60;
    const slots = SLOT_STARTS.filter(slot => {
      const [hours, minutes] = slot.split(":").map(Number);
      return hours * 60 + minutes + service.duration_minutes <= closingTime;
    }).map(time => ({
      time,
      available: !reservedTimes.has(time),
    }));

    return Response.json({ date: bookingDate, slots });
  } catch (error) {
    return errorResponse(error);
  }
}
