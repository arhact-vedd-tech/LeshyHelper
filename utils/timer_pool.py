# utils/timer_pool.py (исправленный с лучшей обработкой ошибок)
"""
Единый игровой цикл (Game Loop) для управления всеми таймерами.
Заменяет множество QTimer на один централизованный таймер.
"""

from PyQt5.QtCore import QTimer
from typing import Callable, List, Dict, Any, Optional
import time


class GameLoop:
    """
    Единый игровой цикл. Вызывается с фиксированным интервалом.
    Все анимации и обновления должны регистрироваться здесь.
    """
    
    def __init__(self, interval_ms: int = 16):
        self.interval_ms = interval_ms
        self.timer = QTimer()
        self.timer.timeout.connect(self._update)
        self._listeners: List[Dict[str, Any]] = []
        self._is_running = False
        self._delta_time = 0
        self._last_update = time.time()
        self._error_count = 0
        self._max_errors = 10  # Максимальное количество ошибок перед остановкой
        
    def start(self):
        """Запускает игровой цикл."""
        if not self._is_running:
            self._is_running = True
            self._last_update = time.time()
            self.timer.start(self.interval_ms)
            
    def stop(self):
        """Останавливает игровой цикл."""
        self._is_running = False
        self.timer.stop()
        
    def register(self, callback: Callable, interval: int = 1):
        """
        Регистрирует функцию для вызова каждый кадр.
        interval - через сколько кадров вызывать (1 = каждый кадр).
        """
        self._listeners.append({
            'callback': callback,
            'interval': max(1, interval),
            'counter': 0
        })
        
    def unregister(self, callback: Callable):
        """Удаляет функцию из списка обновления."""
        self._listeners = [l for l in self._listeners if l['callback'] != callback]
        
    def clear(self):
        """Очищает все зарегистрированные функции."""
        self._listeners.clear()
        
    def _update(self):
        """Основной метод обновления, вызывается по таймеру."""
        if not self._is_running:
            return
            
        current_time = time.time()
        self._delta_time = current_time - self._last_update
        self._last_update = current_time
        
        # Создаем копию списка для безопасной итерации
        listeners_copy = self._listeners.copy()
        
        for listener in listeners_copy:
            try:
                listener['counter'] += 1
                if listener['counter'] >= listener['interval']:
                    listener['counter'] = 0
                    listener['callback']()
            except Exception as e:
                self._error_count += 1
                print(f"Ошибка в игровом цикле: {e}")
                print(f"  Функция: {listener['callback'].__name__ if hasattr(listener['callback'], '__name__') else 'anonymous'}")
                
                # Если слишком много ошибок, останавливаем цикл
                if self._error_count >= self._max_errors:
                    print(f"Слишком много ошибок ({self._error_count}), останавливаем игровой цикл")
                    self.stop()
                    break
    
    def get_delta_time(self) -> float:
        """Возвращает время между кадрами в секундах."""
        return self._delta_time
    
    def is_running(self) -> bool:
        """Проверяет, запущен ли игровой цикл."""
        return self._is_running