# gui/plugins/voice_input.py
"""
Плагин для голосового ввода (Speech-to-Text).
"""

from PyQt5.QtWidgets import QPushButton
from PyQt5.QtCore import pyqtSignal, QObject


class VoiceInputPlugin(QObject):
    """Плагин для распознавания речи."""
    
    text_recognized = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_listening = False
        self.button = None
        
    def create_button(self) -> QPushButton:
        """Создает кнопку для запуска голосового ввода."""
        self.button = QPushButton("🎤")
        self.button.setFixedSize(40, 40)
        self.button.setToolTip("Голосовой ввод")
        self.button.clicked.connect(self.toggle_listening)
        return self.button
    
    def toggle_listening(self):
        """Включает/выключает прослушивание микрофона."""
        if self.is_listening:
            self.stop_listening()
        else:
            self.start_listening()
    
    def start_listening(self):
        """Начинает прослушивание микрофона."""
        self.is_listening = True
        self.button.setText("🔴")
        # TODO: Реализация распознавания речи
        print("Начинаем распознавание речи...")
    
    def stop_listening(self):
        """Останавливает прослушивание микрофона."""
        self.is_listening = False
        self.button.setText("🎤")
        # TODO: Остановка распознавания речи
        print("Останавливаем распознавание речи...")