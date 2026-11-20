
import socket
import json
from PySide6.QtWidgets import QDialog, QMessageBox
from Registro_ui import Ui_Registro


# VENTANA DE REGISTRO

class VentanaRegistro(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.ui = Ui_Registro()
        self.ui.setupUi(self)

        self.ui.btnRegistro.clicked.connect(self.registrar)
        self.ui.btnVolverLogin.clicked.connect(self.volver_login)


    # REGISTRAR USUARIO

    def registrar(self):

        usuario = self.ui.txtUsuario.text().strip()
        nombre = self.ui.txtNombreVi.text().strip()
        contrasena = self.ui.txtContrasea.text()
        confirmar = self.ui.txtConfirmarContra.text()

        if not usuario or not nombre or not contrasena or not confirmar:
            QMessageBox.warning(
                self,
                "Datos incompletos",
                "Debes completar todos los campos."
            )
            return

        if contrasena != confirmar:
            QMessageBox.warning(
                self,
                "Error",
                "Las contraseñas no coinciden."
            )
            return

        if len(contrasena) < 8:
            QMessageBox.warning(
                self,
                "Contraseña",
                "La contraseña debe tener al menos 8 caracteres."
            )
            return

        # ENVIAR REGISTRO AL SERVIDOR

        solicitud = {
            "type": "register",
            "usuario": usuario,
            "nombre_visible": nombre,
            "contrasena": contrasena
        }

        try:
            with socket.create_connection(
                ("127.0.0.1", 5000),
                timeout=5
            ) as conexion:

                conexion.settimeout(5)

                datos = (
                    json.dumps(solicitud, ensure_ascii=False) + "\n"
                ).encode("utf-8")

                conexion.sendall(datos)

                buffer = b""

                while b"\n" not in buffer:
                    parte = conexion.recv(4096)

                    if not parte:
                        raise ConnectionError(
                            "El servidor cerró la conexión."
                        )

                    buffer += parte

                    if len(buffer) > 65536:
                        raise ValueError(
                            "Respuesta del servidor demasiado grande."
                        )

                linea = buffer.split(b"\n", 1)[0]
                respuesta = json.loads(linea.decode("utf-8"))

            if respuesta.get("type") != "register_result":
                raise ValueError(
                    "Respuesta inesperada del servidor."
                )

            if respuesta.get("ok"):
                QMessageBox.information(
                    self,
                    "Registro exitoso",
                    "Tu cuenta fue creada correctamente."
                )

                self.accept()

            else:
                QMessageBox.warning(
                    self,
                    "Registro rechazado",
                    respuesta.get(
                        "text",
                        "No se pudo crear la cuenta."
                    )
                )

        except (OSError, ValueError, UnicodeError) as error:
            QMessageBox.critical(
                self,
                "Error de conexión",
                f"No se pudo completar el registro:\n{error}"
            )


    # VOLVER AL LOGIN

    def volver_login(self):
        self.reject()
