export const SERVICES = {
  "manicure-clasica": {
    id: "manicure-clasica",
    name: "Manicure clásica",
    description: "Limado, cuidado de cutículas y esmaltado",
    price: 18,
    duration_minutes: 45,
  },
  "manicure-gel": {
    id: "manicure-gel",
    name: "Manicure gel",
    description: "Color duradero y acabado brillante",
    price: 28,
    duration_minutes: 60,
  },
  "manicure-completo": {
    id: "manicure-completo",
    name: "Manicure + pedicure",
    description: "Un cuidado completo de manos y pies",
    price: 42,
    duration_minutes: 90,
  },
};

export const SLOT_STARTS = ["09:00", "10:00", "11:30", "13:00", "14:00", "15:30", "16:30"];
const BUSINESS_CLOSE_MINUTES = 18 * 60;

export class HttpError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

export function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}

export function errorResponse(error) {
  if (error instanceof HttpError) {
    return json({ detail: error.message }, error.status);
  }
  console.error("Agenda API request failed:", error);
  return json({ detail: "Ocurrió un error interno. Inténtalo más tarde." }, 500);
}

export async function readJson(request) {
  try {
    return await request.json();
  } catch {
    throw new HttpError(400, "El cuerpo de la solicitud debe ser JSON válido.");
  }
}

function decodeBase64(value) {
  try {
    const bytes = Uint8Array.from(atob(value), character => character.charCodeAt(0));
    return new TextDecoder().decode(bytes);
  } catch {
    return null;
  }
}

function constantTimeEqual(left, right) {
  let difference = left.length ^ right.length;
  const length = Math.max(left.length, right.length);
  for (let index = 0; index < length; index += 1) {
    difference |= (left.charCodeAt(index) || 0) ^ (right.charCodeAt(index) || 0);
  }
  return difference === 0;
}

export function requireAdmin(request, env) {
  const username = env.ADMIN_USERNAME;
  const password = env.ADMIN_PASSWORD;
  if (!username || !password) {
    throw new HttpError(503, "El acceso de administración no está configurado.");
  }

  const authorization = request.headers.get("Authorization") || "";
  const match = /^Basic\s+([A-Za-z0-9+/]+=*)$/i.exec(authorization);
  const decoded = match ? decodeBase64(match[1]) : null;
  const separator = decoded?.indexOf(":") ?? -1;
  const suppliedUsername = separator >= 0 ? decoded.slice(0, separator) : "";
  const suppliedPassword = separator >= 0 ? decoded.slice(separator + 1) : "";
  if (
    !constantTimeEqual(suppliedUsername, username) ||
    !constantTimeEqual(suppliedPassword, password)
  ) {
    throw new HttpError(401, "Credenciales incorrectas.");
  }
}

export function validateBookingDate(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    throw new HttpError(422, "La fecha seleccionada no es válida.");
  }
  const parsed = new Date(`${value}T12:00:00.000Z`);
  if (Number.isNaN(parsed.valueOf()) || parsed.toISOString().slice(0, 10) !== value) {
    throw new HttpError(422, "La fecha seleccionada no es válida.");
  }

  const today = new Date();
  const todayUtc = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate());
  const requestedUtc = Date.UTC(parsed.getUTCFullYear(), parsed.getUTCMonth(), parsed.getUTCDate());
  const daysFromToday = (requestedUtc - todayUtc) / 86_400_000;
  if (daysFromToday < 0 || daysFromToday > 90) {
    throw new HttpError(422, "Elige una fecha entre hoy y los próximos 90 días.");
  }
  if (parsed.getUTCDay() === 0) {
    throw new HttpError(422, "El estudio no atiende los domingos.");
  }
  return parsed;
}

export function getService(serviceId) {
  const service = SERVICES[serviceId];
  if (!service) throw new HttpError(404, "El servicio seleccionado no existe.");
  return service;
}

export function getSlotLocks(startTime, durationMinutes) {
  if (!SLOT_STARTS.includes(startTime)) {
    throw new HttpError(422, "Ese horario no está disponible.");
  }
  const [hours, minutes] = startTime.split(":").map(Number);
  const start = hours * 60 + minutes;
  const end = start + durationMinutes;
  if (end > BUSINESS_CLOSE_MINUTES) {
    throw new HttpError(422, "Ese servicio no cabe completo en el horario de atención.");
  }
  return SLOT_STARTS.filter(slot => {
    const [slotHours, slotMinutes] = slot.split(":").map(Number);
    const slotStart = slotHours * 60 + slotMinutes;
    return start <= slotStart && slotStart < end;
  });
}

export function validateBooking(body) {
  if (!body || typeof body !== "object" || Array.isArray(body)) {
    throw new HttpError(422, "Los datos de la reserva no son válidos.");
  }
  const name = typeof body.customer_name === "string" ? body.customer_name.trim() : "";
  const email = typeof body.customer_email === "string" ? body.customer_email.trim() : "";
  const phone =
    typeof body.customer_phone === "string" && body.customer_phone.trim()
      ? body.customer_phone.trim()
      : null;
  if (name.length < 2 || name.length > 100) {
    throw new HttpError(422, "El nombre debe tener entre 2 y 100 caracteres.");
  }
  if (email.length > 254 || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
    throw new HttpError(422, "Ingresa un correo electrónico válido.");
  }
  if (phone && phone.length > 30) {
    throw new HttpError(422, "El teléfono no puede superar 30 caracteres.");
  }

  const service = getService(body.service_id);
  const parsedDate = validateBookingDate(body.date);
  const slotLocks = getSlotLocks(body.time, service.duration_minutes);
  return {
    customer_name: name,
    customer_email: email,
    customer_phone: phone,
    service,
    date: parsedDate.toISOString().slice(0, 10),
    time: body.time,
    slotLocks,
  };
}

export function overlaps(startTime, durationMinutes, candidateTime) {
  const toMinutes = value => {
    const [hours, minutes] = value.split(":").map(Number);
    return hours * 60 + minutes;
  };
  const start = toMinutes(startTime);
  const candidate = toMinutes(candidateTime);
  return start <= candidate && candidate < start + durationMinutes;
}

export function serializeBooking(row) {
  return {
    id: row.id,
    customer_name: row.customer_name,
    customer_email: row.customer_email,
    customer_phone: row.customer_phone,
    service_id: row.service_id,
    service_name: row.service_name,
    price: row.price,
    duration_minutes: row.duration_minutes,
    date: row.booking_date,
    time: row.booking_time,
    status: row.status,
    created_at: row.created_at,
  };
}
