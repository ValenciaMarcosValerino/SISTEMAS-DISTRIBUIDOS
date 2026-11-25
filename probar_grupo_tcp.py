
import socket
import json
import getpass


# DATOS DEL USUARIO
usuario = input("Usuario: ").strip()
contrasena = getpass.getpass("Contrasena: ")


# ENVIAR MENSAJES AL SERVIDOR
def enviar(sock, mensaje):
    datos = (json.dumps(mensaje) + "\n").encode("utf-8")
    sock.sendall(datos)


# CONECTAR AL SERVIDOR
try:
    with socket.create_connection(
        ("127.0.0.1", 5000), timeout=10
    ) as sock:

        sock.settimeout(15)
        archivo = sock.makefile("r", encoding="utf-8")

        # INICIAR SESION
        enviar(sock, {
            "type": "login",
            "usuario": usuario,
            "contrasena": contrasena
        })

        while True:
            linea = archivo.readline()

            if not linea:
                raise ConnectionError("Servidor desconectado.")

            respuesta = json.loads(linea)

            if respuesta.get("type") == "login_result":
                break

        if not respuesta.get("ok"):
            print("ERROR:", respuesta.get("text"))

        else:
            print("Inicio de sesion correcto.")

            # CREAR GRUPO MEDIANTE TCP
            enviar(sock, {
                "type": "create_group",
                "nombre": "Grupo TCP Prueba"
            })

            while True:
                linea = archivo.readline()

                if not linea:
                    raise ConnectionError("Servidor desconectado.")

                respuesta = json.loads(linea)

                if respuesta.get("type") == "create_group_result":
                    break

            if respuesta.get("ok"):
                print("GRUPO CREADO CORRECTAMENTE POR TCP")
                print("Grupo:", respuesta.get("grupo"))
            else:
                print("ERROR:", respuesta.get("text"))

except (OSError, ConnectionError, ValueError) as error:
    print("Error en la prueba:", error)
