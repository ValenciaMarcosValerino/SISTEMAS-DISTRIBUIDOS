
from db import conectar_bd, guardar_mensaje_privado


# OBTENER LOS IDENTIFICADORES DE MARIANA Y GAEL

conexion = conectar_bd()

try:
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT
            nombre_usuario,
            CONVERT(VARCHAR(36), id_publico)
        FROM dbo.Usuarios
        WHERE nombre_usuario IN (?, ?)
    """, "mariana1234", "gael")

    usuarios = {
        fila[0]: fila[1]
        for fila in cursor.fetchall()
    }

finally:
    conexion.close()


# ENVIAR MENSAJE PRIVADO DE PRUEBA

if "mariana1234" not in usuarios or "gael" not in usuarios:
    print("No se encontraron ambas cuentas.")
else:
    mensaje = guardar_mensaje_privado(
        usuarios["mariana1234"],
        usuarios["gael"],
        "Hola Gael, este es nuestro primer mensaje privado guardado en SQL Server."
    )

    print("Mensaje privado guardado correctamente.")
    print("ID del mensaje:", mensaje["id_mensaje"])
    print("ID de conversación:", mensaje["id_conversacion"])
    print("Contenido:", mensaje["contenido"])
    print("Fecha:", mensaje["fecha_envio"])
