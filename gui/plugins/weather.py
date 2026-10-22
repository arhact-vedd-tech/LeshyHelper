# gui/plugins/weather.py
"""
Плагин для отображения погоды и времени.
"""

import json
import time
from datetime import datetime
from PyQt5.QtWidgets import QLabel


class WeatherPlugin:
    """Плагин для отображения погоды и времени."""
    
    def __init__(self):
        self.weather_label = QLabel()
        self.weather_label.setStyleSheet("""
            QLabel {
                color: #e0d5c1;
                font-size: 14px;
                padding: 5px 10px;
                background-color: rgba(30, 20, 10, 0.7);
                border-radius: 5px;
            }
        """)
        self.weather_label.hide()  # Показывается по нажатию
        self._last_update = 0
        self._update_interval = 300  # 5 минут
    
    def get_widget(self) -> QLabel:
        """Возвращает виджет для отображения информации."""
        return self.weather_label
    
    def update(self, force: bool = False):
        """Обновляет информацию о времени и погоде."""
        current_time = time.time()
        if not force and current_time - self._last_update < self._update_interval:
            return
        
        self._last_update = current_time
        
        # Время
        time_str = datetime.now().strftime("%H:%M")
        
        # TODO: Интеграция с API погоды
        # weather = self._get_weather()
        weather = "🌤️ +18°C"  # Заглушка
        
        self.weather_label.setText(f"{time_str}  {weather}")
        self.weather_label.show()
    
    def _get_weather(self):
        """Получение данных о погоде с API (заглушка)."""
        # TODO: Реализация запроса к API погоды
        return "🌤️ +18°C"