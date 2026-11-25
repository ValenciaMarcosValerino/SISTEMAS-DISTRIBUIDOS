# Messenger Papoi — Guía para compañeros de equipo

Esta guía explica **cómo descargar el proyecto, ejecutarlo localmente y colaborar en GitHub** sin sobrescribir el trabajo de otros integrantes.

## 1. Primera instalación en Windows

Necesitas **Python 3**, **Git**, acceso autorizado a la base SQL Server y **ODBC Driver 18 for SQL Server**. Instalador oficial: https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server

Abre PowerShell y copia:

```powershell
Set-Location $HOME
git clone https://github.com/ValenciaMarcosValerino/SISTEMAS-DISTRIBUIDOS.git
Set-Location "$HOME\SISTEMAS-DISTRIBUIDOS"
python -m pip install -r requirements.txt
python -m py_compile server.py login.py registro.py messenger.py db.py grupos_db.py servidores_db.py papoi_theme.py
```

**No es necesario compilar las interfaces Qt Designer ni ejecutar `messenger.py` directamente.** La interfaz arranca desde `login.py`.

## 2. Iniciar Messenger localmente

**Terminal 1 — Servidor:**

```powershell
Set-Location "$HOME\SISTEMAS-DISTRIBUIDOS"
$env:SQL_MESSENGER_SERVER = '3.149.102.2,1433'
$env:SQL_MESSENGER_DATABASE = 'papois/67'
$env:SQL_MESSENGER_USER = Read-Host 'Usuario SQL autorizado'
$clave = Read-Host 'Contrasena SQL' -AsSecureString
$env:SQL_MESSENGER_PASSWORD = [System.Net.NetworkCredential]::new('', $clave).Password
python server.py
```

Dejar abierta esa terminal. La cuenta SQL se solicita al responsable por un **canal privado**; no es la cuenta del chat.

**Terminal 2 — Aplicación:**

```powershell
Set-Location "$HOME\SISTEMAS-DISTRIBUIDOS"
python login.py
```

Pulsa **Registrarse**, crea tu cuenta e inicia sesión. Para probar dos usuarios en la **misma PC**, ejecuta `python login.py` en una tercera terminal y entra con otra cuenta.

> Atención: por ahora `server.py` y el login están configurados con `127.0.0.1:5000`. Cada PC necesita su servidor local para estas pruebas; el acceso de distintas computadoras al Linux del profesor **aún no está configurado**. No cambies el puerto del servidor compartido sin autorización.

## 3. Colaborar en GitHub

1. El responsable del repositorio debe agregarte en **GitHub → Settings → Collaborators**. Acepta la invitación.
2. Antes de trabajar, actualiza `main`:

```powershell
git switch main
git pull origin main
```

3. Crea una rama para tu cambio (ejemplo `fotos-gael`; usa tu propio nombre):

```powershell
git switch -c mejora-funcion
git status --short
```

4. Haz y prueba tus modificaciones. Después:

```powershell
git add -A
git status --short
git commit -m "Mejora: descripcion breve del cambio"
git push -u origin mejora-funcion
```

5. En GitHub abre un **Pull Request** hacia `main` y pide a otro integrante que lo revise antes de fusionarlo. **No trabajen todos directamente en `main`.**

**Antes de cada `commit`:** comprueba que no se incluyan `.env`, llaves `.pem`, contraseñas, carpetas `venv`, cachés `__pycache__`, respaldos ni volcados con datos de usuarios. El archivo `.gitignore` facilita esto, pero **no protege archivos que ya estuvieran versionados**.

## 4. Qué puede hacer cada integrante

- **Registro / login:** crear una cuenta y entrar a la aplicación.
- **Chat general / privado:** mensajes entre cuentas conectadas.
- **Grupos:** crear grupos, agregar usuarios conectados y recuperar historial.
- **Difusión:** propietario publica; los suscriptores leen y reciben avisos.
- **Servidores de comunidad:** crear servidores, sumar integrantes y conversar en canales separados como `#general`.
- **Perfil:** seleccionar foto PNG/JPG; se guarda en SQL Server y se recupera al iniciar sesión.

Utilicen el texto **`Prueba Papoi`** para las demostraciones.

## 5. Archivos que deben conocer

| Archivo | Uso |
|---|---|
| `server.py` | Servidor TCP; autenticación, permisos y distribución de mensajes. |
| `db.py`, `grupos_db.py`, `servidores_db.py` | Acceso a SQL Server y operaciones persistentes. |
| `login.py`, `registro.py`, `messenger.py` | Ventanas e interacción del cliente PySide6. |
| `papoi_theme.py` | Diseño visual Azul Papoi y otros temas. |
| `*_ui.py`, `*.ui` | Interfaces generadas y archivos editables de Qt Designer. |
| `.env.example` | Nombres de variables de configuración **sin claves reales**. |
| `.env` | Credenciales privadas locales: **no subir a GitHub**. |

## 6. Trabajo en Linux del profesor

El backend se ha copiado a `/home/gaeluwu/MessengerPapoi` y tiene Python/ODBC preparados, pero **todavía falta asignar/configurar el puerto TCP y validar clientes desde otras PCs**. Para trabajar en equipo, usen GitHub y Pull Requests. No modifiquen archivos directamente en la máquina compartida sin coordinarse; su `.env` contiene las credenciales de la base y debe mantenerse privado.

Para consultas de instalación del profesor, ver [`README.md`](README.md).
