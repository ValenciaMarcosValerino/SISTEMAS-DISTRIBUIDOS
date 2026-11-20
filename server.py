
import socket
import threading


# CLASE CLIENTE
# Almacena los datos de cada usuario conectado.

class Cliente:
    def __init__(self):
        self.name = ""
        self.conn = None
        self.addr = None

# VARIABLES DEL SERVIDOR


host = "127.0.0.1"
port = 5000
BUFFER_SIZE = 1024

list_of_clients = []
clientes_lock = threading.Lock()

# FUNCIÓN PARA ATENDER A CADA CLIENTE

def clientthread(conn, addr):
    """
    Atiende la comunicación con un cliente.

    Recibe sus mensajes, identifica comandos
    y reenvía los mensajes a los demás usuarios.
    """

    try:
        conn.sendall(bytes(f"Bienvenido {addr}\n", "utf-8"))

        while True:
            message = conn.recv(BUFFER_SIZE)

            # Si no llegan datos, el cliente se desconectó.
            if not message:
                break

            msg = message.decode("utf-8")

            print(f"<{addr[0]}> {msg}")

            # Registrar nombre del usuario.
            if msg.startswith("<name>"):
                nombre = msg.removeprefix("<name>")
                setName(conn, nombre)

            # Procesar comandos especiales.
            elif msg.startswith("<command>"):
                broadcast(msg + "\n", conn)

            # Mensajes normales.
            else:
                nombre = getName(conn)

                message_to_send = f"<{nombre}> {msg}\n"

                broadcast(message_to_send, conn)

    except (OSError, UnicodeError) as error:
        print(f"Error de comunicación con {addr}: {error}")

    finally:
        remove(conn)
        conn.close()

# FUNCIÓN PARA ASIGNAR NOMBRE AL CLIENTE


def setName(connection, name: str):
    """
    Busca al cliente y almacena su nombre de usuario.
    """

    with clientes_lock:
        for client in list_of_clients:
            if client.conn == connection:
                client.name = name
                break

# FUNCIÓN PARA OBTENER EL NOMBRE DEL CLIENTE

def getName(connection) -> str:
    """
    Devuelve el nombre del usuario asociado
    con una conexión.
    """

    with clientes_lock:
        for client in list_of_clients:
            if client.conn == connection:
                return client.name

    return ""

# FUNCIÓN PARA ENVIAR MENSAJES A OTROS CLIENTES

def broadcast(message, connection):
    """
    Envía un mensaje a todos los clientes conectados,
    excepto al cliente que lo envió.
    """

    with clientes_lock:
        clientes = list_of_clients[:]

    for client in clientes:
        if client.conn != connection:
            try:
                client.conn.sendall(bytes(message, "utf-8"))

            except OSError:
                remove(client.conn)
                client.conn.close()


# FUNCIÓN PARA ELIMINAR CLIENTES DESCONECTADOS

def remove(connection):
    """
    Recorre la lista de clientes y busca el objeto
    cuya conexión coincide con la recibida.

    Si lo encuentra, lo elimina de la lista.
    """

    with clientes_lock:
        for client in list_of_clients[:]:
            if client.conn == connection:
                list_of_clients.remove(client)

                print(
                    f"Cliente desconectado: {client.addr}"
                )

                break


# FUNCIÓN PRINCIPAL DEL SERVIDOR

if __name__ == "__main__":

    # Crear socket TCP.
    server = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    # Permitir reutilizar el puerto.
    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    try:
        # Asociar IP y puerto.
        server.bind((host, port))

        # Escuchar conexiones entrantes.
        server.listen(100)

        print(f"Escuchando conexiones en: {(host, port)}")

        while True:

            # Esperar un cliente.
            conn, addr = server.accept()

            # Crear objeto para el nuevo cliente.
            nuevo_cliente = Cliente()

            nuevo_cliente.conn = conn
            nuevo_cliente.addr = addr

            # Agregarlo a la lista.
            with clientes_lock:
                list_of_clients.append(nuevo_cliente)

            print(f"Cliente conectado: {addr}")

            # Crear un hilo para atender al cliente.
            hilo = threading.Thread(
                target=clientthread,
                args=(conn, addr),
                daemon=True
            )

            hilo.start()

    except KeyboardInterrupt:
        print("\nServidor detenido por el usuario.")

    except OSError as error:
        print(f"Error del servidor: {error}")

    finally:
        # Cerrar conexiones activas.
        with clientes_lock:
            clientes = list_of_clients[:]
            list_of_clients.clear()

        for client in clientes:
            try:
                client.conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

            client.conn.close()

        server.close()

        print("Conexión terminada.")
