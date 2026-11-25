# Messenger Papoi — Instalación y ejecución para el profesor

**Práctica 1 de Sistemas Distribuidos**
Aplicación de escritorio con **Python, PySide6, sockets TCP y Microsoft SQL Server**.

Esta guía permite probar **registro, inicio de sesión, chat general, mensajes privados, grupos, canales de difusión, servidores de comunidad y fotografías de perfil**. La demostración descrita aquí ejecuta **servidor TCP y clientes en una misma PC Windows**. La base de datos está en SQL Server remoto.

> **Antes de comenzar:** el equipo o el responsable de la base debe proporcionar por un canal privado una **cuenta SQL autorizada**. El repositorio no contiene contraseñas ni los datos privados de la base. La base de datos debe tener el esquema y las tablas de la práctica preparados. **No se requiere Docker para esta modalidad**.

## 1. Requisitos (una sola vez)

- Windows 10/11, **Python 3** (comando `python` disponible) y **Git**.
- **ODBC Driver 18 for SQL Server**: [instalación oficial de Microsoft](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server).
- Acceso de red autorizado a SQL Server.

## 2. Descargar e instalar (PowerShell)

Abra **PowerShell de Windows** y copie el bloque completo:

```powershell
Set-Location $HOME
git clone https://github.com/ValenciaMarcosValerino/SISTEMAS-DISTRIBUIDOS.git
Set-Location "$HOME\SISTEMAS-DISTRIBUIDOS"
python -m pip install -r requirements.txt
python -m py_compile server.py db.py login.py registro.py messenger.py grupos_db.py servidores_db.py papoi_theme.py
python -c "import pyodbc; assert 'ODBC Driver 18 for SQL Server' in pyodbc.drivers(), 'Instale ODBC Driver 18'; print('Python y ODBC: OK')"
```

Si ya descargó el repositorio, entre a la carpeta y ejecute `git pull origin main` en lugar de repetir `git clone`.

> `py_compile` **revisa la sintaxis**, no genera un archivo `.exe`. Los archivos `*_ui.py` incluidos ya permiten abrir las ventanas; **no hace falta usar Qt Designer**.

## 3. Iniciar el servidor TCP (Terminal 1)

Abra **una terminal PowerShell**. Copie el bloque completo:

```powershell
Set-Location "$HOME\SISTEMAS-DISTRIBUIDOS"
$env:SQL_MESSENGER_SERVER = '3.149.102.2,1433'
$env:SQL_MESSENGER_DATABASE = 'papois/67'
$env:SQL_MESSENGER_USER = Read-Host 'Usuario SQL autorizado'
$claveSql = Read-Host 'Contrasena SQL autorizada' -AsSecureString
$env:SQL_MESSENGER_PASSWORD = [System.Net.NetworkCredential]::new('', $claveSql).Password
python -c "from db import conectar_bd; c=conectar_bd(); print('Conexion SQL correcta'); c.close()"
python server.py
```

Escriba el **usuario y la contraseña de SQL Server** facilitados por el responsable (son diferentes a los del Messenger). Si todo es correcto, aparecerá:

```text
Escuchando conexiones en: ('127.0.0.1', 5000)
```

**Deje esta terminal abierta**; contiene el servidor TCP. No vuelva a ejecutar `server.py` en otra terminal.

## 4. Abrir el login (Terminal 2)

Abra **una segunda terminal PowerShell**, sin cerrar la primera, y pegue:

```powershell
Set-Location "$HOME\SISTEMAS-DISTRIBUIDOS"
python login.py
```

En la interfaz **Azul Papoi**:

1. Pulse **Crear cuenta / Registro** y complete usuario, nombre visible y contraseña (mínimo 8 caracteres).
2. Regrese a **Iniciar sesión** con el **nombre de usuario** y la contraseña recién registrados.
3. Se abrirá Messenger Papoi automáticamente.

Para abrir un segundo cliente, ejecute nuevamente `python login.py` en **otra terminal** y use **una cuenta distinta**. No puede haber dos sesiones simultáneas de la misma cuenta.

## 5. Pruebas rápidas de la aplicación

| Módulo | Prueba de demostración |
|---|---|
| Chat general | Enviar `Prueba Papoi` y recibirlo en la otra cuenta conectada. |
| Mensajes privados | Seleccionar otro usuario y escribir; volver a entrar para ver su historial. |
| Grupos | Crear un grupo, agregar un usuario conectado y conversar. |
| Difusión | Crear un canal, suscribir a otro usuario y comprobar que **solo el propietario publica**. |
| Servidores | Crear un servidor, entrar en `#general`, agregar miembros y crear otro canal. |
| Fotografías | Perfil → **Cambiar foto**; elegir JPG/PNG y verificar que persiste al reiniciar sesión. |

## 6. Solución rápida de errores

| Error | Qué revisar |
|---|---|
| `ModuleNotFoundError` | Ejecute de nuevo `python -m pip install -r requirements.txt`. |
| `ODBC Driver 18` no aparece | Instale el controlador indicado y reinicie PowerShell. |
| Fallo de SQL Server | Compruebe conexión de red, acceso, nombre de base y credenciales SQL autorizadas. |
| `Connection refused` en login | Asegúrese de que `python server.py` continúe abierto en Terminal 1. |
| Puerto 5000 ocupado | No inicie un segundo servidor; cierre únicamente el proceso `server.py` anterior. |
| Cuenta ya conectada | Cierre su sesión anterior o utilice otra cuenta. |

**Notas para evaluación:** el cliente es **de escritorio**, no utiliza navegador ni WebSockets. Se comunica mediante sockets **TCP** y persiste información en SQL Server. `login.py` es el **punto de entrada de la interfaz**; no ejecute `messenger.py` directamente. El protocolo TCP de este proyecto **no cifra** las comunicaciones: el procedimiento anterior es una **prueba local**, no una configuración segura para exposición directa en Internet. El despliegue de clientes en distintas computadoras se validará por separado con el puerto autorizado por el profesor.
