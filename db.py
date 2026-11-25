
import os
import pyodbc
from argon2 import PasswordHasher
from argon2.low_level import Type
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

from pathlib import Path
from dotenv import load_dotenv
from uuid import UUID


# CARGAR CONFIGURACIÓN DE SQL SERVER

load_dotenv(Path(__file__).resolve().parent / ".env")



# PROTECCIÓN DE CONTRASEÑAS

hasher = PasswordHasher(type=Type.ID)


# CREAR CUENTA

def crear_cuenta(usuario, nombre_visible, contrasena):

    usuario = usuario.strip()
    nombre_visible = nombre_visible.strip()

    if not usuario or not nombre_visible:
        raise ValueError("El usuario y el nombre visible son obligatorios.")

    if len(usuario) > 50 or len(nombre_visible) > 50:
        raise ValueError("Los nombres no pueden superar 50 caracteres.")

    if len(contrasena) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")

    contrasena_hash = hasher.hash(contrasena)

    conexion = conectar_bd()

    try:
        cursor = conexion.cursor()

        cursor.execute("""
            INSERT INTO dbo.Usuarios
                (nombre_usuario, nombre_mostrar, contrasena_hash)
            OUTPUT INSERTED.id_publico
            VALUES (?, ?, ?)
        """, usuario, nombre_visible, contrasena_hash)

        id_publico = cursor.fetchone()[0]

        conexion.commit()

        return str(id_publico)

    except pyodbc.IntegrityError as error:

        if "2627" in str(error) or "2601" in str(error):
            raise ValueError("Ese nombre de usuario ya está registrado.") from error

        raise

    finally:
        conexion.close()


# VERIFICAR CUENTA

def verificar_cuenta(usuario, contrasena):

    conexion = conectar_bd()

    try:
        cursor = conexion.cursor()

        cursor.execute("""
            SELECT id_publico, nombre_usuario,
                   nombre_mostrar, contrasena_hash
            FROM dbo.Usuarios
            WHERE nombre_usuario = ?
        """, usuario.strip())

        resultado = cursor.fetchone()

    finally:
        conexion.close()

    if resultado is None or resultado[3] is None:
        return None

    try:
        hasher.verify(resultado[3], contrasena)

    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return None

    return {
        "id_publico": str(resultado[0]),
        "usuario": resultado[1],
        "nombre_visible": resultado[2]
    }

# CONEXIÓN A LA BASE DE DATOS

def conectar_bd():

    # DATOS DE CONEXIÓN CONFIGURADOS EN .env

    servidor = os.getenv("SQL_MESSENGER_SERVER", "127.0.0.1,1433").strip()
    base_datos = os.getenv("SQL_MESSENGER_DATABASE", "BDD_Messenger").strip()
    usuario_sql = os.getenv("SQL_MESSENGER_USER", "sa").strip()
    password = os.getenv("SQL_MESSENGER_PASSWORD")

    if not password:
        raise RuntimeError("Falta SQL_MESSENGER_PASSWORD en el archivo .env")

    if not all((servidor, base_datos, usuario_sql)):
        raise RuntimeError("Configuración de SQL Server incompleta en .env")

    return pyodbc.connect(
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={servidor};"
        f"DATABASE={base_datos};"
        f"UID={usuario_sql};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;",
        PWD=password,
        timeout=10
    )


# FUNCIÓN PARA REGISTRAR USUARIOS

def registrar_usuario(nombre):

    conexion = conectar_bd()

    try:
        cursor = conexion.cursor()

        cursor.execute("""
            IF NOT EXISTS (
                SELECT 1
                FROM Usuarios
                WHERE nombre_usuario = ?
            )
            INSERT INTO Usuarios (nombre_usuario)
            VALUES (?)
        """, nombre, nombre)

        conexion.commit()

    finally:
        conexion.close()



# PRUEBA DE CONEXIÓN

if __name__ == "__main__":

    conexion = conectar_bd()

    cursor = conexion.cursor()
    cursor.execute("SELECT DB_NAME(), SYSTEM_USER")
    nombre_bd, usuario_sql = cursor.fetchone()
    print(f"Conexión exitosa con {nombre_bd} (usuario SQL: {usuario_sql})")

    conexion.close()



# CREAR SERVIDOR DISCORD

def crear_servidor_discord(nombre, id_creador):

    nombre = nombre.strip()

    if not nombre or len(nombre) > 100:
        raise ValueError("Nombre de servidor no válido.")

    conexion = conectar_bd()

    try:
        cursor = conexion.cursor()

        cursor.execute("""
            INSERT INTO dbo.Servidores (nombre, id_creador)
            OUTPUT INSERTED.id_servidor
            VALUES (?, CONVERT(UNIQUEIDENTIFIER, ?))
        """, nombre, id_creador)

        id_servidor = str(cursor.fetchone()[0])

        cursor.execute("""
            INSERT INTO dbo.MiembrosServidor
                (id_servidor, id_usuario, rol)
            VALUES (
                CONVERT(UNIQUEIDENTIFIER, ?),
                CONVERT(UNIQUEIDENTIFIER, ?),
                'Administrador'
            )
        """, id_servidor, id_creador)

        cursor.execute("""
            INSERT INTO dbo.Canales
                (id_servidor, nombre, descripcion)
            VALUES (
                CONVERT(UNIQUEIDENTIFIER, ?),
                'general',
                'Canal general del servidor'
            )
        """, id_servidor)

        conexion.commit()

        return id_servidor

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()


# OBTENER SERVIDORES DE UN USUARIO

def obtener_servidores_usuario(id_publico):

    conexion = conectar_bd()

    try:
        cursor = conexion.cursor()

        cursor.execute("""
            SELECT
                CONVERT(VARCHAR(36), s.id_servidor) AS id_servidor,
                s.nombre,
                m.rol,
                s.fecha_creacion
            FROM dbo.Servidores AS s
            INNER JOIN dbo.MiembrosServidor AS m
                ON s.id_servidor = m.id_servidor
            WHERE m.id_usuario = CONVERT(UNIQUEIDENTIFIER, ?)
            ORDER BY s.fecha_creacion DESC
        """, id_publico)

        servidores = []

        for fila in cursor.fetchall():
            servidores.append({
                "id_servidor": fila[0],
                "nombre": fila[1],
                "rol": fila[2],
                "fecha_creacion": fila[3].isoformat()
            })

        return servidores

    finally:
        conexion.close()



# OBTENER CANALES DE UN SERVIDOR

def obtener_canales_servidor(id_servidor, id_usuario):

    conexion = conectar_bd()

    try:
        cursor = conexion.cursor()

        cursor.execute("""
            SELECT
                CONVERT(VARCHAR(36), c.id_canal),
                c.nombre,
                c.descripcion,
                c.fecha_creacion
            FROM dbo.Canales AS c
            INNER JOIN dbo.MiembrosServidor AS m
                ON c.id_servidor = m.id_servidor
            WHERE c.id_servidor = CONVERT(UNIQUEIDENTIFIER, ?)
              AND m.id_usuario = CONVERT(UNIQUEIDENTIFIER, ?)
            ORDER BY c.fecha_creacion, c.nombre
        """, id_servidor, id_usuario)

        canales = []

        for fila in cursor.fetchall():
            canales.append({
                "id_canal": fila[0],
                "nombre": fila[1],
                "descripcion": fila[2],
                "fecha_creacion": fila[3].isoformat()
            })

        return canales

    finally:
        conexion.close()


# GUARDAR MENSAJES EN UN CANAL

def guardar_mensaje_canal(id_canal, id_remitente, contenido):

    if not isinstance(contenido, str) or not contenido.strip():
        raise ValueError("El mensaje no puede estar vacío.")

    contenido = contenido.strip()

    if len(contenido) > 4000:
        raise ValueError("El mensaje supera los 4000 caracteres.")

    conexion = conectar_bd()

    try:
        cursor = conexion.cursor()

        cursor.execute("""
            INSERT INTO dbo.MensajesDiscord (
                id_remitente,
                id_canal,
                contenido
            )
            OUTPUT
                INSERTED.id_mensaje,
                INSERTED.fecha_envio
            SELECT
                CONVERT(UNIQUEIDENTIFIER, ?),
                CONVERT(UNIQUEIDENTIFIER, ?),
                ?
            WHERE EXISTS (
                SELECT 1
                FROM dbo.Canales AS c
                INNER JOIN dbo.MiembrosServidor AS m
                    ON c.id_servidor = m.id_servidor
                WHERE c.id_canal = CONVERT(UNIQUEIDENTIFIER, ?)
                  AND m.id_usuario = CONVERT(UNIQUEIDENTIFIER, ?)
            )
        """, id_remitente, id_canal, contenido,
             id_canal, id_remitente)

        fila = cursor.fetchone()

        if fila is None:
            raise ValueError(
                "El usuario no pertenece al servidor de este canal."
            )

        mensaje = {
            "id_mensaje": fila[0],
            "id_canal": id_canal,
            "id_remitente": id_remitente,
            "contenido": contenido,
            "fecha_envio": fila[1].isoformat()
        }

        conexion.commit()

        return mensaje

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()
# OBTENER MIEMBROS DE UN CANAL

def obtener_ids_miembros_canal(id_canal):
    conexion = conectar_bd()
    try:
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT CONVERT(VARCHAR(36), m.id_usuario)
            FROM dbo.MiembrosServidor AS m
            INNER JOIN dbo.Canales AS c
                ON c.id_servidor = m.id_servidor
            WHERE c.id_canal = CONVERT(UNIQUEIDENTIFIER, ?)
        """, id_canal)
        return [fila[0] for fila in cursor.fetchall()]
    finally:
        conexion.close()


# RECUPERAR HISTORIAL DE MENSAJES DE UN CANAL

def obtener_historial_canal(id_canal, id_usuario, limite=50):
    if type(limite) is not int or not 1 <= limite <= 100:
        raise ValueError("El límite debe estar entre 1 y 100 mensajes.")

    conexion = conectar_bd()
    try:
        cursor = conexion.cursor()

        cursor.execute("""
            SELECT 1
            FROM dbo.Canales AS c
            INNER JOIN dbo.MiembrosServidor AS m
                ON m.id_servidor = c.id_servidor
            WHERE c.id_canal = CONVERT(UNIQUEIDENTIFIER, ?)
              AND m.id_usuario = CONVERT(UNIQUEIDENTIFIER, ?)
        """, id_canal, id_usuario)

        if cursor.fetchone() is None:
            raise ValueError("No tienes acceso a este canal.")

        cursor.execute("""
            SELECT TOP (?)
                m.id_mensaje,
                CONVERT(VARCHAR(36), m.id_canal),
                CONVERT(VARCHAR(36), m.id_remitente),
                u.nombre_usuario,
                COALESCE(u.nombre_mostrar, u.nombre_usuario),
                m.contenido,
                m.fecha_envio
            FROM dbo.MensajesDiscord AS m
            INNER JOIN dbo.Usuarios AS u
                ON u.id_publico = m.id_remitente
            WHERE m.id_canal = CONVERT(UNIQUEIDENTIFIER, ?)
            ORDER BY m.id_mensaje DESC
        """, limite, id_canal)

        historial = [
            {
                "id_mensaje": fila[0],
                "id_canal": fila[1],
                "id_remitente": fila[2],
                "usuario": fila[3],
                "nombre_visible": fila[4],
                "contenido": fila[5],
                "fecha_envio": fila[6].isoformat()
            }
            for fila in cursor.fetchall()
        ]
        historial.reverse()
        return historial

    finally:
        conexion.close()


# OBTENER O CREAR CONVERSACIÓN PRIVADA

def obtener_o_crear_conversacion_directa(id_usuario1, id_usuario2):

    try:
        usuario1 = str(UUID(str(id_usuario1)))
        usuario2 = str(UUID(str(id_usuario2)))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Identificador de usuario no válido.")

    if usuario1 == usuario2:
        raise ValueError("No puedes crear una conversación contigo mismo.")

    usuario1, usuario2 = sorted([usuario1, usuario2])

    conexion = conectar_bd()

    try:
        cursor = conexion.cursor()

        cursor.execute("""
            SELECT CONVERT(VARCHAR(36), id_conversacion)
            FROM dbo.ConversacionesDirectas WITH (UPDLOCK, HOLDLOCK)
            WHERE id_usuario1 = CONVERT(UNIQUEIDENTIFIER, ?)
              AND id_usuario2 = CONVERT(UNIQUEIDENTIFIER, ?)
        """, usuario1, usuario2)

        resultado = cursor.fetchone()

        if resultado:
            conexion.commit()
            return resultado[0]

        cursor.execute("""
            INSERT INTO dbo.ConversacionesDirectas
                (id_usuario1, id_usuario2)
            OUTPUT INSERTED.id_conversacion
            VALUES (
                CONVERT(UNIQUEIDENTIFIER, ?),
                CONVERT(UNIQUEIDENTIFIER, ?)
            )
        """, usuario1, usuario2)

        id_conversacion = str(cursor.fetchone()[0])

        conexion.commit()

        return id_conversacion

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()

# GUARDAR MENSAJES PRIVADOS

def guardar_mensaje_privado(id_remitente, id_destinatario, contenido):

    if not isinstance(contenido, str) or not contenido.strip():
        raise ValueError("El mensaje no puede estar vacío.")

    contenido = contenido.strip()

    if len(contenido) > 4000:
        raise ValueError("El mensaje supera los 4000 caracteres.")

    id_remitente = str(UUID(str(id_remitente)))
    id_destinatario = str(UUID(str(id_destinatario)))

    if id_remitente == id_destinatario:
        raise ValueError("No puedes enviarte mensajes a ti mismo.")

    # OBTENER O CREAR CONVERSACIÓN

    id_conversacion = obtener_o_crear_conversacion_directa(
        id_remitente,
        id_destinatario
    )

    conexion = conectar_bd()

    try:
        cursor = conexion.cursor()

        # INSERTAR MENSAJE PRIVADO

        cursor.execute("""
            INSERT INTO dbo.MensajesDiscord (
                id_remitente,
                id_conversacion,
                contenido
            )
            OUTPUT
                INSERTED.id_mensaje,
                INSERTED.fecha_envio
            VALUES (
                CONVERT(UNIQUEIDENTIFIER, ?),
                CONVERT(UNIQUEIDENTIFIER, ?),
                ?
            )
        """, id_remitente, id_conversacion, contenido)

        fila = cursor.fetchone()

        mensaje = {
            "id_mensaje": fila[0],
            "id_conversacion": id_conversacion,
            "id_remitente": id_remitente,
            "id_destinatario": id_destinatario,
            "contenido": contenido,
            "fecha_envio": fila[1].isoformat()
        }

        conexion.commit()

        return mensaje

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()

# OBTENER HISTORIAL DE MENSAJES PRIVADOS

def obtener_historial_privado(id_usuario_actual, id_otro_usuario):

    usuario_actual = str(UUID(str(id_usuario_actual)))
    otro_usuario = str(UUID(str(id_otro_usuario)))

    if usuario_actual == otro_usuario:
        raise ValueError("No puedes consultar una conversación contigo mismo.")

    conexion = conectar_bd()

    try:
        cursor = conexion.cursor()

        cursor.execute("""
            SELECT TOP (50)
                m.id_mensaje,
                CONVERT(VARCHAR(36), m.id_conversacion),
                CONVERT(VARCHAR(36), m.id_remitente),
                u.nombre_usuario,
                COALESCE(u.nombre_mostrar, u.nombre_usuario),
                m.contenido,
                m.fecha_envio
            FROM dbo.MensajesDiscord AS m
            INNER JOIN dbo.ConversacionesDirectas AS cd
                ON m.id_conversacion = cd.id_conversacion
            INNER JOIN dbo.Usuarios AS u
                ON m.id_remitente = u.id_publico
            WHERE (
                (
                    cd.id_usuario1 = CONVERT(UNIQUEIDENTIFIER, ?)
                    AND cd.id_usuario2 = CONVERT(UNIQUEIDENTIFIER, ?)
                )
                OR
                (
                    cd.id_usuario1 = CONVERT(UNIQUEIDENTIFIER, ?)
                    AND cd.id_usuario2 = CONVERT(UNIQUEIDENTIFIER, ?)
                )
            )
            ORDER BY m.id_mensaje DESC
        """, usuario_actual, otro_usuario,
             otro_usuario, usuario_actual)

        mensajes = []

        for fila in reversed(cursor.fetchall()):
            mensajes.append({
                "id_mensaje": fila[0],
                "id_conversacion": fila[1],
                "id_remitente": fila[2],
                "usuario": fila[3],
                "nombre_visible": fila[4],
                "contenido": fila[5],
                "fecha_envio": fila[6].isoformat()
            })

        return mensajes

    finally:
        conexion.close()


# CREAR GRUPOS PRIVADOS

def crear_grupo(nombre, id_creador):

    if not isinstance(nombre, str):
        raise ValueError("Nombre de grupo no válido.")

    nombre = nombre.strip()

    if not nombre or len(nombre) > 100:
        raise ValueError("El nombre debe tener entre 1 y 100 caracteres.")

    try:
        id_creador = str(UUID(str(id_creador)))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Identificador de usuario no válido.")

    conexion = conectar_bd()

    try:
        cursor = conexion.cursor()

        # REGISTRAR GRUPO

        cursor.execute("""
            INSERT INTO dbo.Grupos (nombre, id_creador)
            OUTPUT INSERTED.id_grupo
            VALUES (?, CONVERT(UNIQUEIDENTIFIER, ?))
        """, nombre, id_creador)

        id_grupo = str(cursor.fetchone()[0])

        # AGREGAR AL CREADOR COMO ADMINISTRADOR

        cursor.execute("""
            INSERT INTO dbo.MiembrosGrupo (
                id_grupo,
                id_usuario,
                rol
            )
            VALUES (
                CONVERT(UNIQUEIDENTIFIER, ?),
                CONVERT(UNIQUEIDENTIFIER, ?),
                'Administrador'
            )
        """, id_grupo, id_creador)

        conexion.commit()

        return {
            "id_grupo": id_grupo,
            "nombre": nombre,
            "id_creador": id_creador
        }

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()

# AGREGAR INTEGRANTES A UN GRUPO

def agregar_miembro_grupo(id_grupo, id_administrador, nombre_usuario):

    if not isinstance(nombre_usuario, str):
        raise ValueError("Nombre de usuario no válido.")

    nombre_usuario = nombre_usuario.strip()

    if not nombre_usuario:
        raise ValueError("Debes indicar un usuario.")

    try:
        id_grupo = str(UUID(str(id_grupo)))
        id_administrador = str(UUID(str(id_administrador)))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Identificador no válido.")

    conexion = conectar_bd()

    try:
        cursor = conexion.cursor()

        # VERIFICAR ADMINISTRADOR Y AGREGAR INTEGRANTE

        cursor.execute("""
            INSERT INTO dbo.MiembrosGrupo (
                id_grupo,
                id_usuario,
                rol
            )
            OUTPUT INSERTED.id_usuario
            SELECT
                g.id_grupo,
                u.id_publico,
                'Miembro'
            FROM dbo.Grupos AS g
            INNER JOIN dbo.MiembrosGrupo AS adm
                ON g.id_grupo = adm.id_grupo
            INNER JOIN dbo.Usuarios AS u
                ON u.nombre_usuario = ?
            WHERE g.id_grupo = CONVERT(UNIQUEIDENTIFIER, ?)
              AND adm.id_usuario = CONVERT(UNIQUEIDENTIFIER, ?)
              AND adm.rol = 'Administrador'
        """, nombre_usuario, id_grupo, id_administrador)

        resultado = cursor.fetchone()

        if resultado is None:
            raise ValueError(
                "Usuario inexistente o sin permisos de administrador."
            )

        conexion.commit()

        return {
            "id_grupo": id_grupo,
            "id_usuario": str(resultado[0]),
            "usuario": nombre_usuario,
            "rol": "Miembro"
        }

    except pyodbc.IntegrityError as error:
        conexion.rollback()

        if "2627" in str(error) or "2601" in str(error):
            raise ValueError(
                "El usuario ya pertenece a este grupo."
            ) from error

        raise

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()

# OBTENER INTEGRANTES DE UN GRUPO

def obtener_miembros_grupo(id_grupo, id_usuario):

    try:
        id_grupo = str(UUID(str(id_grupo)))
        id_usuario = str(UUID(str(id_usuario)))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Identificador no válido.")

    conexion = conectar_bd()

    try:
        cursor = conexion.cursor()

        # VERIFICAR ACCESO AL GRUPO

        cursor.execute("""
            SELECT 1
            FROM dbo.MiembrosGrupo
            WHERE id_grupo = CONVERT(UNIQUEIDENTIFIER, ?)
              AND id_usuario = CONVERT(UNIQUEIDENTIFIER, ?)
        """, id_grupo, id_usuario)

        if cursor.fetchone() is None:
            raise ValueError("No perteneces a este grupo.")

        # CONSULTAR INTEGRANTES

        cursor.execute("""
            SELECT
                CONVERT(VARCHAR(36), u.id_publico),
                u.nombre_usuario,
                COALESCE(u.nombre_mostrar, u.nombre_usuario),
                m.rol,
                m.fecha_union
            FROM dbo.MiembrosGrupo AS m
            INNER JOIN dbo.Usuarios AS u
                ON m.id_usuario = u.id_publico
            WHERE m.id_grupo = CONVERT(UNIQUEIDENTIFIER, ?)
            ORDER BY m.fecha_union, u.nombre_usuario
        """, id_grupo)

        integrantes = []

        for fila in cursor.fetchall():
            integrantes.append({
                "id_usuario": fila[0],
                "usuario": fila[1],
                "nombre_visible": fila[2],
                "rol": fila[3],
                "fecha_union": fila[4].isoformat()
            })

        return integrantes

    finally:
        conexion.close()


# GUARDAR MENSAJES DE GRUPO

def guardar_mensaje_grupo(id_grupo, id_remitente, contenido):

    if not isinstance(contenido, str):
        raise ValueError("El contenido debe ser texto.")

    contenido = contenido.strip()

    if not contenido or len(contenido) > 4000:
        raise ValueError("El mensaje debe tener entre 1 y 4000 caracteres.")

    try:
        id_grupo = str(UUID(str(id_grupo)))
        id_remitente = str(UUID(str(id_remitente)))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Identificador no válido.")

    conexion = conectar_bd()

    try:
        cursor = conexion.cursor()

        # VERIFICAR MEMBRESÍA Y GUARDAR EL MENSAJE

        cursor.execute("""
            INSERT INTO dbo.MensajesGrupo (
                id_grupo,
                id_remitente,
                contenido
            )
            OUTPUT
                INSERTED.id_mensaje,
                INSERTED.fecha_envio
            SELECT
                CONVERT(UNIQUEIDENTIFIER, ?),
                CONVERT(UNIQUEIDENTIFIER, ?),
                ?
            WHERE EXISTS (
                SELECT 1
                FROM dbo.MiembrosGrupo
                WHERE id_grupo = CONVERT(UNIQUEIDENTIFIER, ?)
                  AND id_usuario = CONVERT(UNIQUEIDENTIFIER, ?)
            )
        """, id_grupo, id_remitente, contenido,
             id_grupo, id_remitente)

        resultado = cursor.fetchone()

        if resultado is None:
            raise ValueError(
                "No perteneces a este grupo."
            )

        mensaje = {
            "id_mensaje": resultado[0],
            "id_grupo": id_grupo,
            "id_remitente": id_remitente,
            "contenido": contenido,
            "fecha_envio": resultado[1].isoformat()
        }

        conexion.commit()

        return mensaje

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()

# OBTENER HISTORIAL DE MENSAJES GRUPALES

def obtener_historial_grupo(id_grupo, id_usuario):

    try:
        id_grupo = str(UUID(str(id_grupo)))
        id_usuario = str(UUID(str(id_usuario)))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Identificador no válido.")

    conexion = conectar_bd()

    try:
        cursor = conexion.cursor()

        # VERIFICAR QUE EL USUARIO PERTENECE AL GRUPO

        cursor.execute("""
            SELECT 1
            FROM dbo.MiembrosGrupo
            WHERE id_grupo = CONVERT(UNIQUEIDENTIFIER, ?)
              AND id_usuario = CONVERT(UNIQUEIDENTIFIER, ?)
        """, id_grupo, id_usuario)

        if cursor.fetchone() is None:
            raise ValueError(
                "No tienes permiso para consultar este grupo."
            )

        # CONSULTAR LOS ÚLTIMOS 50 MENSAJES

        cursor.execute("""
            SELECT TOP (50)
                m.id_mensaje,
                CONVERT(VARCHAR(36), m.id_grupo),
                CONVERT(VARCHAR(36), m.id_remitente),
                u.nombre_usuario,
                COALESCE(u.nombre_mostrar, u.nombre_usuario),
                m.contenido,
                m.fecha_envio
            FROM dbo.MensajesGrupo AS m
            INNER JOIN dbo.Usuarios AS u
                ON m.id_remitente = u.id_publico
            WHERE m.id_grupo = CONVERT(UNIQUEIDENTIFIER, ?)
            ORDER BY m.id_mensaje DESC
        """, id_grupo)

        mensajes = []

        for fila in reversed(cursor.fetchall()):
            mensajes.append({
                "id_mensaje": fila[0],
                "id_grupo": fila[1],
                "id_remitente": fila[2],
                "usuario": fila[3],
                "nombre_visible": fila[4],
                "contenido": fila[5],
                "fecha_envio": fila[6].isoformat()
            })

        return mensajes

    finally:
        conexion.close()


# CREAR CANALES DE DIFUSION

def crear_canal_difusion(nombre, id_creador, descripcion=""):

    # VALIDAR NOMBRE DEL CANAL

    if not isinstance(nombre, str):
        raise ValueError("El nombre del canal no es valido.")

    nombre = nombre.strip()

    if not nombre or len(nombre) > 100:
        raise ValueError(
            "El nombre debe tener entre 1 y 100 caracteres."
        )

    # VALIDAR DESCRIPCION

    if not isinstance(descripcion, str):
        raise ValueError("La descripcion debe ser texto.")

    descripcion = descripcion.strip()

    if len(descripcion) > 500:
        raise ValueError(
            "La descripcion no puede superar los 500 caracteres."
        )

    # VALIDAR IDENTIFICADOR DEL CREADOR

    try:
        id_creador = str(UUID(str(id_creador)))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Identificador del creador no valido.")

    conexion = conectar_bd()

    try:
        cursor = conexion.cursor()

        # REGISTRAR CANAL EN SQL SERVER

        cursor.execute("""
            INSERT INTO dbo.CanalesDifusion (
                nombre,
                descripcion,
                id_creador
            )
            OUTPUT
                INSERTED.id_canal,
                INSERTED.fecha_creacion
            VALUES (
                ?,
                ?,
                CONVERT(UNIQUEIDENTIFIER, ?)
            )
        """, nombre, descripcion, id_creador)

        resultado = cursor.fetchone()

        id_canal = str(resultado[0])
        fecha_creacion = resultado[1].isoformat()

        # SUSCRIBIR AUTOMATICAMENTE AL CREADOR

        cursor.execute("""
            INSERT INTO dbo.SuscripcionesCanal (
                id_canal,
                id_usuario
            )
            VALUES (
                CONVERT(UNIQUEIDENTIFIER, ?),
                CONVERT(UNIQUEIDENTIFIER, ?)
            )
        """, id_canal, id_creador)

        conexion.commit()

        return {
            "id_canal": id_canal,
            "nombre": nombre,
            "descripcion": descripcion,
            "id_creador": id_creador,
            "fecha_creacion": fecha_creacion
        }

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()


# OBTENER CANALES DE DIFUSION DISPONIBLES

def obtener_canales_difusion(id_usuario):

    # VALIDAR IDENTIFICADOR DEL USUARIO

    try:
        id_usuario = str(UUID(str(id_usuario)))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Identificador de usuario no valido.")

    conexion = conectar_bd()

    try:
        cursor = conexion.cursor()

        # CONSULTAR TODOS LOS CANALES DISPONIBLES

        cursor.execute("""
            SELECT
                CONVERT(VARCHAR(36), c.id_canal),
                c.nombre,
                c.descripcion,
                CONVERT(VARCHAR(36), c.id_creador),
                u.nombre_usuario,
                c.fecha_creacion,
                CASE
                    WHEN s.id_usuario IS NULL THEN 0
                    ELSE 1
                END AS suscrito

            FROM dbo.CanalesDifusion AS c

            INNER JOIN dbo.Usuarios AS u
                ON c.id_creador = u.id_publico

            LEFT JOIN dbo.SuscripcionesCanal AS s
                ON s.id_canal = c.id_canal
                AND s.id_usuario = CONVERT(UNIQUEIDENTIFIER, ?)

            ORDER BY c.fecha_creacion DESC, c.nombre
        """, id_usuario)

        canales = []

        for fila in cursor.fetchall():

            canales.append({
                "id_canal": fila[0],
                "nombre": fila[1],
                "descripcion": fila[2] or "",
                "id_creador": fila[3],
                "creador": fila[4],
                "fecha_creacion": fila[5].isoformat(),
                "suscrito": bool(fila[6]),
                "es_propietario": (
                    str(UUID(fila[3])) == id_usuario
                )
            })

        return canales

    finally:
        conexion.close()

# SUSCRIBIR USUARIO A UN CANAL DE DIFUSION

def suscribirse_canal_difusion(id_canal, id_usuario):

    # VALIDAR IDENTIFICADORES

    try:
        id_canal = str(UUID(str(id_canal)))
        id_usuario = str(UUID(str(id_usuario)))

    except (ValueError, TypeError, AttributeError):
        raise ValueError("Identificador de canal o usuario no valido.")

    conexion = conectar_bd()

    try:
        cursor = conexion.cursor()

        # VERIFICAR QUE EL CANAL EXISTA

        cursor.execute("""
            SELECT nombre
            FROM dbo.CanalesDifusion
            WHERE id_canal = CONVERT(UNIQUEIDENTIFIER, ?)
        """, id_canal)

        canal = cursor.fetchone()

        if canal is None:
            raise ValueError("El canal no existe.")

        nombre_canal = canal[0]

        # VERIFICAR QUE EL USUARIO EXISTA

        cursor.execute("""
            SELECT 1
            FROM dbo.Usuarios
            WHERE id_publico = CONVERT(UNIQUEIDENTIFIER, ?)
        """, id_usuario)

        if cursor.fetchone() is None:
            raise ValueError("El usuario no existe.")

        # EVITAR SUSCRIPCIONES DUPLICADAS

        cursor.execute("""
            SELECT 1
            FROM dbo.SuscripcionesCanal
            WHERE id_canal = CONVERT(UNIQUEIDENTIFIER, ?)
              AND id_usuario = CONVERT(UNIQUEIDENTIFIER, ?)
        """, id_canal, id_usuario)

        if cursor.fetchone() is not None:
            raise ValueError(
                "El usuario ya esta suscrito a este canal."
            )

        # REGISTRAR SUSCRIPCION

        cursor.execute("""
            INSERT INTO dbo.SuscripcionesCanal (
                id_canal,
                id_usuario
            )
            OUTPUT INSERTED.fecha_suscripcion
            VALUES (
                CONVERT(UNIQUEIDENTIFIER, ?),
                CONVERT(UNIQUEIDENTIFIER, ?)
            )
        """, id_canal, id_usuario)

        fecha_suscripcion = cursor.fetchone()[0]

        conexion.commit()

        return {
            "id_canal": id_canal,
            "nombre_canal": nombre_canal,
            "id_usuario": id_usuario,
            "fecha_suscripcion": fecha_suscripcion.isoformat(),
            "suscrito": True
        }

    except pyodbc.IntegrityError as error:
        conexion.rollback()

        if "2627" in str(error) or "2601" in str(error):
            raise ValueError(
                "El usuario ya esta suscrito a este canal."
            ) from error

        raise

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()

# PUBLICAR MENSAJES EN UN CANAL DE DIFUSION

def publicar_canal_difusion(id_canal, id_autor, contenido):

    # VALIDAR CONTENIDO

    if not isinstance(contenido, str):
        raise ValueError("El contenido debe ser texto.")

    contenido = contenido.strip()

    if not contenido or len(contenido) > 4000:
        raise ValueError(
            "La publicacion debe tener entre 1 y 4000 caracteres."
        )

    # VALIDAR IDENTIFICADORES

    try:
        id_canal = str(UUID(str(id_canal)))
        id_autor = str(UUID(str(id_autor)))

    except (ValueError, TypeError, AttributeError):
        raise ValueError("Identificador de canal o autor no valido.")

    conexion = conectar_bd()

    try:
        cursor = conexion.cursor()

        # INSERTAR SOLO SI EL AUTOR ES PROPIETARIO

        cursor.execute("""
            INSERT INTO dbo.PublicacionesCanal (
                id_canal,
                id_autor,
                contenido
            )
            OUTPUT
                INSERTED.id_publicacion,
                INSERTED.fecha_publicacion
            SELECT
                c.id_canal,
                c.id_creador,
                ?
            FROM dbo.CanalesDifusion AS c
            WHERE c.id_canal = CONVERT(UNIQUEIDENTIFIER, ?)
              AND c.id_creador = CONVERT(UNIQUEIDENTIFIER, ?)
        """, contenido, id_canal, id_autor)

        resultado = cursor.fetchone()

        # RECHAZAR PUBLICACIONES NO AUTORIZADAS

        if resultado is None:
            raise ValueError(
                "Solo el propietario del canal puede publicar."
            )

        conexion.commit()

        return {
            "id_publicacion": resultado[0],
            "id_canal": id_canal,
            "id_autor": id_autor,
            "contenido": contenido,
            "fecha_publicacion": resultado[1].isoformat()
        }

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()

# OBTENER HISTORIAL DE UN CANAL DE DIFUSION

def obtener_historial_canal_difusion(id_canal, id_usuario):

    # VALIDAR IDENTIFICADORES

    try:
        id_canal = str(UUID(str(id_canal)))
        id_usuario = str(UUID(str(id_usuario)))

    except (ValueError, TypeError, AttributeError):
        raise ValueError(
            "Identificador de canal o usuario no valido."
        )

    conexion = conectar_bd()

    try:
        cursor = conexion.cursor()

        # COMPROBAR QUE EL CANAL EXISTA

        cursor.execute("""
            SELECT 1
            FROM dbo.CanalesDifusion
            WHERE id_canal = CONVERT(UNIQUEIDENTIFIER, ?)
        """, id_canal)

        if cursor.fetchone() is None:
            raise ValueError("El canal no existe.")

        # VERIFICAR QUE EL USUARIO ESTE SUSCRITO

        cursor.execute("""
            SELECT 1
            FROM dbo.SuscripcionesCanal
            WHERE id_canal = CONVERT(UNIQUEIDENTIFIER, ?)
              AND id_usuario = CONVERT(UNIQUEIDENTIFIER, ?)
        """, id_canal, id_usuario)

        if cursor.fetchone() is None:
            raise ValueError(
                "Debes suscribirte para consultar el historial."
            )

        # OBTENER TODAS LAS PUBLICACIONES DEL CANAL

        cursor.execute("""
            SELECT
                p.id_publicacion,
                CONVERT(VARCHAR(36), p.id_autor),
                u.nombre_usuario,
                p.contenido,
                p.fecha_publicacion

            FROM dbo.PublicacionesCanal AS p

            INNER JOIN dbo.Usuarios AS u
                ON p.id_autor = u.id_publico

            WHERE p.id_canal = CONVERT(UNIQUEIDENTIFIER, ?)

            ORDER BY p.id_publicacion ASC
        """, id_canal)

        historial = []

        for fila in cursor.fetchall():

            historial.append({
                "id_publicacion": fila[0],
                "id_canal": id_canal,
                "id_autor": fila[1],
                "autor": fila[2],
                "contenido": fila[3],
                "fecha_publicacion": fila[4].isoformat()
            })

        return historial

    finally:
        conexion.close()

#FOTOGRAFIAS

def guardar_foto_perfil(id_usuario, datos_imagen, nombre_archivo, mime):

    # VALIDAR USUARIO
    try:
        id_usuario = str(UUID(str(id_usuario)))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Identificador de usuario no valido.")

    # VALIDAR IMAGEN
    if not isinstance(datos_imagen, bytes):
        raise ValueError("La fotografia debe contener datos binarios.")

    if not datos_imagen or len(datos_imagen) > 2 * 1024 * 1024:
        raise ValueError("La fotografia debe pesar maximo 2 MB.")

    # VALIDAR FORMATO REAL DE LA IMAGEN
    es_png = datos_imagen.startswith(b"\x89PNG\r\n\x1a\n")
    es_jpeg = datos_imagen.startswith(b"\xff\xd8\xff")

    if mime == "image/png" and es_png:
        extension = ".png"
    elif mime == "image/jpeg" and es_jpeg:
        extension = ".jpg"
    else:
        raise ValueError("Solo se permiten imagenes PNG o JPEG validas.")

    # GUARDAR NOMBRE SEGURO
    nombre_archivo = "perfil_" + id_usuario + extension

    conexion = conectar_bd()

    try:
        cursor = conexion.cursor()

        cursor.execute("""
            UPDATE dbo.Usuarios
            SET foto_perfil = ?,
                foto_nombre = ?,
                foto_mime = ?
            WHERE id_publico = CONVERT(UNIQUEIDENTIFIER, ?)
        """,
            pyodbc.Binary(datos_imagen),
            nombre_archivo,
            mime,
            id_usuario
        )

        if cursor.rowcount != 1:
            raise ValueError("El usuario no existe.")

        conexion.commit()

        return {
            "id_usuario": id_usuario,
            "nombre": nombre_archivo,
            "mime": mime,
            "tamano": len(datos_imagen)
        }

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()


# RECUPERAR FOTOGRAFIA DE PERFIL

def obtener_foto_perfil(id_usuario):

    try:
        id_usuario = str(UUID(str(id_usuario)))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Identificador de usuario no valido.")

    conexion = conectar_bd()

    try:
        cursor = conexion.cursor()

        cursor.execute("""
            SELECT
                foto_perfil,
                foto_nombre,
                foto_mime
            FROM dbo.Usuarios
            WHERE id_publico = CONVERT(UNIQUEIDENTIFIER, ?)
        """, id_usuario)

        resultado = cursor.fetchone()

        if resultado is None:
            raise ValueError("El usuario no existe.")

        if resultado[0] is None:
            return None

        return {
            "id_usuario": id_usuario,
            "datos": bytes(resultado[0]),
            "nombre": resultado[1],
            "mime": resultado[2]
        }

    finally:
        conexion.close()
