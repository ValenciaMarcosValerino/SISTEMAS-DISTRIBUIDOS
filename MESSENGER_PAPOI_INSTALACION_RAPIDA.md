# Messenger Papoi — Instalación rápida

### Paso 1. Instala Git y Python 3

- **Windows:** [Git](https://git-scm.com/downloads/win) y [Python](https://www.python.org/downloads/windows/) (activar **Add Python to PATH**).
- **Ubuntu:** `sudo apt update && sudo apt install -y git python3 python3-venv python3-pip`
- **Fedora:** `sudo dnf install -y git python3 python3-pip`
- **macOS:** instala [Homebrew](https://brew.sh/) y ejecuta `brew install git python`.

### Paso 2. Descarga el proyecto

```bash
git clone https://github.com/ValenciaMarcosValerino/SISTEMAS-DISTRIBUIDOS.git
cd SISTEMAS-DISTRIBUIDOS
```

### Paso 3. Instala ODBC Driver 18 (solo si vas a ejecutar el servidor con SQL Server)

- **Windows:** instala [ODBC Driver 18](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server).
- **Ubuntu:**
  ```bash
  curl -fsSLO "https://packages.microsoft.com/config/ubuntu/$(. /etc/os-release; echo "$VERSION_ID")/packages-microsoft-prod.deb"
  sudo dpkg -i packages-microsoft-prod.deb
  sudo apt update
  sudo ACCEPT_EULA=Y apt install -y msodbcsql18
  ```
- **macOS:**
  ```bash
  brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
  HOMEBREW_ACCEPT_EULA=Y brew install msodbcsql18
  ```
- **Fedora:** `sudo dnf install -y unixODBC`; Microsoft no ofrece instalación oficial de ODBC 18 para Fedora. Si ya instalaste el controlador, verifícalo.

**Verifica ODBC:**
- **Windows:** abre `odbcad32.exe` → **Controladores** → `ODBC Driver 18 for SQL Server`.
- **Ubuntu, Fedora y macOS:** `odbcinst -q -d` → debe aparecer `ODBC Driver 18 for SQL Server`.

### Paso 4. Crea y activa el entorno virtual

**Windows (PowerShell):**
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Ubuntu, Fedora y macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Paso 5. Instala los requerimientos

```bash
python -m pip install -r requirements.txt
```

### Paso 6. Configura el cliente (servidor remoto: 3.149.102.2, puerto 3072)

**Windows (PowerShell):**
```powershell
$env:PAPOI_SERVER_HOST = "3.149.102.2"
$env:PAPOI_SERVER_PORT = "3072"
```

**Ubuntu, Fedora y macOS:**
```bash
export PAPOI_SERVER_HOST="3.149.102.2"
export PAPOI_SERVER_PORT="3072"
```

### Paso 7. Ejecuta la interfaz

```bash
python login.py
```

