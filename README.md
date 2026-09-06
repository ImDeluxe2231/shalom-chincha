# Sistema de Gestión y Seguimiento de Envíos — Shalom Chincha

Proyecto académico de Ingeniería de Sistemas | Portafolio de desarrollo web

**Autor:** Brayhan Quispe Villalva  
**Estado:** prototipo académico funcional en desarrollo; no es un servicio oficial ni un despliegue de producción.

## Descripción

Aplicación web para gestionar el registro, seguimiento y entrega de envíos, con control de usuarios, clientes, incidencias, indicadores operativos y herramientas de validación académica. El proyecto busca apoyar la trazabilidad y la gestión de información en un escenario logístico de Chincha.

Se trata de una implementación académica independiente inspirada en procesos logísticos. No representa a Shalom ni utiliza una integración oficial con sus servicios. Los datos de demostración son ficticios.

## Funcionalidades implementadas en el código

| Módulo | Alcance |
| --- | --- |
| Usuarios y roles | Autenticación, perfiles, permisos y administración de usuarios. |
| Clientes | Registro de personas y empresas, validaciones, búsquedas y desactivación lógica. |
| Envíos | Agencias, paquetes, origen, destino, modalidades, costos y comprobantes con QR. |
| Seguimiento | Eventos de trazabilidad, ubicación de almacén, transiciones controladas y consulta pública protegida. |
| Entregas e incidencias | Confirmación de entrega, constancias, evidencias, asignación y resolución de incidencias. |
| Dashboard y reportes | Indicadores operativos, filtros, gráficos y exportación a CSV, XLSX y PDF. |
| Validación de tesis | Instrumentos, registro de mediciones, pretest/postest y exportaciones para análisis estadístico. |

Las funcionalidades corresponden a la versión de código adjunta. No se afirma que haya sido auditada, desplegada públicamente o validada con resultados empresariales reales.

## Tecnologías

- **Backend:** Python, Django 5.2 y ORM de Django.
- **Frontend:** plantillas Django, HTML, CSS, JavaScript y Bootstrap.
- **Datos:** SQLite para desarrollo; configuración opcional de MySQL.
- **Infraestructura:** WhiteNoise, Gunicorn y variables de entorno.
- **Reportes:** exportadores a CSV, XLSX y PDF, implementados en el proyecto.
- **Calidad:** pruebas de Django y flujo de integración continua.

## Arquitectura

```text
Navegador
   │
   ▼
Django (URLs · vistas · formularios · permisos)
   │
   ├── accounts/    Usuarios y autenticación
   ├── customers/   Clientes
   ├── shipments/   Envíos y trazabilidad
   ├── operations/  Entregas e incidencias
   ├── reports/     Indicadores y exportaciones
   └── research/    Instrumentos de validación académica
   │
   ▼
ORM de Django → SQLite / MySQL
```

## Instalación local en Windows

**Requisitos:** Python 3.11 o superior compatible con las dependencias, Git y una terminal de PowerShell. La integración continua utiliza Python 3.11. Se recomienda comenzar con SQLite para evitar instalar MySQL innecesariamente.

### 1. Clonar y abrir el proyecto

```powershell
git clone https://github.com/TU-USUARIO/shalom-chincha.git
cd shalom-chincha
code .
```

Sustituye `TU-USUARIO` por tu nombre de usuario real de GitHub. Si descargaste el ZIP, abre directamente la carpeta que contiene `manage.py`.

### 2. Crear el entorno e instalar dependencias

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Si no tienes Python 3.11 pero sí otra versión compatible, puedes usar `py -m venv .venv`.

### 3. Crear la configuración privada

```powershell
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -c "from secrets import token_urlsafe; print(token_urlsafe(48))"
```

Abre `.env` y sustituye `CAMBIA_ESTA_CLAVE_POR_UNA_ALEATORIA` por el valor generado. Mantén `DEBUG=True`, `PRODUCTION=False` y `DB_ENGINE=sqlite` solamente para desarrollo local. Nunca subas `.env` al repositorio.

### 4. Crear la base y las cuentas de prueba

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py create_demo_users
.\.venv\Scripts\python.exe manage.py create_demo_customers
.\.venv\Scripts\python.exe manage.py create_demo_shipments
.\.venv\Scripts\python.exe manage.py create_demo_tracking
```

El comando de usuarios muestra contraseñas aleatorias para las cuentas nuevas `admin`, `ventanilla` y `almacen`. Guárdalas de forma privada: no hay una contraseña universal publicada. Si las cuentas ya existen, el comando no cambia sus contraseñas.

### 5. Iniciar el servidor

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

Abre `http://127.0.0.1:8000/` en tu navegador e inicia sesión con una de las cuentas creadas.

## Datos demostrativos para el dashboard

En una base local de pruebas puedes ejecutar:

```powershell
.\.venv\Scripts\python.exe manage.py cargar_datos_demo
```

La carga predeterminada está configurada para generar 140 clientes y 360 envíos distribuidos en 120 días, con seguimientos, entregas e incidencias. El comando evita duplicar el lote identificado por su marcador. Utilízalo solamente para demostraciones, nunca sobre una base con datos reales ni sobre la base utilizada para mediciones de tesis. Consulta [la guía de datos de ejemplo](docs/DATOS_DEMOSTRATIVOS.md).

## Pruebas

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test
```

GitHub Actions ejecuta las comprobaciones y pruebas en una base de datos temporal. Los resultados de ejecución deben consultarse en la pestaña Actions; no se incluyen métricas de cobertura que no hayan sido medidas.

## Rutas principales

| Ruta | Propósito |
| --- | --- |
| `/` | Dashboard según el rol. |
| `/clientes/` | Gestión de clientes. |
| `/envios/` | Registro y consulta de envíos. |
| `/seguimiento/` | Consulta pública protegida. |
| `/seguimiento/operaciones/` | Seguimiento interno. |
| `/entregas/` | Gestión de entregas. |
| `/incidencias/` | Registro y resolución de incidencias. |
| `/reportes/` | Centro de reportes administrativos. |
| `/validacion/` | Instrumentos e indicadores académicos. |
| `/admin-django/` | Administración de Django. |

## Documentación adicional

- [Manual técnico](docs/MANUAL_TECNICO.md)
- [Manual de usuario](docs/MANUAL_USUARIO.md)
- [Seguimiento operativo](docs/MODULO_4_SEGUIMIENTO.md)
- [Entregas e incidencias](docs/MODULO_5_ENTREGAS_INCIDENCIAS.md)
- [Dashboard y reportes](docs/MODULO_6_DASHBOARD_REPORTES.md)
- [Validación de tesis](docs/MODULO_7_VALIDACION_TESIS.md)
- [Protocolo pretest/postest](docs/PROTOCOLO_PRETEST_POSTTEST.md)
- [Despliegue y configuración](docs/DESPLIEGUE_PRODUCCION.md)
- [Seguridad y publicación](docs/SEGURIDAD_PUBLICACION.md)

## Capturas y demostración

Las capturas deben obtenerse de una ejecución real del sistema con datos ficticios. No se incluyen imágenes generadas como si fueran evidencia funcional. Puedes añadir capturas del login, dashboard, registro de envíos, seguimiento y reportes dentro de `docs/screenshots/`, comprobando antes que no contengan datos personales.

## Alcance académico y autoría

Este repositorio presenta el trabajo como proyecto de portafolio. Si el desarrollo fue realizado en equipo, se deben reconocer las contribuciones de los integrantes y cualquier recurso de terceros utilizado. El código y las dependencias conservan sus respectivas condiciones de licencia; no se declara una licencia de código abierto para el proyecto sin autorización de sus titulares.

**Próximas mejoras:** pruebas adicionales de seguridad, cobertura de pruebas, documentación de arquitectura ampliada, revisión de accesibilidad y despliegue de una demo controlada.
