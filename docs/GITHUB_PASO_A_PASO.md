# Publicación en GitHub desde VS Code

Esta guía se aplica a la copia limpia, no al ZIP original de tesis. No copies el archivo `.env`, la base de datos ni la carpeta `media` desde el proyecto anterior.

## 1. Preparar Git y abrir la carpeta

Instala Git desde https://git-scm.com/download/win si aún no lo tienes. Extrae `shalom-chincha-github.zip` y abre la carpeta `shalom-chincha` en VS Code. Comprueba que en la raíz está `manage.py`.

En la terminal de VS Code, ejecuta:

```powershell
git --version
git config --global user.name "Brayhan Quispe Villalva"
git config --global user.email "TU-CORREO-DE-GITHUB"
```

Reemplaza el correo por el que utilizas en GitHub o por el correo privado `noreply` que GitHub te proporcione. El correo de Git no tiene que ser tu contraseña ni un token.

## 2. Crear el repositorio en GitHub

Entra a https://github.com/new e inicia sesión. Completa:

- Repository name: `shalom-chincha`
- Description: `Sistema web académico de gestión y seguimiento de envíos desarrollado con Django, Python y SQL.`
- Visibility: Public, únicamente si tienes autorización para publicar el código y ya revisaste que no contenga información privada. En caso contrario, elige Private.
- Add a README file: desmarcado.
- Add .gitignore: None.
- Choose a license: None, hasta definir la autorización y licencia correspondiente.

Haz clic en Create repository. Copia la URL HTTPS que GitHub te mostrará. No inventes tu nombre de usuario.

## 3. Crear el primer commit

En la terminal, desde la carpeta que contiene `manage.py`:

```powershell
git init
git branch -M main
git status --short
git add .gitignore .env.example .github README.md docs requirements.txt requirements-mysql.txt Procfile manage.py accounts customers shipments operations reports research shalom_web static templates
git diff --cached --stat
git diff --cached --name-only
git commit -m "Initial commit: sistema de gestion y seguimiento de envios"
```

Antes del commit revisa los nombres preparados. No deben aparecer `.env`, `db.sqlite3`, `media/`, `backups/` ni `.venv/`. Si aparece alguno, detente y retíralo del área de preparación. `git add` solo prepara archivos; el commit registra el contenido en el historial local.

## 4. Conectar y publicar

Sustituye TU-USUARIO por tu usuario real. Si GitHub te muestra otra URL, usa esa URL exacta.

```powershell
git remote add origin https://github.com/TU-USUARIO/shalom-chincha.git
git push -u origin main
```

Si Git solicita autenticación, utiliza el inicio de sesión seguro que abra Git Credential Manager o el método admitido por GitHub. No escribas tu contraseña de GitHub en el campo de token ni compartas credenciales. Si Git indica que `origin` ya existe, consulta `git remote -v` y utiliza `git remote set-url origin URL-CORRECTA` solamente si necesitas corregirlo.

## 5. Comprobar la publicación

Abre el repositorio en tu navegador. Revisa que se vean README, código fuente, migraciones y documentación. Comprueba que no aparezcan archivos privados. En Actions podrás revisar el resultado de las pruebas automatizadas. El repositorio público no convierte automáticamente la aplicación en una web desplegada; para una demo en Internet se necesita un hosting y configuración de producción.

En About agrega la descripción y, si tienes una demo real, su URL. Temas sugeridos: `django`, `python`, `logistics`, `shipment-tracking`, `sql`, `academic-project`, `portfolio`.

## 6. Cambios posteriores

```powershell
git status
git add RUTA-DEL-ARCHIVO-MODIFICADO
git commit -m "Describe el cambio realizado"
git push
```

Selecciona los archivos que realmente modificaste. No subas archivos privados ni uses el ZIP original. Si otro integrante también trabaja sobre el proyecto, acuerden una estrategia de ramas y revisiones antes de fusionar cambios.

## 7. Errores frecuentes

- `git no se reconoce`: instala Git, reinicia VS Code y vuelve a abrir la terminal.
- `Author identity unknown`: configura user.name y user.email.
- `src refspec main does not match any`: comprueba que realizaste el primer commit.
- `Repository not found`: verifica el usuario, nombre, URL y permisos de acceso.
- `Authentication failed`: vuelve a autenticarte mediante el método oficial; no publiques tokens.
- `remote origin already exists`: revisa `git remote -v` antes de cambiar la URL.
- `failed to push some refs`: comprueba si el repositorio remoto contiene commits previos. No fuerces el push ni borres historial sin entender el conflicto.

## Importante sobre secretos

Si ya publicaste una clave real en otro repositorio, cambiar `.gitignore` no la elimina del historial. Revoca o rota la clave y sigue el procedimiento oficial de GitHub para retirar datos confidenciales. El repositorio que se crea con esta copia limpia parte de un historial nuevo y no incluye la historia privada anterior.
