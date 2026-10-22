# gui/plugins/history_widget.py
"""
Виджет для отображения и управления историей.
Интегрируется в основное окно.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QListWidget, QListWidgetItem, QLabel, QLineEdit,
                             QComboBox, QTextEdit, QSplitter, QMessageBox,
                             QFileDialog, QMenu, QAction, QApplication)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor

from .history import HistoryPlugin


class HistoryWidget(QWidget):
    """
    Виджет для отображения и управления историей.
    """
    
    history_item_selected = pyqtSignal(dict)
    
    def __init__(self, history_plugin: HistoryPlugin, parent=None):
        super().__init__(parent)
        self.history = history_plugin
        self.parent_window = parent
        self.current_filter = None
        self._is_updating = False  # Флаг для предотвращения рекурсии
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._apply_search)
        
        self._init_ui()
        self._connect_signals()
        self._update_list()
    
    def _init_ui(self):
        """Создает интерфейс виджета."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Верхняя панель с инструментами
        toolbar = QHBoxLayout()
        
        # Поиск
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Поиск по истории...")
        self.search_input.textChanged.connect(self._on_search_changed)
        toolbar.addWidget(self.search_input)
        
        # Фильтр по категориям
        self.category_filter = QComboBox()
        self.category_filter.addItem("Все категории")
        self.category_filter.currentTextChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self.category_filter)
        
        # Кнопки управления
        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setFixedWidth(30)
        self.refresh_btn.setToolTip("Обновить список")
        self.refresh_btn.clicked.connect(self._update_list)
        toolbar.addWidget(self.refresh_btn)
        
        self.clear_btn = QPushButton("🗑️")
        self.clear_btn.setFixedWidth(30)
        self.clear_btn.setToolTip("Очистить историю")
        self.clear_btn.clicked.connect(self._clear_history)
        toolbar.addWidget(self.clear_btn)
        
        self.export_btn = QPushButton("📤")
        self.export_btn.setFixedWidth(30)
        self.export_btn.setToolTip("Экспортировать историю")
        self.export_btn.clicked.connect(self._export_history)
        toolbar.addWidget(self.export_btn)
        
        layout.addLayout(toolbar)
        
        # Разделитель (список + детали)
        splitter = QSplitter(Qt.Horizontal)
        
        # Список записей
        self.history_list = QListWidget()
        self.history_list.setMinimumWidth(300)
        self.history_list.itemClicked.connect(self._on_item_clicked)
        self.history_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history_list.customContextMenuRequested.connect(self._show_context_menu)
        splitter.addWidget(self.history_list)
        
        # Детали выбранной записи
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(5, 0, 5, 0)
        
        # Заголовок с информацией о записи
        self.entry_info = QLabel("Выберите запись для просмотра")
        self.entry_info.setStyleSheet("color: #8a7b66; font-size: 14px;")
        details_layout.addWidget(self.entry_info)
        
        # # Текст вопроса
        # self.question_display = QTextEdit()
        # self.question_display.setReadOnly(True)
        # self.question_display.setMaximumHeight(80)
        # self.question_display.setPlaceholderText("Вопрос...")
        # details_layout.addWidget(QLabel("❓ Вопрос:"))
        # details_layout.addWidget(self.question_display)
        
        # Текст ответа
        self.answer_display = QTextEdit()
        self.answer_display.setReadOnly(True)
        self.answer_display.setPlaceholderText("💬 Ответ...")
        self.answer_display.setStyleSheet("font-size: 18px;")
        # details_layout.addWidget(QLabel("💬 Ответ:"))
        details_layout.addWidget(self.answer_display)
        
        # Кнопка для копирования ответа
        copy_btn = QPushButton("📋 Копировать ответ")
        copy_btn.clicked.connect(self._copy_answer)
        details_layout.addWidget(copy_btn)
        
        splitter.addWidget(details_widget)
        splitter.setSizes([400, 600])
        
        layout.addWidget(splitter)
        
        # Статистика внизу
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #8a7b66; font-size: 12px;")
        layout.addWidget(self.stats_label)
        
        # Применяем стили
        self.setStyleSheet("""
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #2a1f0f;
            }
            QListWidget::item:selected {
                background-color: #1a4d3e;
                color: #e0f0e8;
            }
            QListWidget::item:hover {
                background-color: #2a3f2f;
            }
        """)
    
    def _connect_signals(self):
        """Подключает сигналы плагина истории."""
        # Используем Qt.QueuedConnection чтобы избежать рекурсии
        self.history.history_changed.connect(self._on_history_changed, Qt.QueuedConnection)
        self.history.history_cleared.connect(self._on_cleared, Qt.QueuedConnection)
        self.history.entry_added.connect(self._on_entry_added, Qt.QueuedConnection)
    
    def _on_history_changed(self):
        """Обработчик изменения истории."""
        # Не обновляем, если мы уже обновляемся
        if not self._is_updating:
            self._update_list()
    
    def _update_list(self):
        """Обновляет список записей."""
        if self._is_updating:
            return
        
        self._is_updating = True
        
        try:
            self.history_list.clear()
            
            entries = self.history.get_history()
            
            # Применяем фильтр
            if self.current_filter and self.current_filter != "Все категории":
                entries = [e for e in entries if e.get("category") == self.current_filter]
            
            # Применяем поиск
            search_text = self.search_input.text().strip()
            if search_text:
                entries = self.history.search_history(search_text)
            
            # Добавляем записи в список
            for entry in reversed(entries):  # Новые сверху
                question = entry.get("question", "")
                date = entry.get("date", "")
                time = entry.get("time", "")
                category = entry.get("category", "general")
                
                # Создаем элемент списка с информацией
                text = f"{date} {time} - {question[:50]}..."
                if len(question) > 50:
                    text += "..."
                
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, entry)
                item.setToolTip(f"Категория: {category}\n{question}")
                
                # Цвет для разных категорий
                if category == "word":
                    item.setForeground(QColor(144, 238, 144))
                elif category == "excel":
                    item.setForeground(QColor(100, 149, 237))
                elif category == "general":
                    item.setForeground(QColor(240, 230, 140))
                
                self.history_list.addItem(item)
            
            # Обновляем статистику
            self._update_stats()
            
            # Обновляем список категорий
            self._update_categories()
            
        except Exception as e:
            print(f"Ошибка при обновлении списка: {e}")
        finally:
            self._is_updating = False
    
    def _update_stats(self):
        """Обновляет отображение статистики."""
        try:
            stats = self.history.get_statistics()
            
            categories_str = ", ".join([f"{k}: {v}" for k, v in stats["categories"].items()])
            if not categories_str:
                categories_str = "нет"
            
            self.stats_label.setText(
                f"📊 Всего: {stats['total']} | "
                f"Категории: {categories_str} | "
                f"Сегодня: {stats['today']} | "
                f"За неделю: {stats['last_week']} | "
                f"Средняя длина: {stats['average_length']} симв."
            )
        except Exception as e:
            print(f"Ошибка обновления статистики: {e}")
    
    def _update_categories(self):
        """Обновляет список категорий в фильтре."""
        try:
            current_text = self.category_filter.currentText()
            self.category_filter.blockSignals(True)  # Блокируем сигналы
            
            self.category_filter.clear()
            categories = self.history.get_categories()
            self.category_filter.addItem("Все категории")
            self.category_filter.addItems(categories)
            
            # Восстанавливаем выбранную категорию
            index = self.category_filter.findText(current_text)
            if index >= 0:
                self.category_filter.setCurrentIndex(index)
                
        except Exception as e:
            print(f"Ошибка обновления категорий: {e}")
        finally:
            self.category_filter.blockSignals(False)
    
    def _on_item_clicked(self, item):
        """Обработка клика по элементу списка."""
        entry = item.data(Qt.UserRole)
        if entry:
            self._display_entry(entry)
            self.history_item_selected.emit(entry)
    
    def _display_entry(self, entry: dict):
        """Отображает запись в панели деталей."""
        question = entry.get("question", "")
        answer = entry.get("answer", "")
        date = entry.get("date", "")
        time = entry.get("time", "")
        category = entry.get("category", "general")
        entry_id = entry.get("id", "?")
        
        self.entry_info.setText(
            f"📝 Запись #{entry_id} | {date} {time} | 🏷️ {category}"
        )
        # self.question_display.setText(question)
        self.answer_display.setText(answer)
    
    def _on_search_changed(self, text):
        """Обработка изменения текста поиска."""
        self.search_timer.start(300)
    
    def _apply_search(self):
        """Применяет поиск к списку."""
        self._update_list()
    
    def _on_filter_changed(self, category):
        """Обработка изменения фильтра категорий."""
        self.current_filter = category
        self._update_list()
    
    def _clear_history(self):
        """Очищает историю с подтверждением."""
        if not self.history.get_size():
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Информация")
            msg_box.setText("История уже пуста!")
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setStandardButtons(QMessageBox.Ok)
            # Применяем стили
            if self.parent_window and hasattr(self.parent_window, '_style_dialog'):
                self.parent_window._style_dialog(msg_box)
            msg_box.exec_()
            return
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Подтверждение")
        msg_box.setText("Вы уверены, что хотите очистить всю историю?")
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        
        # Применяем стили
        if self.parent_window and hasattr(self.parent_window, '_style_dialog'):
            self.parent_window._style_dialog(msg_box)
        
        reply = msg_box.exec_()
        
        if reply == QMessageBox.Yes:
            self.history.clear_history()
            msg_box2 = QMessageBox(self)
            msg_box2.setWindowTitle("Успех")
            msg_box2.setText("История очищена!")
            msg_box2.setIcon(QMessageBox.Information)
            msg_box2.setStandardButtons(QMessageBox.Ok)
            if self.parent_window and hasattr(self.parent_window, '_style_dialog'):
                self.parent_window._style_dialog(msg_box2)
            msg_box2.exec_()

# gui/plugins/history_widget.py (обновленный метод _export_history)

    def _export_history(self):
        """Экспортирует историю."""
        if not self.history.get_size():
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Информация")
            msg_box.setText("Нет данных для экспорта!")
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setStandardButtons(QMessageBox.Ok)
            if self.parent_window and hasattr(self.parent_window, '_style_dialog'):
                self.parent_window._style_dialog(msg_box)
            msg_box.exec_()
            return
        
        # Спрашиваем формат экспорта
        formats = ["Текстовый файл (.txt)", "CSV файл (.csv)"]
        
        # Создаем кастомный диалог для выбора
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QComboBox, QPushButton, QHBoxLayout, QLabel
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Экспорт истории")
        dialog.setFixedSize(350, 150)
        
        if self.parent_window and hasattr(self.parent_window, '_style_dialog'):
            self.parent_window._style_dialog(dialog)
        
        layout = QVBoxLayout(dialog)
        
        label = QLabel("Выберите формат экспорта:")
        layout.addWidget(label)
        
        combo = QComboBox()
        combo.addItems(formats)
        layout.addWidget(combo)
        
        buttons_layout = QHBoxLayout()
        ok_btn = QPushButton("Экспортировать")
        cancel_btn = QPushButton("Отмена")
        
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        buttons_layout.addWidget(ok_btn)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)
        
        if dialog.exec_() != QDialog.Accepted:
            return
        
        format_item = combo.currentText()
        
        # Выбираем файл для сохранения
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if "CSV" in format_item:
            ext = ".csv"
            filter_str = "CSV файлы (*.csv)"
        else:
            ext = ".txt"
            filter_str = "Текстовые файлы (*.txt)"
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить историю",
            f"leshy_history_{timestamp}{ext}",
            filter_str
        )
        
        if not filename:
            return
        
        # Экспортируем
        if ext == ".csv":
            success = self.history.export_to_csv(filename)
        else:
            success = self.history.export_to_text(filename)
        
        if success:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Успех")
            msg_box.setText(f"История экспортирована в:\n{filename}")
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setStandardButtons(QMessageBox.Ok)
            if self.parent_window and hasattr(self.parent_window, '_style_dialog'):
                self.parent_window._style_dialog(msg_box)
            msg_box.exec_()

# gui/plugins/history_widget.py (обновленный метод _show_context_menu)

    def _show_context_menu(self, position):
        """Показывает контекстное меню для списка."""
        item = self.history_list.itemAt(position)
        if not item:
            return
        
        entry = item.data(Qt.UserRole)
        if not entry:
            return
        
        menu = QMenu(self)
        
        # Применяем стили к меню
        if self.parent_window and hasattr(self.parent_window, 'custom_font_family'):
            from ..styles import create_stylesheet
            stylesheet = create_stylesheet(self.parent_window.custom_font_family)
            menu.setStyleSheet(stylesheet)
        
        # Действия
        copy_action = QAction("📋 Копировать ответ", self)
        copy_action.triggered.connect(lambda: self._copy_answer(entry))
        menu.addAction(copy_action)
        
        # copy_q_action = QAction("📋 Копировать вопрос", self)
        # copy_q_action.triggered.connect(lambda: self._copy_question(entry))
        # menu.addAction(copy_q_action)
        
        menu.addSeparator()
        
        delete_action = QAction("🗑️ Удалить запись", self)
        delete_action.triggered.connect(lambda: self._delete_entry(entry))
        menu.addAction(delete_action)
        
        menu.exec_(self.history_list.mapToGlobal(position))
    
    def _copy_answer(self, entry: dict = None):
        """Копирует ответ в буфер обмена."""
        if entry is None:
            current = self.history_list.currentItem()
            if current:
                entry = current.data(Qt.UserRole)
        
        if entry:
            answer = entry.get("answer", "")
            clipboard = QApplication.clipboard()
            clipboard.setText(answer)
            
            # Визуальная обратная связь
            self.answer_display.setStyleSheet("background-color: #1a4d3e;")
            QTimer.singleShot(300, lambda: self.answer_display.setStyleSheet(""))
    
    def _copy_question(self, entry: dict = None):
        """Копирует вопрос в буфер обмена."""
        if entry is None:
            current = self.history_list.currentItem()
            if current:
                entry = current.data(Qt.UserRole)
        
        if entry:
            question = entry.get("question", "")
            clipboard = QApplication.clipboard()
            clipboard.setText(question)
    
    def _delete_entry(self, entry: dict):
        """Удаляет запись из истории."""
        entry_id = entry.get("id")
        if entry_id is None:
            return
        
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить запись?\n\nВопрос: {entry.get('question', '')[:100]}...",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.history.remove_entry(entry_id):
                self._update_list()
    
    def _on_cleared(self):
        """Обработка очистки истории."""
        # self.question_display.clear()
        self.answer_display.clear()
        self.entry_info.setText("История очищена")
        self._update_list()
    
    def _on_entry_added(self, entry):
        """Обработка добавления новой записи."""
        if self.isVisible() and not self._is_updating:
            self._update_list()
    
    def showEvent(self, event):
        """При показе виджета обновляем данные."""
        self._update_list()
        super().showEvent(event)