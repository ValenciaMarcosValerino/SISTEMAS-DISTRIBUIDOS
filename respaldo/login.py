import sys
import socket
import json
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
from IniciarSecion_ui import Ui_login
from registro import VentanaRegistro
from messenger import MainWindow


# VENTANA DE LOGIN

class VentanaLogin(QDialog):

    def __init__(self):
        super().__init__()

        self.ui = Ui_login()
        self.ui.setupUi(self)
        self.conexion = None
        self.lector = None
        self.cuenta = None

        self.ui.btnLogin.clicked.connect(self.iniciar_sesion)
        self.ui.btnRegistro.clicked.connect(self.abrir_registro)
        self.ui.txtLoginP.returnPressed.connect(self.iniciar_sesion)


    # INICIAR SESIÓN

    def iniciar_sesion(self):
        usuario = self.ui.txtLoginU.text().strip()
        contrasena = self.ui.txtLoginP.text()

        if not usuario or not contrasena:
            QMessageBox.warning(
                self, "Datos incompletos", "Ingresa tu usuario y contraseña."
            )
            return

        conexion = None
        lector = None
        try:
            conexion = socket.create_connection(("127.0.0.1", 5000), timeout=5)
            conexion.settimeout(10)
            peticion = {
                "type": "login",
                "usuario": usuario,
                "contrasena": contrasena
            }
            conexion.sendall(
                (json.dumps(peticion, ensure_ascii=False) + "\n").encode("utf-8")
            )

            lector = conexion.makefile("rb")
            linea = lector.readline(65537)
            if not linea or len(linea) > 65536:
                raise ConnectionError("El servidor no respondió correctamente.")
            respuesta = json.loads(linea.decode("utf-8"))

            if not isinstance(respuesta, dict) or respuesta.get("type") != "login_result":
                raise ValueError("Respuesta inesperada del servidor.")

            if not respuesta.get("ok"):
                QMessageBox.warning(
                    self, "Acceso denegado",
                    respuesta.get("text", "Usuario o contraseña incorrectos.")
                )
                return

            cuenta = respuesta.get("cuenta")
            if not isinstance(cuenta, dict) or not cuenta.get("id_publico"):
                raise ValueError("El servidor no devolvió los datos de tu cuenta.")

            conexion.settimeout(None)
            self.conexion = conexion
            self.lector = lector
            self.cuenta = cuenta
            conexion = None
            lector = None
            self.accept()

        except (OSError, UnicodeError, ValueError) as error:
            QMessageBox.critical(self, "Error de conexión", str(error))
        finally:
            if lector is not None:
                lector.close()
            if conexion is not None:
                conexion.close()


    # ABRIR REGISTRO

    def abrir_registro(self):
        VentanaRegistro(self).exec()


# PROGRAMA PRINCIPAL

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    ventana_login = VentanaLogin()
    if ventana_login.exec() == QDialog.DialogCode.Accepted:
        try:
            ventana_chat = MainWindow(
                ventana_login.conexion,
                ventana_login.lector,
                ventana_login.cuenta
            )
            ventana_chat.show()
            app.setQuitOnLastWindowClosed(True)
            sys.exit(app.exec())
        except Exception:
            ventana_login.conexion.close()
            raise

    sys.exit(0)
