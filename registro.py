"""Registro de usuarios de Messenger Papoi: mismo protocolo register del servidor TCP."""

import json
import socket

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QVBoxLayout,
)
from papoi_theme import SERVER_HOST, SERVER_PORT


class VentanaRegistro(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AuthWindow")
        self.setWindowTitle("Messenger Papoi | Crear cuenta")
        self.resize(535, 690)
        self.setMinimumSize(455, 615)
        self._crear_interfaz()

    def _crear_interfaz(self):
        exterior = QVBoxLayout(self)
        exterior.setContentsMargins(34, 24, 34, 24)
        exterior.setSpacing(16)

        marca = QHBoxLayout()
        logo = QLabel("P")
        logo.setObjectName("BrandMark")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setFixedSize(58, 58)
        marca.addWidget(logo)
        text = QVBoxLayout()
        titulo = QLabel("Messenger Papoi")
        titulo.setObjectName("BrandTitle")
        text.addWidget(titulo)
        mensaje = QLabel("Una cuenta, todas tus conversaciones")
        mensaje.setObjectName("MutedText")
        text.addWidget(mensaje)
        marca.addLayout(text)
        marca.addStretch()
        exterior.addLayout(marca)
        exterior.addStretch(1)

        tarjeta = QFrame()
        tarjeta.setObjectName("AuthCard")
        layout = QVBoxLayout(tarjeta)
        layout.setContentsMargins(27, 22, 27, 23)
        layout.setSpacing(11)
        encabezado = QLabel("Crea tu cuenta")
        encabezado.setObjectName("AuthTitle")
        layout.addWidget(encabezado)
        descripcion = QLabel("Completa tus datos para empezar a chatear.")
        descripcion.setObjectName("MutedText")
        layout.addWidget(descripcion)
        layout.addSpacing(9)

        self.txtRegistroU = self._campo(layout, "USUARIO", "Ej. papoi123", 50)
        self.txtRegistroN = self._campo(layout, "NOMBRE VISIBLE", "Cómo quieres aparecer en el chat", 50)
        self.txtRegistroP = self._campo(layout, "CONTRASEÑA", "Al menos 8 caracteres", None, True)
        self.txtConfirmacion = self._campo(layout, "CONFIRMAR CONTRASEÑA", "Repite tu contraseña", None, True)
        self.txtConfirmacion.returnPressed.connect(self.registrar_cuenta)

        layout.addSpacing(6)
        self.btnRegistro = QPushButton("Crear mi cuenta")
        self.btnRegistro.setObjectName("PrimaryButton")
        self.btnRegistro.setMinimumHeight(49)
        self.btnRegistro.clicked.connect(self.registrar_cuenta)
        layout.addWidget(self.btnRegistro)

        self.btnCancelar = QPushButton("Volver al inicio de sesión")
        self.btnCancelar.setObjectName("GhostButton")
        self.btnCancelar.setMinimumHeight(43)
        self.btnCancelar.clicked.connect(self.reject)
        layout.addWidget(self.btnCancelar)
        exterior.addWidget(tarjeta)
        exterior.addStretch(1)

        aviso = QLabel("Tu contraseña se protege en el servidor mediante Argon2id.")
        aviso.setObjectName("FooterText")
        aviso.setAlignment(Qt.AlignmentFlag.AlignCenter)
        exterior.addWidget(aviso)
        self.txtRegistroU.setFocus()

    @staticmethod
    def _campo(layout, etiqueta, placeholder, maximo=None, es_clave=False):
        l = QLabel(etiqueta)
        l.setObjectName("FieldLabel")
        layout.addWidget(l)
        entrada = QLineEdit()
        entrada.setPlaceholderText(placeholder)
        entrada.setMinimumHeight(44)
        if maximo is not None:
            entrada.setMaxLength(maximo)
        if es_clave:
            entrada.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(entrada)
        return entrada

    def registrar_cuenta(self):
        usuario = self.txtRegistroU.text().strip()
        nombre = self.txtRegistroN.text().strip()
        contrasena = self.txtRegistroP.text()
        confirmar = self.txtConfirmacion.text()

        if not usuario or not nombre or not contrasena:
            QMessageBox.warning(self, "Datos incompletos", "Completa los datos de la cuenta.")
            return
        if len(contrasena) < 8:
            QMessageBox.warning(self, "Contraseña", "Usa al menos 8 caracteres.")
            return
        if contrasena != confirmar:
            QMessageBox.warning(self, "Contraseña", "Las contraseñas no coinciden.")
            return

        self.btnRegistro.setEnabled(False)
        try:
            with socket.create_connection((SERVER_HOST, SERVER_PORT), timeout=5) as conexion:
                conexion.settimeout(10)
                mensaje = {
                    "type": "register",
                    "usuario": usuario,
                    "nombre_visible": nombre,
                    "contrasena": contrasena,
                }
                conexion.sendall(
                    (json.dumps(mensaje, ensure_ascii=False) + "\n").encode("utf-8")
                )
                with conexion.makefile("rb") as lector:
                    linea = lector.readline(65537)
            if not linea or len(linea) > 65536:
                raise ConnectionError("El servidor no respondió correctamente.")
            respuesta = json.loads(linea.decode("utf-8"))
            if not isinstance(respuesta, dict) or respuesta.get("type") != "register_result":
                raise ValueError("Respuesta inesperada del servidor.")
            if not respuesta.get("ok"):
                QMessageBox.warning(
                    self, "No se pudo registrar",
                    respuesta.get("text", "Revisa los datos e inténtalo de nuevo.")
                )
                return
            QMessageBox.information(
                self, "Cuenta creada", "¡Tu cuenta está lista! Ya puedes iniciar sesión."
            )
            self.accept()
        except (OSError, ValueError, UnicodeError) as error:
            QMessageBox.critical(self, "Error de conexión", str(error))
        finally:
            self.btnRegistro.setEnabled(True)
