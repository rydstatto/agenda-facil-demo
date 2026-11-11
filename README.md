# Agenda Fácil

Aplicación de agenda para profesionales independientes. Incluye una página pública de reservas, una API con FastAPI, persistencia en SQLite y un panel privado para consultar y cancelar citas.

## Requisitos

- Python 3.11 o posterior
- pip

## Ejecutar localmente

Desde esta carpeta, instala las dependencias:

```powershell
python -m pip install -r requirements.txt
```

Configura un usuario y una contraseña solo para el entorno local y arranca el servidor:

```powershell
$env:ADMIN_USERNAME = "admin"
$env:ADMIN_PASSWORD = "elige-una-contrasena-larga"
python -m uvicorn main:app --reload
```

Abre <http://127.0.0.1:8000/> para reservar y <http://127.0.0.1:8000/admin> para administrar citas. La documentación interactiva de la API está en <http://127.0.0.1:8000/docs>. En la primera ejecución se crea `agenda.db`, ignorada por Git.

No uses la contraseña de GitHub ni de otro servicio para `ADMIN_PASSWORD`. La contraseña solo vive en la variable de entorno de esa terminal; no la guardes en el repositorio.

## API

- `GET /api/services`: lista los servicios del estudio.
- `GET /api/availability?date=AAAA-MM-DD&service_id=...`: devuelve horarios y disponibilidad.
- `POST /api/bookings`: valida y guarda una reserva.
- `GET /api/admin/bookings`: lista las reservas activas y canceladas; requiere autenticación HTTP Basic.
- `POST /api/admin/bookings/{id}/cancel`: cancela una reserva; requiere autenticación HTTP Basic.

La API impide reservas solapadas incluso cuando dos solicitudes llegan casi al mismo tiempo, valida el correo y limita las citas a los próximos 90 días, de lunes a sábado.

## Pruebas

```powershell
python -m unittest discover -s tests -v
```

Las pruebas usan una base de datos temporal; no modifican las reservas locales.

## GitHub Pages y despliegue

GitHub Pages solo aloja páginas estáticas. El enlace publicado allí conserva el modo demo; la API y SQLite funcionan al ejecutar el servidor. Para ofrecer reservas reales por Internet hace falta desplegar FastAPI en un servicio con HTTPS, persistencia de datos y variables de entorno protegidas, y configurar el frontend para conectarse a ese backend.

Este MVP no envía correos, no procesa pagos y no incluye protección contra abuso ni una política de privacidad para operación pública. No lo uses con datos reales de clientes hasta completar esos requisitos y revisar las normas de privacidad aplicables.
