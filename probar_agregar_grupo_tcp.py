import getpass
import json
import socket
from contextlib import ExitStack
from uuid import UUID


HOST = "127.0.0.1"
PORT = 5000
TIMEOUT = 15


def enviar(sock, contenido):
    datos = (json.dumps(contenido, ensure_ascii=False) + "\n").encode("utf-8")
    sock.sendall(datos)


def recibir_tipo(lector, tipo_esperado):
    """Espera una respuesta del tipo solicitado e ignora eventos informativos."""
    while True:
        linea = lector.readline()
        if not linea:
            raise ConnectionError("Se cerró la conexión con el servidor.")

        respuesta = json.loads(linea)
        if respuesta.get("type") == tipo_esperado:
            return respuesta

        if respuesta.get("type") == "error":
            raise RuntimeError(respuesta.get("text", "Error del servidor."))


def conectar_y_autenticar(pila, usuario, contrasena):
    sock = pila.enter_context(
        socket.create_connection((HOST, PORT), timeout=TIMEOUT)
    )
    sock.settimeout(TIMEOUT)
    lector = pila.enter_context(sock.makefile("r", encoding="utf-8"))

    enviar(sock, {
        "type": "login",
        "usuario": usuario,
        "contrasena": contrasena,
    })

    respuesta = recibir_tipo(lector, "login_result")
    if not respuesta.get("ok"):
        raise RuntimeError(
            f"No se pudo iniciar sesión como {usuario}: {respuesta.get('text')}"
        )

    print(f"✓ {usuario}: conectado y autenticado.")
    return sock, lector


def main():
    print("PRUEBA DE GRUPOS POR SOCKETS TCP")
    print("Antes de iniciar, cierra Messenger si Mariana o Gael están conectados allí.\n")

    contrasena_mariana = getpass.getpass("Contraseña de mariana1234: ")
    contrasena_gael = getpass.getpass("Contraseña de gael1234: ")

    with ExitStack() as pila:
        sock_mariana, lector_mariana = conectar_y_autenticar(
            pila, "mariana1234", contrasena_mariana
        )
        _sock_gael, lector_gael = conectar_y_autenticar(
            pila, "gael1234", contrasena_gael
        )

        # Cada ejecución crea un grupo nuevo para no repetir integrantes.
        enviar(sock_mariana, {
            "type": "create_group",
            "nombre": "Grupo TCP Integrantes",
        })
        creacion = recibir_tipo(lector_mariana, "create_group_result")

        if not creacion.get("ok"):
            raise RuntimeError(f"No se pudo crear el grupo: {creacion.get('text')}")

        grupo = creacion.get("grupo")
        id_grupo = grupo.get("id_grupo") if isinstance(grupo, dict) else grupo

        try:
            uuid_grupo = UUID(str(id_grupo))
        except (ValueError, TypeError, AttributeError) as error:
            raise RuntimeError(f"El servidor no devolvió un ID de grupo válido: {grupo!r}") from error

        print("✓ Mariana creó un grupo por TCP:", id_grupo)

        enviar(sock_mariana, {
            "type": "add_group_member",
            "id_grupo": str(uuid_grupo),
            "usuario": "gael1234",
        })
        alta = recibir_tipo(lector_mariana, "add_group_member_result")

        if not alta.get("ok"):
            raise RuntimeError(f"No se pudo agregar a Gael: {alta.get('text')}")

        print("✓ Gael agregado como integrante:", alta.get("integrante"))

        # Comprobar el aviso dirigido al socket de Gael.
        notificacion = recibir_tipo(lector_gael, "group_added")
        id_notificado = notificacion.get("id_grupo")

        print("ID del grupo creado:", repr(id_grupo))
        print("ID de la notificación:", repr(id_notificado))

        try:
            uuid_notificado = UUID(str(id_notificado))
        except (ValueError, TypeError, AttributeError) as error:
            raise RuntimeError("La notificación contiene un ID de grupo inválido.") from error

        if uuid_notificado != uuid_grupo:
            raise RuntimeError("La notificación recibida corresponde a otro grupo.")

        print("✓ Gael recibió la notificación TCP de incorporación.")
        print("\nPRUEBA COMPLETA: CREACIÓN, ALTA Y NOTIFICACIÓN POR TCP CORRECTAS.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ConnectionError, TimeoutError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print("\nPRUEBA NO COMPLETADA:", error)
