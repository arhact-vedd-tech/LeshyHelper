# gui/main_window.py (полная версия с новой системой анимаций)
"""
Главное окно приложения с Лешим.
Обновлённая система анимаций:
- idle — базовая петля
- idle2/idle3 — однократные вставки с возвратом к idle
- thinking/talking — принудительное переключение без ожидания
"""

import sys
import time
import json
import random
from typing import Optional
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QLineEdit, 
                             QTextEdit, QWidget, QVBoxLayout, QHBoxLayout,
                             QSizePolicy, QSystemTrayIcon, QMenu, QAction,
                             QPushButton)
from PyQt5.QtCore import Qt, QTimer, QEvent, QPoint
from PyQt5.QtGui import QPixmap, QFont, QPalette, QColor, QKeyEvent, QTextCursor, QTextCharFormat, QIcon

from core import LeshyWisdom
from utils import GameLoop, StateMachine, LeshyState
from .animation_manager import AnimationManager
from .styles import create_stylesheet
from .fonts import load_custom_font
from config import *
from gui.plugins import HistoryPlugin, HistoryWidget


class LeshyWindow(QMainWindow):
    """Главное окно с Лешим."""
    
    def __init__(self, font_family: Optional[str] = None, personal_dates: dict = None):
        super().__init__()
        
        # Инициализация компонентов
        self.wisdom = LeshyWisdom(
            knowledge_base_path=KNOWLEDGE_BASE_PATH,
            personal_dates=personal_dates  # ← ПЕРЕДАЁМ ПЕРСОНАЛЬНЫЕ ДАТЫ
        )
        self.animation_manager = AnimationManager()
        self.state_machine = StateMachine(LeshyState.IDLE)
        self.game_loop = GameLoop(GAME_LOOP_INTERVAL)
        self.custom_font_family = font_family
        
        # Флаги и счетчики
        self.esc_counter = 0
        self.esc_reset_timer = QTimer()
        self.esc_reset_timer.timeout.connect(self.reset_esc_counter)
        self._last_answer_click_time = 0
        self._is_closing = False
        self._loading_phrase = ""
        self._loading_phrase_length = 0
        self.idle_switch_counter = 0    
        self._input_was_visible = False
        self._answer_was_visible = False
        
        # Настройки однократных idle-анимаций
        self._idle_one_shot_timer = QTimer()
        self._idle_one_shot_timer.setSingleShot(True)
        self._idle_one_shot_timer.timeout.connect(self._try_play_one_shot_idle)
        self._schedule_next_one_shot()
        
        # Скорость печати
        self._typing_speed_multiplier = 1
        self._typing_counter = 0
        self._typing_interval = 1
        
        # Инициализация плагина истории
        self.history_plugin = HistoryPlugin(max_size=100)
        self.history_widget = None
        self.history_container = None
        
        # Настройка конечного автомата
        self._setup_state_machine()
        
        # Форматы для текста
        self._loading_format = QTextCharFormat()
        self._loading_format.setForeground(QColor(COLORS["accent_loading"]))
        self._loading_format.setFontItalic(True)
        
        self._main_format = QTextCharFormat()
        self._main_format.setForeground(QColor(COLORS["text_primary"]))
        self._main_format.setFontItalic(False)
        
        self._current_format = self._loading_format
        
        # Переменные для печати
        self.full_answer = ""
        self.current_char_index = 0
        self.animation_skipped = False
        
        # Инициализация интерфейса
        self.initUI()
        
        # Настройка системного трея
        self.setup_tray()
        
        # Регистрируем функции в игровом цикле
        self.game_loop.register(self._update_animation, interval=1)
        self.game_loop.register(self._update_typing, interval=1)
        self.game_loop.start()
        
        # Запускаем базовую idle-анимацию
        self.animation_manager.play_base("idle")
        
        # Начальная прозрачность
        self.setWindowOpacity(WINDOW_OPACITY_ACTIVE)
        
        # Проверяем, есть ли уже история
        if self.history_plugin.get_size() > 0:
            self._show_history_button()
            
        # Применяем глобальную стилизацию
        self.setStyleSheet(create_stylesheet(self.custom_font_family))
        
        # Пасхалки
        self._current_skin: Optional[str] = None
        self._skin_timer = QTimer()
        self._skin_timer.setSingleShot(True)

        # Настройки
        self._settings_path = Path(__file__).parent.parent / "core" / "settings.json"
        self._settings = self._load_settings()
        
        # Применяем сохранённый скин при запуске
        saved_skin = self._settings.get("active_skin")
        if saved_skin:
            print(f"🎭 Загружен сохранённый скин: {saved_skin}")
            self._apply_skin(saved_skin, silent=True)
    
    def _setup_state_machine(self):
        """Настраивает переходы и действия для конечного автомата."""
        # Добавляем действия при входе в состояния
        self.state_machine.add_on_enter(LeshyState.IDLE, self._on_idle_enter)
        self.state_machine.add_on_enter(LeshyState.INPUT, self._on_input_enter)
        self.state_machine.add_on_enter(LeshyState.THINKING, self._on_thinking_enter)
        self.state_machine.add_on_enter(LeshyState.TALKING, self._on_talking_enter)
        self.state_machine.add_on_enter(LeshyState.ANSWER_VISIBLE, self._on_answer_visible_enter)
        self.state_machine.add_on_enter(LeshyState.HISTORY, self._on_history_enter)
        
        # Добавляем действия при выходе из состояний
        self.state_machine.add_on_exit(LeshyState.INPUT, self._on_input_exit)
        self.state_machine.add_on_exit(LeshyState.TALKING, self._on_talking_exit)
        self.state_machine.add_on_exit(LeshyState.ANSWER_VISIBLE, self._on_answer_visible_exit)
        self.state_machine.add_on_exit(LeshyState.HISTORY, self._on_history_exit)
        
        # Добавляем правила переходов
        self.state_machine.add_transition(LeshyState.IDLE, LeshyState.INPUT)
        self.state_machine.add_transition(LeshyState.INPUT, LeshyState.IDLE)
        self.state_machine.add_transition(LeshyState.INPUT, LeshyState.THINKING)
        self.state_machine.add_transition(LeshyState.IDLE, LeshyState.THINKING)
        self.state_machine.add_transition(LeshyState.THINKING, LeshyState.TALKING)
        self.state_machine.add_transition(LeshyState.TALKING, LeshyState.ANSWER_VISIBLE)
        self.state_machine.add_transition(LeshyState.ANSWER_VISIBLE, LeshyState.IDLE)
        self.state_machine.add_transition(LeshyState.ANSWER_VISIBLE, LeshyState.THINKING)
        self.state_machine.add_transition(LeshyState.IDLE, LeshyState.HISTORY)
        self.state_machine.add_transition(LeshyState.INPUT, LeshyState.HISTORY)
        self.state_machine.add_transition(LeshyState.ANSWER_VISIBLE, LeshyState.HISTORY)
        self.state_machine.add_transition(LeshyState.HISTORY, LeshyState.IDLE)
    
    # ========== Действия состояний ==========
    
    def _on_idle_enter(self):
        """Вход в состояние IDLE."""
        
        # Запускаем базовую петлю idle
        self.animation_manager.play_base("idle")
        
        self.idle_switch_counter = 0
        
        # Скрываем поле ввода
        self.input_field.hide()
        self.input_field.clear()
        
        # Скрываем кнопку истории вместе с полем ввода
        self.history_btn.hide()
        
        # Если история открыта — закрываем её
        if self.history_container and self.history_container.isVisible():
            self._close_history_widget()
        
        # Планируем следующую однократную анимацию
        self._schedule_next_one_shot()
        
    def _on_input_enter(self):
        """Вход в состояние INPUT."""
        
        # Закрываем окно истории, если оно открыто
        if self.history_container and self.history_container.isVisible():
            self._close_history_widget()
            return
        
        # Отменяем таймер однократных анимаций при вводе
        self._idle_one_shot_timer.stop()
        
        self.input_field.show()
        self.input_field.clear()
        self.input_field.setFocus()
        self.input_field.setPlaceholderText("✏️ Введите вопрос...")
        
        # Показываем кнопку истории вместе с полем ввода (если есть записи)
        if self.history_plugin.get_size() > 0:
            self.history_btn.show()
        
        # Оставляем idle при вводе
        self.animation_manager.play_base("idle")

    def _on_thinking_enter(self):
        """Вход в состояние THINKING."""
        
        # Отменяем таймер однократных анимаций
        self._idle_one_shot_timer.stop()
        
        # Закрываем окно истории, если оно открыто
        if self.history_container and self.history_container.isVisible():
            self._close_history_widget()
            return
        
        # ПРИНУДИТЕЛЬНО переключаем на thinking, не дожидаясь idle
        self.animation_manager.play_forced("thinking", loop=True)
        
        self.answer_field.clear()
        self.answer_field.show()
        self._loading_phrase = self.wisdom.get_loading_phrase()
        self._loading_phrase_length = len(self._loading_phrase)
        self._current_format = self._loading_format
        self.full_answer = self._loading_phrase + " \n"
        self.current_char_index = 0
        self._typing_counter = 0
        self._typing_speed_multiplier = 1
        self._typing_interval = 3
        
        # Скрываем кнопку истории при ответе
        self.history_btn.hide()
    
    def _on_input_exit(self):
        """Выход из состояния INPUT."""
        self.input_field.hide()
        self.input_field.clear()
    
    def _on_talking_enter(self):
        """Вход в состояние TALKING."""
        
        # Определяем, какая анимация сейчас играет
        current_anim = self.animation_manager.current_animation
        
        # Если анимация уже talking2, оставляем её
        if current_anim != "talking2":
            # ПРИНУДИТЕЛЬНО переключаем на talking
            self.animation_manager.play_forced("talking", loop=True)
        
        self._typing_counter = 0
        self._typing_speed_multiplier = 1
        self._typing_interval = 2
        
        if hasattr(self, 'animation_manager'):
            anim_name = current_anim if current_anim == "talking2" else "talking"
            info = self.animation_manager.get_animation_info(anim_name)
    
    def _on_talking_exit(self):
        """Выход из состояния TALKING."""
        self._typing_speed_multiplier = 1
    
    def _on_answer_visible_enter(self):
        """Вход в состояние ANSWER_VISIBLE."""
        
        # Закрываем окно истории, если оно открыто
        if self.history_container and self.history_container.isVisible():
            self._close_history_widget()
        
        # Возвращаемся к базовой idle-анимации
        self.animation_manager.play_base("idle")
        
        self._typing_speed_multiplier = 1
        self._typing_interval = 2
        
        # Показываем кнопку истории (если есть записи)
        if self.history_plugin.get_size() > 0:
            self.history_btn.show()
        
        # Планируем следующую однократную анимацию
        self._schedule_next_one_shot()
    
    def _on_answer_visible_exit(self):
        """Выход из состояния ANSWER_VISIBLE."""
        pass
    
    def _on_history_enter(self):
        """Вход в состояние HISTORY."""
        
        # Отменяем таймер однократных анимаций
        self._idle_one_shot_timer.stop()
        
        # Запускаем анимацию "lib" принудительно
        if self.animation_manager.has_animation("lib"):
            self.animation_manager.play_forced("lib", loop=True)
        else:
            self.animation_manager.play_forced("idle", loop=True)

    def _on_history_exit(self):
        """Выход из состояния HISTORY."""
        
        # Возвращаемся к базовой idle
        self.animation_manager.play_base("idle")
        
        # Планируем следующую однократную анимацию
        self._schedule_next_one_shot()
    
    # ========== Система однократных idle-анимаций ==========
    
    def _schedule_next_one_shot(self):
        """Планирует следующую однократную idle-анимацию через случайный интервал."""
        # Случайный интервал от 8 до 20 секунд
        interval = random.randint(8000, 20000)
        self._idle_one_shot_timer.start(interval)
    
    def _try_play_one_shot_idle(self):
        """Пытается проиграть однократную idle-анимацию."""
        # Проверяем, что мы в подходящем состоянии
        if not self.state_machine.is_any_state(LeshyState.IDLE, LeshyState.ANSWER_VISIBLE):
            self._schedule_next_one_shot()
            return
        
        # Проверяем, что анимация в состоянии покоя
        if not self.animation_manager.is_idle():
            self._schedule_next_one_shot()
            return
        
        # Доступные однократные анимации
        one_shot_animations = []
        for name in ["idle2", "idle3"]:
            if self.animation_manager.has_animation(name):
                one_shot_animations.append(name)
        
        if not one_shot_animations:
            self._schedule_next_one_shot()
            return
        
        # Выбираем случайную анимацию
        chosen = random.choice(one_shot_animations)
        
        success = self.animation_manager.play_one_shot(chosen)
        
        # Планируем следующую
        self._schedule_next_one_shot()
    
    # ========== Методы для работы с историей ==========
    
    def _show_history_button(self):
        """Показывает кнопку истории."""
        if hasattr(self, 'history_btn'):
            if self.input_field.isVisible() or self.state_machine.is_state(LeshyState.ANSWER_VISIBLE):
                self.history_btn.show()
                self.history_btn.setEnabled(True)
    
    def _hide_history_button(self):
        """Скрывает кнопку истории."""
        if hasattr(self, 'history_btn'):
            self.history_btn.hide()

    def _determine_category(self, question: str) -> str:
        """Определяет категорию вопроса."""
        question_lower = question.lower()
        
        word_keywords = ['word', 'ворд', 'текст', 'шрифт', 'абзац', 'страница', 
                        'номер', 'колонтитул', 'оглавление', 'сноска', 'картинка']
        excel_keywords = ['excel', 'эксель', 'таблица', 'сумма', 'ячейка', 
                         'диаграмма', 'график', 'формула', 'сортировка', 'фильтр']
        
        for word in word_keywords:
            if word in question_lower:
                return "word"
        
        for word in excel_keywords:
            if word in question_lower:
                return "excel"
        
        return "general"
    
    # ========== Инициализация интерфейса ==========
    
    def initUI(self):
        """Создает и настраивает пользовательский интерфейс."""
        self.setWindowTitle("Хранитель Канцелярского Леса")
        
        # Настройки окна
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Позиционирование
        screen = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(0, screen.height() - WINDOW_HEIGHT, 
                         screen.width(), WINDOW_HEIGHT)
        
        # Центральный виджет
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)
        
        # Основной layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Левая панель
        left_panel = self._create_left_panel()
        main_layout.addWidget(left_panel)
        
        # Правая панель с Лешим
        right_panel = self._create_right_panel()
        main_layout.addWidget(right_panel)
        
        # Применяем стили
        stylesheet = create_stylesheet(self.custom_font_family)
        self.setStyleSheet(stylesheet)
        
        # Устанавливаем первый кадр
        self._update_leshy_frame()
    
    def _create_left_panel(self) -> QWidget:
        """Создает левую панель с контентом и кнопкой истории."""
        left_panel = QWidget()
        left_panel.setObjectName("leftPanel")
        left_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_panel.setAttribute(Qt.WA_TranslucentBackground, True)
        
        layout = QHBoxLayout(left_panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addStretch(1)
        
        # Контейнер контента
        content_container = QWidget()
        content_container.setObjectName("contentContainer")
        content_container.setFixedWidth(CONTENT_WIDTH)
        content_container.setFixedHeight(WINDOW_HEIGHT)
        content_container.setAttribute(Qt.WA_TranslucentBackground, True)
        
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(8)
        
        # Верхняя панель с кнопками
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        
        top_bar.addStretch(1)
        
        # Кнопка истории
        self.history_btn = QPushButton("📚 История")
        self.history_btn.setFixedHeight(30)
        self.history_btn.setToolTip("Показать историю вопросов и ответов")
        self.history_btn.clicked.connect(self._toggle_history_widget)
        self.history_btn.hide()
        top_bar.addWidget(self.history_btn)
        
        content_layout.addLayout(top_bar)
        
        # Поле ответа
        self.answer_field = QTextEdit()
        self.answer_field.setReadOnly(True)
        self.answer_field.hide()
        self.answer_field.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.answer_field.setAttribute(Qt.WA_TranslucentBackground, False)
        self.answer_field.setAutoFillBackground(True)
        self.answer_field.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        self.answer_field.viewport().installEventFilter(self)
        content_layout.addWidget(self.answer_field, stretch=1)
        
        # Поле ввода
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Спросите Хранителя о тайнах Word...")
        self.input_field.returnPressed.connect(self.on_question_submitted)
        self.input_field.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.input_field.setFixedHeight(45)
        self.input_field.setMinimumHeight(45)
        self.input_field.setMaximumHeight(45)
        self.input_field.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.input_field.setAttribute(Qt.WA_TranslucentBackground, False)
        self.input_field.setAutoFillBackground(True)
        self.input_field.hide()
        content_layout.addStretch()
        content_layout.addWidget(self.input_field)
        
        layout.addWidget(content_container)
        
        # ===== ВИДЖЕТ ИСТОРИИ С ФОНОМ =====
        self.history_container = QWidget()
        self.history_container.setObjectName("historyContainer")
        self.history_container.setFixedWidth(CONTENT_WIDTH)
        self.history_container.setFixedHeight(WINDOW_HEIGHT)
        self.history_container.hide()
        
        # Стиль для контейнера истории
        self.history_container.setStyleSheet(f"""
            #historyContainer {{
                background-color: {COLORS["background_history"]};
                border: 1px solid {COLORS["border_primary"]};
                border-radius: 8px;
            }}
        """)
        
        history_layout = QVBoxLayout(self.history_container)
        history_layout.setContentsMargins(5, 5, 5, 5)
        history_layout.setSpacing(5)
        
        # Верхняя панель для кнопки закрытия истории
        history_top_bar = QHBoxLayout()
        history_top_bar.setContentsMargins(0, 0, 0, 0)
        
        history_top_bar.addStretch(1)
        
        # Кнопка закрытия истории
        close_history_btn = QPushButton("✕ Закрыть историю")
        close_history_btn.setFixedHeight(30)
        close_history_btn.setToolTip("Закрыть историю")
        close_history_btn.clicked.connect(self._close_history_widget)
        history_top_bar.addWidget(close_history_btn)
        
        history_layout.addLayout(history_top_bar)
        
        # Виджет истории
        self.history_widget = HistoryWidget(self.history_plugin, self)
        history_layout.addWidget(self.history_widget)
        
        layout.addWidget(self.history_container)
        
        return left_panel
    
    def _create_right_panel(self) -> QWidget:
        """Создает правую панель с портретом Лешего."""
        right_panel = QWidget()
        right_panel.setObjectName("leshyPanel")
        right_panel.setFixedWidth(LESHY_PANEL_WIDTH)
        right_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        right_panel.setAttribute(Qt.WA_TranslucentBackground, True)
        
        layout = QVBoxLayout(right_panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.leshy_label = QLabel()
        self.leshy_label.setAlignment(Qt.AlignCenter)
        self.leshy_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.leshy_label.mousePressEvent = self.on_leshy_click
        self.leshy_label.setToolTip("Нажмите на Лешего, чтобы показать/скрыть поле ввода")
        layout.addWidget(self.leshy_label)
        
        return right_panel
    
    # ========== Системный трей ==========
    
    def setup_tray(self):
        """Создает иконку в системном трее."""
        try:
            self.tray_icon = QSystemTrayIcon(self)
            self.tray_icon.setIcon(QIcon())
            
            tray_menu = QMenu()
            
            show_action = QAction("Показать", self)
            show_action.triggered.connect(self.show_window)
            tray_menu.addAction(show_action)
            
            hide_action = QAction("Скрыть", self)
            hide_action.triggered.connect(self.hide_window)
            tray_menu.addAction(hide_action)
            
            tray_menu.addSeparator()
            
            exit_action = QAction("Выйти", self)
            exit_action.triggered.connect(self.safe_close)
            tray_menu.addAction(exit_action)
            
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.activated.connect(self.on_tray_activated)
            self.tray_icon.show()
        except:
            pass
    
    def show_window(self):
        """Показывает окно."""
        self.showNormal()
        self.raise_()
        self.activateWindow()
    
    def hide_window(self):
        """Скрывает окно."""
        self.hide()
    
    def on_tray_activated(self, reason):
        """Обработка клика по иконке в трее."""
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide_window()
            else:
                self.show_window()
    
    # ========== Обновление кадров ==========
    
    def _update_animation(self):
        """Обновляет анимацию Лешего."""
        if self._is_closing:
            return
        frame = self.animation_manager.update()
        if frame:
            self._update_leshy_frame(frame)
    
    def _update_typing(self):
        """Обновляет печать текста."""
        if self._is_closing:
            return
        
        if not self.state_machine.is_state(LeshyState.TALKING):
            return
        
        self._typing_counter += 1
        effective_interval = max(1, self._typing_interval // self._typing_speed_multiplier)
        
        if self._typing_counter < effective_interval:
            return
        
        self._typing_counter = 0
        
        if self.current_char_index < len(self.full_answer):
            if self.current_char_index >= self._loading_phrase_length + 2:
                self._current_format = self._main_format
            
            cursor = self.answer_field.textCursor()
            cursor.movePosition(cursor.End)
            cursor.insertText(self.full_answer[self.current_char_index], self._current_format)
            self.current_char_index += 1
            
            cursor = self.answer_field.textCursor()
            cursor.movePosition(cursor.End)
            self.answer_field.setTextCursor(cursor)
        else:
            self.state_machine.transition_to(LeshyState.ANSWER_VISIBLE)
    
    def _update_leshy_frame(self, pixmap: Optional[QPixmap] = None):
        """Обновляет отображение Лешего."""
        if self._is_closing:
            return
        if pixmap is None:
            pixmap = self.animation_manager.get_current_frame()
        if pixmap is not None:
            self.leshy_label.setPixmap(pixmap)
        else:
            self.leshy_label.setText("🌿\nХранитель")
            self.leshy_label.setStyleSheet("color: #8a7b66; font-size: 18px; padding: 20px;")
    
    # ========== Обработка событий ==========
    
    def eventFilter(self, obj, event):
        """Перехватывает события."""
        if obj is self.answer_field.viewport():
            if event.type() == QEvent.MouseButtonPress:
                now = time.time()
                
                if self.state_machine.is_state(LeshyState.ANSWER_VISIBLE):
                    if now - self._last_answer_click_time < 0.4:
                        self.hide_answer_field()
                        self._last_answer_click_time = 0
                        return True
                    else:
                        self._last_answer_click_time = now
                        return False
                
                if self.state_machine.is_state(LeshyState.TALKING):
                    self._typing_speed_multiplier = 3
                    if self.current_char_index < len(self.full_answer):
                        self._typing_interval = 1
                    return False
        return super().eventFilter(obj, event)
    
    def keyPressEvent(self, event: QKeyEvent):
        """Перехватывает нажатия клавиш."""
        if event.key() == Qt.Key_Escape:
            # Если история открыта - закрываем её
            if self.history_container and self.history_container.isVisible():
                self._close_history_widget()
                return
            
            # Если поле ввода активно - закрываем его
            if self.state_machine.is_state(LeshyState.INPUT):
                self.state_machine.transition_to(LeshyState.IDLE)
                return
            
            # Иначе считаем нажатия для выхода
            self.esc_counter += 1
            self.esc_reset_timer.start(1500)
            if self.esc_counter >= 3:
                self.safe_close()
        else:
            self.reset_esc_counter()
        super().keyPressEvent(event)
    
    def reset_esc_counter(self):
        """Сбрасывает счетчик Escape."""
        self.esc_counter = 0
        self.esc_reset_timer.stop()
    
    def changeEvent(self, event):
        """Реагирует на изменение состояния окна."""
        if event.type() == event.ActivationChange:
            if self._is_closing:
                return
            if self.isActiveWindow():
                self.setWindowOpacity(WINDOW_OPACITY_ACTIVE)
            else:
                self.setWindowOpacity(WINDOW_OPACITY_INACTIVE)
        super().changeEvent(event)
    
    def closeEvent(self, event):
        """Корректное закрытие окна."""
        self._is_closing = True
        self._idle_one_shot_timer.stop()
        self.game_loop.stop()
        self.esc_reset_timer.stop()
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
        event.accept()
    
    def safe_close(self):
        """Безопасное закрытие приложения."""
        self.close()
        QTimer.singleShot(100, QApplication.instance().quit)
    
    # ========== Основная логика ==========
    
    def on_leshy_click(self, event):
        """Обработка клика по Лешему."""
        if self._is_closing:
            return
        
        state = self.state_machine.get_state()
        
        # Если Леший говорит — ускоряем печать
        if state == LeshyState.TALKING:
            self._typing_speed_multiplier = 10
            return
        
        # Если ответ показан — скрываем его
        if state == LeshyState.ANSWER_VISIBLE:
            self.hide_answer_field()
            return
        
        # Переключаем поле ввода
        if state == LeshyState.IDLE:
            self.state_machine.transition_to(LeshyState.INPUT)
        elif state == LeshyState.INPUT:
            self.state_machine.transition_to(LeshyState.IDLE)
    
    def on_question_submitted(self):
        """Обработка отправки вопроса."""
        if self._is_closing:
            return
        
        user_question = self.input_field.text().strip()
        if not user_question:
            return
        
        if user_question.lower() in EXIT_PHRASES:
            self.safe_close()
            return
        
        # Скрываем поле ввода и переходим в THINKING
        self.input_field.clear()
        self.input_field.hide()
        self.state_machine.transition_to(LeshyState.THINKING)
        
        QTimer.singleShot(1500, lambda: self._process_question(user_question))
    
    def _process_question(self, user_question: str):
        """Обрабатывает вопрос (с проверкой пасхалок и перманентных скинов)."""
        if self._is_closing:
            return
        
        # === ПРОВЕРКА НА ПЕРМАНЕНТНУЮ СМЕНУ СКИНА ===
        question_lower = user_question.lower().strip()
        
        # Фразы для включения горничной
        maid_triggers = ["хочу горничную", "хочу maid", "стань горничной", "режим горничной"]
        if any(trigger in question_lower for trigger in maid_triggers):
            self._set_permanent_skin("maid")
            return
        
        # Фразы для возврата к лешему
        leshy_triggers = ["хочу лешего", "хочу леший", "стань лешим", "режим лешего", "верни лешего"]
        if any(trigger in question_lower for trigger in leshy_triggers):
            self._set_permanent_skin(None)
            return
        
        # === ПРОВЕРКА НА ВРЕМЕННУЮ ПАСХАЛКУ (СКИН) ===
        skin_name = self.animation_manager.check_skin_trigger(user_question)
        if skin_name and skin_name != self._current_skin:
            self._activate_easter_egg(skin_name, user_question)
            return
        
        # === ПРОВЕРКА НА "ПОЗДРАВЬ МЕНЯ" ===
        if self._check_congratulation_trigger(user_question):
            return
        
        # Стандартная обработка вопроса
        answer, is_fallback = self.wisdom.ask_question(user_question)
        self.full_answer += answer
        
        category = self._determine_category(user_question)
        self.history_plugin.add_entry(user_question, answer, category)
        self._show_history_button()
        
        if self.current_char_index >= self._loading_phrase_length + 2:
            self._current_format = self._main_format
        
        if is_fallback:
            self.animation_manager.play_forced("talking2", loop=True)
        else:
            self.animation_manager.play_forced("talking", loop=True)
        
        self.state_machine.transition_to(LeshyState.TALKING)


    def _set_permanent_skin(self, skin_name: Optional[str]):
        """
        Устанавливает скин перманентно (сохраняется в settings.json).
        Если skin_name=None — сбрасывает на стандартного Лешего.
        """
        if skin_name:
            print(f"💾 Устанавливаем перманентный скин: {skin_name}")
            success = self._apply_skin(skin_name)
            if success:
                self._settings["active_skin"] = skin_name
                self._settings["last_skin_change"] = datetime.now().isoformat()
                self._save_settings()
        else:
            print(f"🔄 Сбрасываем скин на стандартного Лешего")
            self.animation_manager.deactivate_skin()
            self._restore_default_colors()
            self._restore_default_data()
            self._current_skin = None
            
            self._settings["active_skin"] = None
            self._settings["last_skin_change"] = datetime.now().isoformat()
            self._save_settings()
            
            # Показываем сообщение о возврате
            self.answer_field.clear()
            self.answer_field.show()
            self.full_answer = "Ох-хо-хо! Вот я и вернулся в свой привычный облик лесного хранителя. Спрашивайте о Word и Excel!"
            self._loading_phrase = ""
            self._loading_phrase_length = 0
            self.current_char_index = 0
            self._typing_counter = 0
            self._current_format = self._main_format
            
            self.animation_manager.play_forced("talking", loop=True)
            self.state_machine.transition_to(LeshyState.TALKING)
            
    def _restore_default_colors(self):
        """Восстанавливает стандартную цветовую схему."""
        print("🎨 Восстанавливаем стандартные цвета")
        
        stylesheet = create_stylesheet(self.custom_font_family)
        self.setStyleSheet(stylesheet)
        self._update_text_formats(COLORS)
        
        if self.history_container:
            self.history_container.setStyleSheet(f"""
                #historyContainer {{
                    background-color: {COLORS["background_history"]};
                    border: 1px solid {COLORS["border_primary"]};
                    border-radius: 8px;
                }}
            """)

    def _check_congratulation_trigger(self, user_question: str) -> bool:
        """
        Проверяет, просит ли пользователь поздравить его.
        Использует данные из PERSONAL_DATES (config.py).
        Возвращает True если обработано как секретная фраза.
        """
        triggers = [
            "поздравь меня",
            "поздравь",
            "скажи поздравление",
            "поздравь с днём рождения",
            "поздравь с днем рождения",
            "хочу поздравление",
            "где моё поздравление",
            "скажи тост",
            "именинница",
            "у меня день рождения",
            "у меня др",
        ]
        
        question_lower = user_question.lower()
        
        # Проверяем, есть ли триггер в вопросе
        is_congratulation = any(trigger in question_lower for trigger in triggers)
        
        if not is_congratulation:
            return False
        
        # Получаем контекст и данные из конфига
        context = self.wisdom.get_context_info()
        personal_info = self._get_birthday_person_info()
        
        name = personal_info["name"]
        bday_day = personal_info["day"]
        bday_month = personal_info["month"]
        bday_month_name = personal_info["month_name"]
        emoji = personal_info["emoji"]
        
        # Определяем ответ в зависимости от контекста
        if context.get("is_birthday_today"):
            answers = self._get_birthday_today_answers(name, emoji)
        elif context.get("personal_event") == "birthday_soon":
            days = context.get("days_until_birthday", 0)
            answers = self._get_birthday_soon_answers(name, days, emoji)
        elif context.get("personal_event") == "birthday_just_passed":
            answers = self._get_birthday_passed_answers(name, emoji)
        else:
            answers = self._get_birthday_far_answers(name, bday_day, bday_month_name, emoji)
        
        import random
        answer = random.choice(answers)
        
        # Показываем ответ
        self._show_secret_answer(answer)
        return True


    def _get_birthday_person_info(self) -> dict:
        """
        Извлекает информацию об имениннике из PERSONAL_DATES.
        Возвращает словарь с ключами: name, day, month, month_name, emoji.
        """
        from config import PERSONAL_DATES
        import datetime
        
        # Ищем запись с типом "birthday"
        for date_str, info in PERSONAL_DATES.items():
            if info.get("type") == "birthday":
                day, month = map(int, date_str.split("."))
                
                # Русские названия месяцев
                month_names = [
                    "", "января", "февраля", "марта", "апреля", "мая", "июня",
                    "июля", "августа", "сентября", "октября", "ноября", "декабря"
                ]
                
                # Именительный падеж для других случаев
                month_names_nominative = [
                    "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
                ]
                
                return {
                    "name": info.get("name", "Хозяйка"),
                    "day": day,
                    "month": month,
                    "month_name": month_names[month] if 1 <= month <= 12 else "",
                    "month_nominative": month_names_nominative[month] if 1 <= month <= 12 else "",
                    "emoji": info.get("emoji", "🎂"),
                    "description": info.get("description", ""),
                }
        
        # Если ничего не нашли — значения по умолчанию
        return {
            "name": "Хозяйка",
            "day": 1,
            "month": 1,
            "month_name": "января",
            "month_nominative": "Январь",
            "emoji": "🎂",
            "description": "",
        }


    def _get_birthday_today_answers(self, name: str, emoji: str) -> list:
        """Генерирует поздравления на сегодняшний день рождения."""
        # Базовые фразы для любого скина
        answers = [
            f"С днём рождения, {name}! {emoji}\n"
            f"Лесные духи, кикиморы, белки и даже старый филин — все собрались, чтобы поздравить вас! "
            f"Пусть этот год будет полон волшебства, радости и ни одной сломанной таблицы в Excel! "
            f"Леший вас обожает и всегда готов прийти на помощь с документами!",
            
            f"Поздравляю от всей моей лесной души! {emoji}\n"
            f"Сегодня особенный день — день, когда лес стал светлее, потому что в нём появились вы! "
            f"Пусть Word всегда сохраняет ваши файлы, Excel считает без ошибок, "
            f"а жизнь будет прекрасной, как июльский рассвет! С днём рождения!",
            
            f"{name}! С днём рождения! {emoji}\n"
            f"Я, Хранитель Канцелярского Леса, торжественно объявляю этот день выходным от всех забот! "
            f"(Но если что — я всегда рядом с подсказками по Word и Excel). "
            f"Сияйте, радуйтесь и принимайте поздравления от всего леса!",
            
            f"Самый тёплый и душевный день в году! {emoji}\n"
            f"С днём рождения, {name}! Пусть сбудутся все мечты — даже те, "
            f"что вы шептали старому дубу на перемене. "
            f"А я прослежу, чтобы ни одна формула в Excel не подвела вас в новом году жизни!",
        ]
        
        # Если активен скин горничной — особые фразы
        if self.animation_manager.get_current_skin() == "maid":
            answers = [
                f"С днём рождения, госпожа {name}! {emoji}\n"
                f"Ваша горничная-хранительница докладывает: лесная усадьба готова к празднику! "
                f"Word исправен, Excel считает идеально, а я лично прослежу, "
                f"чтобы ни одна бумага не испортила ваш чудесный день! "
                f"Позвольте прислуживать вам и дальше — с документами и без!",
                
                f"Госпожа {name}! С днём рождения! {emoji}\n"
                f"Я подготовила для вас особый праздничный чай из лесных трав, "
                f"а все документы разложены по папочкам с бантиками! "
                f"Пусть ваш день будет идеальным — как вы сама! Ваша верная горничная-лешачка.",
            ]
        
        return answers


    def _get_birthday_soon_answers(self, name: str, days: int, emoji: str) -> list:
        """Генерирует ответы когда до дня рождения меньше недели."""
        if days == 1:
            answers = [
                f"Уже завтра! {emoji}\n"
                f"Леший суетится, белки наряжают дуб (праздничный, не срубленный!), "
                f"а кикиморы репетируют хоровод! Завтра — ваш день рождения, {name}, "
                f"и я уже готовлю особенное поздравление! Приходите завтра — скажу самое главное!",
            ]
        else:
            answers = [
                f"Ох-хо-хо! Ещё {days} дня — и будет ваш праздник, {name}! {emoji}\n"
                f"Я уже готовлю особенное поздравление, лесные духи выбирают лучшие грибы в подарок, "
                f"а белки считают дни вместе со мной. Потерпите чуть-чуть — "
                f"в ваш день рождения я скажу всё, что положено!",
                
                f"Подождите {days} дня, {name}! {emoji}\n"
                f"Самое главное поздравление — в день рождения! А пока — репетирую. "
                f"Лесные птицы разучивают праздничную трель, "
                f"а я оттачиваю каллиграфию для поздравительной открытки на бересте!",
            ]
        
        # Скин горничной
        if self.animation_manager.get_current_skin() == "maid":
            answers = [
                f"Госпожа {name}, осталось всего {days} дня! {emoji}\n"
                f"Я уже начищаю до блеска всё в усадьбе и готовлю праздничный сюрприз. "
                f"Потерпите чуть-чуть — в ваш день рождения всё будет идеально!",
            ]
        
        return answers


    def _get_birthday_passed_answers(self, name: str, emoji: str) -> list:
        """Генерирует ответы когда день рождения только прошёл."""
        answers = [
            f"Ваш день рождения только-только прошёл, {name}! {emoji}\n"
            f"Но я всё ещё принимаю поздравления для вас от опоздавших лесных жителей! "
            f"Ёжик вчера принёс запоздалую открытку — говорит, долго шёл. "
            f"С прошедшим! Пусть весь год будет таким же волшебным, как этот праздник!",
        ]
        
        if self.animation_manager.get_current_skin() == "maid":
            answers = [
                f"Госпожа {name}, ваш день рождения был так прекрасен! {emoji}\n"
                f"Я до сих пор прибираю конфетти из лепестков, но это приятные хлопоты. "
                f"С прошедшим праздником! Жду следующего года, чтобы снова вас радовать!",
            ]
        
        return answers


    def _get_birthday_far_answers(self, name: str, day: int, month_name: str, emoji: str) -> list:
        """Генерирует ответы когда день рождения ещё далеко."""
        import datetime
        
        now = datetime.datetime.now()
        bday = datetime.datetime(now.year, month_from_name(month_name), day)
        if bday < now:
            bday = datetime.datetime(now.year + 1, month_from_name(month_name), day)
        days_left = (bday - now).days
        months_left = days_left // 30
        
        # Текущий месяц в родительном падеже
        month_names_genitive = [
            "", "января", "февраля", "марта", "апреля", "мая", "июня",
            "июля", "августа", "сентября", "октября", "ноября", "декабря"
        ]
        current_month_name = month_names_genitive[now.month] if 1 <= now.month <= 12 else ""
        
        if months_left >= 6:
            answers = [
                f"Рано, {name}, рано! {emoji}\n"
                f"До вашего дня рождения ещё {days_left} дней (это больше полугода!). "
                f"Леший, конечно, может поздравить и сейчас, но настоящее волшебство случится {day} {month_name}! "
                f"Приходите тогда — я скажу самые главные слова!",
                
                f"Ох, нетерпеливая вы моя, {name}! {emoji}\n"
                f"День рождения — {day} {month_name}, а сейчас только {current_month_name}. "
                f"Подождите до лета — тогда я устрою вам настоящее лесное поздравление "
                f"с хороводами и фейерверками из светлячков!",
            ]
        else:
            answers = [
                f"Уже скоро, но ещё не время, {name}! {emoji}\n"
                f"До {day} {month_name} осталось {days_left} дней. "
                f"Леший уже начинает подготовку: белки запасают конфетти из лепестков, "
                f"а я репетирую поздравительную речь. Но главные слова — в ваш день рождения!",
                
                f"Терпение, {name}! {emoji}\n"
                f"Ваш день рождения — {day} {month_name}. Ещё {days_left} дней — "
                f"и я скажу вам всё, что думаю о вас (спойлер: только хорошее!). "
                f"А пока — спрашивайте о Word и Excel!",
            ]
        
        # Скин горничной
        if self.animation_manager.get_current_skin() == "maid":
            if months_left >= 6:
                answers = [
                    f"Госпожа {name}, до вашего праздника ещё далеко! {emoji}\n"
                    f"День рождения — {day} {month_name}. Я уже начала подготовку: "
                    f"заказала новые бантики для документов и особый сорт чая. "
                    f"Но главное торжество — в ваш день! А пока я к вашим услугам с Word и Excel.",
                ]
            else:
                answers = [
                    f"Госпожа {name}, обратный отсчёт пошёл! {emoji}\n"
                    f"До {day} {month_name} — {days_left} дней. "
                    f"Я уже выбрала скатерть и polishing серебро. "
                    f"Ваш день рождения будет идеальным, обещаю!",
                ]
        
        return answers


    def month_from_name(month_name: str) -> int:
        """Конвертирует название месяца (родительный падеж) в номер."""
        mapping = {
            "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
            "мая": 5, "июня": 6, "июля": 7, "августа": 8,
            "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12
        }
        return mapping.get(month_name.lower(), 1)


    def hide_answer_field(self):
        """Скрывает поле ответа."""
        if self._is_closing:
            return
        if self.state_machine.is_state(LeshyState.ANSWER_VISIBLE):
            self.answer_field.hide()
            self.state_machine.transition_to(LeshyState.IDLE)
    
    def style_dialog(self, dialog):
        """Применяет темную тему к диалоговому окну."""
        from PyQt5.QtWidgets import QGraphicsDropShadowEffect
        stylesheet = create_stylesheet(self.custom_font_family)
        dialog.setStyleSheet(stylesheet)
        
        # Делаем фон прозрачным для диалога
        dialog.setAttribute(Qt.WA_TranslucentBackground, True)
        
        # Добавляем тень
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 4)
        dialog.setGraphicsEffect(shadow)
        
        return dialog
    
    # Для совместимости с history_widget.py (там вызывается _style_dialog)
    def _style_dialog(self, dialog):
        """Применяет темную тему к диалоговому окну (алиас для style_dialog)."""
        return self.style_dialog(dialog)

    # ========== Управление историей ==========

    def _toggle_history_widget(self):
        """Показывает/скрывает виджет истории."""
        if self.history_container.isVisible():
            self._close_history_widget()
        else:
            self._show_history_widget()

    def _show_history_widget(self):
        """Показывает виджет истории."""
        if self.history_widget is None:
            self.history_widget = HistoryWidget(self.history_plugin, self)
        
        # Сохраняем состояние полей
        self._input_was_visible = self.input_field.isVisible()
        self._answer_was_visible = self.answer_field.isVisible()
        
        # Скрываем поля ввода и вывода
        self.input_field.hide()
        self.answer_field.hide()
        
        # Скрываем кнопку истории
        self.history_btn.hide()
        
        # Показываем контейнер истории
        self.history_container.show()
        
        # Переходим в состояние HISTORY (запустит анимацию lib)
        self.state_machine.transition_to(LeshyState.HISTORY)
        
        # Обновляем список
        if self.history_widget:
            self.history_widget._update_list()

    def _close_history_widget(self):
        """Скрывает виджет истории."""
        self.history_container.hide()
        
        # Восстанавливаем поля, которые были видны
        if hasattr(self, '_input_was_visible') and self._input_was_visible:
            self.input_field.show()
            if self.history_plugin.get_size() > 0:
                self.history_btn.show()
        
        if hasattr(self, '_answer_was_visible') and self._answer_was_visible:
            self.answer_field.show()
        
        # Показываем кнопку истории обратно (если есть записи)
        if self.history_plugin.get_size() > 0:
            self.history_btn.show()
        else:
            self.history_btn.hide()
        
        # Возвращаемся в IDLE (автоматически запустит idle и запланирует one-shot)
        if self.state_machine.is_state(LeshyState.HISTORY):
            self.state_machine.transition_to(LeshyState.IDLE)
        elif not self.state_machine.is_state(LeshyState.IDLE):
            self.state_machine.transition_to(LeshyState.IDLE)
    
    # ========== ПАСХАЛКИ ==========
    
    def _activate_easter_egg(self, skin_name: str, trigger_text: str):
        """Активирует ВРЕМЕННУЮ пасхалку (скин) — не сохраняется после перезапуска."""
        print(f"🥚 Временная пасхалка! Триггер: '{trigger_text}' → скин: '{skin_name}'")
        
        success = self._apply_skin(skin_name)
        
        if not success:
            self._process_question_normal(trigger_text)
            return
        
        # Сохраняем в историю
        category = "easter_egg"
        easter_egg_responses = {
            "maid": [
                "Ох-хо-хо! Кажется, я сегодня в особенном настроении... ✨\nДобро пожаловать, хозяйка! Чем могу служить в канцелярском лесу?",
            ],
        }
        
        if skin_name in easter_egg_responses:
            answer = random.choice(easter_egg_responses[skin_name])
        else:
            answer = f"✨ Пасхалка '{skin_name}' активирована!"
        
        self.history_plugin.add_entry(trigger_text, answer, category)
        self._show_history_button()

    def _update_text_formats(self, colors: dict):
        """Обновляет форматы текста при смене цветовой схемы."""
        self._loading_format = QTextCharFormat()
        self._loading_format.setForeground(QColor(colors["accent_loading"]))
        self._loading_format.setFontItalic(True)
        
        self._main_format = QTextCharFormat()
        self._main_format.setForeground(QColor(colors["text_primary"]))
        self._main_format.setFontItalic(False)
        
        # Обновляем текущий формат, если он был main
        if self._current_format != self._loading_format:
            self._current_format = self._main_format

    def _show_secret_answer(self, answer: str):
        """Показывает секретный ответ (без сохранения в историю)."""
        self.answer_field.clear()
        self.answer_field.show()
        self.full_answer = answer
        self._loading_phrase = ""
        self._loading_phrase_length = 0
        self.current_char_index = 0
        self._typing_counter = 0
        self._typing_speed_multiplier = 1
        self._typing_interval = 2
        self._current_format = self._main_format
        
        self.animation_manager.play_forced("talking", loop=True)
        self.state_machine.transition_to(LeshyState.TALKING)

    def _process_question_normal(self, user_question: str):
        """Обычная обработка вопроса (используется как fallback)."""
        answer, is_fallback = self.wisdom.ask_question(user_question)
        self.full_answer += answer
        
        category = self._determine_category(user_question)
        self.history_plugin.add_entry(user_question, answer, category)
        self._show_history_button()
        
        if self.current_char_index >= self._loading_phrase_length + 2:
            self._current_format = self._main_format
        
        if is_fallback:
            self.animation_manager.play_forced("talking2", loop=True)
        else:
            self.animation_manager.play_forced("talking", loop=True)
        
        self.state_machine.transition_to(LeshyState.TALKING)

    def _load_settings(self) -> dict:
        """Загружает настройки из JSON. Работает и в .exe, и в исходниках."""
        import sys
        from pathlib import Path
        
        if getattr(sys, 'frozen', False):
            # В .exe: настройки хранятся рядом с .exe
            settings_path = Path(sys.executable).parent / "settings.json"
        else:
            # В исходниках: core/settings.json
            settings_path = Path(__file__).parent.parent / "core" / "settings.json"
        
        self._settings_path = settings_path  # Обновляем путь
        
        if not settings_path.exists():
            return {"active_skin": None, "last_skin_change": None}
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Ошибка загрузки настроек: {e}")
            return {"active_skin": None, "last_skin_change": None}


    def _save_settings(self):
        """Сохраняет настройки в JSON."""
        try:
            self._settings_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._settings_path, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, ensure_ascii=False, indent=2)
            print(f"✅ Настройки сохранены: {self._settings_path}")
        except Exception as e:
            print(f"❌ Ошибка сохранения настроек: {e}")
    
    def _apply_skin(self, skin_name: str, silent: bool = False):
        """
        Применяет скин (анимации + цвета + данные).
        Если silent=True — не показывать приветственное сообщение.
        """
        # Активируем скин анимации
        success = self.animation_manager.activate_skin(skin_name)
        if not success:
            print(f"❌ Не удалось активировать скин: {skin_name}")
            return False
        
        # Применяем цветовую схему
        skin_colors = self.animation_manager.get_skin_colors(skin_name)
        if skin_colors:
            stylesheet = create_stylesheet(self.custom_font_family, skin_colors)
            self.setStyleSheet(stylesheet)
            self._update_text_formats(skin_colors)
            
            if self.history_container:
                self.history_container.setStyleSheet(f"""
                    #historyContainer {{
                        background-color: {skin_colors["background_history"]};
                        border: 1px solid {skin_colors["border_primary"]};
                        border-radius: 8px;
                    }}
                """)
        
        # Подгружаем данные скина (базу знаний, фразы)
        self._load_skin_data(skin_name)
        
        if not silent:
            # Показываем приветственное сообщение
            self._show_skin_greeting(skin_name)
        
        self._current_skin = skin_name
        return True
    
    def _get_base_path(self) -> Path:
        """Возвращает базовый путь (работает и в .exe, и в исходниках)."""
        import sys
        from pathlib import Path
        
        if getattr(sys, 'frozen', False):
            return Path(sys._MEIPASS)
        else:
            return Path(__file__).parent.parent

    def _load_skin_data(self, skin_name: str):
        """
        Загружает альтернативные данные для скина:
        - core/{skin}/knowledge_base.json
        - core/{skin}/fallback_answers.json
        - core/{skin}/loading_phrases.json
        Если файл не найден — используются стандартные.
        """
        import sys
        
        if getattr(sys, 'frozen', False):
            base = Path(sys._MEIPASS)
        else:
            base = Path(__file__).parent.parent
        
        skin_dir = base / "core" / skin_name
        
        if not skin_dir.exists():
            print(f"ℹ️ Директория скина не найдена: {skin_dir} (используются стандартные данные)")
            return
        
        print(f"📂 Загружаем данные скина из: {skin_dir}")
        
        # Подменяем knowledge_base
        kb_path = skin_dir / "knowledge_base.json"
        if kb_path.exists():
            self.wisdom.knowledge_base_path = kb_path
            self.wisdom.load_knowledge()
            print(f"   ✓ knowledge_base.json ({len(self.wisdom.knowledge_base)} записей)")
        
        # Подменяем fallback_answers
        fa_path = skin_dir / "fallback_answers.json"
        if fa_path.exists():
            try:
                with open(fa_path, 'r', encoding='utf-8') as f:
                    self.wisdom._fallback_cache = json.load(f)
                print(f"   ✓ fallback_answers.json")
            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
        
        # Подменяем loading_phrases
        lp_path = skin_dir / "loading_phrases.json"
        if lp_path.exists():
            try:
                with open(lp_path, 'r', encoding='utf-8') as f:
                    self.wisdom._loading_cache = json.load(f)
                print(f"   ✓ loading_phrases.json")
            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
    
    def _restore_default_data(self):
        """Восстанавливает стандартные данные (без скина)."""
        import sys
        
        if getattr(sys, 'frozen', False):
            base = Path(sys._MEIPASS)
        else:
            base = Path(__file__).parent.parent
        
        core_dir = base / "core"
        
        # Восстанавливаем knowledge_base
        kb_path = core_dir / "knowledge_base.json"
        if kb_path.exists():
            self.wisdom.knowledge_base_path = kb_path
            self.wisdom.load_knowledge()
        
        # Восстанавливаем fallback_answers
        fa_path = core_dir / "fallback_answers.json"
        if fa_path.exists():
            try:
                with open(fa_path, 'r', encoding='utf-8') as f:
                    self.wisdom._fallback_cache = json.load(f)
            except Exception as e:
                print(f"❌ Ошибка восстановления fallback: {e}")
        
        # Восстанавливаем loading_phrases
        lp_path = core_dir / "loading_phrases.json"
        if lp_path.exists():
            try:
                with open(lp_path, 'r', encoding='utf-8') as f:
                    self.wisdom._loading_cache = json.load(f)
            except Exception as e:
                print(f"❌ Ошибка восстановления loading: {e}")
    
    def _show_skin_greeting(self, skin_name: str):
        """Показывает приветственное сообщение при смене скина."""
        greetings = {
            "maid": [
                "Ох-хо-хо! Кажется, я сегодня в особенном настроении... ✨\nДобро пожаловать, хозяйка! Чем могу служить в канцелярском лесу?",
                "Слушаюсь, хозяйка! Ваша горничная-хранительница к вашим услугам. Спрашивайте о Word и Excel!",
                "Ох! Вы нашли мою тайную форму. Что ж, теперь я ваша лесная помощница. Чем могу помочь с документами?",
            ],
        }
        
        if skin_name in greetings:
            answer = random.choice(greetings[skin_name])
        else:
            answer = f"✨ Скин '{skin_name}' активирован! Спрашивайте о Word и Excel!"
        
        self.answer_field.clear()
        self.answer_field.show()
        self.full_answer = answer
        self._loading_phrase = ""
        self._loading_phrase_length = 0
        self.current_char_index = 0
        self._typing_counter = 0
        self._current_format = self._main_format
        
        self.animation_manager.play_forced("talking", loop=True)
        self.state_machine.transition_to(LeshyState.TALKING)
        
    # ========== Заглушки для будущих функций ==========
    
    def start_voice_input(self):
        pass
    
    def show_context_menu(self, position: QPoint):
        pass
    
    def enable_kiosk_mode(self):
        pass
    
    def update_weather_and_time(self):
        pass