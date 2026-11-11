import { errorResponse, requireAdmin } from "../../../_shared.js";

export async function onRequestPost({ request, env, params }) {
  try {
    requireAdmin(request, env);
    const id = params.id;
    const booking = await env.DB.prepare(
      "SELECT id, status FROM bookings WHERE id = ?",
    )
      .bind(id)
      .first();
    if (!booking || booking.status !== "confirmed") {
      return Response.json(
        { detail: "No se encontró una reserva activa con ese número." },
        { status: 404 },
      );
    }

    await env.DB.batch([
      env.DB.prepare("UPDATE bookings SET status = 'cancelled' WHERE id = ?").bind(id),
      env.DB.prepare("DELETE FROM booking_slots WHERE booking_id = ?").bind(id),
    ]);
    return Response.json({ message: "La reserva fue cancelada." });
  } catch (error) {
    return errorResponse(error);
  }
}
