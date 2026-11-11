import { SERVICES } from "./_shared.js";

export function onRequestGet() {
  return Response.json(Object.values(SERVICES));
}
