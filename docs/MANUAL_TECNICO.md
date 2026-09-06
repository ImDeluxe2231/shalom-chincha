# Manual técnico

## Arquitectura

El sistema utiliza una arquitectura web cliente-servidor:

- backend: Python 3 y Django 5.2;
- frontend: plantillas Django, HTML, CSS, Bootstrap y JavaScript;
- desarrollo local: SQLite;
- producción de tesis: MySQL con `utf8mb4`;
- servidor WSGI: Gunicorn;
- archivos estáticos: WhiteNoise;
- evidencias: carpeta `media` o almacenamiento persistente equivalente.

Aplicaciones Django:

- `accounts`: autenticación, usuarios y roles;
- `customers`: clientes;
- `shipments`: envíos, paquetes, agencias y trazabilidad;
- `operations`: entregas e incidencias;
- `reports`: dashboard, reportes y exportaciones;
- `research`: tres indicadores, instrumentos y comparación pretest/postest.

## Instalación

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py create_demo_users
python manage.py runserver
```

No copie la carpeta `.venv` de otra computadora. Debe generarla nuevamente.

## Actualización desde los módulos 1 al 6

Conserve antes de reemplazar archivos:

- `.env`;
- `db.sqlite3`;
- carpeta `media`;
- respaldo externo reciente.

Después ejecute:

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py test
python manage.py runserver
```

La migración crea nuevas tablas y no elimina usuarios, clientes, envíos,
entregas, incidencias ni reportes existentes.

## Pruebas

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

La versión incluye pruebas automatizadas de todos los módulos y pruebas POST
específicas para cada uno de los tres instrumentos de la tesis.

## Respaldo portable

```powershell
python manage.py backup_sistema
```

El ZIP generado contiene `datos.json`, `manifest.json` y los archivos de
`media`. Guárdelo fuera de la carpeta del proyecto y protéjalo porque contiene
información personal.

Para restaurar en una base vacía:

```powershell
python manage.py migrate
python manage.py loaddata datos.json
```

Después copie el contenido respaldado de `media` en la carpeta del mismo nombre.

## Datos demostrativos

`python manage.py cargar_datos_demo` es exclusivamente demostrativo. No debe
ejecutarse sobre la base destinada al pretest o postest.
