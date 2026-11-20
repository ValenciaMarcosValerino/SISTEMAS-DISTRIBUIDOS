
import sys
import socket

from PySide6.QtWidgets import QApplication, QMainWindow, QDialog
from PySide6.QtCore import QThread, Signal

from principal_ui import Ui_Messenger
from conectar_ui import Ui_Dialog


BUFFER_SIZE = 1024


# CLASE PARA LA COMUNICACIÓN TCP

class ThreadSocket(QThread):

    signal_message = Signal(str)
    signal_users = Signal(list)
    signal_connection = Signal(bool)

    def __init__(self, host, port, name):
        super().__init__()

        self.host = host
        self.port = port
        self.name = name
        self.server = None
        self.connected = False
        self.running = True

    def run(self):

        try:
            self.server = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM
            )

            self.server.settimeout(5)
            self.server.connect((self.host, self.port))
            self.server.settimeout(None)

            if not self.running:
                return

            self.connected = True

            self.server.sendall(
                f"<name>{self.name}".encode("utf-8")
            )

            self.signal_connection.emit(True)

            buffer = b""

            while self.running:

                datos = self.server.recv(BUFFER_SIZE)

                if not datos:
                    break

                buffer += datos

                while b"\n" in buffer:

                    linea, buffer = buffer.split(b"\n", 1)

                    mensaje = linea.decode("utf-8").rstrip("\r")

                    if mensaje.startswith("<users>"):

                        usuarios = mensaje.removeprefix("<users>")

                        lista = [
                            usuario
                            for usuario in usuarios.split(",")
                            if usuario
                        ]

                        print("Usuarios recibidos:", lista)

                        self.signal_users.emit(lista)

                    elif mensaje:
                        self.signal_message.emit(mensaje)

        except (OSError, UnicodeError) as error:

            if self.running:
                self.signal_message.emit(
                    f"Error de conexión: {error}"
                )

        finally:

            self.connected = False

            if self.server is not None:
                self.server.close()

            self.signal_connection.emit(False)

    def enviar(self, mensaje):

        if not self.connected or self.server is None:
            return False

        try:
            self.server.sendall(mensaje.encode("utf-8"))
            return True

        except OSError as error:
            self.signal_message.emit(
                f"Error al enviar: {error}"
            )
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

        self.setWindowTitle("Messenger - Desconectado")

        self.actionConectar.triggered.connect(self.showDialog)
        self.actionSalir.triggered.connect(self.salir)

        self.btnSend.clicked.connect(self.mensaje_saliente)
        self.txtSend.returnPressed.connect(self.mensaje_saliente)

        self.listWidget.clear()


# FUNCIÓN PARA ENVIAR MENSAJES

    def mensaje_saliente(self):

        mensaje = self.txtSend.text().strip()

        if not mensaje:
            return

        if self.coneccion is None:
            return

        if self.coneccion.enviar(mensaje):

            self.txtSend.clear()

            self.mensage_entrante(
                f"<Tú> {mensaje}"
            )


# FUNCIÓN PARA MOSTRAR MENSAJES

    def mensage_entrante(self, mensaje):

        self.txtMsgs.appendPlainText(mensaje)

        barra = self.txtMsgs.verticalScrollBar()
        barra.setValue(barra.maximum())


# FUNCIÓN PARA ACTUALIZAR USUARIOS

    def actualizar_usuarios(self, usuarios):

        self.listWidget.clear()

        for usuario in usuarios:
            self.listWidget.addItem(usuario)


# FUNCIÓN PARA ACTUALIZAR LA CONEXIÓN

    def actualizar_conexion(self, conectado):

        if conectado:
            self.setWindowTitle("Messenger - Conectado")

        else:
            self.setWindowTitle("Messenger - Desconectado")
            self.listWidget.clear()


# FUNCIÓN PARA CONECTARSE AL SERVIDOR

    def showDialog(self):

        if self.coneccion is not None:

            if self.coneccion.isRunning():
                return

        dialog = MiDialogo(self)

        resp = dialog.exec()

        if resp == QDialog.DialogCode.Accepted:

            host = dialog.txtServer.text().strip()
            user = dialog.txtUser.text().strip()
            port = dialog.txtPort.text().strip()

            if not host or not user:
                self.mensage_entrante(
                    "Debes ingresar servidor y usuario."
                )
                return

            if not port.isdecimal() or not 1 <= int(port) <= 65535:
                self.mensage_entrante(
                    "Debes ingresar un puerto válido."
                )
                return

            self.coneccion = ThreadSocket(
                host,
                int(port),
                user
            )

            self.coneccion.signal_message.connect(
                self.mensage_entrante
            )

            self.coneccion.signal_users.connect(
                self.actualizar_usuarios
            )

            self.coneccion.signal_connection.connect(
                self.actualizar_conexion
            )

            self.coneccion.start()


# FUNCIÓN PARA SALIR DEL PROGRAMA

    def salir(self):
        self.close()

    def closeEvent(self, event):

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
