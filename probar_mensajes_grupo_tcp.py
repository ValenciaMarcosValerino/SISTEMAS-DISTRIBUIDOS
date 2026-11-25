"""Prueba TCP de mensajes grupales en ambos sentidos.

Requisitos:
    - server.py actualizado escuchando en 127.0.0.1:5000.
    - Cuentas mariana1234 y gael1234 sin otras sesiones activas.

Crea un grupo de prueba nuevo, incorpora a Gael y comprueba
la entrega de un mensaje en cada dirección. No almacena contraseñas.
"""

import getpass
import json
import socket
from contextlib import ExitStack
from uuid import UUID

HOST = "127.0.0.1"
PORT = 5000
TIMEOUT = 20


def enviar(sock, contenido):
    sock.sendall((json.dumps(contenido, ensure_ascii=False) + "\n").encode("utf-8"))


def recibir_tipo(lector, tipo_esperado):
    """Ignora notificaciones de presencia y espera la respuesta pertinente."""
    while True:
        linea = lector.readline()
        if not linea:
            raise ConnectionError("El servidor cerro la conexion.")

        respuesta = json.loads(linea)
        if not isinstance(respuesta, dict):
            continue
        tipo = respuesta.get("type")
        if tipo == tipo_esperado:
            return respuesta
        if tipo == "error":
            raise RuntimeError(respuesta.get("text", "Error del servidor."))


def conectar_y_autenticar(pila, usuario, contrasena):
    sock = pila.enter_context(
        socket.create_connection((HOST, PORT), timeout=TIMEOUT)
    )
    sock.settimeout(TIMEOUT)
    lector = pila.enter_context(sock.makefile("r", encoding="utf-8"))

    enviar(sock, {"type": "login", "usuario": usuario, "contrasena": contrasena})
    respuesta = recibir_tipo(lector, "login_result")
    if not respuesta.get("ok"):
        raise RuntimeError(
            f"No se pudo iniciar sesion como {usuario}: {respuesta.get('text')}"
        )
    print(f"[OK] {usuario} conectado y autenticado.")
    return sock, lector


def comprobar_mensaje(respuesta, id_grupo, contenido, usuario):
    mensaje = respuesta.get("message")
    if not isinstance(mensaje, dict):
        raise RuntimeError("La respuesta no contiene un mensaje valido.")
    try:
        grupo_recibido = UUID(str(mensaje.get("id_grupo")))
    except (ValueError, TypeError, AttributeError) as error:
        raise RuntimeError("El mensaje contiene un ID de grupo invalido.") from error

    if grupo_recibido != id_grupo:
        raise RuntimeError("El mensaje corresponde a un grupo distinto.")
    if mensaje.get("contenido") != contenido:
        raise RuntimeError("El contenido recibido no coincide.")
    if mensaje.get("usuario") != usuario:
        raise RuntimeError("El remitente recibido no coincide.")


def main():
    print("PRUEBA DE MENSAJES GRUPALES POR TCP")
    print("Cierra Messenger si Mariana o Gael tienen una sesion activa.\n")
    contrasena_mariana = getpass.getpass("Contrasena de mariana1234: ")
    contrasena_gael = getpass.getpass("Contrasena de gael1234: ")

    with ExitStack() as pila:
        sock_mariana, lector_mariana = conectar_y_autenticar(
            pila, "mariana1234", contrasena_mariana
        )
        sock_gael, lector_gael = conectar_y_autenticar(
            pila, "gael1234", contrasena_gael
        )

        # Crear un grupo diferente en cada ejecucion.
        enviar(sock_mariana, {"type": "create_group", "nombre": "Grupo Prueba Mensajes TCP"})
        creacion = recibir_tipo(lector_mariana, "create_group_result")
        if not creacion.get("ok"):
            raise RuntimeError("Error al crear grupo: " + str(creacion.get("text")))

        grupo = creacion.get("grupo")
        id_texto = grupo.get("id_grupo") if isinstance(grupo, dict) else grupo
        try:
            id_grupo = UUID(str(id_texto))
        except (ValueError, TypeError, AttributeError) as error:
            raise RuntimeError("ID de grupo creado no valido.") from error
        print("[OK] Grupo de prueba creado:", id_grupo)

        # Inscribir a Gael, que ya esta conectado.
        enviar(sock_mariana, {
            "type": "add_group_member",
            "id_grupo": str(id_grupo),
            "usuario": "gael1234",
        })
        alta = recibir_tipo(lector_mariana, "add_group_member_result")
        if not alta.get("ok"):
            raise RuntimeError("Error al agregar a Gael: " + str(alta.get("text")))

        aviso = recibir_tipo(lector_gael, "group_added")
        if UUID(str(aviso.get("id_grupo"))) != id_grupo:
            raise RuntimeError("El aviso de grupo no coincide.")
        print("[OK] Gael fue incorporado y recibio el aviso TCP.")

        # Mariana envia; Gael recibe en su socket independiente.
        texto_mariana = "Hola Gael, mensaje grupal enviado por TCP."
        enviar(sock_mariana, {
            "type": "send_group_message",
            "id_grupo": str(id_grupo),
            "text": texto_mariana,
        })
        confirmacion = recibir_tipo(lector_mariana, "group_message_result")
        if not confirmacion.get("ok"):
            raise RuntimeError("Error al enviar mensaje: " + str(confirmacion.get("text")))
        comprobar_mensaje(confirmacion, id_grupo, texto_mariana, "mariana1234")

        recibido_gael = recibir_tipo(lector_gael, "group_message")
        comprobar_mensaje(recibido_gael, id_grupo, texto_mariana, "mariana1234")
        print("[OK] Mariana envio su mensaje; Gael lo recibio por TCP.")

        # Gael responde; Mariana recibe en su socket independiente.
        texto_gael = "Hola Mariana, recibi el mensaje y respondo por TCP."
        enviar(sock_gael, {
            "type": "send_group_message",
            "id_grupo": str(id_grupo),
            "text": texto_gael,
        })
        confirmacion_gael = recibir_tipo(lector_gael, "group_message_result")
        if not confirmacion_gael.get("ok"):
            raise RuntimeError("Error al responder: " + str(confirmacion_gael.get("text")))
        comprobar_mensaje(confirmacion_gael, id_grupo, texto_gael, "gael1234")

        recibido_mariana = recibir_tipo(lector_mariana, "group_message")
        comprobar_mensaje(recibido_mariana, id_grupo, texto_gael, "gael1234")
        print("[OK] Gael respondio; Mariana recibio su mensaje por TCP.")
        print("\nPRUEBA COMPLETA: CHAT GRUPAL BIDIRECCIONAL POR TCP CORRECTO.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ConnectionError, RuntimeError, ValueError,
            TypeError, json.JSONDecodeError) as error:
        print("\nPRUEBA NO COMPLETADA:", error)
