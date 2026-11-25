
from db import conectar_bd, obtener_historial_grupo


# BUSCAR GRUPO Y USUARIOS

conexion = conectar_bd()

try:
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT TOP 1 CONVERT(VARCHAR(36), id_grupo)
        FROM dbo.Grupos
        WHERE nombre = ?
        ORDER BY fecha_creacion DESC
    """, "Grupo Papois")

    grupo = cursor.fetchone()

    cursor.execute("""
        SELECT nombre_usuario, CONVERT(VARCHAR(36), id_publico)
        FROM dbo.Usuarios
        WHERE nombre_usuario IN (?, ?, ?)
    """, "mariana1234", "gael1234", "daniela")

    usuarios = {fila[0]: fila[1] for fila in cursor.fetchall()}

finally:
    conexion.close()


# VERIFICAR HISTORIAL DE LOS INTEGRANTES

if grupo is None or len(usuarios) != 3:
    print("No se encontró el grupo o alguno de los usuarios.")

else:
    id_grupo = grupo[0]

    for nombre in ("mariana1234", "gael1234"):

        print(f"\nHISTORIAL CONSULTADO POR {nombre}")

        mensajes = obtener_historial_grupo(
            id_grupo, usuarios[nombre]
        )

        print("Total de mensajes:", len(mensajes))

        for mensaje in mensajes:
            print(
                f"{mensaje['usuario']}: {mensaje['contenido']}"
            )

    # PROBAR ACCESO DE UN USUARIO AJENO AL GRUPO

    print("\nPRUEBA DE SEGURIDAD CON DANIELA")

    try:
        obtener_historial_grupo(
            id_grupo, usuarios["daniela"]
        )
        print("ERROR: Daniela pudo consultar el grupo.")

    except ValueError as error:
        print("Acceso denegado correctamente:", error)
