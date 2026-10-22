# gui/styles.py (обновлённый)

from config import COLORS

def create_stylesheet(font_family: str = None, override_colors: dict = None) -> str:
    """
    Создает CSS-стили для всех виджетов.
    
    Args:
        font_family: название шрифта
        override_colors: словарь с переопределением цветов (для скинов)
    """
    # Если переданы цвета скина — используем их, иначе стандартные
    c = override_colors if override_colors else COLORS
    
    if font_family:
        main_font = f'"{font_family}", Georgia, "Times New Roman", serif'
    else:
        main_font = 'Georgia, "Times New Roman", serif'
    
    return f"""
    QWidget {{
        color: {c["text_secondary"]};
        font-family: {main_font};
    }}

    #leftPanel {{
        background-color: transparent;
    }}

    #contentContainer {{
        background-color: transparent;
    }}

    #leshyPanel {{
        background-color: transparent;
    }}

    QLineEdit {{
        background-color: {c["background_input"]};
        border: 1px solid {c["border_primary"]};
        border-radius: 10px;
        padding: 10px 14px;
        font-size: 22px;
        color: {c["text_primary"]};
        font-family: {main_font};
        selection-background-color: {c["background_selected"]};
        selection-color: {c["text_selected"]};
    }}

    QLineEdit:focus {{
        border: 1px solid {c["border_focus"]};
    }}

    QTextEdit {{
        background-color: {c["background_input"]};
        border: 1px solid {c["border_primary"]};
        border-radius: 0px;
        padding: 14px;
        font-size: 22px;
        line-height: 1.6;
        color: {c["text_primary"]};
        font-family: {main_font};
        selection-background-color: {c["background_selected"]};
        selection-color: {c["text_selected"]};
    }}

    QPushButton {{
        background-color: {c["background_tertiary"]};
        border: 1px solid {c["border_primary"]};
        border-radius: 8px;
        padding: 5px 12px;
        color: {c["text_secondary"]};
        font-family: {main_font};
        font-size: 14px;
    }}

    QPushButton:hover {{
        background-color: {c["background_hover"]};
        border: 1px solid {c["border_hover"]};
    }}

    QPushButton:pressed {{
        background-color: {c["background_selected"]};
        border: 1px solid {c["border_focus"]};
        color: {c["text_selected"]};
    }}

    QPushButton:disabled {{
        background-color: {c["background_secondary"]};
        color: {c["text_disabled"]};
        border: 1px solid {c["border_disabled"]};
    }}

    /* ===== КОНТЕКСТНЫЕ МЕНЮ ===== */
    QMenu {{
        background-color: {c["background_menu"]};
        border: 1px solid {c["border_primary"]};
        border-radius: 8px;
        padding: 5px 0px;
        color: {c["text_secondary"]};
        font-family: {main_font};
        font-size: 14px;
    }}

    QMenu::item {{
        padding: 5px 30px 5px 25px;
        border-radius: 4px;
        margin: 2px 5px;
    }}

    QMenu::item:selected {{
        background-color: {c["background_selected"]};
        color: {c["text_selected"]};
    }}

    QMenu::item:disabled {{
        color: {c["text_disabled"]};
    }}

    QMenu::separator {{
        height: 1px;
        background-color: {c["border_separator"]};
        margin: 4px 10px;
    }}

    QMenu::icon {{
        padding-left: 5px;
    }}

    /* ===== ПОДСКАЗКИ ===== */
    QToolTip {{
        background-color: {c["background_menu"]};
        border: 1px solid {c["border_primary"]};
        border-radius: 6px;
        padding: 8px 12px;
        color: {c["text_secondary"]};
        font-family: {main_font};
        font-size: 12px;
    }}

    /* ===== ВЫПАДАЮЩИЕ СПИСКИ ===== */
    QComboBox {{
        background-color: {c["background_input"]};
        border: 1px solid {c["border_primary"]};
        border-radius: 8px;
        padding: 5px 10px;
        color: {c["text_secondary"]};
        font-family: {main_font};
        font-size: 14px;
        min-height: 25px;
    }}

    QComboBox:hover {{
        border: 1px solid {c["border_hover"]};
    }}

    QComboBox:on {{
        border: 1px solid {c["border_focus"]};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}

    QComboBox::down-arrow {{
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 5px solid {c["border_hover"]};
        margin-right: 5px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {c["background_menu"]};
        border: 1px solid {c["border_primary"]};
        border-radius: 8px;
        padding: 5px;
        color: {c["text_secondary"]};
        selection-background-color: {c["background_selected"]};
        selection-color: {c["text_selected"]};
        font-family: {main_font};
        font-size: 14px;
    }}

    QComboBox QAbstractItemView::item {{
        padding: 5px 10px;
        border-radius: 4px;
    }}

    QComboBox QAbstractItemView::item:hover {{
        background-color: {c["background_hover"]};
    }}

    QComboBox QAbstractItemView::item:selected {{
        background-color: {c["background_selected"]};
        color: {c["text_selected"]};
    }}

    /* ===== СПИСКИ ===== */
    QListWidget {{
        background-color: {c["background_input"]};
        border: 1px solid {c["border_primary"]};
        border-radius: 8px;
        padding: 5px;
        color: {c["text_secondary"]};
        font-family: {main_font};
        font-size: 14px;
        outline: none;
    }}

    QListWidget::item {{
        padding: 8px 10px;
        border-radius: 4px;
        border: none;
        margin: 1px 0px;
    }}

    QListWidget::item:selected {{
        background-color: {c["background_selected"]};
        color: {c["text_selected"]};
    }}

    QListWidget::item:hover {{
        background-color: {c["background_hover"]};
    }}

    /* ===== ДИАЛОГИ ===== */
    QDialog {{
        background-color: {c["background_dialog"]};
        border: 1px solid {c["border_primary"]};
        border-radius: 10px;
        color: {c["text_secondary"]};
    }}

    QMessageBox {{
        background-color: {c["background_dialog"]};
        color: {c["text_secondary"]};
        font-family: {main_font};
    }}

    QMessageBox QPushButton {{
        background-color: {c["background_tertiary"]};
        border: 1px solid {c["border_primary"]};
        border-radius: 6px;
        padding: 6px 20px;
        min-width: 80px;
        color: {c["text_secondary"]};
    }}

    QMessageBox QPushButton:hover {{
        background-color: {c["background_hover"]};
        border: 1px solid {c["border_hover"]};
    }}

    QMessageBox QPushButton:pressed {{
        background-color: {c["background_selected"]};
    }}

    QDialog QLineEdit {{
        background-color: {c["background_input"]};
        border: 1px solid {c["border_primary"]};
        border-radius: 6px;
        padding: 6px 10px;
        color: {c["text_primary"]};
        font-family: {main_font};
    }}

    QDialog QLineEdit:focus {{
        border: 1px solid {c["border_focus"]};
    }}

    /* ===== ПРОКРУТКА ===== */
    QScrollBar:vertical {{
        background-color: {c["background_input"]};
        border: none;
        border-radius: 4px;
        width: 12px;
        margin: 0px;
    }}

    QScrollBar::handle:vertical {{
        background-color: {c["border_primary"]};
        border-radius: 4px;
        min-height: 20px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {c["border_hover"]};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        border: none;
        background: none;
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background-color: {c["background_input"]};
        border: none;
        border-radius: 4px;
        height: 12px;
        margin: 0px;
    }}

    QScrollBar::handle:horizontal {{
        background-color: {c["border_primary"]};
        border-radius: 4px;
        min-width: 20px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background-color: {c["border_hover"]};
    }}

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        border: none;
        background: none;
        width: 0px;
    }}

    /* ===== ЛЕЙБЛЫ ===== */
    QLabel {{
        color: {c["text_secondary"]};
        font-family: {main_font};
    }}
    """