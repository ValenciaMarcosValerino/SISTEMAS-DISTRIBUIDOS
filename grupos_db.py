"""Consultas de grupos adicionales para la interfaz gráfica.

Se utiliza db.conectar_bd, sin copiar ni almacenar credenciales.
"""

from uuid import UUID
from db import conectar_bd


def obtener_grupos_usuario(id_usuario):
    """Devuelve solamente los grupos de un usuario autenticado."""
    try:
        id_usuario = str(UUID(str(id_usuario)))
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError("Identificador de usuario no válido.") from error

    conexion = conectar_bd()
    try:
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT
                CONVERT(VARCHAR(36), g.id_grupo),
                g.nombre,
                m.rol,
                g.fecha_creacion
            FROM dbo.Grupos AS g
            INNER JOIN dbo.MiembrosGrupo AS m
                ON m.id_grupo = g.id_grupo
            WHERE m.id_usuario = CONVERT(UNIQUEIDENTIFIER, ?)
            ORDER BY g.fecha_creacion DESC, g.nombre
        """, id_usuario)
        return [
            {
                "id_grupo": fila[0],
                "nombre": fila[1],
                "rol": fila[2],
                "fecha_creacion": fila[3].isoformat(),
            }
            for fila in cursor.fetchall()
        ]
    finally:
        conexion.close()
