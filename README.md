# Messenger Papoi — Instalación de la interfaz gráfica en Windows, Fedora, Ubuntu y macOS

Guía de instalación para ejecutar **`login.py`** y **`messenger.py`** desde diferentes sistemas operativos. Incluye instalación y comprobación opcional de **Microsoft ODBC Driver 18 for SQL Server**, creación de un entorno virtual, instalación de `requirements.txt`, configuración de red y solución de errores.

> **Arquitectura del proyecto:** `login.py` y `messenger.py` son el **cliente gráfico**. Se comunican por TCP con `server.py`, que es quien accede a SQL Server. Si solo vas a utilizar el cliente gráfico, **no necesitas ODBC 18 ni el archivo `.env` de la base de datos en tu computadora**. ODBC 18 y el `.env` se necesitan en la máquina que ejecuta `server.py` o en la que realmente llame a `db.py` para acceder a SQL Server. Aun así, se documenta el procedimiento ODBC en los cuatro sistemas por si también se ejecutará código de base de datos.

## 1. Requisitos comunes

- Python 3 compatible con la versión de **PySide6** incluida en `requirements.txt` (se recomienda una versión reciente soportada por PySide6).
- Git, si se descargará el código mediante `git clone`.
- Acceso a una sesión gráfica de escritorio para abrir PySide6 (un servidor Linux sin entorno gráfico no muestra la ventana).
- Archivo `requirements.txt` ubicado en la raíz del proyecto.
- Servidor Messenger Papoi activo y accesible mediante la IP y el puerto autorizados.

Si aún no tienes el código:

```bash
git clone https://github.com/ValenciaMarcosValerino/SISTEMAS-DISTRIBUIDOS.git
cd SISTEMAS-DISTRIBUIDOS
```

Si ya clonaste el repositorio, entra a esa carpeta y omite `git clone`.

## 2. Windows 10/11 — PowerShell

### 2.1 Instalar Python y Git

Descarga Python desde <https://www.python.org/downloads/windows/>. Comprueba:

```powershell
py --version
git --version
```

Instala Git desde <https://git-scm.com/downloads/win> si es necesario.

### 2.2 Instalar Microsoft ODBC Driver 18 (si se necesita SQL desde este equipo)

1. Abre la página oficial: <https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server>.
2. Descarga **Microsoft ODBC Driver 18 for SQL Server** adecuado a tu arquitectura (normalmente **x64**).
3. Ejecuta el instalador y completa el asistente.
4. Comprueba el registro en PowerShell:

```powershell
Get-OdbcDriver -Name "*ODBC Driver 18 for SQL Server*"
```

También puedes ejecutar `odbcad32.exe` y revisar la pestaña **Controladores**. El nombre esperado es **ODBC Driver 18 for SQL Server**.

### 2.3 Crear entorno virtual e instalar `requirements.txt`

Ubícate en la carpeta que contiene `login.py` y `requirements.txt`:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Usar `\.venv\Scripts\python.exe` evita problemas con la política de ejecución de PowerShell.

Comprueba:

```powershell
.\.venv\Scripts\python.exe -c "import PySide6, pyodbc, argon2, dotenv; print('Dependencias Python: OK'); print('ODBC:', pyodbc.drivers())"
```

### 2.4 Configurar el servidor y abrir la interfaz

En **la misma terminal**:

```powershell
$env:PAPOI_SERVER_HOST = "3.149.102.2"
$env:PAPOI_SERVER_PORT = "3072"
.\.venv\Scripts\python.exe -c "from papoi_theme import SERVER_HOST, SERVER_PORT; print(SERVER_HOST, SERVER_PORT)"
.\.venv\Scripts\python.exe login.py
```

La comprobación debe imprimir `3.149.102.2 3072`. Si usas otro puerto asignado, cambia `3072` por el correspondiente.

## 3. Ubuntu — Terminal

### 3.1 Instalar Python, herramientas y bibliotecas gráficas

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip python3-dev \
  build-essential curl ca-certificates git unixodbc unixodbc-dev \
  libgl1 libegl1 libxkbcommon-x11-0 libxcb-cursor0

python3 --version
```

### 3.2 Instalar Microsoft ODBC Driver 18 (si se necesita SQL desde Ubuntu)

El siguiente procedimiento utiliza el repositorio de Microsoft correspondiente a la versión de Ubuntu. Microsoft documenta, entre otras, las versiones **22.04, 24.04 y 26.04**; comprueba el soporte de tu versión antes de instalar.

```bash
. /etc/os-release
echo "Ubuntu $VERSION_ID"

# Solo si la versión está soportada por los paquetes de Microsoft:
curl -fsSLO "https://packages.microsoft.com/config/ubuntu/${VERSION_ID}/packages-microsoft-prod.deb"
sudo dpkg -i packages-microsoft-prod.deb
rm packages-microsoft-prod.deb

sudo apt update
sudo env ACCEPT_EULA=Y apt install -y msodbcsql18
```

Al utilizar `ACCEPT_EULA=Y` se acepta la licencia de uso del controlador. Si quieres revisarla primero, consulta la documentación oficial.

**Verificar el controlador:**

```bash
odbcinst -q -d
odbcinst -q -d -n "ODBC Driver 18 for SQL Server"
dpkg -l msodbcsql18
```

Debe figurar `ODBC Driver 18 for SQL Server`.

### 3.3 Instalar `requirements.txt`

```bash
cd /ruta/al/proyecto/SISTEMAS-DISTRIBUIDOS
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "import PySide6, pyodbc, argon2, dotenv; print('Dependencias Python: OK'); print('ODBC:', pyodbc.drivers())"
```

### 3.4 Abrir la interfaz

```bash
export PAPOI_SERVER_HOST="3.149.102.2"
export PAPOI_SERVER_PORT="3072"
python -c "from papoi_theme import SERVER_HOST, SERVER_PORT; print(SERVER_HOST, SERVER_PORT)"
python login.py
```

## 4. Fedora — Terminal

### 4.1 Instalar Python, herramientas y componentes gráficos

```bash
sudo dnf install -y python3 python3-pip python3-devel gcc gcc-c++ \
  git curl unixODBC unixODBC-devel libxkbcommon-x11 xcb-util-cursor

python3 --version
```

### 4.2 Microsoft ODBC Driver 18 en Fedora: compatibilidad

**Importante:** Microsoft **no incluye Fedora en su lista oficial de distribuciones compatibles** con el controlador ODBC 18. La lista sí incluye RHEL y Ubuntu. Si tu equipo Fedora **solo ejecuta `login.py`**, omite ODBC y continúa con la sección 4.3.

Primero verifica si ya tienes ODBC 18 instalado:

```bash
rpm -q msodbcsql18
odbcinst -q -d
odbcinst -q -d -n "ODBC Driver 18 for SQL Server"
```

Si aparece `ODBC Driver 18 for SQL Server`, ya está registrado y no debes volver a instalarlo.

**Instalación experimental (no soportada oficialmente):** si necesitas ejecutar `db.py` directamente desde Fedora, algunos entornos pueden intentar el paquete RPM de **RHEL 9**, pero no se garantiza compatibilidad ni resolución de dependencias con Fedora. No fuerces paquetes, no elimines bibliotecas del sistema ni continúes si aparecen conflictos. Para un despliegue confiable, ejecuta el backend de SQL Server en Ubuntu/RHEL compatible.

```bash
# Opcional y bajo responsabilidad del administrador de Fedora:
curl -fsSLO https://packages.microsoft.com/config/rhel/9/packages-microsoft-prod.rpm
sudo dnf install ./packages-microsoft-prod.rpm
sudo env ACCEPT_EULA=Y dnf install -y msodbcsql18

# Comprobar instalación:
odbcinst -q -d -n "ODBC Driver 18 for SQL Server"
```

Si la instalación devuelve errores de dependencias, **detente**: el repositorio RHEL no garantiza paquetes compatibles con Fedora. Consulta la [guía Linux oficial](https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server).

### 4.3 Crear entorno virtual e instalar `requirements.txt`

```bash
cd /ruta/al/proyecto/SISTEMAS-DISTRIBUIDOS
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "import PySide6, pyodbc, argon2, dotenv; print('Dependencias Python: OK'); print('ODBC:', pyodbc.drivers())"
```

### 4.4 Abrir la interfaz y verificar IP/puerto

```bash
export PAPOI_SERVER_HOST="3.149.102.2"
export PAPOI_SERVER_PORT="3072"
python -c "from papoi_theme import SERVER_HOST, SERVER_PORT; print(SERVER_HOST, SERVER_PORT)"
python login.py
```

**Si Python imprime `127.0.0.1 3072`**, revisa `papoi_theme.py`. Debe tomar las variables desde el entorno, por ejemplo:

```python
import os
SERVER_HOST = os.environ.get("PAPOI_SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.environ.get("PAPOI_SERVER_PORT", "5000"))
```

Los `export` solo afectan la terminal actual y los procesos iniciados desde ella. Si abres otra terminal, tendrás que configurarlos de nuevo.

## 5. macOS — Terminal

### 5.1 Instalar Python y Homebrew

1. Instala Homebrew siguiendo <https://brew.sh/>.
2. Luego verifica e instala herramientas:

```bash
brew --version
brew install python git unixodbc
python3 --version
```

Si `brew` no se reconoce tras instalarlo, sigue las indicaciones que muestra el instalador para agregar Homebrew al `PATH`.

### 5.2 Instalar Microsoft ODBC Driver 18 (si se necesita SQL desde macOS)

```bash
brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
brew update
HOMEBREW_ACCEPT_EULA=Y brew install msodbcsql18
```

Si Homebrew informa que no confía en la fórmula de Microsoft, verifica el origen y luego ejecuta (solo si el mensaje lo requiere):

```bash
brew trust --formula microsoft/mssql-release/msodbcsql18
HOMEBREW_ACCEPT_EULA=Y brew install msodbcsql18
```

**Verifica la instalación:**

```bash
brew list --versions msodbcsql18
odbcinst -q -d
odbcinst -q -d -n "ODBC Driver 18 for SQL Server"
```

En Apple silicon (ARM64), utiliza Python, Homebrew, unixODBC y el controlador de la **misma arquitectura**. Evita mezclar Python x64 mediante Rosetta con un controlador ARM64.

### 5.3 Instalar `requirements.txt`

```bash
cd /ruta/al/proyecto/SISTEMAS-DISTRIBUIDOS
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "import PySide6, pyodbc, argon2, dotenv; print('Dependencias Python: OK'); print('ODBC:', pyodbc.drivers())"
```

### 5.4 Ejecutar Messenger

```bash
export PAPOI_SERVER_HOST="3.149.102.2"
export PAPOI_SERVER_PORT="3072"
python -c "from papoi_theme import SERVER_HOST, SERVER_PORT; print(SERVER_HOST, SERVER_PORT)"
python login.py
```

## 6. Probar que existe conexión TCP con el servidor

**Esta prueba no requiere SQL Server ni ODBC en el cliente.** Se puede ejecutar desde cualquier sistema con Python:

```bash
python -c "import socket; s=socket.create_connection(('3.149.102.2',3072),timeout=5); print('TCP OK: servidor accesible'); s.close()"
```

En Windows también es posible ejecutar:

```powershell
Test-NetConnection 3.149.102.2 -Port 3072
```

**Ojo:** que TCP responda no garantiza que el inicio de sesión o el acceso a la base de datos funcionen; solo demuestra que el puerto es alcanzable.

## 7. Si vas a ejecutar también `server.py`

La instancia que ejecuta **`server.py`**, no los clientes gráficos, necesita el archivo privado `.env` y el controlador ODBC de SQL Server 18. La configuración debe proporcionar, sin publicarse:

```dotenv
SQL_MESSENGER_SERVER=servidor_sql,1433
SQL_MESSENGER_DATABASE=nombre_de_la_base
SQL_MESSENGER_USER=usuario_sql
SQL_MESSENGER_PASSWORD=contraseña_privada
```

Crea el `.env` **solo en el servidor**, con valores reales que te haya autorizado el administrador; **no incluyas datos reales en el repositorio**. En Linux, protege sus permisos con `chmod 600 .env`.

Para verificar que el archivo tiene los nombres correctos **sin imprimir secretos**:

```bash
python - <<'PY'
from dotenv import dotenv_values
config = dotenv_values('.env')
for key in ('SQL_MESSENGER_SERVER','SQL_MESSENGER_DATABASE','SQL_MESSENGER_USER','SQL_MESSENGER_PASSWORD'):
    print(key, 'OK' if config.get(key) else 'FALTA')
PY
```

Verificación del nombre ODBC desde Python (en la instancia que utiliza SQL):

```bash
python -c "import pyodbc; print(pyodbc.drivers())"
```

Debe contener `ODBC Driver 18 for SQL Server`. **No compartas capturas con contraseñas ni subas `.env` a GitHub.**

## 8. Solución de errores comunes

| Mensaje o síntoma | Qué revisar |
| --- | --- |
| `ModuleNotFoundError: No module named 'argon2'` | Activa el entorno virtual e instala `python -m pip install -r requirements.txt`; el paquete es `argon2-cffi`. |
| `ModuleNotFoundError: No module named 'PySide6'` | Instala las dependencias dentro del mismo entorno virtual que ejecuta `login.py`. |
| Fedora imprime `127.0.0.1 3072` | Verifica los `export` y que `papoi_theme.py` use `os.environ.get('PAPOI_SERVER_HOST', ...)`. |
| `Connection refused` | Confirma que el servidor esté escuchando en el puerto indicado. |
| `Connection timed out` | Verifica firewall, ruta y permisos de red; el acceso TCP debe estar autorizado. |
| `Falta SQL_MESSENGER_PASSWORD en el archivo .env` | El `.env` debe existir y ser cargado por el proceso que ejecuta `server.py`; no pertenece al cliente. |
| `Can't open lib 'ODBC Driver 18 for SQL Server'` | Revisa `odbcinst -q -d`, arquitectura y rutas del administrador ODBC. |
| `SSL Provider: certificate verify failed` | El controlador 18 valida certificados por defecto. Configura un certificado confiable en SQL Server; evita desactivar su verificación en producción. |
| Qt: `Could not load the Qt platform plugin "xcb"` | En Linux revisa dependencias gráficas Qt/XCB y si hay una sesión gráfica activa. |
| `Address already in use` | Ya existe otro `server.py` escuchando en ese puerto. Revisa `ss -ltnp` antes de iniciar una segunda instancia. |

## 9. Seguridad y buenas prácticas

- **No subas** `.env`, `.pem`, contraseñas ni respaldos de producción a GitHub.
- **No publiques contraseñas por TCP sin TLS**. El protocolo actual de Messenger Papoi envía credenciales de inicio de sesión en JSON; usar la IP pública directamente puede exponerlas. Para pruebas, prefiere túnel SSH o una VPN; para un despliegue público, agrega TLS al protocolo.
- La dirección `0.0.0.0` se utiliza **solo para escuchar en el servidor**; los clientes deben conectarse a la IP o nombre DNS real del servidor, nunca a `0.0.0.0`.
- El puerto `3072` es el ejemplo actual del proyecto; actualiza todas las comprobaciones si tu equipo usa otro puerto asignado.
- Si el servidor corre en Linux con `tmux`, primero verifica que no esté activa otra instancia del mismo puerto antes de reiniciarlo.

## 10. Documentación oficial

- Microsoft: [Descarga ODBC Driver 18 para Windows](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)
- Microsoft: [Instalación ODBC en Linux](https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server)
- Microsoft: [Instalación ODBC en macOS](https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/install-microsoft-odbc-driver-sql-server-macos)
- Microsoft: [Preguntas frecuentes, compatibilidad y verificaciones ODBC](https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/frequently-asked-questions-faq-for-odbc-linux)
- Qt: [PySide6](https://doc.qt.io/qtforpython-6/)

---

**Resumen rápido:** para abrir **solo la vista**, instala Python, crea `.venv`, instala `requirements.txt`, configura `PAPOI_SERVER_HOST` y `PAPOI_SERVER_PORT`, y ejecuta `python login.py`. Para ejecutar el **backend con SQL Server**, además instala ODBC Driver 18 y configura el `.env` privado en el servidor.
