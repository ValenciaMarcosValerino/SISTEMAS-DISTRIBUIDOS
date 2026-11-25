
from db import conectar_bd, obtener_historial_privado


# OBTENER IDENTIFICADORES DE MARIANA Y GAEL

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


# CONSULTAR HISTORIAL PRIVADO

if "mariana1234" not in usuarios or "gael" not in usuarios:
    print("No se encontraron ambas cuentas.")
else:
    mensajes = obtener_historial_privado(
        usuarios["mariana1234"],
        usuarios["gael"]
    )

    print("historial privado entre mariana y gael")
    print("Total de mensajes recuperados:", len(mensajes))

    for mensaje in mensajes:
        print(
            f"[{mensaje['fecha_envio']}] "
            f"{mensaje['usuario']}: {mensaje['contenido']}"
        )
