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
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Las pruebas usan una base de datos temporal; no modifican las reservas locales.

## Publicar una demo con GitHub Pages y Render

GitHub Pages sirve el frontend estático y Render ejecuta FastAPI. El blueprint `render.yaml` crea el backend en el plan gratuito y genera credenciales aleatorias para el panel.

1. Abre [Render Blueprint](https://render.com/deploy?repo=https://github.com/rydstatto/agenda-facil-demo) e inicia sesión en Render.
2. Autoriza el acceso al repositorio `rydstatto/agenda-facil-demo` y crea el servicio definido en `render.yaml`.
3. Espera el despliegue y copia la URL HTTPS asignada al backend, por ejemplo `https://agenda-facil-api.onrender.com`.
4. En `config.js`, establece `window.AGENDA_API_BASE_URL` con esa URL (sin barra final), guarda el archivo y súbelo a `main`:

   ```js
   window.AGENDA_API_BASE_URL = "https://TU-SERVICIO.onrender.com";
   ```

5. Espera a que GitHub Pages publique el cambio. La página pública confirmará que está conectada al backend.
6. Render genera `ADMIN_USERNAME` y `ADMIN_PASSWORD`. Consúltalos en el servicio, en **Environment**, para iniciar sesión en `/admin`. No los publiques ni los guardes en el repositorio.

Si Render muestra un error de acceso a GitHub, usa el panel de Render para conceder acceso al repositorio y vuelve a abrir el enlace Blueprint. No compartas credenciales o tokens en el chat. La URL pública del backend no es secreta; se necesita para conectar la web después del despliegue.

## Alcance de la demo pública

El backend gratuito usa SQLite en el sistema de archivos temporal del servicio: las reservas de prueba pueden borrarse al reiniciar, suspender o volver a desplegar el servicio. El servicio gratuito también puede tardar en despertar. Esto es adecuado para enseñar un prototipo, **no para gestionar clientes**. El sitio solicita nombre y correo, así que para la demo usa únicamente datos ficticios.

La demo no envía correos ni procesa pagos. Antes de usarla para un negocio hay que configurar una base de datos persistente, envío de correos, HTTPS, protección contra abuso, copias de seguridad y una política de privacidad apropiada.
