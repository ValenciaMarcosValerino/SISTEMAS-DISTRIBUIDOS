import socket
import threading
import json
from db import crear_cuenta, verificar_cuenta


# CLASE CLIENTE

class Cliente:
    def __init__(self, conn, addr):
        self.conn = conn
        self.addr = addr
        self.id_publico = None
        self.usuario = None
        self.nombre_visible = None
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
            if c.id_publico is not None and c is not excluir
        ]
    for cliente in clientes:
        if not enviar(cliente, mensaje):
            remove(cliente)


# FUNCIÓN PARA OBTENER UN CLIENTE

def buscar_cliente(id_publico):
    with clientes_lock:
        for cliente in list_of_clients:
            if cliente.id_publico == id_publico:
                return cliente
    return None


# FUNCIÓN PARA ENVIAR LA LISTA DE USUARIOS

def enviar_lista_usuarios():
    with clientes_lock:
        usuarios = [
            {
                "id_publico": c.id_publico,
                "usuario": c.usuario,
                "nombre_visible": c.nombre_visible
            }
            for c in list_of_clients if c.id_publico is not None
        ]
    broadcast({"type": "users", "users": usuarios})


# REGISTRO DE NUEVAS CUENTAS

def registrar_cuenta(cliente, mensaje):
    usuario = mensaje.get("usuario")
    nombre = mensaje.get("nombre_visible")
    contrasena = mensaje.get("contrasena")

    if not all(isinstance(x, str) for x in (usuario, nombre, contrasena)):
        enviar(cliente, {
            "type": "register_result", "ok": False,
            "text": "Datos de registro no válidos."
        })
        return

    try:
        id_publico = crear_cuenta(usuario, nombre, contrasena)
        enviar(cliente, {
            "type": "register_result",
            "ok": True,
            "text": "Cuenta registrada correctamente.",
            "id_publico": id_publico
        })
        print(f"Cuenta registrada: {usuario}")
    except ValueError as error:
        enviar(cliente, {
            "type": "register_result", "ok": False, "text": str(error)
        })
    except Exception as error:
        print(f"Error al registrar cuenta: {error}")
        enviar(cliente, {
            "type": "register_result", "ok": False,
            "text": "No se pudo registrar la cuenta."
        })


# AUTENTICACIÓN DE USUARIOS

def autenticar_cliente(cliente, mensaje):
    usuario = mensaje.get("usuario")
    contrasena = mensaje.get("contrasena")

    if not isinstance(usuario, str) or not isinstance(contrasena, str):
        enviar(cliente, {
            "type": "login_result", "ok": False,
            "text": "Datos de inicio de sesión no válidos."
        })
        return False

    try:
        cuenta = verificar_cuenta(usuario, contrasena)
    except Exception as error:
        print(f"Error al autenticar: {error}")
        enviar(cliente, {
            "type": "login_result", "ok": False,
            "text": "No se pudo verificar la cuenta."
        })
        return False

    if cuenta is None:
        enviar(cliente, {
            "type": "login_result", "ok": False,
            "text": "Usuario o contraseña incorrectos."
        })
        return False

    with clientes_lock:
        duplicado = any(
            c is not cliente and c.id_publico == cuenta["id_publico"]
            for c in list_of_clients
        )
        if not duplicado:
            cliente.id_publico = cuenta["id_publico"]
            cliente.usuario = cuenta["usuario"]
            cliente.nombre_visible = cuenta["nombre_visible"] or cuenta["usuario"]

    if duplicado:
        enviar(cliente, {
            "type": "login_result", "ok": False,
            "text": "Esa cuenta ya tiene una sesión abierta."
        })
        return False

    if not enviar(cliente, {"type": "login_result", "ok": True, "cuenta": {
        "id_publico": cliente.id_publico,
        "usuario": cliente.usuario,
        "nombre_visible": cliente.nombre_visible
    }}):
        return False

    broadcast({
        "type": "system",
        "text": f"{cliente.nombre_visible} (@{cliente.usuario}) se ha conectado."
    }, excluir=cliente)
    enviar_lista_usuarios()
    print(f"Sesión iniciada: {cliente.usuario}")
    return True


# FUNCIÓN PARA ELIMINAR CLIENTES

def remove(cliente):
    with clientes_lock:
        if cliente not in list_of_clients:
            return
        list_of_clients.remove(cliente)
        usuario = cliente.usuario
        nombre = cliente.nombre_visible

    try:
        cliente.conn.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    cliente.conn.close()
    print(f"Cliente desconectado: {cliente.addr}")

    if usuario:
        broadcast({
            "type": "system",
            "text": f"{nombre} (@{usuario}) se ha desconectado."
        })
        enviar_lista_usuarios()


# FUNCIÓN PARA ATENDER A CADA CLIENTE

def clientthread(cliente):
    buffer = b""
    intentos_login = 0

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
                        "type": "error", "text": "Formato de mensaje no válido."
                    })
                    continue
                if not isinstance(mensaje, dict):
                    continue
                tipo = mensaje.get("type")

                # USUARIO SIN AUTENTICAR
                if cliente.id_publico is None:
                    if tipo == "register":
                        registrar_cuenta(cliente, mensaje)
                    elif tipo == "login":
                        if autenticar_cliente(cliente, mensaje):
                            intentos_login = 0
                        else:
                            intentos_login += 1
                            if intentos_login >= 5:
                                return
                    else:
                        enviar(cliente, {
                            "type": "error", "text": "Debes iniciar sesión."
                        })
                        return
                    continue

                # CHAT GENERAL
                if tipo == "public":
                    texto = mensaje.get("text")
                    if isinstance(texto, str) and texto.strip() and len(texto) <= 5000:
                        broadcast({
                            "type": "public",
                            "from": cliente.nombre_visible,
                            "from_usuario": cliente.usuario,
                            "from_id": cliente.id_publico,
                            "text": texto
                        }, excluir=cliente)

                # MENSAJES PRIVADOS
                elif tipo == "private":
                    destino = mensaje.get("to")
                    texto = mensaje.get("text")
                    if not isinstance(destino, str) or not isinstance(texto, str):
                        continue
                    if not texto.strip() or len(texto) > 5000:
                        continue
                    receptor = buscar_cliente(destino)
                    if receptor is None or receptor is cliente:
                        enviar(cliente, {
                            "type": "error", "text": "Destinatario no disponible."
                        })
                        continue
                    if not enviar(receptor, {
                        "type": "private",
                        "from": cliente.nombre_visible,
                        "from_usuario": cliente.usuario,
                        "from_id": cliente.id_publico,
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
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind((host, port))
        server.listen(100)
        print(f"Escuchando conexiones en: {(host, port)}")

        while True:
            conn, addr = server.accept()
            cliente = Cliente(conn, addr)
            with clientes_lock:
                list_of_clients.append(cliente)
            print(f"Cliente conectado: {addr}")
            threading.Thread(
                target=clientthread, args=(cliente,), daemon=True
            ).start()

    except KeyboardInterrupt:
        print("\nServidor detenido.")
    except OSError as error:
        print(f"Error del servidor: {error}")
    finally:
        with clientes_lock:
            clientes = list_of_clients[:]
        for cliente in clientes:
            remove(cliente)
        server.close()
        print("Conexión terminada.")
