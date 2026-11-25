import socket
import threading
import json
import base64
import binascii
from uuid import UUID
from db import (
    crear_cuenta, verificar_cuenta, crear_servidor_discord,
    obtener_servidores_usuario, obtener_canales_servidor,
    guardar_mensaje_canal, obtener_historial_canal, obtener_ids_miembros_canal,
    guardar_mensaje_privado, obtener_historial_privado
)
from db import crear_grupo
from db import agregar_miembro_grupo
from db import guardar_mensaje_grupo, obtener_miembros_grupo, obtener_historial_grupo
from grupos_db import obtener_grupos_usuario
from db import crear_canal_difusion
from db import obtener_canales_difusion
from db import suscribirse_canal_difusion
from db import publicar_canal_difusion, conectar_bd, obtener_historial_canal_difusion
from db import guardar_foto_perfil, obtener_foto_perfil
from servidores_db import (
    agregar_integrante_servidor,
    crear_canal_texto_servidor,
    listar_integrantes_servidor,
)



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
BUFFER_SIZE = 8192
# Una foto de 2 MB convertida a Base64 ocupa hasta ~2.7 MB en JSON.
MAX_FOTO_BYTES = 2 * 1024 * 1024
MAX_TCP_LINEA = 3 * 1024 * 1024 + 8192
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
            if (
                isinstance(cliente.id_publico, str)
                and cliente.id_publico.casefold() == id_publico.casefold()
            ):
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


# CREAR SERVIDORES

def crear_servidor(cliente, mensaje):
    nombre = mensaje.get("nombre")

    if not isinstance(nombre, str) or not nombre.strip() or len(nombre.strip()) > 100:
        enviar(cliente, {
            "type": "create_server_result", "ok": False,
            "text": "El nombre del servidor debe tener entre 1 y 100 caracteres."
        })
        return

    nombre = nombre.strip()
    try:
        id_servidor = crear_servidor_discord(nombre, cliente.id_publico)
        enviar(cliente, {
            "type": "create_server_result",
            "ok": True,
            "text": "Servidor creado correctamente.",
            "id_servidor": str(id_servidor),
            "nombre": nombre
        })
        print(f"Servidor creado: {nombre} (creador: {cliente.usuario})")
    except ValueError as error:
        enviar(cliente, {
            "type": "create_server_result", "ok": False,
            "text": str(error)
        })
    except Exception as error:
        print(f"Error al crear servidor: {error}")
        enviar(cliente, {
            "type": "create_server_result", "ok": False,
            "text": "No se pudo crear el servidor."
        })


# CONSULTAR SERVIDORES DEL USUARIO AUTENTICADO

def listar_servidores(cliente):
    try:
        servidores = obtener_servidores_usuario(cliente.id_publico)
        enviar(cliente, {
            "type": "servers_list",
            "ok": True,
            "servers": servidores
        })
    except Exception as error:
        print(f"Error al consultar servidores: {error}")
        enviar(cliente, {
            "type": "servers_list",
            "ok": False,
            "servers": [],
            "text": "No se pudieron consultar los servidores."
        })


# CONSULTAR CANALES DE UN SERVIDOR

def listar_canales(cliente, mensaje):
    id_servidor = mensaje.get("id_servidor")

    if not isinstance(id_servidor, str) or not id_servidor.strip():
        enviar(cliente, {
            "type": "channels_list",
            "ok": False,
            "text": "Identificador de servidor no válido."
        })
        return

    try:
        canales = obtener_canales_servidor(
            id_servidor.strip(), cliente.id_publico
        )
        enviar(cliente, {
            "type": "channels_list",
            "ok": True,
            "id_servidor": id_servidor.strip(),
            "channels": canales
        })
    except Exception as error:
        print(f"Error al consultar canales: {error}")
        enviar(cliente, {
            "type": "channels_list",
            "ok": False,
            "text": "No se pudieron consultar los canales."
        })


# ADMINISTRACION DE SERVIDORES DE COMUNIDAD (PASO 17.1)

def agregar_integrante_servidor_tcp(cliente, mensaje):
    tipo = "add_server_member_result"
    try:
        integrante = agregar_integrante_servidor(
            mensaje.get("id_servidor"), cliente.id_publico,
            mensaje.get("usuario")
        )
        enviar(cliente, {
            "type": tipo, "ok": True,
            "integrante": integrante,
            "text": "Integrante agregado al servidor."
        })
        receptor = buscar_cliente(integrante["id_usuario"])
        if receptor is not None and receptor is not cliente:
            enviar(receptor, {
                "type": "server_member_added",
                "id_servidor": integrante["id_servidor"],
                "text": "Te agregaron a un servidor."
            })
    except ValueError as error:
        enviar(cliente, {"type": tipo, "ok": False, "text": str(error)})
    except Exception as error:
        print(f"Error al agregar integrante de servidor: {error}")
        enviar(cliente, {"type": tipo, "ok": False,
                         "text": "No se pudo agregar el integrante."})


def crear_canal_servidor_tcp(cliente, mensaje):
    tipo = "create_server_channel_result"
    try:
        canal = crear_canal_texto_servidor(
            mensaje.get("id_servidor"), cliente.id_publico,
            mensaje.get("nombre"), mensaje.get("descripcion", "")
        )
        enviar(cliente, {"type": tipo, "ok": True, "canal": canal,
                         "text": "Canal de texto creado correctamente."})
    except ValueError as error:
        enviar(cliente, {"type": tipo, "ok": False, "text": str(error)})
    except Exception as error:
        print(f"Error al crear canal del servidor: {error}")
        enviar(cliente, {"type": tipo, "ok": False,
                         "text": "No se pudo crear el canal."})
    else:
        # El canal ya está guardado; un fallo al notificar no debe
        # cambiar la respuesta de creación correcta.
        try:
            integrantes = listar_integrantes_servidor(
                canal["id_servidor"], cliente.id_publico
            )
            ids = {u["id_usuario"].lower() for u in integrantes}
            with clientes_lock:
                receptores = [
                    c for c in list_of_clients
                    if c.id_publico is not None
                    and str(c.id_publico).lower() in ids and c is not cliente
                ]
            for receptor in receptores:
                if not enviar(receptor, {
                    "type": "server_channel_created",
                    "id_servidor": canal["id_servidor"],
                    "text": "Hay un canal nuevo en tu servidor."
                }):
                    remove(receptor)
        except Exception as error:
            print(f"Canal guardado, aviso a integrantes fallido: {error}")


def listar_integrantes_servidor_tcp(cliente, mensaje):
    tipo = "server_members_list"
    try:
        id_servidor = str(UUID(str(mensaje.get("id_servidor"))))
        integrantes = listar_integrantes_servidor(
            id_servidor, cliente.id_publico
        )
        enviar(cliente, {"type": tipo, "ok": True,
                         "id_servidor": id_servidor, "members": integrantes})
    except (ValueError, TypeError, AttributeError) as error:
        enviar(cliente, {"type": tipo, "ok": False, "text": str(error)})
    except Exception as error:
        print(f"Error al consultar integrantes: {error}")
        enviar(cliente, {"type": tipo, "ok": False,
                         "text": "No se pudieron consultar los integrantes."})


# VALIDAR IDENTIFICADORES DE CANAL

def validar_id_canal(id_canal):
    if not isinstance(id_canal, str):
        return None
    try:
        return str(UUID(id_canal))
    except (ValueError, AttributeError):
        return None


# ENVIAR Y GUARDAR MENSAJE EN UN CANAL

def enviar_mensaje_canal(cliente, mensaje):
    id_canal = validar_id_canal(mensaje.get("id_canal"))
    texto = mensaje.get("text")

    if id_canal is None or not isinstance(texto, str) or not texto.strip():
        enviar(cliente, {
            "type": "channel_message_result", "ok": False,
            "text": "Canal o contenido no válido."
        })
        return
    if len(texto.strip()) > 4000:
        enviar(cliente, {
            "type": "channel_message_result", "ok": False,
            "text": "El mensaje no puede superar 4000 caracteres."
        })
        return

    try:
        guardado = guardar_mensaje_canal(id_canal, cliente.id_publico, texto)
    except ValueError as error:
        enviar(cliente, {
            "type": "channel_message_result", "ok": False, "text": str(error)
        })
        return
    except Exception as error:
        print(f"Error al guardar mensaje de canal: {error}")
        enviar(cliente, {
            "type": "channel_message_result", "ok": False,
            "text": "No se pudo guardar el mensaje."
        })
        return

    enviar(cliente, {
        "type": "channel_message_result", "ok": True,
        "message": guardado
    })

    try:
        miembros = {
            str(UUID(id_usuario))
            for id_usuario in obtener_ids_miembros_canal(id_canal)
        }
        with clientes_lock:
            receptores = [
                c for c in list_of_clients
                if c.id_publico is not None
                and str(UUID(c.id_publico)) in miembros
            ]

        evento = {
            "type": "channel_message",
            "message": {
                **guardado,
                "usuario": cliente.usuario,
                "nombre_visible": cliente.nombre_visible
            }
        }
        for receptor in receptores:
            if not enviar(receptor, evento):
                remove(receptor)
    except Exception as error:
        print(f"Mensaje guardado, pero falló la notificación en tiempo real: {error}")


# RECUPERAR HISTORIAL DE UN CANAL

def consultar_historial_canal(cliente, mensaje):
    id_canal = validar_id_canal(mensaje.get("id_canal"))
    limite = mensaje.get("limit", 50)

    if id_canal is None or type(limite) is not int or not 1 <= limite <= 100:
        enviar(cliente, {
            "type": "channel_history_result", "ok": False,
            "text": "Canal o límite de mensajes no válido."
        })
        return

    try:
        historial = obtener_historial_canal(
            id_canal, cliente.id_publico, limite
        )
        enviar(cliente, {
            "type": "channel_history_result", "ok": True,
            "id_canal": id_canal,
            "messages": historial
        })
    except ValueError as error:
        enviar(cliente, {
            "type": "channel_history_result", "ok": False,
            "text": str(error)
        })
    except Exception as error:
        print(f"Error al consultar historial de canal: {error}")
        enviar(cliente, {
            "type": "channel_history_result", "ok": False,
            "text": "No se pudo recuperar el historial del canal."
        })


# ENVIAR Y GUARDAR MENSAJES PRIVADOS

def enviar_mensaje_privado(cliente, mensaje):
    destino = mensaje.get("to")
    texto = mensaje.get("text")

    try:
        id_destino = str(UUID(destino))
    except (ValueError, TypeError, AttributeError):
        enviar(cliente, {
            "type": "error", "text": "Destinatario no válido."
        })
        return

    if not isinstance(texto, str) or not texto.strip() or len(texto.strip()) > 4000:
        enviar(cliente, {
            "type": "error", "text": "El mensaje privado debe tener entre 1 y 4000 caracteres."
        })
        return

    if id_destino == str(UUID(cliente.id_publico)):
        enviar(cliente, {
            "type": "error", "text": "No puedes enviarte un mensaje privado."
        })
        return

    try:
        guardado = guardar_mensaje_privado(
            cliente.id_publico, id_destino, texto
        )
    except ValueError as error:
        enviar(cliente, {
            "type": "error", "text": str(error)
        })
        return
    except Exception as error:
        print(f"Error al guardar mensaje privado: {error}")
        enviar(cliente, {
            "type": "error", "text": "No se pudo guardar el mensaje privado."
        })
        return

    # CONFIRMAR AL REMITENTE SIN DUPLICARLO EN SU CHAT
    enviar(cliente, {
        "type": "private_result",
        "ok": True,
        "to": id_destino,
        "message": guardado
    })

    # ENTREGAR EN TIEMPO REAL SI EL DESTINATARIO ESTÁ CONECTADO
    receptor = buscar_cliente(id_destino)
    if receptor is not None and receptor is not cliente:
        if not enviar(receptor, {
            "type": "private",
            "from": cliente.nombre_visible,
            "from_usuario": cliente.usuario,
            "from_id": cliente.id_publico,
            "text": guardado["contenido"],
            "id_mensaje": guardado["id_mensaje"],
            "fecha_envio": guardado["fecha_envio"]
        }):
            remove(receptor)


# CONSULTAR HISTORIAL DE CONVERSACIÓN PRIVADA

def consultar_historial_privado(cliente, mensaje):
    destino = mensaje.get("to")

    try:
        id_destino = str(UUID(destino))
    except (ValueError, TypeError, AttributeError):
        enviar(cliente, {
            "type": "private_history_result",
            "ok": False,
            "text": "Destinatario no válido."
        })
        return

    if id_destino == str(UUID(cliente.id_publico)):
        enviar(cliente, {
            "type": "private_history_result",
            "ok": False,
            "text": "No puedes consultar tu propio historial como destinatario."
        })
        return

    try:
        historial = obtener_historial_privado(cliente.id_publico, id_destino)
        enviar(cliente, {
            "type": "private_history_result",
            "ok": True,
            "to": id_destino,
            "messages": historial
        })
    except ValueError as error:
        enviar(cliente, {
            "type": "private_history_result",
            "ok": False,
            "text": str(error)
        })
    except Exception as error:
        print(f"Error al consultar historial privado: {error}")
        enviar(cliente, {
            "type": "private_history_result",
            "ok": False,
            "text": "No se pudo recuperar el historial privado."
        })


# LISTAR GRUPOS DE UN USUARIO AUTENTICADO

def listar_grupos(cliente):
    try:
        grupos = obtener_grupos_usuario(cliente.id_publico)
        enviar(cliente, {
            "type": "groups_list",
            "ok": True,
            "groups": grupos,
        })
    except Exception as error:
        print(f"Error al listar grupos: {error}")
        enviar(cliente, {
            "type": "groups_list",
            "ok": False,
            "groups": [],
            "text": "No se pudieron consultar los grupos.",
        })


# CREAR CANALES DE DIFUSION (PROPIETARIO = USUARIO AUTENTICADO)

def crear_canal_difusion_tcp(cliente, mensaje):
    nombre = mensaje.get("nombre")
    descripcion = mensaje.get("descripcion", "")

    try:
        # No aceptar un id_creador proporcionado por el cliente.
        # La identidad procede exclusivamente de la sesion autenticada.
        canal = crear_canal_difusion(
            nombre, cliente.id_publico, descripcion
        )

        enviar(cliente, {
            "type": "create_broadcast_channel_result",
            "ok": True,
            "text": "Canal de difusion creado correctamente.",
            "canal": canal
        })
        print(
            f"Canal de difusion creado: {canal['nombre']} "
            f"(creador: {cliente.usuario})"
        )

    except ValueError as error:
        enviar(cliente, {
            "type": "create_broadcast_channel_result",
            "ok": False,
            "text": str(error)
        })

    except Exception as error:
        print(f"Error al crear canal de difusion: {error}")
        enviar(cliente, {
            "type": "create_broadcast_channel_result",
            "ok": False,
            "text": "No se pudo crear el canal de difusion."
        })


# LISTAR CANALES DE DIFUSION PARA EL USUARIO AUTENTICADO

def listar_canales_difusion_tcp(cliente):
    try:
        # Siempre usar la identidad de la sesion; nunca confiar en un ID enviado.
        canales = obtener_canales_difusion(cliente.id_publico)
        enviar(cliente, {
            "type": "broadcast_channels_list",
            "ok": True,
            "channels": canales
        })

    except ValueError as error:
        enviar(cliente, {
            "type": "broadcast_channels_list",
            "ok": False,
            "channels": [],
            "text": str(error)
        })

    except Exception as error:
        print(f"Error al consultar canales de difusion: {error}")
        enviar(cliente, {
            "type": "broadcast_channels_list",
            "ok": False,
            "channels": [],
            "text": "No se pudieron consultar los canales de difusion."
        })


# SUSCRIBIR AL USUARIO AUTENTICADO A UN CANAL DE DIFUSION

def suscribir_canal_difusion_tcp(cliente, mensaje):
    # Nunca aceptar id_usuario desde el cliente: tomarlo de su sesion.
    id_canal = validar_id_canal(mensaje.get("id_canal"))

    if id_canal is None:
        enviar(cliente, {
            "type": "subscribe_broadcast_channel_result",
            "ok": False,
            "text": "Identificador de canal no valido."
        })
        return

    try:
        suscripcion = suscribirse_canal_difusion(
            id_canal, cliente.id_publico
        )
        enviar(cliente, {
            "type": "subscribe_broadcast_channel_result",
            "ok": True,
            "text": "Suscripcion realizada correctamente.",
            "id_canal": id_canal,
            "subscription": suscripcion
        })
        print(
            f"Usuario suscrito a canal de difusion: "
            f"{cliente.usuario} -> {id_canal}"
        )

    except ValueError as error:
        enviar(cliente, {
            "type": "subscribe_broadcast_channel_result",
            "ok": False,
            "id_canal": id_canal,
            "text": str(error)
        })

    except Exception as error:
        print(f"Error al suscribir al canal de difusion: {error}")
        enviar(cliente, {
            "type": "subscribe_broadcast_channel_result",
            "ok": False,
            "id_canal": id_canal,
            "text": "No se pudo realizar la suscripcion al canal."
        })


# PUBLICACIONES EN TIEMPO REAL: SOLO EL CREADOR PUEDE PUBLICAR

def publicar_canal_difusion_tcp(cliente, mensaje):
    # El usuario que publica se obtiene de la sesion autenticada.
    # Ignorar cualquier id_autor que envie el cliente.
    id_canal = validar_id_canal(mensaje.get("id_canal"))
    contenido = mensaje.get("text")

    if id_canal is None or not isinstance(contenido, str):
        enviar(cliente, {
            "type": "publish_broadcast_channel_result",
            "ok": False,
            "text": "Identificador de canal o contenido no valido."
        })
        return

    contenido = contenido.strip()
    if not contenido or len(contenido) > 4000:
        enviar(cliente, {
            "type": "publish_broadcast_channel_result",
            "ok": False,
            "text": "La publicacion debe tener entre 1 y 4000 caracteres."
        })
        return

    try:
        # Esta funcion valida en SQL Server que el autor sea el creador.
        publicacion = publicar_canal_difusion(
            id_canal, cliente.id_publico, contenido
        )
    except ValueError as error:
        enviar(cliente, {
            "type": "publish_broadcast_channel_result",
            "ok": False,
            "text": str(error)
        })
        return
    except Exception as error:
        print(f"Error al guardar publicacion de difusion: {error}")
        enviar(cliente, {
            "type": "publish_broadcast_channel_result",
            "ok": False,
            "text": "No se pudo guardar la publicacion."
        })
        return

    # Informar primero que el mensaje quedo persistido en SQL Server.
    enviar(cliente, {
        "type": "publish_broadcast_channel_result",
        "ok": True,
        "text": "Publicacion guardada correctamente.",
        "post": publicacion
    })

    # Notificar solo a suscriptores conectados, incluido el propietario.
    # Si falla el aviso en vivo, el registro persiste en la BD.
    try:
        conexion = conectar_bd()
        try:
            cursor = conexion.cursor()
            cursor.execute("""
                SELECT CONVERT(VARCHAR(36), id_usuario)
                FROM dbo.SuscripcionesCanal
                WHERE id_canal = CONVERT(UNIQUEIDENTIFIER, ?)
            """, id_canal)
            ids_suscritos = {
                str(UUID(str(fila[0])))
                for fila in cursor.fetchall()
            }
        finally:
            conexion.close()

        with clientes_lock:
            receptores = [
                c for c in list_of_clients
                if c.id_publico is not None
                and str(UUID(str(c.id_publico))) in ids_suscritos
            ]

        evento = {
            "type": "broadcast_channel_post",
            "post": {
                **publicacion,
                "autor": cliente.usuario,
                "nombre_visible": cliente.nombre_visible
            }
        }

        for receptor in receptores:
            if not enviar(receptor, evento):
                remove(receptor)

        print(
            f"Publicacion en canal de difusion {id_canal}: "
            f"autor={cliente.usuario}, receptores={len(receptores)}"
        )

    except Exception as error:
        print(
            "Publicacion guardada, pero fallo la notificacion "
            f"en tiempo real: {error}"
        )


# CONSULTAR HISTORIAL DE CANAL DE DIFUSION POR TCP

def consultar_historial_canal_difusion_tcp(cliente, mensaje):
    # El usuario debe estar autenticado. El ID del solicitante se toma
    # de la sesion, nunca de un campo enviado en el JSON.
    id_canal = validar_id_canal(mensaje.get("id_canal"))

    if id_canal is None:
        enviar(cliente, {
            "type": "broadcast_channel_history_result",
            "ok": False,
            "text": "Identificador de canal no valido."
        })
        return

    try:
        # La funcion de BD verifica que el canal exista y que el usuario
        # sea suscriptor antes de devolver el historial completo.
        publicaciones = obtener_historial_canal_difusion(
            id_canal, cliente.id_publico
        )

        enviar(cliente, {
            "type": "broadcast_channel_history_result",
            "ok": True,
            "id_canal": id_canal,
            "posts": publicaciones
        })

    except ValueError as error:
        enviar(cliente, {
            "type": "broadcast_channel_history_result",
            "ok": False,
            "id_canal": id_canal,
            "text": str(error)
        })

    except Exception as error:
        print(f"Error al recuperar historial de canal de difusion: {error}")
        enviar(cliente, {
            "type": "broadcast_channel_history_result",
            "ok": False,
            "id_canal": id_canal,
            "text": "No se pudo recuperar el historial del canal."
        })


# FOTOGRAFIAS DE PERFIL (PASO 19.3)
# La identidad del usuario se obtiene del socket autenticado.

def cambiar_foto_perfil_tcp(cliente, mensaje):
    tipo = "profile_photo_result"
    datos_b64 = mensaje.get("data_base64")
    mime = mensaje.get("mime")
    nombre = mensaje.get("nombre", "perfil.png")

    if (not isinstance(datos_b64, str) or not isinstance(mime, str)
            or not isinstance(nombre, str)):
        enviar(cliente, {"type": tipo, "ok": False,
                         "text": "Fotografia o formato no valido."})
        return

    # Limite previo a la decodificacion: evita objetos grandes en memoria.
    max_b64 = 4 * ((MAX_FOTO_BYTES + 2) // 3) + 8
    if not datos_b64 or len(datos_b64) > max_b64:
        enviar(cliente, {"type": tipo, "ok": False,
                         "text": "La fotografia no puede superar 2 MB."})
        return

    try:
        contenido = base64.b64decode(datos_b64, validate=True)
    except (binascii.Error, ValueError):
        enviar(cliente, {"type": tipo, "ok": False,
                         "text": "La fotografia no tiene Base64 valido."})
        return

    if not contenido or len(contenido) > MAX_FOTO_BYTES:
        enviar(cliente, {"type": tipo, "ok": False,
                         "text": "La fotografia no puede superar 2 MB."})
        return

    try:
        # Nunca se acepta id_usuario desde el JSON para cambiar fotos.
        resultado = guardar_foto_perfil(
            cliente.id_publico, contenido, nombre, mime
        )
    except ValueError as error:
        enviar(cliente, {"type": tipo, "ok": False, "text": str(error)})
        return
    except Exception as error:
        print(f"Error al guardar foto de perfil: {error}")
        enviar(cliente, {"type": tipo, "ok": False,
                         "text": "No se pudo guardar la fotografia."})
        return

    enviar(cliente, {
        "type": tipo, "ok": True, "text": "Fotografia actualizada.",
        "id_usuario": cliente.id_publico,
        "mime": resultado["mime"], "tamano": resultado["tamano"]
    })

    # Aviso ligero: los clientes recuperan la foto actualizada por TCP.
    # Los datos binarios no se replican aqui para evitar trafico innecesario.
    broadcast({
        "type": "profile_photo_updated",
        "id_usuario": cliente.id_publico
    })


def obtener_foto_perfil_tcp(cliente, mensaje):
    tipo = "profile_photo_data"
    identificador = mensaje.get("id_usuario", cliente.id_publico)
    try:
        id_usuario = str(UUID(str(identificador)))
    except (ValueError, TypeError, AttributeError):
        enviar(cliente, {"type": tipo, "ok": False,
                         "text": "Identificador de usuario no valido."})
        return

    try:
        foto = obtener_foto_perfil(id_usuario)
    except ValueError as error:
        enviar(cliente, {"type": tipo, "ok": False,
                         "id_usuario": id_usuario, "text": str(error)})
        return
    except Exception as error:
        print(f"Error al recuperar foto de perfil: {error}")
        enviar(cliente, {"type": tipo, "ok": False,
                         "id_usuario": id_usuario,
                         "text": "No se pudo consultar la fotografia."})
        return

    if foto is None:
        enviar(cliente, {"type": tipo, "ok": True,
                         "id_usuario": id_usuario,
                         "data_base64": None, "mime": None})
        return

    contenido = foto.get("datos")
    if (not isinstance(contenido, bytes) or len(contenido) > MAX_FOTO_BYTES):
        enviar(cliente, {"type": tipo, "ok": False,
                         "id_usuario": id_usuario,
                         "text": "La foto almacenada no es valida."})
        return

    enviar(cliente, {
        "type": tipo, "ok": True, "id_usuario": id_usuario,
        "mime": foto.get("mime"),
        "data_base64": base64.b64encode(contenido).decode("ascii")
    })


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



# ENVIAR MENSAJES GRUPALES EN TIEMPO REAL

def enviar_mensaje_grupal(cliente, mensaje):
    id_grupo = mensaje.get("id_grupo")
    texto = mensaje.get("text")

    # VALIDAR EL IDENTIFICADOR DEL GRUPO
    try:
        if not isinstance(id_grupo, str):
            raise ValueError("Identificador de grupo no válido.")
        id_grupo = str(UUID(id_grupo))
    except (ValueError, TypeError, AttributeError):
        enviar(cliente, {
            "type": "group_message_result",
            "ok": False,
            "text": "Identificador de grupo no válido."
        })
        return

    # VALIDAR EL CONTENIDO DEL MENSAJE
    if not isinstance(texto, str) or not texto.strip():
        enviar(cliente, {
            "type": "group_message_result",
            "ok": False,
            "text": "El mensaje no puede estar vacío."
        })
        return

    texto = texto.strip()
    if len(texto) > 4000:
        enviar(cliente, {
            "type": "group_message_result",
            "ok": False,
            "text": "El mensaje supera los 4000 caracteres."
        })
        return

    # GUARDAR EN SQL SERVER; db.py VERIFICA QUE EL REMITENTE SEA MIEMBRO
    try:
        guardado = guardar_mensaje_grupo(
            id_grupo, cliente.id_publico, texto
        )
    except ValueError as error:
        enviar(cliente, {
            "type": "group_message_result",
            "ok": False,
            "text": str(error)
        })
        return
    except Exception as error:
        print(f"Error al guardar mensaje grupal: {error}")
        enviar(cliente, {
            "type": "group_message_result",
            "ok": False,
            "text": "No se pudo guardar el mensaje."
        })
        return

    mensaje_completo = {
        **guardado,
        "usuario": cliente.usuario,
        "nombre_visible": cliente.nombre_visible
    }

    # CONFIRMAR AL REMITENTE (SIN DUPLICAR SU MENSAJE EN EL EVENTO)
    enviar(cliente, {
        "type": "group_message_result",
        "ok": True,
        "message": mensaje_completo
    })

    # ENTREGAR SOLAMENTE A MIEMBROS CONECTADOS
    try:
        integrantes = obtener_miembros_grupo(id_grupo, cliente.id_publico)
        ids_integrantes = {
            str(UUID(integrante["id_usuario"]))
            for integrante in integrantes
        }

        with clientes_lock:
            receptores = [
                c for c in list_of_clients
                if c.id_publico is not None
                and c is not cliente
                and str(UUID(c.id_publico)) in ids_integrantes
            ]

        evento = {
            "type": "group_message",
            "message": mensaje_completo
        }

        for receptor in receptores:
            if not enviar(receptor, evento):
                remove(receptor)

        print(f"Mensaje grupal enviado por {cliente.usuario} al grupo {id_grupo}")
    except Exception as error:
        print(f"Mensaje guardado, pero falló la notificación en tiempo real: {error}")


# CONSULTAR HISTORIAL GRUPAL MEDIANTE TCP

def consultar_historial_grupo(cliente, mensaje):
    id_grupo = mensaje.get("id_grupo")

    try:
        if not isinstance(id_grupo, str):
            raise ValueError("Identificador de grupo no válido.")
        id_grupo = str(UUID(id_grupo))
    except (ValueError, TypeError, AttributeError) as error:
        enviar(cliente, {
            "type": "group_history_result",
            "ok": False,
            "text": "Identificador de grupo no válido."
        })
        return

    try:
        # db.py verifica la membresía antes de devolver los mensajes.
        historial = obtener_historial_grupo(id_grupo, cliente.id_publico)
        enviar(cliente, {
            "type": "group_history_result",
            "ok": True,
            "id_grupo": id_grupo,
            "messages": historial
        })
    except ValueError as error:
        enviar(cliente, {
            "type": "group_history_result",
            "ok": False,
            "text": str(error)
        })
    except Exception as error:
        print(f"Error al consultar historial grupal: {error}")
        enviar(cliente, {
            "type": "group_history_result",
            "ok": False,
            "text": "No se pudo recuperar el historial grupal."
        })


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
            if len(buffer) > MAX_TCP_LINEA:
                enviar(cliente, {"type": "error", "text": "Solicitud demasiado grande."})
                return

            while b"\n" in buffer:
                linea, buffer = buffer.split(b"\n", 1)
                if not linea:
                    continue
                if len(linea) > MAX_TCP_LINEA:
                    enviar(cliente, {"type": "error", "text": "Solicitud demasiado grande."})
                    return
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

                # FOTOS DE PERFIL: solo usuarios autenticados.
                if tipo == "set_profile_photo":
                    cambiar_foto_perfil_tcp(cliente, mensaje)
                    continue
                elif tipo == "get_profile_photo":
                    obtener_foto_perfil_tcp(cliente, mensaje)
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

                # MENSAJES PRIVADOS PERSISTENTES
                elif tipo == "private":
                    enviar_mensaje_privado(cliente, mensaje)

                # HISTORIAL DE MENSAJES PRIVADOS
                elif tipo == "private_history":
                    consultar_historial_privado(cliente, mensaje)

                # CREAR SERVIDORES (SOLO USUARIOS AUTENTICADOS)
                elif tipo == "create_server":
                    crear_servidor(cliente, mensaje)

                # CREAR CANALES DE DIFUSION
                elif tipo == "create_broadcast_channel":
                    crear_canal_difusion_tcp(cliente, mensaje)

                # CONSULTAR CANALES DE DIFUSION
                elif tipo == "list_broadcast_channels":
                    listar_canales_difusion_tcp(cliente)

                # SUSCRIBIRSE A UN CANAL DE DIFUSION
                elif tipo == "subscribe_broadcast_channel":
                    suscribir_canal_difusion_tcp(cliente, mensaje)

                # PUBLICAR AVISO EN CANAL DE DIFUSION (SOLO PROPIETARIO)
                elif tipo == "publish_broadcast_channel":
                    publicar_canal_difusion_tcp(cliente, mensaje)

                # CONSULTAR HISTORIAL DE CANAL DE DIFUSION
                elif tipo == "broadcast_channel_history":
                    consultar_historial_canal_difusion_tcp(cliente, mensaje)

                # CREAR GRUPOS PRIVADOS
                elif tipo == "create_group":
                    nombre = mensaje.get("nombre")

                    if not isinstance(nombre, str) or not nombre.strip() or len(nombre.strip()) > 100:
                        enviar(cliente, {
                            "type": "create_group_result",
                            "ok": False,
                            "text": "Nombre de grupo no válido."
                        })
                        continue

                    try:
                        grupo = crear_grupo(
                            nombre.strip(),
                            cliente.id_publico
                        )

                        enviar(cliente, {
                            "type": "create_group_result",
                            "ok": True,
                            "grupo": grupo,
                            "text": "Grupo creado correctamente."
                        })

                    except ValueError as error:
                        enviar(cliente, {
                            "type": "create_group_result",
                            "ok": False,
                            "text": str(error)
                        })

                    except Exception as error:
                        print(f"Error al crear grupo: {error}")
                        enviar(cliente, {
                            "type": "create_group_result",
                            "ok": False,
                            "text": "No se pudo crear el grupo."
                        })


                # AGREGAR INTEGRANTES A UN GRUPO PRIVADO
                elif tipo == "add_group_member":

                    id_grupo = mensaje.get("id_grupo")
                    nombre_usuario = mensaje.get("usuario")

                    # VALIDAR DATOS RECIBIDOS

                    if not isinstance(id_grupo, str) or not isinstance(nombre_usuario, str):
                        enviar(cliente, {
                            "type": "add_group_member_result",
                            "ok": False,
                            "text": "Datos del grupo o usuario no validos."
                        })
                        continue

                    nombre_usuario = nombre_usuario.strip()

                    if not nombre_usuario:
                        enviar(cliente, {
                            "type": "add_group_member_result",
                            "ok": False,
                            "text": "Debes indicar un usuario."
                        })
                        continue

                    # COMPROBAR QUE EL USUARIO ESTE CONECTADO

                    with clientes_lock:
                        receptor = next(
                            (
                                c for c in list_of_clients
                                if c.id_publico is not None
                                and c.usuario is not None
                                and c.usuario.casefold() == nombre_usuario.casefold()
                            ),
                            None
                        )

                    if receptor is None:
                        enviar(cliente, {
                            "type": "add_group_member_result",
                            "ok": False,
                            "text": "El usuario no esta conectado al servidor."
                        })
                        continue

                    # AGREGAR USUARIO A LA BASE DE DATOS

                    try:
                        resultado = agregar_miembro_grupo(
                            id_grupo,
                            cliente.id_publico,
                            receptor.usuario
                        )

                        enviar(cliente, {
                            "type": "add_group_member_result",
                            "ok": True,
                            "integrante": resultado,
                            "text": "Integrante agregado correctamente."
                        })

                        # NOTIFICAR AL INTEGRANTE
                        enviar(receptor, {
                            "type": "group_added",
                            "id_grupo": id_grupo,
                            "text": "Te agregaron a un grupo."
                        })

                    except ValueError as error:
                        enviar(cliente, {
                            "type": "add_group_member_result",
                            "ok": False,
                            "text": str(error)
                        })

                    except Exception as error:
                        print(f"Error al agregar integrante: {error}")

                        enviar(cliente, {
                            "type": "add_group_member_result",
                            "ok": False,
                            "text": "No se pudo agregar al integrante."
                        })


                # ENVIAR MENSAJES GRUPALES
                elif tipo == "send_group_message":
                    enviar_mensaje_grupal(cliente, mensaje)

                # CONSULTAR HISTORIAL DE MENSAJES GRUPALES
                elif tipo == "group_history":
                    consultar_historial_grupo(cliente, mensaje)

                # RECUPERAR LOS GRUPOS DEL USUARIO AUTENTICADO
                elif tipo == "list_groups":
                    listar_grupos(cliente)

                # CONSULTAR SERVIDORES DEL USUARIO
                elif tipo == "list_servers":
                    listar_servidores(cliente)

                # CONSULTAR CANALES DE UN SERVIDOR
                elif tipo == "list_channels":
                    listar_canales(cliente, mensaje)

                # INVITAR CUENTAS REGISTRADAS A UN SERVIDOR
                elif tipo == "add_server_member":
                    agregar_integrante_servidor_tcp(cliente, mensaje)

                # CREAR UN CANAL DE TEXTO EN UN SERVIDOR
                elif tipo == "create_server_channel":
                    crear_canal_servidor_tcp(cliente, mensaje)

                # CONSULTAR INTEGRANTES DEL SERVIDOR
                elif tipo == "list_server_members":
                    listar_integrantes_servidor_tcp(cliente, mensaje)

                # ENVIAR MENSAJE DE CANAL
                elif tipo == "send_channel_message":
                    enviar_mensaje_canal(cliente, mensaje)

                # RECUPERAR HISTORIAL DE CANAL
                elif tipo == "channel_history":
                    consultar_historial_canal(cliente, mensaje)

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
