# config.py (только цвета, без лишних изменений)

import os
import sys
from pathlib import Path

# Определяем, запущены ли мы из .exe или из исходников
if getattr(sys, 'frozen', False):
    # Запущены из .exe (PyInstaller)
    BASE_DIR = Path(sys._MEIPASS)
else:
    # Запущены из исходников
    BASE_DIR = Path(__file__).parent.absolute()

ASSETS_DIR = BASE_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
LESHY_ASSETS_DIR = ASSETS_DIR / "leshy"
KNOWLEDGE_BASE_PATH = BASE_DIR / "core" / "knowledge_base.json"

# Настройки окна
WINDOW_HEIGHT = 300
CONTENT_WIDTH = 600
LESHY_PANEL_WIDTH = 300
WINDOW_OPACITY_ACTIVE = 1.0
WINDOW_OPACITY_INACTIVE = 0.5

# Настройки анимаций
IDLE_SWITCH_INTERVAL = 5000
TYPING_SPEED_NORMAL = 25
TYPING_SPEED_FAST = 10
ANIMATION_FRAME_INTERVAL = 100
GAME_LOOP_INTERVAL = 16

# Секретные слова для выхода
EXIT_PHRASES = ["до свидания", "прощай", "пока", "выход", "закрыть"]

# Настройки для режима киоска
KIOSK_MODE = False
KIOSK_PASSWORD = "leshy2026"

PERSONAL_DATES = {
    "15.07": {
        "type": "birthday",
        "name": "Антонина",  # Имя или обращение
        "description": "День рождения Тоси (=",
        "emoji": "🎂🎉",
    },
    # Можно добавить другие даты:
    # "01.09": {
    #     "type": "work_anniversary", 
    #     "name": "Хозяйка",
    #     "description": "Годовщина работы в школе",
    # },
}

# ========== ЦВЕТОВАЯ СХЕМА ==========

# Основные цвета (только то, что нужно для стилей)
COLORS = {
    # Фоновые цвета
    "background_primary": "#1a1208",      # Основной фон (очень темный)
    "background_secondary": "#1e140a",    # Вторичный фон (темный)
    "background_tertiary": "#1e140a",     # Третичный фон (для кнопок)
    "background_input": "#1e140a",        # Фон полей ввода
    "background_menu": "#1a1208",         # Фон меню
    "background_hover": "#2a3f2f",        # Фон при наведении
    "background_selected": "#1a4d3e",     # Фон при выделении
    "background_dialog": "#1a1208",       # Фон диалогов
    "background_history": "#1a120870",    # Фон истории
    
    # Цвета текста
    "text_primary": "#f5e7d3",            # Основной текст (светлый)
    "text_secondary": "#e0d5c1",          # Вторичный текст
    "text_muted": "#8a7b66",              # Приглушенный текст
    "text_selected": "#e0f0e8",           # Текст при выделении
    "text_disabled": "#6a5a4a",           # Отключенный текст
    
    # Цвета границ
    "border_primary": "#6a5a4a",          # Основные границы
    "border_hover": "#8a7a5a",            # Границы при наведении
    "border_focus": "#c0a060",            # Границы при фокусе
    "border_disabled": "#3a2f1f",         # Отключенные границы
    "border_separator": "#3a2f1f",        # Разделители
    "border_history": "#6a5a4a10",        # Границы истории
    
    # Акцентные цвета
    "accent_loading": "#daa520",          # Золотой для загрузки
    "accent_primary": "#c0a060",          # Основной акцент
    
    # Цвета категорий
    "category_word": "#90ee90",           # Светло-зеленый для Word
    "category_excel": "#6495ed",          # Светло-синий для Excel
    "category_general": "#f0e68c",        # Светло-золотой для общего
}
# ========== ЦВЕТОВЫЕ СХЕМЫ СКИНОВ ==========

SKIN_COLORS = {
    "maid": {
        # Фоновые цвета — светлые, пастельные
        "background_primary": "#F3EEDF",      # Основной фон (светло-кремовый)
        "background_secondary": "#FDF5F0",    # Вторичный фон (светлее)
        "background_tertiary": "#F5E6E0",     # Третичный фон (розоватый)
        "background_input": "#FFF8F5",        # Фон полей ввода (почти белый с розовинкой)
        "background_menu": "#F3EEDF",         # Фон меню
        "background_hover": "#F0D5D0",        # Фон при наведении (светло-розовый)
        "background_selected": "#E8C4BC",     # Фон при выделении (пыльно-розовый)
        "background_dialog": "#F3EEDF",       # Фон диалогов
        "background_history": "#F3EEDF90",    # Фон истории
        
        # Цвета текста — тёмные, контрастные
        "text_primary": "#2C1810",            # Основной текст (тёмно-коричневый)
        "text_secondary": "#3D2015",          # Вторичный текст
        "text_muted": "#8B6B5E",              # Приглушенный текст (серо-коричневый)
        "text_selected": "#FFFFFF",           # Текст при выделении (белый)
        "text_disabled": "#B8A090",           # Отключенный текст
        
        # Цвета границ — тёмные, чёткие
        "border_primary": "#C4A090",          # Основные границы (бежево-коричневый)
        "border_hover": "#D4A0A0",            # Границы при наведении (розоватый)
        "border_focus": "#B8485E",            # Границы при фокусе (бордово-красный)
        "border_disabled": "#E0D0C8",         # Отключенные границы
        "border_separator": "#E0D0C8",        # Разделители
        "border_history": "#C4A09010",        # Границы истории
        
        # Акцентные цвета — красные и бордовые оттенки
        "accent_loading": "#C04860",          # Бордовый для загрузки
        "accent_primary": "#B8485E",          # Основной акцент (тёмно-розовый)
        
        # Цвета категорий — контрастные
        "category_word": "#2D7D46",           # Тёмно-зеленый для Word
        "category_excel": "#1A5276",          # Тёмно-синий для Excel
        "category_general": "#8B6040",        # Коричневый для общего
    },
    
    # Можно добавить другие скины:
    # "wizard": {
    #     "background_primary": "#1a1a2e",
    #     "text_primary": "#e0e0ff",
    #     "accent_primary": "#7b68ee",
    #     ...
    # },
}

# Для обратной совместимости
COLOR_LOADING = COLORS["accent_loading"]
COLOR_MAIN = COLORS["text_primary"]