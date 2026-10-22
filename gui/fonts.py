# gui/fonts.py
"""
Загрузка кастомных шрифтов из файлов в память.
"""

import os
from PyQt5.QtGui import QFontDatabase
from config import FONTS_DIR


def load_custom_font() -> str:
    """
    Загружает кастомный шрифт из папки assets/fonts/ В ПАМЯТЬ.
    Файл шрифта читается и закрывается, не блокируя его.
    Возвращает название шрифта (font family).
    Если шрифт не найден — возвращает None.
    """
    try:
        if not FONTS_DIR.exists():
            print(f"Папка со шрифтами не найдена: {FONTS_DIR}")
            return None
        
        font_files = [f for f in os.listdir(FONTS_DIR) 
                      if f.lower().endswith(('.ttf', '.otf'))]
        
        if not font_files:
            print(f"Шрифты не найдены в папке: {FONTS_DIR}")
            return None
        
        font_path = FONTS_DIR / font_files[0]
        print(f"Загружаем шрифт: {font_files[0]}")
        
        # Читаем файл шрифта в память и сразу закрываем
        with open(font_path, 'rb') as font_file:
            font_data = font_file.read()
        
        # Загружаем шрифт из данных в памяти
        font_id = QFontDatabase.addApplicationFontFromData(font_data)
        
        if font_id == -1:
            print(f"Ошибка загрузки шрифта из данных: {font_files[0]}")
            return None
        
        font_families = QFontDatabase.applicationFontFamilies(font_id)
        
        if font_families:
            font_family = font_families[0]
            print(f"Шрифт успешно загружен в память: {font_family}")
            return font_family
        else:
            print("Не удалось определить семейство шрифта")
            return None
    
    except Exception as e:
        print(f"Ошибка при загрузке шрифта: {e}")
        return None