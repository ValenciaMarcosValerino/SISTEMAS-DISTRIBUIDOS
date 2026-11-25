
from db import conectar_bd, guardar_mensaje_grupo

# BUSCAR EL GRUPO Y A MARIANA

conexion = conectar_bd()

try:
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT TOP 1
            CONVERT(VARCHAR(36), g.id_grupo),
            CONVERT(VARCHAR(36), u.id_publico)
        FROM dbo.Grupos AS g
        INNER JOIN dbo.Usuarios AS u
            ON g.id_creador = u.id_publico
        WHERE g.nombre = ?
          AND u.nombre_usuario = ?
        ORDER BY g.fecha_creacion DESC
    """, "Grupo Papois", "mariana1234")

    resultado = cursor.fetchone()

finally:
    conexion.close()


# GUARDAR MENSAJE GRUPAL

if resultado is None:
    print("No se encontro el grupo.")
else:
    mensaje = guardar_mensaje_grupo(
        resultado[0],
        resultado[1],
        "Hola Gael, este es nuestro primer mensaje grupal."
    )

    print("Mensaje grupal guardado correctamente.")
    print("ID del mensaje:", mensaje["id_mensaje"])
    print("ID del grupo:", mensaje["id_grupo"])
    print("Contenido:", mensaje["contenido"])
    print("Fecha:", mensaje["fecha_envio"])
