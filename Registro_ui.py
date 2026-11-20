# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'Registro.ui'
##
## Created by: Qt User Interface Compiler version 6.12.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QDialog, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QWidget)

class Ui_Registro(object):
    def setupUi(self, Registro):
        if not Registro.objectName():
            Registro.setObjectName(u"Registro")
        Registro.resize(450, 500)
        self.label = QLabel(Registro)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(10, 40, 49, 16))
        self.label_2 = QLabel(Registro)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setGeometry(QRect(10, 120, 161, 16))
        self.label_3 = QLabel(Registro)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setGeometry(QRect(10, 210, 161, 16))
        self.label_4 = QLabel(Registro)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setGeometry(QRect(10, 290, 131, 16))
        self.txtUsuario = QLineEdit(Registro)
        self.txtUsuario.setObjectName(u"txtUsuario")
        self.txtUsuario.setGeometry(QRect(0, 70, 113, 26))
        self.txtNombreVi = QLineEdit(Registro)
        self.txtNombreVi.setObjectName(u"txtNombreVi")
        self.txtNombreVi.setGeometry(QRect(0, 160, 113, 26))
        self.txtContrasea = QLineEdit(Registro)
        self.txtContrasea.setObjectName(u"txtContrasea")
        self.txtContrasea.setGeometry(QRect(0, 240, 113, 26))
        self.txtContrasea.setEchoMode(QLineEdit.EchoMode.Password)
        self.txtConfirmarContra = QLineEdit(Registro)
        self.txtConfirmarContra.setObjectName(u"txtConfirmarContra")
        self.txtConfirmarContra.setGeometry(QRect(10, 320, 113, 26))
        self.txtConfirmarContra.setEchoMode(QLineEdit.EchoMode.Password)
        self.btnRegistro = QPushButton(Registro)
        self.btnRegistro.setObjectName(u"btnRegistro")
        self.btnRegistro.setGeometry(QRect(210, 170, 81, 26))
        self.btnVolverLogin = QPushButton(Registro)
        self.btnVolverLogin.setObjectName(u"btnVolverLogin")
        self.btnVolverLogin.setGeometry(QRect(210, 280, 141, 26))

        self.retranslateUi(Registro)

        QMetaObject.connectSlotsByName(Registro)
    # setupUi

    def retranslateUi(self, Registro):
        Registro.setWindowTitle(QCoreApplication.translate("Registro", u"RegistrarUsuario", None))
        self.label.setText(QCoreApplication.translate("Registro", u"Usuario", None))
        self.label_2.setText(QCoreApplication.translate("Registro", u"NombreVisible", None))
        self.label_3.setText(QCoreApplication.translate("Registro", u"Contrase\u00f1a", None))
        self.label_4.setText(QCoreApplication.translate("Registro", u"Confirmar Contrase\u00f1a", None))
        self.btnRegistro.setText(QCoreApplication.translate("Registro", u"Registrarse", None))
        self.btnVolverLogin.setText(QCoreApplication.translate("Registro", u"Volver al login", None))
    # retranslateUi

