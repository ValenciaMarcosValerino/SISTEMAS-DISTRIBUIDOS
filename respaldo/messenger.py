import sys
import socket
import json
import threading
from PySide6.QtWidgets import QApplication, QMainWindow, QListWidgetItem, QMessageBox
from PySide6.QtCore import QThread, Signal, Qt
from principal_ui import Ui_Messenger


# CLASE PARA LA COMUNICACIÓN TCP

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
                linea = self.lector.readline(1048577)
                if not linea or len(linea) > 1048576:
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
        self.id_publico = cuenta["id_publico"]
        self.nombre_visible = cuenta["nombre_visible"]
        self.destino_actual = "Chat general"
        self.historiales = {"Chat general": []}
        self.usuarios = {}
        self.cerrando = False

        self.setWindowTitle(
            f"Messenger - {self.nombre_visible} (@{self.usuario})"
        )

        self.actionConectar.setEnabled(False)
        self.actionSalir.triggered.connect(self.salir)
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


    # FUNCIÓN PARA ENVIAR MENSAJES

    def mensaje_saliente(self):
        texto = self.txtSend.text().strip()
        if not texto or not self.coneccion.connected:
            return
        if len(texto) > 5000:
            QMessageBox.warning(self, "Mensaje", "Máximo 5000 caracteres.")
            return

        destino = self.destino_actual
        if destino == "Chat general":
            mensaje = {"type": "public", "text": texto}
        else:
            if destino not in self.usuarios:
                QMessageBox.warning(self, "Mensaje", "Usuario no disponible.")
                return
            mensaje = {"type": "private", "to": destino, "text": texto}

        if self.coneccion.enviar(mensaje):
            self.txtSend.clear()
            self.agregar_mensaje(destino, f"<Tú> {texto}")
        else:
            QMessageBox.warning(self, "Conexión", "No se pudo enviar el mensaje.")


    # FUNCIÓN PARA GUARDAR Y MOSTRAR MENSAJES

    def agregar_mensaje(self, conversacion, texto):
        self.historiales.setdefault(conversacion, []).append(texto)
        if conversacion == self.destino_actual:
            self.mostrar_historial()

    def mostrar_historial(self):
        mensajes = self.historiales.get(self.destino_actual, [])
        self.txtMsgs.setPlainText("\n".join(mensajes))
        barra = self.txtMsgs.verticalScrollBar()
        barra.setValue(barra.maximum())


    # FUNCIÓN PARA RECIBIR MENSAJES

    def recibir_evento(self, evento):
        tipo = evento.get("type")
        if tipo == "users":
            self.actualizar_usuarios(evento.get("users", []))

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
            nombre = evento.get("from", "")
            usuario = evento.get("from_usuario", "")
            texto = evento.get("text", "")
            self.agregar_mensaje(
                remitente_id, f"<{nombre} (@{usuario})> {texto}"
            )

        elif tipo == "system":
            self.agregar_mensaje(
                "Chat general", f"[Sistema] {evento.get('text', '')}"
            )

        elif tipo == "error":
            self.agregar_mensaje(
                self.destino_actual, f"[Sistema] {evento.get('text', '')}"
            )


    # FUNCIÓN PARA ACTUALIZAR USUARIOS

    def actualizar_usuarios(self, usuarios):
        anterior = self.destino_actual
        self.usuarios = {
            u["id_publico"]: u
            for u in usuarios
            if isinstance(u, dict) and isinstance(u.get("id_publico"), str)
        }
        self.listWidget.blockSignals(True)
        self.listWidget.clear()

        item_general = QListWidgetItem("Chat general")
        item_general.setData(Qt.ItemDataRole.UserRole, "Chat general")
        self.listWidget.addItem(item_general)
        seleccionado = item_general

        for id_publico, usuario in sorted(
            self.usuarios.items(),
            key=lambda par: par[1].get("usuario", "").casefold()
        ):
            etiqueta = (
                f"{usuario.get('nombre_visible', '')} "
                f"(@{usuario.get('usuario', '')})"
            )
            if id_publico == self.id_publico:
                etiqueta += " (Tú)"
            item = QListWidgetItem(etiqueta)
            item.setData(Qt.ItemDataRole.UserRole, id_publico)
            if id_publico == self.id_publico:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            self.listWidget.addItem(item)
            if id_publico == anterior:
                seleccionado = item

        if anterior not in self.usuarios and anterior != "Chat general":
            self.destino_actual = "Chat general"

        self.listWidget.setCurrentItem(seleccionado)
        self.listWidget.blockSignals(False)
        self.mostrar_historial()


    # FUNCIÓN PARA CAMBIAR DE CONVERSACIÓN

    def cambiar_conversacion(self, actual, anterior):
        if actual is None:
            return
        destino = actual.data(Qt.ItemDataRole.UserRole)
        if destino == "Chat general" or destino in self.usuarios:
            self.destino_actual = destino
            self.mostrar_historial()


    # FUNCIÓN PARA ACTUALIZAR LA CONEXIÓN

    def actualizar_conexion(self, conectado):
        if conectado:
            self.setWindowTitle(
                f"Messenger - {self.nombre_visible} (@{self.usuario})"
            )
        else:
            self.setWindowTitle("Messenger - Desconectado")
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
