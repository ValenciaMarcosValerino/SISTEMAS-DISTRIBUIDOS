
from db import conectar_bd, guardar_mensaje_canal


# BUSCAR A MARIANA Y SU CANAL GENERAL

conexion = conectar_bd()

try:
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT
            CONVERT(VARCHAR(36), u.id_publico),
            CONVERT(VARCHAR(36), c.id_canal)
        FROM dbo.Usuarios AS u
        INNER JOIN dbo.MiembrosServidor AS m
            ON u.id_publico = m.id_usuario
        INNER JOIN dbo.Servidores AS s
            ON m.id_servidor = s.id_servidor
        INNER JOIN dbo.Canales AS c
            ON s.id_servidor = c.id_servidor
        WHERE u.nombre_usuario = ?
          AND s.nombre = ?
          AND c.nombre = ?
    """, "mariana1234", "equipoPapois", "general")

    resultado = cursor.fetchone()

finally:
    conexion.close()


# GUARDAR MENSAJE DE PRUEBA

if resultado is None:
    print("No se encontró el usuario o el canal.")
else:
    id_usuario = resultado[0]
    id_canal = resultado[1]

    mensaje = guardar_mensaje_canal(
        id_canal,
        id_usuario,
        "Hola, soy Mariana. Este mensaje se guardó en SQL Server."
    )

    print("Mensaje guardado correctamente")
    print(mensaje)
