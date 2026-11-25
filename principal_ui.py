# -*- coding: utf-8 -*-
# Generado para principal.ui: interfaz compatible con Qt Designer / PySide6.
# Si editas principal.ui en Qt Designer, regenera usando:
#     pyside6-uic principal.ui -o principal_ui.py

from PySide6.QtCore import QCoreApplication, QMetaObject, QRect
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLineEdit, QListWidget, QMainWindow,
    QMenu, QMenuBar, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)


class Ui_Messenger(object):
    def setupUi(self, Messenger):
        if not Messenger.objectName():
            Messenger.setObjectName("Messenger")
        Messenger.resize(1100, 650)

        self.actionConectar = QAction(Messenger)
        self.actionConectar.setObjectName("actionConectar")
        self.actionSalir = QAction(Messenger)
        self.actionSalir.setObjectName("actionSalir")
        self.actionCrearServidor = QAction(Messenger)
        self.actionCrearServidor.setObjectName("actionCrearServidor")
        self.actionCrearGrupo = QAction(Messenger)
        self.actionCrearGrupo.setObjectName("actionCrearGrupo")
        self.actionAgregarIntegrante = QAction(Messenger)
        self.actionAgregarIntegrante.setObjectName("actionAgregarIntegrante")
        self.actionActualizarGrupos = QAction(Messenger)
        self.actionActualizarGrupos.setObjectName("actionActualizarGrupos")

        self.centralwidget = QWidget(Messenger)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.listWidget = QListWidget(self.centralwidget)
        self.listWidget.setObjectName("listWidget")
        self.horizontalLayout.addWidget(self.listWidget, 1)

        self.txtMsgs = QPlainTextEdit(self.centralwidget)
        self.txtMsgs.setObjectName("txtMsgs")
        self.txtMsgs.setEnabled(True)
        self.txtMsgs.setFrameShape(QFrame.Shape.Box)
        self.txtMsgs.setFrameShadow(QFrame.Shadow.Raised)
        self.txtMsgs.setReadOnly(True)
        self.horizontalLayout.addWidget(self.txtMsgs, 3)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.txtSend = QLineEdit(self.centralwidget)
        self.txtSend.setObjectName("txtSend")
        self.txtSend.setEnabled(True)
        self.txtSend.setMaxLength(4000)
        self.horizontalLayout_2.addWidget(self.txtSend)
        self.btnSend = QPushButton(self.centralwidget)
        self.btnSend.setObjectName("btnSend")
        self.horizontalLayout_2.addWidget(self.btnSend)
        self.verticalLayout.addLayout(self.horizontalLayout_2)

        Messenger.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(Messenger)
        self.menubar.setObjectName("menubar")
        self.menubar.setGeometry(QRect(0, 0, 1100, 33))
        self.menuArchivo = QMenu(self.menubar)
        self.menuArchivo.setObjectName("menuArchivo")
        self.menuServidores = QMenu(self.menubar)
        self.menuServidores.setObjectName("menuServidores")
        self.menuGrupos = QMenu(self.menubar)
        self.menuGrupos.setObjectName("menuGrupos")
        Messenger.setMenuBar(self.menubar)

        self.menubar.addAction(self.menuArchivo.menuAction())
        self.menubar.addAction(self.menuServidores.menuAction())
        self.menubar.addAction(self.menuGrupos.menuAction())
        self.menuArchivo.addAction(self.actionConectar)
        self.menuArchivo.addSeparator()
        self.menuArchivo.addAction(self.actionSalir)
        self.menuServidores.addAction(self.actionCrearServidor)
        self.menuGrupos.addAction(self.actionCrearGrupo)
        self.menuGrupos.addAction(self.actionAgregarIntegrante)
        self.menuGrupos.addAction(self.actionActualizarGrupos)

        self.retranslateUi(Messenger)
        QMetaObject.connectSlotsByName(Messenger)

    def retranslateUi(self, Messenger):
        Messenger.setWindowTitle(QCoreApplication.translate("Messenger", "Messenger", None))
        self.actionConectar.setText(QCoreApplication.translate("Messenger", "Co&nectar", None))
        self.actionConectar.setShortcut(QCoreApplication.translate("Messenger", "Ctrl+C", None))
        self.actionSalir.setText(QCoreApplication.translate("Messenger", "&Salir", None))
        self.actionSalir.setShortcut(QCoreApplication.translate("Messenger", "Ctrl+X", None))
        self.actionCrearServidor.setText(QCoreApplication.translate("Messenger", "Crear Servidor", None))
        self.actionCrearGrupo.setText(QCoreApplication.translate("Messenger", "Crear grupo...", None))
        self.actionAgregarIntegrante.setText(QCoreApplication.translate("Messenger", "Agregar integrante conectado...", None))
        self.actionActualizarGrupos.setText(QCoreApplication.translate("Messenger", "Actualizar mis grupos", None))
        self.txtSend.setPlaceholderText(QCoreApplication.translate("Messenger", "Escribe tu mensaje aquí...", None))
        self.btnSend.setText(QCoreApplication.translate("Messenger", "Enviar", None))
        self.menuArchivo.setTitle(QCoreApplication.translate("Messenger", "&Archivo", None))
        self.menuServidores.setTitle(QCoreApplication.translate("Messenger", "Servidores", None))
        self.menuGrupos.setTitle(QCoreApplication.translate("Messenger", "Grupos", None))
