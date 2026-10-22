# gui/plugins/__init__.py (обновленный)
"""
Плагины для расширения функциональности Лешего.
"""

from .history import HistoryPlugin
from .history_widget import HistoryWidget
from .voice_input import VoiceInputPlugin
from .weather import WeatherPlugin
from .kiosk import KioskPlugin

__all__ = [
    'HistoryPlugin', 
    'HistoryWidget',
    'VoiceInputPlugin', 
    'WeatherPlugin', 
    'KioskPlugin'
]