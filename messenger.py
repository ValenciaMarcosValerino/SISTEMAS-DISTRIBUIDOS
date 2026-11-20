
import sys
import socket
import json
import threading

from PySide6.QtWidgets import QApplication, QMainWindow, QDialog
from PySide6.QtCore import QThread, Signal, Qt

from principal_ui import Ui_Messenger
from conectar_ui import Ui_Dialog


BUFFER_SIZE = 4096


# CLASE PARA LA COMUNICACIÓN TCP

class ThreadSocket(QThread):

    signal_event = Signal(dict)
    signal_connection = Signal(bool)

    def __init__(self, host, port, name):
        super().__init__()

        self.host = host
        self.port = port
        self.name = name
        self.server = None
        self.connected = False
        self.running = True
        self.send_lock = threading.Lock()

    def run(self):
        try:
            self.server = socket.create_connection(
                (self.host, self.port),
                timeout=5
            )

            self.server.settimeout(None)

            if not self.running:
                return

            datos = {
                "type": "join",
                "name": self.name
            }

            with self.send_lock:
                self.server.sendall(
                    (json.dumps(datos, ensure_ascii=False) + "\n").encode("utf-8")
                )

            self.connected = True
            self.signal_connection.emit(True)

            buffer = b""

            while self.running:
                datos = self.server.recv(BUFFER_SIZE)

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
                        evento = json.loads(
                            linea.decode("utf-8")
                        )
                    except (UnicodeError, ValueError):
                        continue

                    if isinstance(evento, dict):
                        self.signal_event.emit(evento)

        except OSError as error:
            if self.running:
                self.signal_event.emit({
                    "type": "error",
                    "text": str(error)
                })

        finally:
            self.connected = False

            if self.server is not None:
                self.server.close()

            self.signal_connection.emit(False)

    def enviar(self, mensaje):
        if not self.connected or self.server is None:
            return False

        try:
            datos = (
                json.dumps(mensaje, ensure_ascii=False) + "\n"
            ).encode("utf-8")

            with self.send_lock:
                self.server.sendall(datos)

            return True

        except OSError:
            return False

    def stop(self):
        self.running = False

        if self.server is not None:
            try:
                self.server.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

        self.wait()


# CLASE PRINCIPAL DEL MESSENGER

class MainWindow(QMainWindow, Ui_Messenger):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setupUi(self)

        self.coneccion = None
        self.usuario = ""
        self.destino_actual = "Chat general"
        self.historiales = {"Chat general": []}
        self.cerrando = False

        self.setWindowTitle("Messenger - Desconectado")

        self.actionConectar.triggered.connect(self.showDialog)
        self.actionSalir.triggered.connect(self.salir)

        self.btnSend.clicked.connect(self.mensaje_saliente)
        self.txtSend.returnPressed.connect(self.mensaje_saliente)

        self.listWidget.addItem("Chat general")
        self.listWidget.setCurrentRow(0)

        self.listWidget.currentItemChanged.connect(
            self.cambiar_conversacion
        )


    # FUNCIÓN PARA ENVIAR MENSAJES

    def mensaje_saliente(self):
        texto = self.txtSend.text().strip()

        if not texto:
            return

        if self.coneccion is None or not self.coneccion.connected:
            return

        destino = self.destino_actual

        if destino == "Chat general":
            mensaje = {
                "type": "public",
                "text": texto
            }
        else:
            mensaje = {
                "type": "private",
                "to": destino,
                "text": texto
            }

        if self.coneccion.enviar(mensaje):
            self.txtSend.clear()
            self.agregar_mensaje(destino, f"<Tú> {texto}")


    # FUNCIÓN PARA GUARDAR Y MOSTRAR MENSAJES

    def agregar_mensaje(self, conversacion, texto):
        if conversacion not in self.historiales:
            self.historiales[conversacion] = []

        self.historiales[conversacion].append(texto)

        if conversacion == self.destino_actual:
            self.mostrar_historial()

    def mostrar_historial(self):
        mensajes = self.historiales.get(
            self.destino_actual, []
        )

        self.txtMsgs.setPlainText("\n".join(mensajes))

        barra = self.txtMsgs.verticalScrollBar()
        barra.setValue(barra.maximum())


    # FUNCIÓN PARA RECIBIR MENSAJES

    def recibir_evento(self, evento):
        tipo = evento.get("type")

        if tipo == "users":
            self.actualizar_usuarios(
                evento.get("users", [])
            )

        elif tipo == "public":
            nombre = evento.get("from", "")
            texto = evento.get("text", "")

            self.agregar_mensaje(
                "Chat general",
                f"<{nombre}> {texto}"
            )

        elif tipo == "private":
            nombre = evento.get("from", "")
            texto = evento.get("text", "")

            self.agregar_mensaje(
                nombre,
                f"<{nombre}> {texto}"
            )

        elif tipo == "system":
            self.agregar_mensaje(
                "Chat general",
                f"[Sistema] {evento.get('text', '')}"
            )

        elif tipo == "error":
            self.agregar_mensaje(
                self.destino_actual,
                f"[Sistema] {evento.get('text', '')}"
            )


    # FUNCIÓN PARA ACTUALIZAR USUARIOS

    def actualizar_usuarios(self, usuarios):
        anterior = self.destino_actual

        self.listWidget.blockSignals(True)
        self.listWidget.clear()

        self.listWidget.addItem("Chat general")

        for usuario in usuarios:
            self.listWidget.addItem(usuario)

            item = self.listWidget.item(
                self.listWidget.count() - 1
            )

            if usuario.casefold() == self.usuario.casefold():
                item.setFlags(
                    item.flags() & ~Qt.ItemFlag.ItemIsEnabled
                )

        indice = 0

        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)

            if (item.text() == anterior and
                    item.flags() & Qt.ItemFlag.ItemIsEnabled):
                indice = i
                break

        self.listWidget.setCurrentRow(indice)
        self.listWidget.blockSignals(False)

        self.destino_actual = self.listWidget.currentItem().text()
        self.mostrar_historial()


    # FUNCIÓN PARA CAMBIAR DE CONVERSACIÓN

    def cambiar_conversacion(self, actual, anterior):
        if actual is None:
            return

        self.destino_actual = actual.text()
        self.mostrar_historial()


    # FUNCIÓN PARA ACTUALIZAR LA CONEXIÓN

    def actualizar_conexion(self, conectado):
        if conectado:
            self.setWindowTitle("Messenger - Conectado")

        else:
            self.setWindowTitle("Messenger - Desconectado")

            if self.cerrando:
                return

            self.listWidget.clear()
            self.listWidget.addItem("Chat general")
            self.listWidget.setCurrentRow(0)

            self.agregar_mensaje(
                "Chat general",
                "[Sistema] Te has desconectado del servidor."
            )


    # FUNCIÓN PARA CONECTARSE AL SERVIDOR

    def showDialog(self):
        if self.coneccion is not None:
            if self.coneccion.isRunning():
                return

        dialog = MiDialogo(self)
        resp = dialog.exec()

        if resp != QDialog.DialogCode.Accepted:
            return

        host = dialog.txtServer.text().strip()
        user = dialog.txtUser.text().strip()
        port = dialog.txtPort.text().strip()

        if not host or not user:
            self.agregar_mensaje(
                "Chat general",
                "[Sistema] Debes ingresar servidor y usuario."
            )
            return

        if not port.isdecimal() or not 1 <= int(port) <= 65535:
            self.agregar_mensaje(
                "Chat general",
                "[Sistema] Puerto no válido."
            )
            return

        self.usuario = user
        self.destino_actual = "Chat general"
        self.historiales = {"Chat general": []}

        self.listWidget.clear()
        self.listWidget.addItem("Chat general")
        self.listWidget.setCurrentRow(0)

        self.mostrar_historial()

        self.coneccion = ThreadSocket(
            host,
            int(port),
            user
        )

        self.coneccion.signal_event.connect(
            self.recibir_evento
        )

        self.coneccion.signal_connection.connect(
            self.actualizar_conexion
        )

        self.coneccion.start()


    # FUNCIÓN PARA SALIR

    def salir(self):
        self.close()

    def closeEvent(self, event):
        self.cerrando = True

        if self.coneccion is not None:
            self.coneccion.stop()

        event.accept()


# CLASE DEL DIÁLOGO DE CONEXIÓN

class MiDialogo(QDialog, Ui_Dialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)


# EJECUCIÓN PRINCIPAL

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
