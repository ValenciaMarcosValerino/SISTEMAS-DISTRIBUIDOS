
import sys
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
from IniciarSecion_ui import Ui_login


# VENTANA DE LOGIN

class VentanaLogin(QDialog):

    def __init__(self):
        super().__init__()

        self.ui = Ui_login()
        self.ui.setupUi(self)

        self.ui.btnLogin.clicked.connect(self.iniciar_sesion)
        self.ui.btnRegistro.clicked.connect(self.abrir_registro)


    # INICIAR SESION

    def iniciar_sesion(self):

        usuario = self.ui.txtLoginU.text().strip()
        contrasena = self.ui.txtLoginP.text()

        if not usuario or not contrasena:

            QMessageBox.warning(
                self,
                "Datos incompletos",
                "Ingresa tu usuario y contraseña."
            )
            return

        QMessageBox.information(
            self,
            "Login",
            "Datos capturados correctamente."
        )


    # REGISTRAR USUARIO

    def abrir_registro(self):

        QMessageBox.information(
            self,
            "Registro",
            "Aquí abriremos la ventana para crear una cuenta."
        )


# PROGRAMA PRINCIPAL

if __name__ == "__main__":

    app = QApplication(sys.argv)

    ventana = VentanaLogin()
    ventana.show()

    sys.exit(app.exec())
