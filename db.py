
import os
import pyodbc
from argon2 import PasswordHasher
from argon2.low_level import Type
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError


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

    password = os.getenv("SQL_MESSENGER_PASSWORD")

    if not password:
        raise RuntimeError("Falta la contraseña de SQL Server")

    return pyodbc.connect(
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=127.0.0.1,1433;"
        "DATABASE=BDD_Messenger;"
        "UID=sa;"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;",
        PWD=password,
        timeout=5
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

    print("Conexión exitosa con BDD_Messenger")

    conexion.close()
