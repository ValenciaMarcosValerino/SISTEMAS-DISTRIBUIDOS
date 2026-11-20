# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'IniciarSecion.ui'
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

class Ui_login(object):
    def setupUi(self, login):
        if not login.objectName():
            login.setObjectName(u"login")
        login.resize(800, 800)
        self.lblUsuario = QLabel(login)
        self.lblUsuario.setObjectName(u"lblUsuario")
        self.lblUsuario.setGeometry(QRect(30, 90, 131, 16))
        self.txtLoginU = QLineEdit(login)
        self.txtLoginU.setObjectName(u"txtLoginU")
        self.txtLoginU.setGeometry(QRect(20, 110, 113, 26))
        self.lblContrasea = QLabel(login)
        self.lblContrasea.setObjectName(u"lblContrasea")
        self.lblContrasea.setGeometry(QRect(20, 220, 171, 16))
        self.txtLoginP = QLineEdit(login)
        self.txtLoginP.setObjectName(u"txtLoginP")
        self.txtLoginP.setGeometry(QRect(20, 240, 113, 26))
        self.txtLoginP.setEchoMode(QLineEdit.EchoMode.Password)
        self.btnLogin = QPushButton(login)
        self.btnLogin.setObjectName(u"btnLogin")
        self.btnLogin.setGeometry(QRect(250, 150, 81, 26))
        self.btnRegistro = QPushButton(login)
        self.btnRegistro.setObjectName(u"btnRegistro")
        self.btnRegistro.setGeometry(QRect(240, 210, 81, 26))

        self.retranslateUi(login)

        QMetaObject.connectSlotsByName(login)
    # setupUi

    def retranslateUi(self, login):
        login.setWindowTitle(QCoreApplication.translate("login", u"IniciarSesion", None))
        self.lblUsuario.setText(QCoreApplication.translate("login", u"ACA VA EL USUARIO", None))
        self.lblContrasea.setText(QCoreApplication.translate("login", u"ACA VA LA CONTRASE\u00d1A", None))
        self.btnLogin.setText(QCoreApplication.translate("login", u"PushButton", None))
        self.btnRegistro.setText("")
    # retranslateUi

