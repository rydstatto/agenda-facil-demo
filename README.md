# Agenda Fácil

Demo de agenda de citas para un estudio ficticio. Incluye una página pública, funciones API, una base de datos D1 y un panel privado. El proyecto puede ejecutarse localmente con FastAPI/SQLite o publicarse como un solo sitio en Cloudflare Pages con Pages Functions y D1.

> **Solo para portafolio y pruebas.** Usa nombres y correos ficticios. La demo no envía correos ni procesa pagos; no la uses para administrar clientes reales.

## Publicación gratuita: Cloudflare Pages + D1

Cloudflare ofrece cuotas gratuitas para Pages, Workers/Functions y D1. Las cuotas y condiciones pueden cambiar; consulta [Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/) y [D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/) antes de publicar. No hace falta contratar un plan de pago para seguir estos pasos. Si la plataforma solicita tarjeta o información de pago, detente y no la introduzcas.

### 1. Crear la base D1

1. Crea o inicia sesión en una cuenta gratuita de Cloudflare.
2. En el panel, abre **Workers & Pages → D1 SQL database → Create database** y crea una base llamada `agenda-facil-demo`.
3. Copia el **Database ID** que muestra la página de detalles. Es un identificador público de configuración, no una contraseña.
4. Sustituye el valor de `database_id` en `wrangler.toml` por ese identificador y publica el cambio en GitHub. No cambies el binding `DB`.
5. En la consola SQL de esa base, ejecuta el contenido de [`migrations/0001_create_bookings.sql`](./migrations/0001_create_bookings.sql) una sola vez. Esto crea las tablas que usa la agenda.

### 2. Crear el sitio Pages conectado a GitHub

1. En Cloudflare, abre **Workers & Pages → Create application → Pages → Connect to Git** y autoriza el repositorio `rydstatto/agenda-facil-demo`.
2. Configura el comando de compilación como `npm run build` y el directorio de salida como `dist`.
3. Confirma que el proyecto reconoce `wrangler.toml` y que la función D1 aparece vinculada como `DB`. Si no aparece, agrega en la configuración de Pages un binding D1 con variable `DB` y selecciona `agenda-facil-demo`.
4. Espera el despliegue. Cloudflare asignará una dirección `*.pages.dev`.

El script de compilación copia únicamente `index.html`, `admin.html` y `config.js` al directorio público. Los archivos Python, SQL y de configuración no se sirven como páginas estáticas.

### 3. Configurar el acceso privado al panel

En **Pages → tu proyecto → Settings → Variables and Secrets**, agrega estos dos valores como secretos/variables privadas de producción:

- `ADMIN_USERNAME`: usuario nuevo para esta demo.
- `ADMIN_PASSWORD`: contraseña larga y única para esta demo.

Después de guardarlos, vuelve a desplegar el proyecto. No escribas esas credenciales en el código ni las compartas por chat. El panel queda en `https://TU-SITIO.pages.dev/admin.html`.

La API y el sitio usan el mismo dominio, por lo que `config.js` debe mantener `window.AGENDA_API_BASE_URL = ""`.

## Ejecutar localmente

### Backend Python existente

Requiere Python 3.11 o posterior:

```powershell
python -m pip install -r requirements.txt
$env:ADMIN_USERNAME = "admin"
$env:ADMIN_PASSWORD = "elige-una-contrasena-local"
python -m uvicorn main:app --reload
```

Abre <http://127.0.0.1:8000/> para reservar y <http://127.0.0.1:8000/admin> para administrar. La primera ejecución crea `agenda.db`, ignorada por Git.

### Pages Functions y D1 local

Requiere Node.js 22 o posterior:

```powershell
npm ci
npm run build
npx wrangler d1 migrations apply agenda-facil-demo --local
npx wrangler pages dev dist --port 8788 --binding ADMIN_USERNAME=admin --binding ADMIN_PASSWORD=elige-una-contrasena-local
```

Abre <http://127.0.0.1:8788/>. Los datos locales de Wrangler quedan en `.wrangler/`, ignorado por Git.

## API

- `GET /api/services`: lista los servicios.
- `GET /api/availability?date=AAAA-MM-DD&service_id=...`: devuelve horarios disponibles.
- `POST /api/bookings`: valida y guarda una reserva; rechaza horarios que se solapan.
- `GET /api/admin/bookings`: lista las reservas; requiere autenticación HTTP Basic.
- `POST /api/admin/bookings/{id}/cancel`: cancela una reserva y libera el horario; requiere autenticación HTTP Basic.
- `GET /healthz`: comprobación básica del servicio.

El acceso de administración protege las rutas de gestión, pero la página pública es una demostración y no incluye controles antiabuso, sistema de correo, copias de seguridad ni política de privacidad para operación comercial. D1 persiste las reservas dentro de los límites del plan y las cuotas gratuitas; no se promete disponibilidad ilimitada.

## Pruebas

```powershell
npm ci
npm test
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

`npm test` compila el sitio y valida las reglas principales de las Pages Functions. Las pruebas Python comprueban también la API local FastAPI/SQLite.
