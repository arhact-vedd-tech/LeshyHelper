# gui/plugins/kiosk.py
"""
Плагин для режима киоска (Kiosk Mode).
"""

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QDialog, QLabel, QLineEdit, QVBoxLayout, QPushButton


class KioskPlugin:
    """Плагин для управления режимом киоска."""
    
    def __init__(self, password: str = "leshy2026"):
        self.password = password
        self.is_active = False
        self._exit_timer = QTimer()
    
    def activate(self):
        """Активирует режим киоска."""
        self.is_active = True
        # TODO: Блокировка всех кнопок и выходов
        print("Режим киоска активирован")
    
    def deactivate(self):
        """Деактивирует режим киоска."""
        self.is_active = False
        # TODO: Разблокировка всех элементов
        print("Режим киоска деактивирован")
    
    def show_password_dialog(self) -> bool:
        """Показывает диалог ввода пароля для выхода из киоск-режима."""
        dialog = QDialog()
        dialog.setWindowTitle("Выход из режима киоска")
        dialog.setFixedSize(300, 150)
        
        layout = QVBoxLayout(dialog)
        
        label = QLabel("Введите пароль для выхода:")
        layout.addWidget(label)
        
        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.Password)
        password_input.returnPressed.connect(dialog.accept)
        layout.addWidget(password_input)
        
        confirm_btn = QPushButton("Подтвердить")
        confirm_btn.clicked.connect(dialog.accept)
        layout.addWidget(confirm_btn)
        
        if dialog.exec_() == QDialog.Accepted:
            if password_input.text() == self.password:
                return True
        
        return False