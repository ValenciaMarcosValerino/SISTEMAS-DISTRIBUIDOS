# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'principal.ui'
##
## Created by: Qt User Interface Compiler version 6.12.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QMenu,
    QMenuBar, QPlainTextEdit, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_Messenger(object):
    def setupUi(self, Messenger):
        if not Messenger.objectName():
            Messenger.setObjectName(u"Messenger")
        Messenger.resize(800, 500)
        self.actionConectar = QAction(Messenger)
        self.actionConectar.setObjectName(u"actionConectar")
        self.actionSalir = QAction(Messenger)
        self.actionSalir.setObjectName(u"actionSalir")
        self.centralwidget = QWidget(Messenger)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.listWidget = QListWidget(self.centralwidget)
        self.listWidget.setObjectName(u"listWidget")

        self.horizontalLayout.addWidget(self.listWidget)

        self.txtMsgs = QPlainTextEdit(self.centralwidget)
        self.txtMsgs.setObjectName(u"txtMsgs")
        self.txtMsgs.setEnabled(True)
        self.txtMsgs.setFrameShape(QFrame.Shape.Box)
        self.txtMsgs.setFrameShadow(QFrame.Shadow.Raised)
        self.txtMsgs.setReadOnly(True)

        self.horizontalLayout.addWidget(self.txtMsgs)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.txtSend = QLineEdit(self.centralwidget)
        self.txtSend.setObjectName(u"txtSend")
        self.txtSend.setEnabled(True)
        self.txtSend.setMaxLength(1023)

        self.horizontalLayout_2.addWidget(self.txtSend)

        self.btnSend = QPushButton(self.centralwidget)
        self.btnSend.setObjectName(u"btnSend")

        self.horizontalLayout_2.addWidget(self.btnSend)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        Messenger.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(Messenger)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 800, 33))
        self.menuArchivo = QMenu(self.menubar)
        self.menuArchivo.setObjectName(u"menuArchivo")
        Messenger.setMenuBar(self.menubar)

        self.menubar.addAction(self.menuArchivo.menuAction())
        self.menuArchivo.addAction(self.actionConectar)
        self.menuArchivo.addSeparator()
        self.menuArchivo.addAction(self.actionSalir)

        self.retranslateUi(Messenger)

        QMetaObject.connectSlotsByName(Messenger)
    # setupUi

    def retranslateUi(self, Messenger):
        Messenger.setWindowTitle(QCoreApplication.translate("Messenger", u"Messenger", None))
        self.actionConectar.setText(QCoreApplication.translate("Messenger", u"Co&nectar", None))
#if QT_CONFIG(shortcut)
        self.actionConectar.setShortcut(QCoreApplication.translate("Messenger", u"Ctrl+C", None))
#endif // QT_CONFIG(shortcut)
        self.actionSalir.setText(QCoreApplication.translate("Messenger", u"&Salir", None))
#if QT_CONFIG(shortcut)
        self.actionSalir.setShortcut(QCoreApplication.translate("Messenger", u"Ctrl+X", None))
#endif // QT_CONFIG(shortcut)
        self.txtSend.setPlaceholderText("")
        self.btnSend.setText(QCoreApplication.translate("Messenger", u"Enviar", None))
        self.menuArchivo.setTitle(QCoreApplication.translate("Messenger", u"&Archivo", None))
    # retranslateUi

