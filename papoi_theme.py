"""Estilos compartidos de Messenger Papoi.

No participa en comunicaciones TCP ni SQL Server.
Los temas se guardan en QSettings y pueden cambiarse en caliente.
"""

import os
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

SERVER_HOST = os.environ.get("PAPOI_SERVER_HOST", "3.149.102.2")
try:
    SERVER_PORT = int(os.environ.get("PAPOI_SERVER_PORT", "3072"))
except ValueError:
    SERVER_PORT = 5000

THEMES = {
    "oceano": {
        "nombre": "Azul Papoi",
        "bg": "#0A1528", "header": "#101F36", "sidebar": "#101F35",
        "panel": "#14253C", "card": "#172C46", "card2": "#203752",
        "input": "#0E1E32", "text": "#EAF5FF", "muted": "#A8B9CF",
        "border": "#2B4160", "accent": "#39C5E8", "accent_hover": "#67D8F0",
        "accent_text": "#071727", "selection": "#244C65", "message": "#1C304A",
        "mine": "#174C63", "danger": "#F09A9A", "success": "#6EE7BD",
    },
    "claro": {
        "nombre": "Minimalista claro",
        "bg": "#EDF2FA", "header": "#FFFFFF", "sidebar": "#FFFFFF",
        "panel": "#FFFFFF", "card": "#F8FAFE", "card2": "#E8EFFA",
        "input": "#F7FAFF", "text": "#1A2942", "muted": "#687A91",
        "border": "#DAE3EF", "accent": "#426FDF", "accent_hover": "#6189ED",
        "accent_text": "#FFFFFF", "selection": "#E1EAFD", "message": "#F0F4FA",
        "mine": "#DCE8FF", "danger": "#A82D46", "success": "#1B8763",
    },
    "violeta": {
        "nombre": "Grafito violeta",
        "bg": "#151323", "header": "#201C32", "sidebar": "#1C192C",
        "panel": "#231F36", "card": "#28233D", "card2": "#352C4B",
        "input": "#1B192D", "text": "#F1ECFF", "muted": "#B3A9CB",
        "border": "#42395A", "accent": "#B49AFF", "accent_hover": "#CAB8FF",
        "accent_text": "#221832", "selection": "#42325D", "message": "#322A49",
        "mine": "#4B386A", "danger": "#FFACBE", "success": "#9EE8C9",
    },
}


def theme_name():
    value = QSettings("Papoi", "MessengerPapoi").value("tema", "oceano")
    return value if value in THEMES else "oceano"


def palette(name=None):
    return THEMES[name or theme_name()]


def set_theme(name, app=None):
    if name not in THEMES:
        raise ValueError("Tema desconocido")
    QSettings("Papoi", "MessengerPapoi").setValue("tema", name)
    apply_theme(app, name)


def apply_theme(app=None, name=None):
    app = app or QApplication.instance()
    if app is None:
        return
    p = palette(name)
    app.setStyle("Fusion")
    app.setStyleSheet(_stylesheet(p))


def _stylesheet(p):
    return """
    QWidget {
      font-family: 'Segoe UI', 'Arial';
      color: %(text)s;
      font-size: 10pt;
      selection-background-color: %(accent)s;
      selection-color: %(accent_text)s;
    }
    QMainWindow, QDialog#AuthWindow, QWidget#CentralWorkspace {
      background-color: %(bg)s;
    }
    QDialog, QMessageBox, QInputDialog {
      background-color: %(panel)s;
    }
    QFrame#AuthCard, QFrame#ChatPanel, QFrame#SidebarPanel {
      background-color: %(panel)s;
      border: 1px solid %(border)s;
      border-radius: 18px;
    }
    QFrame#AppHeader, QFrame#ComposerBar {
      background-color: %(header)s;
      border: 1px solid %(border)s;
      border-radius: 15px;
    }
    QLabel#AppTitle, QLabel#AuthTitle {
      font-size: 21pt;
      font-weight: 750;
      color: %(text)s;
    }
    QLabel#BrandTitle { font-weight: 800; font-size: 17pt; color: %(text)s; }
    QLabel#ChatTitle { font-weight: 750; font-size: 18pt; color: %(text)s; }
    QLabel#BrandMark {
      background: %(accent)s;
      color: %(accent_text)s;
      font-size: 22pt;
      font-weight: 900;
      border-radius: 14px;
      padding: 7px;
    }
    QLabel#ChatSubtitle, QLabel#MutedText, QLabel#SectionTitle,
    QLabel#FieldLabel, QLabel#StatusText, QLabel#FooterText {
      color: %(muted)s;
    }
    QLabel#SectionTitle {
      font-weight: 750;
      font-size: 9pt;
      letter-spacing: 1px;
    }
    QLabel#FieldLabel { font-weight: 650; font-size: 9pt; }
    QLabel#Pill {
      background-color: %(card2)s;
      color: %(accent)s;
      border: 1px solid %(border)s;
      border-radius: 11px;
      padding: 7px 12px;
      font-weight: 650;
    }
    QLabel#StatusText { font-size: 9pt; }
    QLineEdit, QComboBox, QPlainTextEdit, QTextBrowser, QTextEdit {
      color: %(text)s;
      background-color: %(input)s;
      border: 1px solid %(border)s;
      border-radius: 10px;
      padding: 10px 12px;
      selection-background-color: %(accent)s;
      selection-color: %(accent_text)s;
    }
    QLineEdit:focus, QComboBox:focus, QTextBrowser:focus {
      border: 2px solid %(accent)s;
    }
    QLineEdit:disabled { color: %(muted)s; background-color: %(card)s; }
    QComboBox::drop-down { border: 0; width: 28px; }
    QComboBox QAbstractItemView {
      background: %(panel)s;
      color: %(text)s;
      selection-background-color: %(selection)s;
      selection-color: %(text)s;
      border: 1px solid %(border)s;
    }
    QPushButton {
      padding: 10px 15px;
      border-radius: 10px;
      font-weight: 650;
      border: 1px solid %(border)s;
      background-color: %(card2)s;
      color: %(text)s;
    }
    QPushButton:hover { background-color: %(selection)s; border-color: %(accent)s; }
    QPushButton:disabled { background-color: %(card)s; color: %(muted)s; border-color: %(border)s; }
    QPushButton#PrimaryButton, QPushButton#btnSend {
      background-color: %(accent)s;
      color: %(accent_text)s;
      border: 1px solid %(accent)s;
      font-weight: 800;
    }
    QPushButton#PrimaryButton:hover, QPushButton#btnSend:hover {
      background-color: %(accent_hover)s;
      border-color: %(accent_hover)s;
    }
    QPushButton#PrimaryButton:disabled, QPushButton#btnSend:disabled {
      background: %(card2)s; color: %(muted)s; border-color: %(border)s;
    }
    QPushButton#GhostButton { background: transparent; border: 1px solid %(border)s; }
    QPushButton#TextButton { background: transparent; color: %(accent)s; border: 0; }
    QListWidget#listWidget {
      color: %(text)s;
      background-color: transparent;
      border: 0;
      outline: 0;
      padding: 2px;
    }
    QListWidget#listWidget::item {
      border-radius: 9px;
      margin: 2px 1px;
      padding: 9px 8px;
      min-height: 19px;
    }
    QListWidget#listWidget::item:hover { background-color: %(card2)s; }
    QListWidget#listWidget::item:selected {
      background: %(selection)s;
      border-left: 3px solid %(accent)s;
      color: %(text)s;
      font-weight: 650;
    }
    QListWidget#listWidget::item:disabled { color: %(muted)s; }
    QTextBrowser#txtMsgs {
      background-color: %(panel)s;
      border: 0;
      border-radius: 0;
      padding: 12px 14px;
    }
    QMenuBar { color: %(text)s; background: %(header)s; padding: 6px; }
    QMenuBar::item { padding: 9px 13px; border-radius: 8px; }
    QMenuBar::item:selected { background: %(selection)s; }
    QMenu {
      color: %(text)s; background-color: %(panel)s;
      border: 1px solid %(border)s; padding: 6px;
    }
    QMenu::item { padding: 8px 24px; border-radius: 5px; }
    QMenu::item:selected { background-color: %(selection)s; }
    QMenu::separator { background: %(border)s; height: 1px; margin: 6px 8px; }
    QScrollBar:vertical { background: transparent; width: 10px; margin: 1px; }
    QScrollBar::handle:vertical {
      background: %(border)s; border-radius: 5px; min-height: 28px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    QScrollBar:horizontal { background: transparent; height: 10px; }
    QScrollBar::handle:horizontal { background: %(border)s; border-radius: 5px; }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
    """ % p
