import getpass
import json
import socket
from contextlib import ExitStack
from uuid import UUID

from db import conectar_bd

HOST = "127.0.0.1"
PORT = 5000
TIMEOUT = 20
NOMBRE_GRUPO = "Grupo Prueba Mensajes TCP"

# Mensajes guardados durante nuestra prueba bidireccional anterior.
MENSAJES_ESPERADOS = {
    ("mariana1234", "Hola Gael, mensaje grupal enviado por TCP."),
    ("gael1234", "Hola Mariana, recibi el mensaje y respondo por TCP."),
}


def encontrar_grupo_existente():
    """Busca el grupo de prueba mas reciente sin leer su historial."""
    conexion = conectar_bd()
    try:
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT TOP (1) CONVERT(VARCHAR(36), g.id_grupo)
            FROM dbo.Grupos AS g
            JOIN dbo.Usuarios AS creadora
                ON g.id_creador = creadora.id_publico
            WHERE g.nombre = ?
              AND creadora.nombre_usuario = ?
              AND EXISTS (
                  SELECT 1
                  FROM dbo.MiembrosGrupo AS mg
                  JOIN dbo.Usuarios AS u ON mg.id_usuario = u.id_publico
                  WHERE mg.id_grupo = g.id_grupo
                    AND u.nombre_usuario = ?
              )
              AND EXISTS (
                  SELECT 1 FROM dbo.MensajesGrupo AS m
                  WHERE m.id_grupo = g.id_grupo
              )
            ORDER BY g.fecha_creacion DESC
        """, NOMBRE_GRUPO, "mariana1234", "gael1234")
        fila = cursor.fetchone()
        if fila is None:
            raise RuntimeError(
                "No encontre un grupo de la prueba anterior con mensajes. "
                "Primero ejecuta probar_mensajes_grupo_tcp.py."
            )
        return UUID(str(fila[0]))
    finally:
        conexion.close()


def enviar(sock, datos):
    paquete = (json.dumps(datos, ensure_ascii=False) + "\n").encode("utf-8")
    sock.sendall(paquete)


def recibir_tipo(lector, esperado):
    """Ignora avisos de presencia y otros eventos que lleguen por TCP."""
    while True:
        linea = lector.readline()
        if not linea:
            raise ConnectionError("El servidor cerro la conexion.")
        respuesta = json.loads(linea)
        if not isinstance(respuesta, dict):
            continue
        if respuesta.get("type") == esperado:
            return respuesta
        if respuesta.get("type") == "error":
            raise RuntimeError(respuesta.get("text", "Error del servidor."))


def conectar(pila, nombre, contrasena):
    sock = pila.enter_context(socket.create_connection((HOST, PORT), timeout=TIMEOUT))
    sock.settimeout(TIMEOUT)
    lector = pila.enter_context(sock.makefile("r", encoding="utf-8"))
    enviar(sock, {
        "type": "login",
        "usuario": nombre,
        "contrasena": contrasena,
    })
    respuesta = recibir_tipo(lector, "login_result")
    if not respuesta.get("ok"):
        raise RuntimeError(f"No pude iniciar sesion con {nombre}: {respuesta.get('text')}")
    print(f"[OK] {nombre} inicio sesion por TCP.")
    return sock, lector


def pedir_historial(sock, lector, id_grupo):
    enviar(sock, {"type": "group_history", "id_grupo": str(id_grupo)})
    respuesta = recibir_tipo(lector, "group_history_result")
    return respuesta


def verificar_historial(respuesta, id_grupo, usuario):
    if respuesta.get("ok") is not True:
        raise RuntimeError(f"Historial denegado para {usuario}: {respuesta.get('text')}")
    try:
        id_respuesta = UUID(str(respuesta.get("id_grupo")))
    except (TypeError, ValueError, AttributeError) as error:
        raise RuntimeError(f"El historial de {usuario} no tiene un UUID valido.") from error
    if id_respuesta != id_grupo:
        raise RuntimeError(f"El historial de {usuario} pertenece a otro grupo.")

    mensajes = respuesta.get("messages")
    if not isinstance(mensajes, list):
        raise RuntimeError(f"El servidor no devolvio una lista de mensajes a {usuario}.")

    encontrados = {
        (m.get("usuario"), m.get("contenido"))
        for m in mensajes if isinstance(m, dict)
    }
    faltantes = MENSAJES_ESPERADOS - encontrados
    if faltantes:
        raise RuntimeError(
            f"Al historial de {usuario} le faltan mensajes de la prueba: {faltantes}"
        )
    print(f"[OK] {usuario} recupero {len(mensajes)} mensajes por TCP.")
    return mensajes


def main():
    print("PRUEBA DE HISTORIAL GRUPAL Y PERMISOS POR TCP\n")
    print("Cierra otras sesiones de Mariana, Gael y el tercer usuario.\n")
    usuario_ajeno = input("Cuenta ajena al grupo [daniela]: ").strip() or "daniela"
    if usuario_ajeno.casefold() in ("mariana1234", "gael1234"):
        raise RuntimeError("La tercera cuenta debe ser diferente de Mariana y Gael.")

    pwd_mariana = getpass.getpass("Contrasena de mariana1234: ")
    pwd_gael = getpass.getpass("Contrasena de gael1234: ")
    pwd_ajeno = getpass.getpass(f"Contrasena de {usuario_ajeno}: ")

    grupo = encontrar_grupo_existente()
    print(f"\n[OK] Grupo ya existente: {NOMBRE_GRUPO} ({grupo})")

    with ExitStack() as pila:
        s_mariana, l_mariana = conectar(pila, "mariana1234", pwd_mariana)
        s_gael, l_gael = conectar(pila, "gael1234", pwd_gael)
        s_ajeno, l_ajeno = conectar(pila, usuario_ajeno, pwd_ajeno)

        hist_mariana = verificar_historial(
            pedir_historial(s_mariana, l_mariana, grupo), grupo, "mariana1234"
        )
        hist_gael = verificar_historial(
            pedir_historial(s_gael, l_gael, grupo), grupo, "gael1234"
        )
        if hist_mariana != hist_gael:
            raise RuntimeError("Mariana y Gael recibieron historiales diferentes.")
        print("[OK] Ambos usuarios recibieron exactamente el mismo historial.")

        respuesta_ajeno = pedir_historial(s_ajeno, l_ajeno, grupo)
        if respuesta_ajeno.get("ok") is not False:
            raise RuntimeError("FALLO DE SEGURIDAD: el usuario ajeno pudo leer el grupo.")
        if respuesta_ajeno.get("messages"):
            raise RuntimeError("FALLO DE SEGURIDAD: se filtraron mensajes al usuario ajeno.")
        print(f"[OK] Acceso denegado a {usuario_ajeno}: {respuesta_ajeno.get('text')}")

        print("\nPRUEBA COMPLETA: HISTORIAL GRUPAL POR TCP Y PRIVACIDAD CORRECTOS.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ConnectionError, RuntimeError, ValueError,
            TypeError, json.JSONDecodeError) as error:
        print("\nPRUEBA NO COMPLETADA:", error)
