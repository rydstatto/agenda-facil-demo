import {
  errorResponse,
  requireAdmin,
  serializeBooking,
} from "../_shared.js";

export async function onRequestGet({ request, env }) {
  try {
    requireAdmin(request, env);
    const result = await env.DB.prepare(
      "SELECT * FROM bookings ORDER BY booking_date, booking_time, id",
    ).all();
    return Response.json((result.results || []).map(serializeBooking));
  } catch (error) {
    return errorResponse(error);
  }
}
