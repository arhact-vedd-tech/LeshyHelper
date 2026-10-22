# main.py (обновленный)
"""
Точка входа в приложение Хранитель Канцелярского Леса.
"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont

from gui import LeshyWindow, load_custom_font
from config import PERSONAL_DATES


def main():
    """Основная функция запуска приложения."""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    
    # Загружаем кастомный шрифт
    custom_font_family = load_custom_font()
    if custom_font_family:
        font = QFont(custom_font_family, 10)
        app.setFont(font)
    
    # Создаем и показываем окно (передаём персональные даты)
    window = LeshyWindow(
        font_family=custom_font_family,
        personal_dates=PERSONAL_DATES
    )
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()