import getpass
import json
import socket
import sys


# ENVIAR Y RECIBIR MENSAJES DEL PROTOCOLO TCP

def enviar(sock, datos):
    paquete = (json.dumps(datos, ensure_ascii=False) + "\n").encode("utf-8")
    sock.sendall(paquete)


def recibir_tipo(lector, tipo_esperado):
    for _ in range(100):
        linea = lector.readline()
        if not linea:
            raise ConnectionError("El servidor cerró la conexión.")
        evento = json.loads(linea.decode("utf-8"))
        if evento.get("type") == tipo_esperado:
            return evento
        if evento.get("type") == "error":
            raise RuntimeError(evento.get("text", "Error del servidor."))
    raise RuntimeError(f"No llegó la respuesta: {tipo_esperado}.")


# INICIAR SESIÓN Y BUSCAR CANAL

def main():
    usuario = input("Usuario del Messenger [mariana1234]: ").strip() or "mariana1234"
    contrasena = getpass.getpass("Contraseña de esta cuenta del Messenger: ")

    with socket.create_connection(("127.0.0.1", 5000), timeout=10) as sock:
        sock.settimeout(20)
        with sock.makefile("rb") as lector:
            enviar(sock, {"type": "login", "usuario": usuario, "contrasena": contrasena})
            login = recibir_tipo(lector, "login_result")
            if not login.get("ok"):
                raise RuntimeError(login.get("text", "No se pudo iniciar sesión."))
            print("\nInicio de sesión correcto.")

            enviar(sock, {"type": "list_servers"})
            respuesta = recibir_tipo(lector, "servers_list")
            if not respuesta.get("ok"):
                raise RuntimeError(respuesta.get("text", "No se pudieron consultar servidores."))
            servidores = respuesta.get("servers", [])
            if not servidores:
                raise RuntimeError("Esta cuenta no pertenece a ningún servidor.")
            servidor = next(
                (s for s in servidores if s.get("nombre", "").casefold() == "equipopapois"),
                servidores[0]
            )
            print("Servidor seleccionado:", servidor["nombre"])

            enviar(sock, {"type": "list_channels", "id_servidor": servidor["id_servidor"]})
            respuesta = recibir_tipo(lector, "channels_list")
            if not respuesta.get("ok"):
                raise RuntimeError(respuesta.get("text", "No se pudieron consultar canales."))
            canales = respuesta.get("channels", [])
            canal = next((c for c in canales if c.get("nombre") == "general"), None)
            if canal is None:
                raise RuntimeError("No se encontró el canal #general en el servidor elegido.")
            print("Canal seleccionado: #" + canal["nombre"])

            texto = "Prueba de mensaje TCP con historial persistente."
            enviar(sock, {"type": "send_channel_message", "id_canal": canal["id_canal"], "text": texto})
            respuesta = recibir_tipo(lector, "channel_message_result")
            if not respuesta.get("ok"):
                raise RuntimeError(respuesta.get("text", "No se pudo guardar el mensaje."))
            guardado = respuesta["message"]
            print("\nMensaje guardado. ID:", guardado["id_mensaje"])

            enviar(sock, {"type": "channel_history", "id_canal": canal["id_canal"], "limit": 10})
            respuesta = recibir_tipo(lector, "channel_history_result")
            if not respuesta.get("ok"):
                raise RuntimeError(respuesta.get("text", "No se pudo recuperar el historial."))
            mensajes = respuesta.get("messages", [])
            print("\nÚltimos mensajes del canal:")
            for m in mensajes:
                print(f"  [{m['id_mensaje']}] {m['usuario']}: {m['contenido']}")
            if any(m.get("id_mensaje") == guardado["id_mensaje"] for m in mensajes):
                print("\nPRUEBA CORRECTA: el mensaje enviado por TCP aparece en el historial.")
            else:
                raise RuntimeError("Se guardó el mensaje, pero no apareció en el historial consultado.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        print("\nERROR:", exc)
        sys.exit(1)
