"""Operaciones SQL para comunidades de Messenger Papoi (paso 17.1).

Se reutilizan las tablas existentes: Servidores, MiembrosServidor y Canales.
No altera los canales de difusión ni la base de datos.
"""
from uuid import UUID
from db import conectar_bd


def _uuid(valor, etiqueta):
    try:
        return str(UUID(str(valor)))
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError(f"{etiqueta} no válido.") from error


def _revisar_administrador(cursor, id_servidor, id_administrador):
    cursor.execute("""
        SELECT 1
        FROM dbo.MiembrosServidor
        WHERE id_servidor = CONVERT(UNIQUEIDENTIFIER, ?)
          AND id_usuario = CONVERT(UNIQUEIDENTIFIER, ?)
          AND rol = N'Administrador'
    """, id_servidor, id_administrador)
    if cursor.fetchone() is None:
        raise ValueError("Solo un administrador del servidor puede realizar esta acción.")


def agregar_integrante_servidor(id_servidor, id_administrador, nombre_usuario):
    """Invita a una cuenta registrada; no requiere que esté conectada."""
    id_servidor = _uuid(id_servidor, "Servidor")
    id_administrador = _uuid(id_administrador, "Administrador")
    if not isinstance(nombre_usuario, str) or not nombre_usuario.strip() or len(nombre_usuario.strip()) > 50:
        raise ValueError("Nombre de usuario no válido.")
    nombre_usuario = nombre_usuario.strip()

    conexion = conectar_bd()
    try:
        cursor = conexion.cursor()
        _revisar_administrador(cursor, id_servidor, id_administrador)
        cursor.execute("""
            SELECT CONVERT(VARCHAR(36), id_publico), nombre_usuario
            FROM dbo.Usuarios WHERE nombre_usuario = ?
        """, nombre_usuario)
        usuario = cursor.fetchone()
        if usuario is None:
            raise ValueError("No existe una cuenta con ese nombre de usuario.")
        id_usuario = str(UUID(str(usuario[0])))
        cursor.execute("""
            SELECT 1 FROM dbo.MiembrosServidor
            WHERE id_servidor = CONVERT(UNIQUEIDENTIFIER, ?)
              AND id_usuario = CONVERT(UNIQUEIDENTIFIER, ?)
        """, id_servidor, id_usuario)
        if cursor.fetchone() is not None:
            raise ValueError("Ese usuario ya pertenece al servidor.")

        cursor.execute("""
            INSERT INTO dbo.MiembrosServidor (id_servidor, id_usuario, rol)
            OUTPUT INSERTED.fecha_union
            VALUES (CONVERT(UNIQUEIDENTIFIER, ?), CONVERT(UNIQUEIDENTIFIER, ?), N'Miembro')
        """, id_servidor, id_usuario)
        fecha = cursor.fetchone()[0]
        conexion.commit()
        return {
            "id_servidor": id_servidor,
            "id_usuario": id_usuario,
            "usuario": str(usuario[1]),
            "rol": "Miembro",
            "fecha_union": fecha.isoformat(),
        }
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def crear_canal_texto_servidor(id_servidor, id_administrador, nombre, descripcion=""):
    id_servidor = _uuid(id_servidor, "Servidor")
    id_administrador = _uuid(id_administrador, "Administrador")
    if not isinstance(nombre, str) or not 1 <= len(nombre.strip()) <= 100:
        raise ValueError("El canal debe tener un nombre de 1 a 100 caracteres.")
    nombre = nombre.strip()
    if not isinstance(descripcion, str) or len(descripcion.strip()) > 255:
        raise ValueError("La descripción no puede exceder 255 caracteres.")
    descripcion = descripcion.strip()

    conexion = conectar_bd()
    try:
        cursor = conexion.cursor()
        _revisar_administrador(cursor, id_servidor, id_administrador)
        cursor.execute("""
            SELECT 1 FROM dbo.Canales
            WHERE id_servidor = CONVERT(UNIQUEIDENTIFIER, ?)
              AND nombre = ?
        """, id_servidor, nombre)
        if cursor.fetchone() is not None:
            raise ValueError("Ya existe un canal con ese nombre en el servidor.")
        cursor.execute("""
            INSERT INTO dbo.Canales (id_servidor, nombre, descripcion)
            OUTPUT INSERTED.id_canal, INSERTED.fecha_creacion
            VALUES (CONVERT(UNIQUEIDENTIFIER, ?), ?, ?)
        """, id_servidor, nombre, descripcion)
        fila = cursor.fetchone()
        conexion.commit()
        return {
            "id_canal": str(UUID(str(fila[0]))),
            "id_servidor": id_servidor,
            "nombre": nombre,
            "descripcion": descripcion,
            "fecha_creacion": fila[1].isoformat(),
        }
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def listar_integrantes_servidor(id_servidor, id_consultante):
    id_servidor = _uuid(id_servidor, "Servidor")
    id_consultante = _uuid(id_consultante, "Usuario")
    conexion = conectar_bd()
    try:
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT 1 FROM dbo.MiembrosServidor
            WHERE id_servidor = CONVERT(UNIQUEIDENTIFIER, ?)
              AND id_usuario = CONVERT(UNIQUEIDENTIFIER, ?)
        """, id_servidor, id_consultante)
        if cursor.fetchone() is None:
            raise ValueError("No perteneces a este servidor.")
        cursor.execute("""
            SELECT CONVERT(VARCHAR(36), u.id_publico),
                   u.nombre_usuario,
                   COALESCE(u.nombre_mostrar, u.nombre_usuario),
                   m.rol
            FROM dbo.MiembrosServidor AS m
            INNER JOIN dbo.Usuarios AS u ON u.id_publico = m.id_usuario
            WHERE m.id_servidor = CONVERT(UNIQUEIDENTIFIER, ?)
            ORDER BY CASE WHEN m.rol = N'Administrador' THEN 0 ELSE 1 END,
                     u.nombre_usuario
        """, id_servidor)
        return [{
            "id_usuario": str(UUID(str(fila[0]))),
            "usuario": fila[1],
            "nombre_visible": fila[2],
            "rol": fila[3],
        } for fila in cursor.fetchall()]
    finally:
        conexion.close()
