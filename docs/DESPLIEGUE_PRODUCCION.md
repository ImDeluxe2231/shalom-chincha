# Despliegue seguro para la sustentación

## Base de datos MySQL

1. Instale MySQL Server y cree una base `shalom_chincha` con `utf8mb4`.
2. Instale el controlador con `pip install -r requirements-mysql.txt`.
3. Complete en `.env`:

```env
DB_ENGINE=mysql
DB_NAME=shalom_chincha
DB_USER=usuario_exclusivo
DB_PASSWORD=contraseña_segura
DB_HOST=127.0.0.1
DB_PORT=3306
```

4. Ejecute `python manage.py migrate`.

XAMPP no es obligatorio para Django. Puede usarse únicamente como proveedor
local de MySQL si se configura correctamente, pero no debe utilizarse Apache
para ejecutar el servidor de desarrollo de Django.

## Variables de producción

```env
DEBUG=False
PRODUCTION=True
SECRET_KEY=una-clave-larga-y-unica
ALLOWED_HOSTS=dominio.example.com
CSRF_TRUSTED_ORIGINS=https://dominio.example.com
PUBLIC_BASE_URL=https://dominio.example.com
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
```

No publique `.env`, `db.sqlite3`, respaldos ni la carpeta `media` en GitHub.

## HTTPS

El dominio debe contar con certificado TLS válido. La plataforma de alojamiento
o proxy debe enviar `X-Forwarded-Proto: https`. Antes de activar HSTS confirme
que todo el sitio funciona por HTTPS, porque el navegador recordará la política.

## Comandos de publicación

```powershell
python manage.py check --deploy
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py test
gunicorn shalom_web.wsgi
```

## Archivos y respaldo

La carpeta `media` debe permanecer en un volumen persistente. Programe respaldos
periódicos y compruebe al menos una restauración antes de la sustentación.

## Lista de verificación

- `DEBUG=False`;
- contraseña de demostración cambiada;
- MySQL activo;
- HTTPS sin advertencias;
- cookies seguras;
- dominio en `ALLOWED_HOSTS`;
- origen HTTPS en `CSRF_TRUSTED_ORIGINS`;
- `media` persistente;
- respaldo reciente descargado;
- todas las pruebas automatizadas aprobadas;
- prueba manual de los tres perfiles;
- consulta pública comprobada desde otro dispositivo.
