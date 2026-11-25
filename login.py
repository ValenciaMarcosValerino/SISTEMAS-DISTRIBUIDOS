"""Pantalla de inicio de sesión para Messenger Papoi.

Mantiene el protocolo TCP, las claves de respuesta y la transferencia del
socket a MainWindow de las versiones anteriores del proyecto.
"""

import json
import socket
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QVBoxLayout,
)

from messenger import MainWindow
from papoi_theme import (
    SERVER_HOST, SERVER_PORT, THEMES, apply_theme, set_theme, theme_name,
)
from registro import VentanaRegistro


class VentanaLogin(QDialog):
    def __init__(self):
        super().__init__()
        self.conexion = None
        self.lector = None
        self.cuenta = None

        self.setObjectName("AuthWindow")
        self.setWindowTitle("Messenger Papoi | Iniciar sesión")
        self.resize(535, 665)
        self.setMinimumSize(465, 615)
        self._crear_interfaz()

    def _crear_interfaz(self):
        exterior = QVBoxLayout(self)
        exterior.setContentsMargins(34, 24, 34, 24)
        exterior.setSpacing(17)

        marca = QHBoxLayout()
        marca.setSpacing(12)
        logo = QLabel("P")
        logo.setObjectName("BrandMark")
        logo.setFixedSize(60, 60)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        marca.addWidget(logo)
        nombres = QVBoxLayout()
        titulo = QLabel("Messenger Papoi")
        titulo.setObjectName("BrandTitle")
        subtitulo = QLabel("Conecta, conversa y comparte")
        subtitulo.setObjectName("MutedText")
        nombres.addWidget(titulo)
        nombres.addWidget(subtitulo)
        marca.addLayout(nombres)
        marca.addStretch()
        exterior.addLayout(marca)

        exterior.addStretch(1)
        tarjeta = QFrame()
        tarjeta.setObjectName("AuthCard")
        contenido = QVBoxLayout(tarjeta)
        contenido.setContentsMargins(27, 25, 27, 25)
        contenido.setSpacing(12)

        encabezado = QLabel("Bienvenido de nuevo")
        encabezado.setObjectName("AuthTitle")
        contenido.addWidget(encabezado)
        nota = QLabel("Inicia sesión para entrar a tus conversaciones.")
        nota.setObjectName("MutedText")
        nota.setWordWrap(True)
        contenido.addWidget(nota)
        contenido.addSpacing(8)

        contenido.addWidget(self._label("USUARIO"))
        self.txtLoginU = QLineEdit()
        self.txtLoginU.setObjectName("txtLoginU")
        self.txtLoginU.setPlaceholderText("Tu nombre de usuario")
        self.txtLoginU.setClearButtonEnabled(True)
        self.txtLoginU.setMaxLength(50)
        self.txtLoginU.setMinimumHeight(49)
        contenido.addWidget(self.txtLoginU)
        contenido.addSpacing(5)

        contenido.addWidget(self._label("CONTRASEÑA"))
        clave_row = QHBoxLayout()
        clave_row.setSpacing(8)
        self.txtLoginP = QLineEdit()
        self.txtLoginP.setObjectName("txtLoginP")
        self.txtLoginP.setPlaceholderText("Tu contraseña")
        self.txtLoginP.setEchoMode(QLineEdit.EchoMode.Password)
        self.txtLoginP.setMinimumHeight(49)
        self.txtLoginP.returnPressed.connect(self.iniciar_sesion)
        clave_row.addWidget(self.txtLoginP, 1)
        self.btnMostrar = QPushButton("Ver")
        self.btnMostrar.setObjectName("GhostButton")
        self.btnMostrar.setFixedWidth(67)
        self.btnMostrar.setMinimumHeight(49)
        self.btnMostrar.setCheckable(True)
        self.btnMostrar.toggled.connect(self._mostrar_contrasena)
        clave_row.addWidget(self.btnMostrar)
        contenido.addLayout(clave_row)
        contenido.addSpacing(14)

        self.btnLogin = QPushButton("Entrar a Messenger")
        self.btnLogin.setObjectName("PrimaryButton")
        self.btnLogin.setMinimumHeight(50)
        self.btnLogin.clicked.connect(self.iniciar_sesion)
        contenido.addWidget(self.btnLogin)

        contenido.addSpacing(7)
        self.btnRegistro = QPushButton("Crear una cuenta nueva")
        self.btnRegistro.setObjectName("GhostButton")
        self.btnRegistro.setMinimumHeight(45)
        self.btnRegistro.clicked.connect(self.abrir_registro)
        contenido.addWidget(self.btnRegistro)
        exterior.addWidget(tarjeta)
        exterior.addStretch(1)

        opciones = QHBoxLayout()
        etiqueta = QLabel("APARIENCIA")
        etiqueta.setObjectName("SectionTitle")
        opciones.addWidget(etiqueta)
        opciones.addStretch()
        self.selector_tema = QComboBox()
        self.selector_tema.setMinimumWidth(195)
        for clave, tema in THEMES.items():
            self.selector_tema.addItem(tema["nombre"], clave)
        index = self.selector_tema.findData(theme_name())
        self.selector_tema.setCurrentIndex(max(0, index))
        self.selector_tema.currentIndexChanged.connect(self._seleccionar_tema)
        opciones.addWidget(self.selector_tema)
        exterior.addLayout(opciones)

        pie = QLabel("Chat general · Privados · Grupos · Canales de difusión")
        pie.setObjectName("FooterText")
        pie.setAlignment(Qt.AlignmentFlag.AlignCenter)
        exterior.addWidget(pie)
        self.txtLoginU.setFocus()

    @staticmethod
    def _label(texto):
        l = QLabel(texto)
        l.setObjectName("FieldLabel")
        return l

    def _seleccionar_tema(self, indice):
        nombre = self.selector_tema.itemData(indice)
        if nombre in THEMES:
            set_theme(nombre)

    def _mostrar_contrasena(self, mostrar):
        self.txtLoginP.setEchoMode(
            QLineEdit.EchoMode.Normal if mostrar else QLineEdit.EchoMode.Password
        )
        self.btnMostrar.setText("Ocultar" if mostrar else "Ver")

    def iniciar_sesion(self):
        usuario = self.txtLoginU.text().strip()
        contrasena = self.txtLoginP.text()
        if not usuario or not contrasena:
            QMessageBox.warning(self, "Datos incompletos", "Ingresa tu usuario y contraseña.")
            return

        conexion = None
        lector = None
        self.btnLogin.setEnabled(False)
        try:
            conexion = socket.create_connection((SERVER_HOST, SERVER_PORT), timeout=5)
            conexion.settimeout(10)
            peticion = {
                "type": "login",
                "usuario": usuario,
                "contrasena": contrasena,
            }
            conexion.sendall((json.dumps(peticion, ensure_ascii=False) + "\n").encode("utf-8"))
            lector = conexion.makefile("rb")
            linea = lector.readline(65537)
            if not linea or len(linea) > 65536:
                raise ConnectionError("El servidor no respondió correctamente.")
            respuesta = json.loads(linea.decode("utf-8"))
            if not isinstance(respuesta, dict) or respuesta.get("type") != "login_result":
                raise ValueError("Respuesta inesperada del servidor.")
            if not respuesta.get("ok"):
                QMessageBox.warning(
                    self, "Acceso denegado", respuesta.get("text", "Usuario o contraseña incorrectos.")
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
            self.btnLogin.setEnabled(True)
            if lector is not None:
                lector.close()
            if conexion is not None:
                conexion.close()

    def abrir_registro(self):
        VentanaRegistro(self).exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Messenger Papoi")
    app.setQuitOnLastWindowClosed(False)
    apply_theme(app)

    ventana_login = VentanaLogin()
    if ventana_login.exec() == QDialog.DialogCode.Accepted:
        try:
            ventana_chat = MainWindow(
                ventana_login.conexion,
                ventana_login.lector,
                ventana_login.cuenta,
            )
            ventana_chat.show()
            app.setQuitOnLastWindowClosed(True)
            sys.exit(app.exec())
        except Exception:
            ventana_login.conexion.close()
            raise
    sys.exit(0)
