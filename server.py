
import socket
import threading
import json
from db import registrar_usuario

# CLASE CLIENTE

class Cliente:
    def __init__(self, conn, addr):
        self.name = ""
        self.conn = conn
        self.addr = addr
        self.send_lock = threading.Lock()


# VARIABLES DEL SERVIDOR

host = "127.0.0.1"
port = 5000
BUFFER_SIZE = 4096

list_of_clients = []
clientes_lock = threading.Lock()


# FUNCIÓN PARA ENVIAR DATOS

def enviar(cliente, mensaje):
    datos = (json.dumps(mensaje, ensure_ascii=False) + "\n").encode("utf-8")

    try:
        with cliente.send_lock:
            cliente.conn.sendall(datos)
        return True

    except OSError:
        return False


# FUNCIÓN PARA ENVIAR MENSAJES A TODOS

def broadcast(mensaje, excluir=None):
    with clientes_lock:
        clientes = [
            c for c in list_of_clients
            if c.name and c != excluir
        ]

    for cliente in clientes:
        if not enviar(cliente, mensaje):
            remove(cliente)


# FUNCIÓN PARA OBTENER UN CLIENTE

def buscar_cliente(nombre):
    with clientes_lock:
        for cliente in list_of_clients:
            if cliente.name.casefold() == nombre.casefold() and cliente.name:
                return cliente

    return None



# FUNCIÓN PARA ASIGNAR NOMBRE AL CLIENTE

def setName(cliente, nombre):

    nombre = nombre.strip()

    if not nombre or len(nombre) > 30 or nombre.casefold() == "chat general":
        enviar(cliente, {
            "type": "error",
            "text": "Nombre de usuario no válido."
        })
        return False

    with clientes_lock:
        existe = any(
            c.name.casefold() == nombre.casefold()
            for c in list_of_clients
            if c.name
        )

        if not existe:
            cliente.name = nombre

    if existe:
        enviar(cliente, {
            "type": "error",
            "text": f"El usuario {nombre} ya está conectado."
        })
        return False

    try:
        registrar_usuario(nombre)

    except Exception as error:
        with clientes_lock:
            cliente.name = ""

        print(f"Error en BDD: {error}")

        enviar(cliente, {
            "type": "error",
            "text": "No se pudo registrar el usuario."
        })
        return False

    enviar(cliente, {
        "type": "system",
        "text": f"Bienvenido {nombre}"
    })

    broadcast({
        "type": "system",
        "text": f"{nombre} se ha conectado."
    }, cliente)

    enviar_lista_usuarios()

    return True

# FUNCIÓN PARA ENVIAR LA LISTA DE USUARIOS

def enviar_lista_usuarios():
    with clientes_lock:
        nombres = [
            c.name for c in list_of_clients
            if c.name
        ]

    broadcast({
        "type": "users",
        "users": nombres
    })


# FUNCIÓN PARA ELIMINAR CLIENTES

def remove(cliente):
    with clientes_lock:
        if cliente not in list_of_clients:
            return

        list_of_clients.remove(cliente)
        nombre = cliente.name

    try:
        cliente.conn.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass

    cliente.conn.close()

    print(f"Cliente desconectado: {cliente.addr}")

    if nombre:
        broadcast({
            "type": "system",
            "text": f"{nombre} se ha desconectado."
        })

        enviar_lista_usuarios()


# FUNCIÓN PARA ATENDER A CADA CLIENTE

def clientthread(cliente):
    buffer = b""

    try:
        while True:
            datos = cliente.conn.recv(BUFFER_SIZE)

            if not datos:
                break

            buffer += datos

            if len(buffer) > 1048576:
                break

            while b"\n" in buffer:
                linea, buffer = buffer.split(b"\n", 1)

                if not linea:
                    continue

                try:
                    mensaje = json.loads(linea.decode("utf-8"))
                except (UnicodeError, ValueError):
                    enviar(cliente, {
                        "type": "error",
                        "text": "Formato de mensaje no válido."
                    })
                    continue

                if not isinstance(mensaje, dict):
                    continue

                tipo = mensaje.get("type")

                if not cliente.name:
                    nombre = mensaje.get("name")

                    if tipo != "join" or not isinstance(nombre, str):
                        return

                    if not setName(cliente, nombre):
                        return

                    continue

                if tipo == "public":
                    texto = mensaje.get("text", "")

                    if isinstance(texto, str) and texto.strip():
                        broadcast({
                            "type": "public",
                            "from": cliente.name,
                            "text": texto
                        }, cliente)

                elif tipo == "private":
                    destino = mensaje.get("to", "")
                    texto = mensaje.get("text", "")

                    if not isinstance(destino, str) or not isinstance(texto, str):
                        continue

                    receptor = buscar_cliente(destino)

                    if receptor is None or receptor == cliente:
                        enviar(cliente, {
                            "type": "error",
                            "text": "Destinatario no disponible."
                        })
                        continue

                    if texto.strip():
                        if not enviar(receptor, {
                            "type": "private",
                            "from": cliente.name,
                            "text": texto
                        }):
                            remove(receptor)
                            enviar(cliente, {
                                "type": "error",
                                "text": "No se pudo entregar el mensaje privado."
                            })

    except OSError as error:
        print(f"Error de conexión: {error}")

    finally:
        remove(cliente)


# FUNCIÓN PRINCIPAL DEL SERVIDOR

if __name__ == "__main__":
    server = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    try:
        server.bind((host, port))
        server.listen(100)

        print(f"Escuchando conexiones en: {(host, port)}")

        while True:
            conn, addr = server.accept()

            nuevo_cliente = Cliente(conn, addr)

            with clientes_lock:
                list_of_clients.append(nuevo_cliente)

            print(f"Cliente conectado: {addr}")

            hilo = threading.Thread(
                target=clientthread,
                args=(nuevo_cliente,),
                daemon=True
            )

            hilo.start()

    except KeyboardInterrupt:
        print("\nServidor detenido.")

    except OSError as error:
        print(f"Error del servidor: {error}")

    finally:
        with clientes_lock:
            clientes = list_of_clients[:]
            list_of_clients.clear()

        for cliente in clientes:
            cliente.conn.close()

        server.close()

        print("Conexión terminada.")
