
import os
import pyodbc


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
