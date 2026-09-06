# Seguridad y alcance de la publicación

Esta copia es un proyecto académico independiente y no una plataforma oficial de Shalom. No debe recibir datos reales sin autorización y sin una evaluación de seguridad y privacidad.

## Cambios efectuados sobre el ZIP de tesis

- Se excluyeron `.env`, `db.sqlite3`, `media/`, cachés y artefactos locales.
- Se conservó el código fuente, las migraciones, plantillas, recursos estáticos y documentación.
- Se amplió `.gitignore` y se creó una configuración de ejemplo sin credenciales reales.
- Los comandos de usuarios y datos demostrativos ya no incorporan contraseñas universales; generan claves aleatorias para cuentas nuevas y se bloquean fuera del desarrollo local.
- No se modificó la base de datos original ni se alteró el ZIP recibido.

## Antes de publicar

Revisa todo archivo que añadas al repositorio. Las reglas de `.gitignore` no eliminan archivos que ya hayan sido confirmados en Git. Si alguna clave real se ha publicado, revócala o rótala y revisa el historial del repositorio. No basta con borrar el archivo del último commit.

## Antes de desplegar en Internet

La instalación local no constituye una auditoría de seguridad. Deben verificarse permisos, control de acceso a archivos, validación de entradas, autenticación, rate limiting, manejo de errores, HTTPS, cookies seguras, almacenamiento persistente, respaldos y protección de datos. No ejecutes el servidor de desarrollo de Django como servidor de producción. Revisa `DESPLIEGUE_PRODUCCION.md` y `python manage.py check --deploy` con la configuración real.

Los datos de los generadores son ficticios. No deben presentarse como resultados reales de una empresa o como mediciones auténticas de la tesis. Los resultados pretest/postest solo podrán informarse cuando exista una recolección y validación metodológica real.
