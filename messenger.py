import sys
import socket
import json
import threading
import html
import re
import os
import base64
import binascii
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QListWidgetItem, QMessageBox, QInputDialog,
    QFrame, QLabel, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout,
    QTextBrowser, QFileDialog
)
from PySide6.QtCore import QThread, Signal, Qt, QSize, QRect, QByteArray, QBuffer, QIODevice
from PySide6.QtGui import QPixmap, QIcon, QImageReader, QPainter, QPainterPath, QColor, QBrush
from uuid import UUID
from principal_ui import Ui_Messenger
from papoi_theme import THEMES, palette, apply_theme, set_theme, theme_name


# CLASE PARA LA COMUNICACIÓN TCP

MAX_FOTO_BYTES = 2 * 1024 * 1024
MAX_TCP_LINEA = 3 * 1024 * 1024 + 8192


class ThreadSocket(QThread):

    signal_event = Signal(dict)
    signal_connection = Signal(bool)

    def __init__(self, conexion, lector):
        super().__init__()
        self.server = conexion
        self.lector = lector
        self.connected = True
        self.running = True
        self.send_lock = threading.Lock()

    def run(self):
        self.signal_connection.emit(True)
        try:
            while self.running:
                linea = self.lector.readline(MAX_TCP_LINEA + 1)
                if not linea or len(linea) > MAX_TCP_LINEA:
                    break
                try:
                    evento = json.loads(linea.decode("utf-8"))
                except (UnicodeError, ValueError):
                    continue
                if isinstance(evento, dict):
                    self.signal_event.emit(evento)
        except (OSError, ValueError) as error:
            if self.running:
                self.signal_event.emit({
                    "type": "error", "text": str(error)
                })
        finally:
            self.connected = False
            self.signal_connection.emit(False)

    def enviar(self, mensaje):
        if not self.connected or self.server is None:
            return False
        try:
            datos = (json.dumps(mensaje, ensure_ascii=False) + "\n").encode("utf-8")
            with self.send_lock:
                self.server.sendall(datos)
            return True
        except OSError:
            return False

    def stop(self):
        self.running = False
        try:
            self.server.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.wait(2000)
        if not self.isRunning():
            self.lector.close()
        self.server.close()


# CLASE PRINCIPAL DEL MESSENGER

class MainWindow(QMainWindow, Ui_Messenger):

    def __init__(self, conexion, lector, cuenta):
        super().__init__()
        self.setupUi(self)

        self.cuenta = cuenta
        self.usuario = cuenta["usuario"]
        self.id_publico = cuenta["id_publico"].lower()
        self.nombre_visible = cuenta["nombre_visible"]
        self.destino_actual = "Chat general"
        self.historiales = {"Chat general": []}
        self.mensajes_privados = {}
        self.usuarios = {}
        self.servidores = []
        self.canales_por_servidor = {}
        self.canales_servidor = {}
        self.mensajes_canales_servidor = {}
        self.servidor_pendiente_seleccionar = None
        self.canal_servidor_pendiente = None
        self.agregando_miembro_servidor = False
        self.creando_canal_servidor = False
        self.cerrando = False
        self.creando_servidor = False
        self.creando_grupo = False
        self.agregando_integrante = False
        self.grupos = {}
        self.mensajes_grupales = {}
        self.grupo_pendiente_seleccionar = None

        # Canales de difusion: distintos de los canales de servidores.
        self.canales_difusion = {}
        self.publicaciones_difusion = {}
        self.creando_canal_difusion = False
        self.suscribiendo_canal_difusion = False
        self.canal_difusion_pendiente = None

        # Fotos solicitadas al servidor, almacenadas temporalmente en memoria.
        self.fotos_usuarios = {}
        self.fotos_pendientes = set()
        self.fotos_consultadas = set()
        self.actualizando_foto = False

        self.setWindowTitle(
            f"Messenger Papoi - {self.nombre_visible} (@{self.usuario})"
        )
        # Solo sustituye la presentación de Qt; no modifica TCP ni SQL.
        self._construir_interfaz_visual()

        self.actionConectar.setEnabled(False)
        self.actionSalir.triggered.connect(self.salir)
        self.actionCrearServidor.triggered.connect(self.crear_servidor)
        # La UI original ya tiene menuServidores; añadimos acciones sin editar .ui.
        self.menuServidores.addSeparator()
        self.actionActualizarServidores = self.menuServidores.addAction("Actualizar servidores")
        self.actionAgregarMiembroServidor = self.menuServidores.addAction("Agregar integrante...")
        self.actionCrearCanalServidor = self.menuServidores.addAction("Crear canal de texto...")
        self.actionVerMiembrosServidor = self.menuServidores.addAction("Ver integrantes")
        self.actionActualizarServidores.triggered.connect(self.solicitar_servidores)
        self.actionAgregarMiembroServidor.triggered.connect(self.agregar_miembro_servidor_gui)
        self.actionCrearCanalServidor.triggered.connect(self.crear_canal_servidor_gui)
        self.actionVerMiembrosServidor.triggered.connect(self.ver_miembros_servidor_gui)
        self.actionCrearGrupo.triggered.connect(self.crear_grupo)
        self.actionAgregarIntegrante.triggered.connect(self.agregar_integrante)
        self.actionActualizarGrupos.triggered.connect(self.solicitar_grupos)
        self.actionAgregarIntegrante.setEnabled(False)

        # Nuevo menu agregado por codigo: no es necesario editar principal.ui.
        self.menuDifusion = self.menuBar().addMenu("Difusión")
        self.actionCrearCanalDifusion = self.menuDifusion.addAction("Crear canal de difusión...")
        self.actionActualizarCanalesDifusion = self.menuDifusion.addAction("Actualizar canales")
        self.actionSuscribirCanalDifusion = self.menuDifusion.addAction("Suscribirme al canal seleccionado")
        self.actionCrearCanalDifusion.triggered.connect(self.crear_canal_difusion_gui)
        self.actionActualizarCanalesDifusion.triggered.connect(self.solicitar_canales_difusion)
        self.actionSuscribirCanalDifusion.triggered.connect(self.suscribirse_canal_difusion_gui)
        self.actionSuscribirCanalDifusion.setEnabled(False)
        self.menuPerfil = self.menuBar().addMenu("Perfil")
        self.actionCambiarFotoPerfil = self.menuPerfil.addAction("Cambiar mi foto...")
        self.actionActualizarFotos = self.menuPerfil.addAction("Actualizar fotografías")
        self.actionCambiarFotoPerfil.triggered.connect(self.cambiar_foto_perfil_gui)
        self.actionActualizarFotos.triggered.connect(self.actualizar_fotos_gui)
        self._configurar_menu_temas()

        self.btnSend.clicked.connect(self.mensaje_saliente)
        self.txtSend.returnPressed.connect(self.mensaje_saliente)
        self.listWidget.currentItemChanged.connect(self.cambiar_conversacion)

        self.listWidget.addItem("Chat general")
        self.listWidget.item(0).setData(
            Qt.ItemDataRole.UserRole, "Chat general"
        )
        self.listWidget.setCurrentRow(0)

        self.coneccion = ThreadSocket(conexion, lector)
        self.coneccion.signal_event.connect(self.recibir_evento)
        self.coneccion.signal_connection.connect(self.actualizar_conexion)
        self.coneccion.start()

        # SOLICITAR LOS SERVIDORES DEL USUARIO

        self.solicitar_servidores()
        self.solicitar_grupos()
        self.solicitar_canales_difusion()
        self.solicitar_foto_usuario(self.id_publico)




    # PRESENTACION VISUAL GLOBAL. LOS MENSAJES SIGUEN USANDO LOS MISMOS SOCKETS.

    def _construir_interfaz_visual(self):
        self.setMinimumSize(900, 585)
        self.resize(1190, 730)
        self.centralwidget.setObjectName("CentralWorkspace")
        self.verticalLayout.setContentsMargins(18, 16, 18, 16)
        self.verticalLayout.setSpacing(12)
        self.horizontalLayout.setSpacing(14)

        # Barra de marca superior.
        barra = QFrame(self.centralwidget)
        barra.setObjectName("AppHeader")
        barra_layout = QHBoxLayout(barra)
        barra_layout.setContentsMargins(18, 12, 18, 12)
        barra_layout.setSpacing(13)
        insignia = QLabel("P")
        insignia.setObjectName("BrandMark")
        insignia.setAlignment(Qt.AlignmentFlag.AlignCenter)
        insignia.setFixedSize(45, 45)
        barra_layout.addWidget(insignia)
        titulo = QLabel("Messenger Papoi")
        titulo.setObjectName("BrandTitle")
        barra_layout.addWidget(titulo)
        barra_layout.addStretch()
        self.label_estado_tcp = QLabel("●  Conectando...")
        self.label_estado_tcp.setObjectName("StatusText")
        barra_layout.addWidget(self.label_estado_tcp)
        self.avatar_propio = QLabel(barra)
        self.avatar_propio.setFixedSize(42, 42)
        self.avatar_propio.setToolTip("Tu fotografía de perfil")
        barra_layout.addWidget(self.avatar_propio)
        self.label_cuenta = QLabel("@" + self.usuario)
        self.label_cuenta.setObjectName("Pill")
        barra_layout.addWidget(self.label_cuenta)
        self.boton_cambiar_foto = QPushButton("Cambiar foto")
        self.boton_cambiar_foto.setObjectName("GhostButton")
        self.boton_cambiar_foto.setToolTip("Seleccionar JPG o PNG (máximo 2 MB)")
        self.boton_cambiar_foto.clicked.connect(self.cambiar_foto_perfil_gui)
        barra_layout.addWidget(self.boton_cambiar_foto)
        self.verticalLayout.insertWidget(0, barra)

        # Barra lateral: búsqueda, conversaciones, grupos y canales.
        panel_izquierdo = QFrame(self.centralwidget)
        panel_izquierdo.setObjectName("SidebarPanel")
        izquierda = QVBoxLayout(panel_izquierdo)
        izquierda.setContentsMargins(15, 19, 15, 15)
        izquierda.setSpacing(12)
        seccion = QLabel("CONVERSACIONES")
        seccion.setObjectName("SectionTitle")
        izquierda.addWidget(seccion)
        self.buscador_chats = QLineEdit()
        self.buscador_chats.setPlaceholderText("Buscar chat, grupo o canal...")
        self.buscador_chats.setClearButtonEnabled(True)
        self.buscador_chats.setMinimumHeight(44)
        self.buscador_chats.textChanged.connect(self._filtrar_lista)
        izquierda.addWidget(self.buscador_chats)

        self.horizontalLayout.removeWidget(self.listWidget)
        self.listWidget.setIconSize(QSize(29, 29))
        izquierda.addWidget(self.listWidget, 1)
        acciones = QHBoxLayout()
        acciones.setSpacing(8)
        btn_grupo = QPushButton("+ Grupo")
        btn_grupo.setObjectName("GhostButton")
        btn_grupo.setToolTip("Crear un grupo privado")
        btn_grupo.clicked.connect(self.crear_grupo)
        acciones.addWidget(btn_grupo)
        btn_canal = QPushButton("+ Canal")
        btn_canal.setObjectName("GhostButton")
        btn_canal.setToolTip("Crear un canal de difusión")
        btn_canal.clicked.connect(self.crear_canal_difusion_gui)
        acciones.addWidget(btn_canal)
        izquierda.addLayout(acciones)
        self.horizontalLayout.addWidget(panel_izquierdo, 1)

        # Panel de conversación y composición de mensajes.
        panel_chat = QFrame(self.centralwidget)
        panel_chat.setObjectName("ChatPanel")
        chat = QVBoxLayout(panel_chat)
        chat.setContentsMargins(14, 18, 14, 13)
        chat.setSpacing(11)

        encabezado = QHBoxLayout()
        self.avatar_conversacion = QLabel(panel_chat)
        self.avatar_conversacion.setFixedSize(48, 48)
        encabezado.addWidget(self.avatar_conversacion)
        nombres = QVBoxLayout()
        nombres.setSpacing(4)
        self.label_chat_titulo = QLabel("Chat general")
        self.label_chat_titulo.setObjectName("ChatTitle")
        nombres.addWidget(self.label_chat_titulo)
        self.label_chat_detalle = QLabel("Conversación para todos los conectados")
        self.label_chat_detalle.setObjectName("ChatSubtitle")
        self.label_chat_detalle.setWordWrap(True)
        nombres.addWidget(self.label_chat_detalle)
        encabezado.addLayout(nombres, 1)
        self.label_tipo = QLabel("GENERAL")
        self.label_tipo.setObjectName("Pill")
        encabezado.addWidget(self.label_tipo)
        chat.addLayout(encabezado)

        viejo_visor = self.txtMsgs
        self.horizontalLayout.removeWidget(viejo_visor)
        viejo_visor.hide()
        viejo_visor.deleteLater()
        self.txtMsgs = QTextBrowser(panel_chat)
        self.txtMsgs.setObjectName("txtMsgs")
        self.txtMsgs.setOpenExternalLinks(False)
        self.txtMsgs.setFrameShape(QFrame.Shape.NoFrame)
        chat.addWidget(self.txtMsgs, 1)

        # Reutilizar el mismo input y el botón del Designer: eventos intactos.
        self.horizontalLayout_2.removeWidget(self.txtSend)
        self.horizontalLayout_2.removeWidget(self.btnSend)
        self.verticalLayout.removeItem(self.horizontalLayout_2)
        self.horizontalLayout_2.deleteLater()

        compositor = QFrame(panel_chat)
        compositor.setObjectName("ComposerBar")
        composer = QHBoxLayout(compositor)
        composer.setContentsMargins(9, 8, 9, 8)
        composer.setSpacing(8)
        self.txtSend.setMinimumHeight(45)
        self.txtSend.setClearButtonEnabled(True)
        self.txtSend.setPlaceholderText("Escribe tu mensaje...")
        composer.addWidget(self.txtSend, 1)
        self.btnSend.setMinimumHeight(45)
        self.btnSend.setMinimumWidth(106)
        self.btnSend.setText("Enviar →")
        composer.addWidget(self.btnSend)
        chat.addWidget(compositor)
        self.horizontalLayout.addWidget(panel_chat, 3)

        self.listWidget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        apply_theme(QApplication.instance())
        self._actualizar_cabecera_conversacion()
        self._actualizar_avatares()

    def _configurar_menu_temas(self):
        self.menuApariencia = self.menuBar().addMenu("Apariencia")
        self.acciones_tema = {}
        for nombre, datos in THEMES.items():
            action = self.menuApariencia.addAction(datos["nombre"])
            action.setCheckable(True)
            action.setChecked(theme_name() == nombre)
            action.triggered.connect(
                lambda checked=False, tema=nombre: self._cambiar_tema(tema)
            )
            self.acciones_tema[nombre] = action

    def _cambiar_tema(self, nombre):
        set_theme(nombre, QApplication.instance())
        for clave, accion in self.acciones_tema.items():
            accion.setChecked(clave == nombre)
        self.mostrar_historial()
        self._actualizar_avatares()

    def _filtrar_lista(self, texto):
        busqueda = texto.strip().casefold()
        for indice in range(self.listWidget.count()):
            item = self.listWidget.item(indice)
            if not busqueda:
                item.setHidden(False)
            else:
                etiqueta = item.text().casefold()
                # Secciones siguen visibles para conservar la navegación.
                es_seccion = "────" in etiqueta
                item.setHidden(not es_seccion and busqueda not in etiqueta)

    def _actualizar_cabecera_conversacion(self):
        destino = self.destino_actual
        if destino in self.canales_servidor:
            canal = self.canales_servidor[destino]
            servidor = self._datos_servidor(canal.get("id_servidor")) or {}
            self.label_chat_titulo.setText("#" + canal.get("nombre", "general"))
            self.label_chat_detalle.setText(
                "Servidor: " + servidor.get("nombre", "Comunidad") + " · Canal de texto"
            )
            self.label_tipo.setText("SERVIDOR")
        elif self._es_clave_servidor(destino):
            servidor = self._datos_servidor_por_clave(destino) or {}
            self.label_chat_titulo.setText(servidor.get("nombre", "Servidor"))
            self.label_chat_detalle.setText("Selecciona un canal de texto como #general")
            self.label_tipo.setText(str(servidor.get("rol", "Miembro")).upper())
        elif destino in self.canales_difusion:
            canal = self.canales_difusion[destino]
            self.label_chat_titulo.setText(canal.get("nombre", "Canal"))
            estado = "Propietario" if canal.get("es_propietario") else (
                "Suscrito" if canal.get("suscrito") else "Sin suscripción"
            )
            self.label_chat_detalle.setText(
                "Canal de difusión · @" + str(canal.get("creador", "usuario"))
            )
            self.label_tipo.setText(estado.upper())
        elif destino in self.grupos:
            grupo = self.grupos[destino]
            self.label_chat_titulo.setText(grupo.get("nombre", "Grupo"))
            self.label_chat_detalle.setText("Grupo privado · Solo integrantes")
            self.label_tipo.setText(str(grupo.get("rol", "Miembro")).upper())
        elif destino in self.usuarios and destino != self.id_publico:
            datos = self.usuarios[destino]
            self.label_chat_titulo.setText(
                datos.get("nombre_visible") or datos.get("usuario", "Usuario")
            )
            self.label_chat_detalle.setText("Mensaje privado · @" + datos.get("usuario", ""))
            self.label_tipo.setText("PRIVADO")
        else:
            self.label_chat_titulo.setText("Chat general")
            self.label_chat_detalle.setText("Mensajes para las personas conectadas")
            self.label_tipo.setText("GENERAL")
        self._actualizar_avatares()

    # Las fotos viajan por TCP y se leen desde SQL Server: no dependen de
    # una ruta local. El icono predeterminado usa iniciales del usuario.
    @staticmethod
    def _avatar_redondo(imagen, nombre, dimension):
        pixmap = QPixmap(dimension, dimension)
        pixmap.fill(Qt.GlobalColor.transparent)
        pintor = QPainter(pixmap)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
        if isinstance(imagen, QPixmap) and not imagen.isNull():
            borde = QPainterPath()
            borde.addEllipse(0, 0, dimension, dimension)
            pintor.setClipPath(borde)
            ajustada = imagen.scaled(
                dimension, dimension,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            x = (dimension - ajustada.width()) // 2
            y = (dimension - ajustada.height()) // 2
            pintor.drawPixmap(x, y, ajustada)
        else:
            pintor.setBrush(QBrush(QColor(palette()["accent"])))
            pintor.setPen(Qt.PenStyle.NoPen)
            pintor.drawEllipse(0, 0, dimension, dimension)
            pintor.setPen(QColor("#101C32"))
            fuente = pintor.font()
            fuente.setBold(True)
            fuente.setPixelSize(max(11, int(dimension * .43)))
            pintor.setFont(fuente)
            inicial = str(nombre or "P").strip()[:1].upper() or "P"
            pintor.drawText(QRect(0, 0, dimension, dimension),
                            Qt.AlignmentFlag.AlignCenter, inicial)
        pintor.end()
        return pixmap

    def _actualizar_avatares(self):
        # Puede llamarse durante la construcción inicial de la ventana.
        if not hasattr(self, "avatar_propio"):
            return
        propio = self.fotos_usuarios.get(self.id_publico)
        self.avatar_propio.setPixmap(
            self._avatar_redondo(propio, self.usuario, 42)
        )
        if hasattr(self, "avatar_conversacion"):
            destino = self.destino_actual
            if destino in self.usuarios:
                datos = self.usuarios[destino]
                nombre = datos.get("nombre_visible") or datos.get("usuario", "P")
                foto = self.fotos_usuarios.get(destino)
            elif destino in self.grupos:
                nombre, foto = "G", None
            elif destino in self.canales_difusion:
                nombre, foto = "D", None
            elif destino in self.canales_servidor or self._es_clave_servidor(destino):
                nombre, foto = "S", None
            else:
                nombre, foto = "P", None
            self.avatar_conversacion.setPixmap(
                self._avatar_redondo(foto, nombre, 48)
            )

    def solicitar_foto_usuario(self, id_usuario, forzar=False):
        try:
            uid = str(UUID(str(id_usuario)))
        except (ValueError, TypeError, AttributeError):
            return
        if not hasattr(self, "coneccion") or not self.coneccion.connected:
            return
        if uid in self.fotos_pendientes:
            return
        if not forzar and uid in self.fotos_consultadas:
            return
        if self.coneccion.enviar({"type": "get_profile_photo", "id_usuario": uid}):
            self.fotos_pendientes.add(uid)

    def actualizar_fotos_gui(self):
        self.fotos_consultadas.clear()
        self.fotos_pendientes.clear()
        for uid in {self.id_publico, *self.usuarios.keys()}:
            self.solicitar_foto_usuario(uid, forzar=True)

    def cambiar_foto_perfil_gui(self):
        if not hasattr(self, "coneccion") or not self.coneccion.connected:
            QMessageBox.warning(self, "Perfil", "No hay conexión con el servidor.")
            return
        if self.actualizando_foto:
            return
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Selecciona tu foto de perfil", "",
            "Fotografías (*.png *.jpg *.jpeg)"
        )
        if not ruta:
            return
        try:
            if os.path.getsize(ruta) > MAX_FOTO_BYTES:
                raise ValueError("El archivo debe pesar máximo 2 MB.")
            lector = QImageReader(ruta)
            lector.setAutoTransform(True)
            dimensiones = lector.size()
            if dimensiones.isValid() and (dimensiones.width() > 8000 or
                                          dimensiones.height() > 8000):
                raise ValueError("La imagen tiene dimensiones demasiado grandes.")
            imagen = lector.read()
            if imagen.isNull():
                raise ValueError("No se pudo leer la fotografía seleccionada.")
            imagen = imagen.scaled(
                256, 256,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            # Convertir JPG/PNG a PNG compacto: iconos consistentes y
            # sin enviar rutas del disco ni metadatos del archivo original.
            datos_qt = QByteArray()
            buffer = QBuffer(datos_qt)
            if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
                raise ValueError("No se pudo preparar la imagen.")
            guardado = imagen.save(buffer, "PNG")
            buffer.close()
            if not guardado:
                raise ValueError("No se pudo convertir la imagen a PNG.")
            datos = bytes(datos_qt)
            if not datos or len(datos) > MAX_FOTO_BYTES:
                raise ValueError("La fotografía convertida debe pesar máximo 2 MB.")
            peticion = {
                "type": "set_profile_photo",
                "data_base64": base64.b64encode(datos).decode("ascii"),
                "nombre": "foto_papoi.png",
                "mime": "image/png"
            }
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Perfil", str(error))
            return
        self.actualizando_foto = True
        self.actionCambiarFotoPerfil.setEnabled(False)
        self.boton_cambiar_foto.setEnabled(False)
        if not self.coneccion.enviar(peticion):
            self.actualizando_foto = False
            self.actionCambiarFotoPerfil.setEnabled(True)
            self.boton_cambiar_foto.setEnabled(True)
            QMessageBox.warning(self, "Perfil", "No se pudo enviar la fotografía.")

    def _recibir_foto_perfil(self, evento):
        identificador = evento.get("id_usuario")
        try:
            uid = str(UUID(str(identificador)))
        except (ValueError, TypeError, AttributeError):
            return
        self.fotos_pendientes.discard(uid)
        if not evento.get("ok"):
            # Mantener estado anterior y permitir reintentar.
            self.fotos_consultadas.discard(uid)
            return
        data = evento.get("data_base64")
        if data is None:
            self.fotos_usuarios.pop(uid, None)
        elif isinstance(data, str) and len(data) <= 4 * ((MAX_FOTO_BYTES + 2)//3) + 8:
            try:
                binario = base64.b64decode(data, validate=True)
            except (binascii.Error, ValueError):
                return
            if len(binario) > MAX_FOTO_BYTES:
                return
            imagen = QPixmap()
            if not imagen.loadFromData(binario):
                return
            self.fotos_usuarios[uid] = imagen
        else:
            return
        self.fotos_consultadas.add(uid)
        self._actualizar_avatares()
        self.refrescar_lista()

    @staticmethod
    def _html_mensaje(texto, paleta):
        texto = str(texto)
        encontrado = re.match(r"^<([^>]+)>\s*(.*)$", texto, re.S)
        sistema = texto.startswith("[Sistema]")
        if encontrado:
            autor = encontrado.group(1)
            contenido = encontrado.group(2)
        elif sistema:
            autor = "Sistema"
            contenido = texto.replace("[Sistema]", "", 1).strip()
        else:
            autor = "Mensaje"
            contenido = texto
        es_mio = autor.strip().casefold() == "tú"
        fondo = paleta["mine"] if es_mio else paleta["message"]
        alineacion = "right" if es_mio else "left"
        autor_html = html.escape(autor)
        contenido_html = html.escape(contenido).replace("\n", "<br/>")
        # Qt QTextDocument renderiza tablas de forma consistente en Windows/Linux.
        return (
            '<table width="100%%" cellspacing="0" cellpadding="0">'
            '<tr><td align="%s">'
            '<table cellspacing="0" cellpadding="9" bgcolor="%s" '
            'style="border:1px solid %s;">'
            '<tr><td><span style="font-size:9pt;color:%s;font-weight:bold;">%s</span>'
            '<br/><span style="font-size:10pt;color:%s;">%s</span></td></tr>'
            '</table></td></tr></table><p style="margin:4px;">&nbsp;</p>'
        ) % (
            alineacion, fondo, paleta["border"],
            paleta["accent"] if es_mio else paleta["muted"],
            autor_html, paleta["text"], contenido_html
        )

    def _html_conversacion(self, mensajes, aviso=None):
        paleta = palette()
        if aviso:
            contenido = '<p style="color:%s;font-size:11pt;">%s</p>' % (
                paleta["muted"], html.escape(aviso)
            )
        elif mensajes:
            contenido = "".join(self._html_mensaje(m, paleta) for m in mensajes)
        else:
            contenido = (
                '<p style="color:%s;font-size:11pt;">'
                'Todavía no hay mensajes. Inicia la conversación.</p>' % paleta["muted"]
            )
        return (
            '<html><body style="background-color:%s;color:%s;'
            'font-family:Segoe UI,Arial;font-size:10pt;">%s</body></html>'
        ) % (paleta["panel"], paleta["text"], contenido)

    # FUNCIÓN PARA CREAR SERVIDORES

    def crear_servidor(self):
        if not self.coneccion.connected:
            QMessageBox.warning(
                self, "Conexión", "No hay conexión con el servidor TCP."
            )
            return
        if self.creando_servidor:
            return

        nombre, aceptado = QInputDialog.getText(
            self, "Crear servidor", "Nombre del servidor:"
        )
        if not aceptado:
            return

        nombre = nombre.strip()
        if not nombre or len(nombre) > 100:
            QMessageBox.warning(
                self, "Crear servidor",
                "El nombre debe tener entre 1 y 100 caracteres."
            )
            return

        self.creando_servidor = True
        self.actionCrearServidor.setEnabled(False)
        if not self.coneccion.enviar({
            "type": "create_server", "nombre": nombre
        }):
            self.creando_servidor = False
            self.actionCrearServidor.setEnabled(True)
            QMessageBox.warning(
                self, "Conexión", "No se pudo enviar la solicitud."
            )


    # SERVIDORES: CANALES DE TEXTO CON MENSAJES PARA SUS INTEGRANTES

    @staticmethod
    def clave_servidor(id_servidor):
        try:
            return "servidor:" + str(UUID(str(id_servidor)))
        except (ValueError, TypeError, AttributeError):
            return None

    @staticmethod
    def clave_canal_servidor(id_canal):
        try:
            return "canal_servidor:" + str(UUID(str(id_canal)))
        except (ValueError, TypeError, AttributeError):
            return None

    @staticmethod
    def _es_clave_servidor(valor):
        return isinstance(valor, str) and valor.startswith("servidor:")

    def _datos_servidor(self, id_servidor):
        clave = self.clave_servidor(id_servidor)
        return next((s for s in self.servidores
                     if self.clave_servidor(s.get("id_servidor")) == clave), None)

    def _datos_servidor_por_clave(self, clave):
        return next((s for s in self.servidores
                     if self.clave_servidor(s.get("id_servidor")) == clave), None)

    def _servidor_contexto(self):
        if self._es_clave_servidor(self.destino_actual):
            return self._datos_servidor_por_clave(self.destino_actual)
        canal = self.canales_servidor.get(self.destino_actual)
        if canal is not None:
            return self._datos_servidor(canal.get("id_servidor"))
        return None

    def solicitar_servidores(self):
        if hasattr(self, "coneccion") and self.coneccion.connected:
            self.coneccion.enviar({"type": "list_servers"})

    def solicitar_canales_servidor(self, id_servidor):
        if self.coneccion.connected:
            self.coneccion.enviar({
                "type": "list_channels", "id_servidor": id_servidor
            })

    def agregar_miembro_servidor_gui(self):
        servidor = self._servidor_contexto()
        if servidor is None:
            QMessageBox.information(
                self, "Servidores", "Selecciona un servidor o uno de sus canales."
            )
            return
        if servidor.get("rol") != "Administrador":
            QMessageBox.warning(self, "Servidores", "Solo un administrador puede invitar integrantes.")
            return
        if self.agregando_miembro_servidor or not self.coneccion.connected:
            return
        usuario, aceptado = QInputDialog.getText(
            self, "Invitar al servidor", "Nombre de usuario registrado (ej. gael1234):"
        )
        if not aceptado:
            return
        usuario = usuario.strip()
        if not usuario or len(usuario) > 50:
            QMessageBox.warning(self, "Servidores", "Introduce un nombre de usuario válido.")
            return
        self.agregando_miembro_servidor = True
        self.actualizar_acciones_servidor()
        if not self.coneccion.enviar({
            "type": "add_server_member",
            "id_servidor": servidor["id_servidor"],
            "usuario": usuario,
        }):
            self.agregando_miembro_servidor = False
            self.actualizar_acciones_servidor()
            QMessageBox.warning(self, "Servidores", "No se pudo enviar la invitación.")

    def crear_canal_servidor_gui(self):
        servidor = self._servidor_contexto()
        if servidor is None:
            QMessageBox.information(
                self, "Servidores", "Selecciona un servidor o uno de sus canales."
            )
            return
        if servidor.get("rol") != "Administrador":
            QMessageBox.warning(self, "Servidores", "Solo un administrador puede crear canales.")
            return
        if self.creando_canal_servidor or not self.coneccion.connected:
            return
        nombre, aceptado = QInputDialog.getText(
            self, "Nuevo canal de texto", "Nombre del canal (ej. proyectos):"
        )
        if not aceptado:
            return
        nombre = nombre.strip()
        if not 1 <= len(nombre) <= 100:
            QMessageBox.warning(self, "Servidores", "Usa un nombre de 1 a 100 caracteres.")
            return
        descripcion, aceptado = QInputDialog.getText(
            self, "Nuevo canal de texto", "Descripción (opcional):"
        )
        if not aceptado:
            return
        if len(descripcion.strip()) > 255:
            QMessageBox.warning(self, "Servidores", "Máximo 255 caracteres en la descripción.")
            return
        self.creando_canal_servidor = True
        self.actualizar_acciones_servidor()
        if not self.coneccion.enviar({
            "type": "create_server_channel", "id_servidor": servidor["id_servidor"],
            "nombre": nombre, "descripcion": descripcion.strip(),
        }):
            self.creando_canal_servidor = False
            self.actualizar_acciones_servidor()
            QMessageBox.warning(self, "Servidores", "No se pudo solicitar la creación.")

    def ver_miembros_servidor_gui(self):
        servidor = self._servidor_contexto()
        if servidor is None:
            QMessageBox.information(self, "Servidores", "Selecciona primero un servidor.")
            return
        if self.coneccion.connected:
            self.coneccion.enviar({
                "type": "list_server_members", "id_servidor": servidor["id_servidor"]
            })

    def actualizar_acciones_servidor(self):
        if not hasattr(self, "coneccion"):
            return
        conectado = self.coneccion.connected and not self.cerrando
        servidor = self._servidor_contexto()
        es_administrador = bool(servidor and servidor.get("rol") == "Administrador")
        self.actionActualizarServidores.setEnabled(conectado)
        self.actionAgregarMiembroServidor.setEnabled(
            conectado and es_administrador and not self.agregando_miembro_servidor
        )
        self.actionCrearCanalServidor.setEnabled(
            conectado and es_administrador and not self.creando_canal_servidor
        )
        self.actionVerMiembrosServidor.setEnabled(conectado and servidor is not None)

    def registrar_mensaje_canal_servidor(self, mensaje):
        if not isinstance(mensaje, dict):
            return
        clave = self.clave_canal_servidor(mensaje.get("id_canal"))
        id_mensaje = mensaje.get("id_mensaje")
        contenido = mensaje.get("contenido")
        if clave is None or type(id_mensaje) is not int or not isinstance(contenido, str):
            return
        remitente = mensaje.get("id_remitente", "")
        if isinstance(remitente, str) and remitente.casefold() == self.id_publico.casefold():
            nombre = "Tú"
        else:
            usuario = mensaje.get("usuario", "")
            visible = mensaje.get("nombre_visible") or usuario or "Usuario"
            nombre = f"{visible} (@{usuario})" if usuario else visible
        almacenados = self.mensajes_canales_servidor.setdefault(clave, {})
        almacenados[id_mensaje] = f"<{nombre}> {contenido}"
        self.historiales[clave] = [almacenados[i] for i in sorted(almacenados)]
        if self.destino_actual == clave:
            self.mostrar_historial()

    # CANALES DE DIFUSION (SOLO EL CREADOR PUEDE PUBLICAR)

    @staticmethod
    def clave_canal_difusion(id_canal):
        try:
            return "difusion:" + str(UUID(str(id_canal)))
        except (ValueError, TypeError, AttributeError):
            return None

    def solicitar_canales_difusion(self):
        if not self.coneccion.connected:
            return
        if not self.coneccion.enviar({"type": "list_broadcast_channels"}):
            QMessageBox.warning(self, "Difusión", "No se pudo consultar la lista de canales.")

    def crear_canal_difusion_gui(self):
        if not self.coneccion.connected or self.creando_canal_difusion:
            return
        nombre, aceptado = QInputDialog.getText(
            self, "Crear canal de difusión", "Nombre del canal (1 a 100 caracteres):"
        )
        if not aceptado:
            return
        nombre = nombre.strip()
        if not 1 <= len(nombre) <= 100:
            QMessageBox.warning(self, "Difusión", "El nombre debe tener entre 1 y 100 caracteres.")
            return
        descripcion, aceptado = QInputDialog.getText(
            self, "Crear canal de difusión", "Descripción (opcional, máximo 500 caracteres):"
        )
        if not aceptado:
            return
        descripcion = descripcion.strip()
        if len(descripcion) > 500:
            QMessageBox.warning(self, "Difusión", "Máximo 500 caracteres en la descripción.")
            return
        self.creando_canal_difusion = True
        self.actualizar_estado_difusion()
        if not self.coneccion.enviar({
            "type": "create_broadcast_channel", "nombre": nombre,
            "descripcion": descripcion,
        }):
            self.creando_canal_difusion = False
            self.actualizar_estado_difusion()
            QMessageBox.warning(self, "Difusión", "No se pudo enviar la solicitud.")

    def suscribirse_canal_difusion_gui(self):
        if not self.coneccion.connected or self.suscribiendo_canal_difusion:
            return
        canal = self.canales_difusion.get(self.destino_actual)
        if canal is None:
            QMessageBox.information(self, "Difusión", "Selecciona un canal de difusión.")
            return
        if canal.get("suscrito"):
            QMessageBox.information(self, "Difusión", "Ya estás suscrito a este canal.")
            return
        self.suscribiendo_canal_difusion = True
        self.actualizar_estado_difusion()
        if not self.coneccion.enviar({
            "type": "subscribe_broadcast_channel",
            "id_canal": canal["id_canal"],
        }):
            self.suscribiendo_canal_difusion = False
            self.actualizar_estado_difusion()
            QMessageBox.warning(self, "Difusión", "No se pudo enviar la suscripción.")

    def solicitar_historial_canal_difusion(self, clave):
        canal = self.canales_difusion.get(clave)
        if not canal or not canal.get("suscrito") or not self.coneccion.connected:
            return
        if not self.coneccion.enviar({
            "type": "broadcast_channel_history",
            "id_canal": canal["id_canal"],
        }):
            QMessageBox.warning(self, "Difusión", "No se pudo consultar el historial.")

    def registrar_publicacion_difusion(self, publicacion):
        if not isinstance(publicacion, dict):
            return
        clave = self.clave_canal_difusion(publicacion.get("id_canal"))
        identificador = publicacion.get("id_publicacion")
        contenido = publicacion.get("contenido")
        if clave is None or type(identificador) is not int or not isinstance(contenido, str):
            return

        id_autor = publicacion.get("id_autor", "")
        if isinstance(id_autor, str) and id_autor.casefold() == self.id_publico.casefold():
            nombre = "Tú"
        else:
            usuario = publicacion.get("autor") or "Propietario"
            nombre = f"@{usuario}"

        guardadas = self.publicaciones_difusion.setdefault(clave, {})
        guardadas[identificador] = f"<{nombre}> {contenido}"
        self.historiales[clave] = [guardadas[i] for i in sorted(guardadas)]
        if self.destino_actual == clave:
            self.mostrar_historial()

    def actualizar_estado_difusion(self):
        # La interfaz solo refuerza los permisos: la validacion real esta
        # en server.py y db.py.
        if not hasattr(self, "coneccion"):
            return
        conectado = self.coneccion.connected and not self.cerrando
        canal = self.canales_difusion.get(self.destino_actual)
        propietario = bool(canal and canal.get("es_propietario"))
        suscrito = bool(canal and canal.get("suscrito"))
        puede_escribir = (
            not self._es_clave_servidor(self.destino_actual)
            and (canal is None or (propietario and suscrito))
        )

        self.txtSend.setEnabled(conectado and puede_escribir)
        self.btnSend.setEnabled(conectado and puede_escribir)
        self.actionCrearCanalDifusion.setEnabled(
            conectado and not self.creando_canal_difusion
        )
        self.actionActualizarCanalesDifusion.setEnabled(conectado)
        self.actionSuscribirCanalDifusion.setEnabled(
            conectado and canal is not None and not suscrito
            and not self.suscribiendo_canal_difusion
        )
        if self._es_clave_servidor(self.destino_actual):
            self.txtSend.setPlaceholderText("Selecciona #general u otro canal de texto.")
        elif canal is not None and not suscrito:
            self.txtSend.setPlaceholderText("Suscríbete para leer este canal.")
        elif canal is not None and not propietario:
            self.txtSend.setPlaceholderText("Solo el propietario puede publicar.")
        else:
            self.txtSend.setPlaceholderText("Escribe tu mensaje aquí...")

    # OPERACIONES DE GRUPOS DESDE LA INTERFAZ

    @staticmethod
    def clave_grupo(id_grupo):
        try:
            return "grupo:" + str(UUID(str(id_grupo)))
        except (ValueError, TypeError, AttributeError):
            return None

    def solicitar_grupos(self):
        if self.coneccion.connected:
            if not self.coneccion.enviar({"type": "list_groups"}):
                QMessageBox.warning(self, "Grupos", "No se pudo solicitar la lista de grupos.")

    def crear_grupo(self):
        if not self.coneccion.connected:
            QMessageBox.warning(self, "Grupos", "No hay conexión TCP.")
            return
        if self.creando_grupo:
            return
        nombre, aceptado = QInputDialog.getText(
            self, "Crear grupo", "Nombre del grupo (máximo 100 caracteres):"
        )
        if not aceptado:
            return
        nombre = nombre.strip()
        if not 1 <= len(nombre) <= 100:
            QMessageBox.warning(self, "Grupos", "El nombre debe tener entre 1 y 100 caracteres.")
            return
        self.creando_grupo = True
        self.actionCrearGrupo.setEnabled(False)
        if not self.coneccion.enviar({"type": "create_group", "nombre": nombre}):
            self.creando_grupo = False
            self.actionCrearGrupo.setEnabled(True)
            QMessageBox.warning(self, "Grupos", "No se pudo enviar la solicitud.")

    def agregar_integrante(self):
        if not self.coneccion.connected or self.agregando_integrante:
            return
        clave = self.destino_actual
        if not isinstance(clave, str) or clave not in self.grupos:
            QMessageBox.warning(self, "Grupos", "Selecciona primero un grupo.")
            return
        if self.grupos[clave].get("rol") != "Administrador":
            QMessageBox.warning(self, "Grupos", "Solo un administrador puede agregar integrantes.")
            return

        opciones = []
        mapa = {}
        for id_usuario, datos in sorted(
            self.usuarios.items(), key=lambda par: par[1].get("usuario", "").casefold()
        ):
            if id_usuario == self.id_publico:
                continue
            nombre_usuario = datos.get("usuario")
            if not isinstance(nombre_usuario, str):
                continue
            etiqueta = f"{datos.get('nombre_visible') or nombre_usuario} (@{nombre_usuario})"
            opciones.append(etiqueta)
            mapa[etiqueta] = nombre_usuario

        if not opciones:
            QMessageBox.information(self, "Grupos", "No hay otros usuarios conectados.")
            return
        elegido, aceptado = QInputDialog.getItem(
            self, "Agregar integrante", "Selecciona un usuario conectado:",
            opciones, 0, False
        )
        if not aceptado or elegido not in mapa:
            return

        self.agregando_integrante = True
        self.actionAgregarIntegrante.setEnabled(False)
        if not self.coneccion.enviar({
            "type": "add_group_member",
            "id_grupo": self.grupos[clave]["id_grupo"],
            "usuario": mapa[elegido],
        }):
            self.agregando_integrante = False
            self.habilitar_acciones_grupo()
            QMessageBox.warning(self, "Grupos", "No se pudo enviar la solicitud.")

    def habilitar_acciones_grupo(self):
        conectado = self.coneccion.connected
        self.actionCrearGrupo.setEnabled(conectado and not self.creando_grupo)
        self.actionActualizarGrupos.setEnabled(conectado)
        es_admin = (
            self.destino_actual in self.grupos
            and self.grupos[self.destino_actual].get("rol") == "Administrador"
        )
        self.actionAgregarIntegrante.setEnabled(
            conectado and es_admin and not self.agregando_integrante
        )

    def registrar_mensaje_grupal(self, mensaje):
        if not isinstance(mensaje, dict):
            return
        clave = self.clave_grupo(mensaje.get("id_grupo"))
        id_mensaje = mensaje.get("id_mensaje")
        if clave is None or not isinstance(id_mensaje, int):
            return
        remitente = mensaje.get("id_remitente", "")
        if isinstance(remitente, str) and remitente.lower() == self.id_publico:
            nombre = "Tú"
        else:
            visible = mensaje.get("nombre_visible") or "Usuario"
            usuario = mensaje.get("usuario")
            nombre = f"{visible} (@{usuario})" if usuario else visible
        contenido = mensaje.get("contenido")
        if not isinstance(contenido, str):
            return
        almacenados = self.mensajes_grupales.setdefault(clave, {})
        almacenados[id_mensaje] = f"<{nombre}> {contenido}"
        self.historiales[clave] = [almacenados[n] for n in sorted(almacenados)]
        if clave == self.destino_actual:
            self.mostrar_historial()

    # FUNCIÓN PARA ENVIAR MENSAJES

    def mensaje_saliente(self):
        texto = self.txtSend.text().strip()
        if not texto or not self.coneccion.connected:
            return
        destino = self.destino_actual
        if destino == "Chat general":
            if len(texto) > 5000:
                QMessageBox.warning(self, "Mensaje", "Máximo 5000 caracteres.")
                return
            mensaje = {"type": "public", "text": texto}
        elif destino in self.canales_difusion:
            canal = self.canales_difusion[destino]
            if not canal.get("suscrito") or not canal.get("es_propietario"):
                QMessageBox.warning(self, "Difusión", "Solo el propietario puede publicar.")
                return
            if len(texto) > 4000:
                QMessageBox.warning(self, "Difusión", "Máximo 4000 caracteres por publicación.")
                return
            mensaje = {
                "type": "publish_broadcast_channel",
                "id_canal": canal["id_canal"],
                "text": texto,
            }
        elif destino in self.canales_servidor:
            if len(texto) > 4000:
                QMessageBox.warning(self, "Servidores", "Máximo 4000 caracteres.")
                return
            mensaje = {
                "type": "send_channel_message",
                "id_canal": self.canales_servidor[destino]["id_canal"],
                "text": texto,
            }
        elif self._es_clave_servidor(destino):
            QMessageBox.information(self, "Servidores", "Selecciona primero #general.")
            return
        elif destino in self.grupos:
            if len(texto) > 4000:
                QMessageBox.warning(self, "Mensaje", "Máximo 4000 caracteres en grupos.")
                return
            mensaje = {
                "type": "send_group_message",
                "id_grupo": self.grupos[destino]["id_grupo"],
                "text": texto,
            }
        else:
            if len(texto) > 4000:
                QMessageBox.warning(self, "Mensaje", "Máximo 4000 caracteres en mensajes privados.")
                return
            if destino not in self.usuarios:
                QMessageBox.warning(self, "Mensaje", "Usuario no disponible.")
                return
            mensaje = {"type": "private", "to": destino, "text": texto}

        if self.coneccion.enviar(mensaje):
            self.txtSend.clear()
            if destino == "Chat general":
                self.agregar_mensaje(destino, f"<Tú> {texto}")
        else:
            QMessageBox.warning(self, "Conexión", "No se pudo enviar el mensaje.")


    # FUNCIÓN PARA GUARDAR Y MOSTRAR MENSAJES

    def agregar_mensaje(self, conversacion, texto):
        self.historiales.setdefault(conversacion, []).append(texto)
        if conversacion == self.destino_actual:
            self.mostrar_historial()

    def mostrar_historial(self):
        self._actualizar_cabecera_conversacion()
        mensajes = self.historiales.get(self.destino_actual, [])
        canal = self.canales_difusion.get(self.destino_actual)
        if self._es_clave_servidor(self.destino_actual):
            aviso = "Selecciona #general u otro canal debajo del servidor para conversar."
        elif self.destino_actual in self.canales_servidor and not mensajes:
            aviso = "No hay mensajes todavía. Escribe: Prueba Papoi"
        elif canal is not None and not canal.get("suscrito"):
            aviso = "Aún no estás suscrito. Abre Difusión > Suscribirme al canal seleccionado."
        elif canal is not None and not mensajes:
            aviso = "Todavía no hay publicaciones en este canal."
        else:
            aviso = None
        self.txtMsgs.setHtml(self._html_conversacion(mensajes, aviso))
        barra = self.txtMsgs.verticalScrollBar()
        barra.setValue(barra.maximum())


    # REGISTRAR MENSAJES PRIVADOS SIN DUPLICADOS

    def registrar_mensaje_privado(self, id_otro_usuario, mensaje):
        if not isinstance(id_otro_usuario, str) or not isinstance(mensaje, dict):
            return
        id_otro_usuario = id_otro_usuario.lower()

        id_mensaje = mensaje.get("id_mensaje")
        if not isinstance(id_mensaje, int):
            return

        id_remitente = mensaje.get("id_remitente", "")
        if isinstance(id_remitente, str) and id_remitente.lower() == self.id_publico.lower():
            nombre = "Tú"
        else:
            nombre_visible = mensaje.get("nombre_visible") or "Usuario"
            usuario = mensaje.get("usuario")
            nombre = f"{nombre_visible} (@{usuario})" if usuario else nombre_visible

        texto = mensaje.get("contenido", "")
        if not isinstance(texto, str):
            return

        almacenados = self.mensajes_privados.setdefault(id_otro_usuario, {})
        almacenados[id_mensaje] = f"<{nombre}> {texto}"
        self.historiales[id_otro_usuario] = [
            almacenados[identificador] for identificador in sorted(almacenados)
        ]
        if id_otro_usuario == self.destino_actual:
            self.mostrar_historial()


    # FUNCIÓN PARA RECIBIR MENSAJES

    def recibir_evento(self, evento):
        tipo = evento.get("type")
        if tipo == "users":
            self.actualizar_usuarios(evento.get("users", []))

        elif tipo == "profile_photo_result":
            self.actualizando_foto = False
            self.actionCambiarFotoPerfil.setEnabled(self.coneccion.connected)
            self.boton_cambiar_foto.setEnabled(self.coneccion.connected)
            if evento.get("ok"):
                QMessageBox.information(self, "Perfil", "Fotografía actualizada correctamente.")
                self.fotos_consultadas.discard(self.id_publico)
                self.fotos_pendientes.discard(self.id_publico)
                self.solicitar_foto_usuario(self.id_publico, forzar=True)
            else:
                QMessageBox.warning(self, "Perfil", evento.get("text", "No se pudo guardar la fotografía."))

        elif tipo == "profile_photo_data":
            self._recibir_foto_perfil(evento)

        elif tipo == "profile_photo_updated":
            try:
                uid = str(UUID(str(evento.get("id_usuario"))))
            except (ValueError, TypeError, AttributeError):
                return
            self.fotos_consultadas.discard(uid)
            self.fotos_pendientes.discard(uid)
            self.solicitar_foto_usuario(uid, forzar=True)

        elif tipo == "public":
            nombre = evento.get("from", "")
            usuario = evento.get("from_usuario", "")
            texto = evento.get("text", "")
            self.agregar_mensaje(
                "Chat general", f"<{nombre} (@{usuario})> {texto}"
            )

        elif tipo == "private":
            remitente_id = evento.get("from_id")
            if not isinstance(remitente_id, str):
                return
            self.registrar_mensaje_privado(remitente_id, {
                "id_mensaje": evento.get("id_mensaje"),
                "id_remitente": remitente_id,
                "nombre_visible": evento.get("from", ""),
                "usuario": evento.get("from_usuario", ""),
                "contenido": evento.get("text", "")
            })

        elif tipo == "private_result":
            if evento.get("ok"):
                self.registrar_mensaje_privado(
                    evento.get("to"), evento.get("message")
                )
            else:
                QMessageBox.warning(
                    self, "Mensaje privado",
                    evento.get("text", "No se pudo guardar el mensaje.")
                )

        elif tipo == "private_history_result":
            if evento.get("ok"):
                destinatario = evento.get("to")
                mensajes = evento.get("messages", [])
                if isinstance(destinatario, str) and isinstance(mensajes, list):
                    for mensaje in mensajes:
                        self.registrar_mensaje_privado(destinatario, mensaje)
            else:
                QMessageBox.warning(
                    self, "Historial privado",
                    evento.get("text", "No se pudo consultar el historial.")
                )

        # RESPUESTAS DE LOS CANALES DE DIFUSION
        elif tipo == "broadcast_channels_list":
            if not evento.get("ok"):
                QMessageBox.warning(self, "Difusión", evento.get("text", "No se pudieron consultar los canales."))
            else:
                lista = evento.get("channels", [])
                if not isinstance(lista, list):
                    return
                canales = {}
                for canal in lista:
                    if not isinstance(canal, dict) or not isinstance(canal.get("nombre"), str):
                        continue
                    clave = self.clave_canal_difusion(canal.get("id_canal"))
                    if clave is not None:
                        canales[clave] = canal
                self.canales_difusion = canales
                if self.canal_difusion_pendiente in canales:
                    self.destino_actual = self.canal_difusion_pendiente
                self.canal_difusion_pendiente = None
                self.refrescar_lista()
                self.solicitar_historial_canal_difusion(self.destino_actual)

        elif tipo == "create_broadcast_channel_result":
            self.creando_canal_difusion = False
            self.actualizar_estado_difusion()
            if evento.get("ok"):
                canal = evento.get("canal", {})
                self.canal_difusion_pendiente = self.clave_canal_difusion(canal.get("id_canal"))
                self.solicitar_canales_difusion()
                QMessageBox.information(self, "Difusión", "Canal creado correctamente.")
            else:
                QMessageBox.warning(self, "Difusión", evento.get("text", "No se pudo crear el canal."))

        elif tipo == "subscribe_broadcast_channel_result":
            self.suscribiendo_canal_difusion = False
            self.actualizar_estado_difusion()
            if evento.get("ok"):
                self.canal_difusion_pendiente = self.clave_canal_difusion(evento.get("id_canal"))
                self.solicitar_canales_difusion()
                QMessageBox.information(self, "Difusión", "Suscripción correcta. Ya puedes consultar el historial.")
            else:
                QMessageBox.warning(self, "Difusión", evento.get("text", "No se pudo realizar la suscripción."))

        elif tipo == "publish_broadcast_channel_result":
            if evento.get("ok"):
                # El evento de tiempo real puede llegar tambien al autor.
                # El identificador evita mostrar la publicacion duplicada.
                self.registrar_publicacion_difusion(evento.get("post"))
            else:
                QMessageBox.warning(self, "Difusión", evento.get("text", "No se pudo publicar el aviso."))

        elif tipo == "broadcast_channel_post":
            self.registrar_publicacion_difusion(evento.get("post"))

        elif tipo == "broadcast_channel_history_result":
            if evento.get("ok"):
                publicaciones = evento.get("posts", [])
                if isinstance(publicaciones, list):
                    for publicacion in publicaciones:
                        self.registrar_publicacion_difusion(publicacion)
                    if self.clave_canal_difusion(evento.get("id_canal")) == self.destino_actual:
                        self.mostrar_historial()
            else:
                QMessageBox.warning(self, "Historial de difusión", evento.get("text", "No se pudo consultar el historial."))

        # RESPUESTAS DE GRUPOS MEDIANTE TCP
        elif tipo == "groups_list":
            if not evento.get("ok"):
                QMessageBox.warning(self, "Grupos", evento.get("text", "No se pudieron consultar los grupos."))
            else:
                grupos = evento.get("groups", [])
                if not isinstance(grupos, list):
                    return
                nuevos = {}
                for grupo in grupos:
                    if not isinstance(grupo, dict):
                        continue
                    clave = self.clave_grupo(grupo.get("id_grupo"))
                    if clave is not None and isinstance(grupo.get("nombre"), str):
                        nuevos[clave] = grupo
                self.grupos = nuevos
                if self.grupo_pendiente_seleccionar in nuevos:
                    self.destino_actual = self.grupo_pendiente_seleccionar
                self.grupo_pendiente_seleccionar = None
                self.refrescar_lista()
                if self.destino_actual in self.grupos:
                    self.coneccion.enviar({
                        "type": "group_history",
                        "id_grupo": self.grupos[self.destino_actual]["id_grupo"],
                    })

        elif tipo == "create_group_result":
            self.creando_grupo = False
            self.habilitar_acciones_grupo()
            if evento.get("ok"):
                grupo = evento.get("grupo")
                id_grupo = grupo.get("id_grupo") if isinstance(grupo, dict) else grupo
                self.grupo_pendiente_seleccionar = self.clave_grupo(id_grupo)
                self.solicitar_grupos()
                QMessageBox.information(self, "Grupos", "Grupo creado correctamente.")
            else:
                QMessageBox.warning(self, "Grupos", evento.get("text", "No se pudo crear el grupo."))

        elif tipo == "add_group_member_result":
            self.agregando_integrante = False
            self.habilitar_acciones_grupo()
            if evento.get("ok"):
                QMessageBox.information(self, "Grupos", "Integrante agregado correctamente.")
            else:
                QMessageBox.warning(self, "Grupos", evento.get("text", "No se pudo agregar al integrante."))

        elif tipo == "group_added":
            self.agregar_mensaje("Chat general", "[Sistema] Te agregaron a un grupo.")
            self.solicitar_grupos()

        elif tipo == "group_message":
            self.registrar_mensaje_grupal(evento.get("message"))

        elif tipo == "group_message_result":
            if evento.get("ok"):
                self.registrar_mensaje_grupal(evento.get("message"))
            else:
                QMessageBox.warning(self, "Mensaje grupal", evento.get("text", "No se pudo guardar el mensaje."))

        elif tipo == "group_history_result":
            if evento.get("ok"):
                mensajes = evento.get("messages", [])
                if isinstance(mensajes, list):
                    for mensaje in mensajes:
                        self.registrar_mensaje_grupal(mensaje)
            else:
                QMessageBox.warning(self, "Historial de grupo", evento.get("text", "No se pudo consultar el historial."))

        elif tipo == "system":
            self.agregar_mensaje(
                "Chat general", f"[Sistema] {evento.get('text', '')}"
            )

        elif tipo == "create_server_result":
            self.creando_servidor = False
            if self.coneccion.connected:
                self.actionCrearServidor.setEnabled(True)
            if evento.get("ok"):
                nombre = evento.get("nombre", "Servidor")
                id_servidor = evento.get("id_servidor", "")
                QMessageBox.information(
                    self, "Servidor creado",
                    f"Se creó correctamente '{nombre}'.\n\n"
                    f"ID del servidor: {id_servidor}"
                )
                self.servidor_pendiente_seleccionar = self.clave_servidor(id_servidor)
                self.solicitar_servidores()
            else:
                QMessageBox.warning(
                    self, "Crear servidor",
                    evento.get("text", "No se pudo crear el servidor.")
                )

        # ADMINISTRACIÓN DE SERVIDORES Y SUS CANALES
        elif tipo == "add_server_member_result":
            self.agregando_miembro_servidor = False
            self.actualizar_acciones_servidor()
            if evento.get("ok"):
                integrante = evento.get("integrante") or {}
                QMessageBox.information(
                    self, "Servidores",
                    "Integrante agregado: @" + str(integrante.get("usuario", "usuario"))
                )
            else:
                QMessageBox.warning(self, "Servidores", evento.get("text", "No se pudo invitar."))

        elif tipo == "server_member_added":
            self.agregar_mensaje("Chat general", "[Sistema] Te agregaron a un servidor.")
            self.solicitar_servidores()

        elif tipo == "create_server_channel_result":
            self.creando_canal_servidor = False
            self.actualizar_acciones_servidor()
            if evento.get("ok"):
                canal = evento.get("canal") or {}
                self.canal_servidor_pendiente = self.clave_canal_servidor(canal.get("id_canal"))
                self.solicitar_canales_servidor(canal.get("id_servidor"))
                QMessageBox.information(self, "Servidores", "Canal de texto creado correctamente.")
            else:
                QMessageBox.warning(self, "Servidores", evento.get("text", "No se creó el canal."))

        elif tipo == "server_channel_created":
            id_servidor = evento.get("id_servidor")
            if self.clave_servidor(id_servidor) is not None:
                self.solicitar_canales_servidor(id_servidor)

        elif tipo == "server_members_list":
            if evento.get("ok"):
                miembros = evento.get("members", [])
                detalles = [
                    f"{m.get('nombre_visible') or m.get('usuario')} "
                    f"(@{m.get('usuario')}) — {m.get('rol', 'Miembro')}"
                    for m in miembros if isinstance(m, dict)
                ]
                QMessageBox.information(
                    self, "Integrantes del servidor",
                    "\n".join(detalles) if detalles else "No hay integrantes."
                )
            else:
                QMessageBox.warning(self, "Servidores", evento.get("text", "No se pudo consultar."))

        elif tipo == "channel_message_result":
            if evento.get("ok"):
                self.registrar_mensaje_canal_servidor(evento.get("message"))
            else:
                QMessageBox.warning(self, "Servidores", evento.get("text", "Mensaje rechazado."))

        elif tipo == "channel_message":
            self.registrar_mensaje_canal_servidor(evento.get("message"))

        elif tipo == "channel_history_result":
            if evento.get("ok"):
                mensajes = evento.get("messages", [])
                if isinstance(mensajes, list):
                    for mensaje in mensajes:
                        self.registrar_mensaje_canal_servidor(mensaje)
            else:
                QMessageBox.warning(self, "Servidores", evento.get("text", "Historial no disponible."))

        elif tipo == "servers_list":
            if evento.get("ok"):
                servidores = evento.get("servers", [])
                self.servidores = [s for s in servidores if isinstance(s, dict)] if isinstance(servidores, list) else []
                self.canales_por_servidor = {}
                self.canales_servidor = {}
                if self.servidor_pendiente_seleccionar is not None:
                    self.destino_actual = self.servidor_pendiente_seleccionar
                self.servidor_pendiente_seleccionar = None
                self.refrescar_lista()
                for servidor in self.servidores:
                    id_servidor = servidor.get("id_servidor")
                    if self.clave_servidor(id_servidor) is not None:
                        self.solicitar_canales_servidor(id_servidor)
            else:
                QMessageBox.warning(self, "Servidores", evento.get("text", "No se pudieron consultar."))

        elif tipo == "channels_list":
            if not evento.get("ok"):
                self.agregar_mensaje("Chat general", "[Sistema] " + evento.get(
                    "text", "No se pudieron consultar los canales de un servidor."
                ))
                return
            id_servidor = evento.get("id_servidor")
            clave_servidor = self.clave_servidor(id_servidor)
            if clave_servidor is None:
                return
            canales = evento.get("channels", [])
            if not isinstance(canales, list):
                return
            id_servidor_normalizado = clave_servidor.split(":", 1)[1]
            self.canales_por_servidor[id_servidor_normalizado] = canales
            self.canales_servidor = {
                clave: dato for clave, dato in self.canales_servidor.items()
                if self.clave_servidor(dato.get("id_servidor")) != clave_servidor
            }
            for canal in canales:
                if not isinstance(canal, dict):
                    continue
                clave_canal = self.clave_canal_servidor(canal.get("id_canal"))
                if clave_canal is not None:
                    self.canales_servidor[clave_canal] = {
                        **canal, "id_servidor": id_servidor_normalizado
                    }
            if self.canal_servidor_pendiente in self.canales_servidor:
                self.destino_actual = self.canal_servidor_pendiente
                self.canal_servidor_pendiente = None
            self.refrescar_lista()
            if self.destino_actual in self.canales_servidor:
                self.coneccion.enviar({
                    "type": "channel_history",
                    "id_canal": self.canales_servidor[self.destino_actual]["id_canal"],
                    "limit": 50,
                })

        elif tipo == "error":
            self.agregar_mensaje(
                self.destino_actual, f"[Sistema] {evento.get('text', '')}"
            )


    # ACTUALIZAR USUARIOS Y CONSERVAR LOS GRUPOS EN LA LISTA

    def actualizar_usuarios(self, usuarios):
        if not isinstance(usuarios, list):
            return
        self.usuarios = {
            u["id_publico"].lower(): u
            for u in usuarios
            if isinstance(u, dict) and isinstance(u.get("id_publico"), str)
        }
        self.refrescar_lista()
        for uid in {self.id_publico, *self.usuarios.keys()}:
            self.solicitar_foto_usuario(uid)

    def refrescar_lista(self):
        anterior = self.destino_actual
        self.listWidget.blockSignals(True)
        self.listWidget.clear()

        item_general = QListWidgetItem("Chat general")
        item_general.setData(Qt.ItemDataRole.UserRole, "Chat general")
        self.listWidget.addItem(item_general)
        seleccionado = item_general

        for id_publico, usuario in sorted(
            self.usuarios.items(), key=lambda par: par[1].get("usuario", "").casefold()
        ):
            etiqueta = (
                f"{usuario.get('nombre_visible', '')} "
                f"(@{usuario.get('usuario', '')})"
            )
            if id_publico == self.id_publico:
                etiqueta += " (Tú)"
            item = QListWidgetItem(etiqueta)
            item.setIcon(QIcon(self._avatar_redondo(
                self.fotos_usuarios.get(id_publico),
                usuario.get("nombre_visible") or usuario.get("usuario", "P"), 29
            )))
            item.setData(Qt.ItemDataRole.UserRole, id_publico)
            if id_publico == self.id_publico:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            self.listWidget.addItem(item)
            if id_publico == anterior:
                seleccionado = item

        if self.grupos:
            separador = QListWidgetItem("──── MIS GRUPOS ────")
            separador.setFlags(separador.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            self.listWidget.addItem(separador)

        for clave, grupo in sorted(
            self.grupos.items(), key=lambda par: par[1].get("nombre", "").casefold()
        ):
            item = QListWidgetItem(f"👥 {grupo['nombre']} ({grupo.get('rol', 'Miembro')})")
            item.setData(Qt.ItemDataRole.UserRole, clave)
            self.listWidget.addItem(item)
            if clave == anterior:
                seleccionado = item

        if self.servidores:
            separador = QListWidgetItem("──── MIS SERVIDORES ────")
            separador.setFlags(separador.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            self.listWidget.addItem(separador)

        for servidor in sorted(self.servidores, key=lambda s: s.get("nombre", "").casefold()):
            id_servidor = servidor.get("id_servidor")
            clave_s = self.clave_servidor(id_servidor)
            if clave_s is None:
                continue
            item = QListWidgetItem(
                f"🌐 {servidor.get('nombre', 'Servidor')} ({servidor.get('rol', 'Miembro')})"
            )
            item.setData(Qt.ItemDataRole.UserRole, clave_s)
            self.listWidget.addItem(item)
            if clave_s == anterior:
                seleccionado = item
            canales = sorted(
                (c for c in self.canales_servidor.values()
                 if self.clave_servidor(c.get("id_servidor")) == clave_s),
                key=lambda c: (c.get("nombre", "") != "general", c.get("nombre", "").casefold())
            )
            for canal in canales:
                clave_c = self.clave_canal_servidor(canal.get("id_canal"))
                if clave_c is None:
                    continue
                item_c = QListWidgetItem("    # " + canal.get("nombre", "Canal"))
                item_c.setData(Qt.ItemDataRole.UserRole, clave_c)
                self.listWidget.addItem(item_c)
                if clave_c == anterior:
                    seleccionado = item_c

        if self.canales_difusion:
            separador = QListWidgetItem("──── CANALES DE DIFUSIÓN ────")
            separador.setFlags(separador.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            self.listWidget.addItem(separador)

        for clave, canal in sorted(
            self.canales_difusion.items(), key=lambda par: par[1].get("nombre", "").casefold()
        ):
            if canal.get("es_propietario"):
                estado = "Propietario"
            elif canal.get("suscrito"):
                estado = "Suscrito"
            else:
                estado = "Sin suscripción"
            item = QListWidgetItem(f"📢 {canal['nombre']} ({estado})")
            item.setData(Qt.ItemDataRole.UserRole, clave)
            self.listWidget.addItem(item)
            if clave == anterior:
                seleccionado = item

        if seleccionado is item_general and anterior != "Chat general":
            self.destino_actual = "Chat general"
        self.listWidget.setCurrentItem(seleccionado)
        self.listWidget.blockSignals(False)
        self._filtrar_lista(self.buscador_chats.text())
        self.mostrar_historial()
        self.habilitar_acciones_grupo()
        self.actualizar_estado_difusion()
        self.actualizar_acciones_servidor()

    # SELECCIONAR CHAT GENERAL, MENSAJE PRIVADO, GRUPO O CANAL

    def cambiar_conversacion(self, actual, anterior):
        if actual is None:
            return
        destino = actual.data(Qt.ItemDataRole.UserRole)
        if (destino == "Chat general" or destino in self.usuarios
                or destino in self.grupos or destino in self.canales_difusion
                or destino in self.canales_servidor
                or (self._es_clave_servidor(destino) and self._datos_servidor_por_clave(destino))):
            self.destino_actual = destino
            self.mostrar_historial()
            # Durante la construccion inicial aun no existe el hilo TCP.
            if not hasattr(self, "coneccion"):
                return
            self.habilitar_acciones_grupo()
            self.actualizar_estado_difusion()
            self.actualizar_acciones_servidor()
            if not self.coneccion.connected:
                return
            if destino in self.canales_difusion:
                self.solicitar_historial_canal_difusion(destino)
                return
            if destino in self.canales_servidor:
                self.coneccion.enviar({
                    "type": "channel_history",
                    "id_canal": self.canales_servidor[destino]["id_canal"],
                    "limit": 50,
                })
                return
            if self._es_clave_servidor(destino):
                return
            if destino in self.grupos:
                ok = self.coneccion.enviar({
                    "type": "group_history",
                    "id_grupo": self.grupos[destino]["id_grupo"],
                })
            elif destino in self.usuarios and destino != self.id_publico:
                ok = self.coneccion.enviar({"type": "private_history", "to": destino})
            else:
                return
            if not ok:
                QMessageBox.warning(self, "Conexión", "No se pudo solicitar el historial.")


    # FUNCIÓN PARA ACTUALIZAR LA CONEXIÓN

    def actualizar_conexion(self, conectado):
        if conectado:
            self.setWindowTitle(
                f"Messenger Papoi - {self.nombre_visible} (@{self.usuario})"
            )
            self.label_estado_tcp.setText("●  Conectado")
            if not self.creando_servidor:
                self.actionCrearServidor.setEnabled(True)
            self.habilitar_acciones_grupo()
            self.actualizar_estado_difusion()
            self.actualizar_acciones_servidor()
        else:
            self.setWindowTitle("Messenger Papoi - Desconectado")
            self.label_estado_tcp.setText("●  Desconectado")
            self.actionCrearServidor.setEnabled(False)
            self.actionCambiarFotoPerfil.setEnabled(False)
            self.boton_cambiar_foto.setEnabled(False)
            self.creando_servidor = False
            self.habilitar_acciones_grupo()
            self.actualizar_estado_difusion()
            self.actualizar_acciones_servidor()
            if self.cerrando:
                return
            self.agregar_mensaje(
                "Chat general", "[Sistema] Te has desconectado del servidor."
            )
            self.btnSend.setEnabled(False)


    # FUNCIÓN PARA SALIR

    def salir(self):
        self.close()

    def closeEvent(self, event):
        self.cerrando = True
        self.coneccion.stop()
        event.accept()


# EJECUCIÓN PRINCIPAL

if __name__ == "__main__":
    print("Inicia Messenger desde login.py para autenticarte.")
