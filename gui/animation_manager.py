# gui/animation_manager.py (добавляем поддержку скинов)

"""
Управление анимациями Лешего.
Поддерживает скины (пасхалки) — замену всех анимаций на альтернативный набор.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from config import LESHY_ASSETS_DIR
from config import SKIN_COLORS


class AnimationManager:
    """
    Менеджер анимаций. Загружает, кэширует и управляет проигрыванием.
    
    Поддерживает скины — альтернативные наборы анимаций в подпапках assets/leshy/.
    Например, папка assets/leshy/maid/ содержит анимации горничной.
    """
    
    # Рекомендуемые интервалы для разных типов анимаций (в миллисекундах)
    ANIMATION_SPEEDS = {
        "idle": 150,
        "idle2": 130,
        "idle3": 130,
        "thinking": 200,
        "talking": 80,
        "talking2": 80,
        "lib": 150,
        "default": 100
    }
    
    # Ключевые слова для активации скинов
    SKIN_TRIGGERS = {
        "maid": ["maid", "горничная", "горничной", "maid-san", "мейд"],
        # Можно добавить другие скины:
        # "wizard": ["wizard", "волшебник", "маг"],
        # "cat": ["cat", "кот", "кошка", "neko"],
    }
    
    def get_skin_colors(self, skin_name: str = None) -> Optional[dict]:
        """
        Возвращает цветовую схему для указанного скина.
        Если skin_name не указан — возвращает цвета текущего скина.
        """
        if skin_name is None:
            skin_name = self._current_skin
        
        if skin_name and skin_name in SKIN_COLORS:
            return SKIN_COLORS[skin_name]
        
        return None
    
    def get_current_colors(self) -> dict:
        """
        Возвращает актуальную цветовую схему.
        Если активен скин — возвращает его цвета, иначе None.
        """
        if self._current_skin and self._current_skin in SKIN_COLORS:
            return SKIN_COLORS[self._current_skin]
        return None
    
    def __init__(self):
        self.assets_path = LESHY_ASSETS_DIR
        self.cache: Dict[str, List[QPixmap]] = {}
        
        # Скины
        self._available_skins: Dict[str, str] = {}  # {skin_name: skin_path}
        self._current_skin: Optional[str] = None
        self._skin_cache: Dict[str, Dict[str, List[QPixmap]]] = {}  # {skin_name: {anim_name: frames}}
        
        # Текущее состояние
        self.current_animation: Optional[str] = None
        self.current_frames: List[QPixmap] = []
        self.current_frame_index: int = 0
        
        # Настройки воспроизведения
        self.loop: bool = True
        self.is_playing: bool = False
        self.interval: int = 100
        
        # Система приоритетов анимаций
        self._base_animation = "idle"
        self._one_shot_pending: Optional[Tuple[str, int]] = None
        self._force_switch_pending: Optional[Tuple[str, bool, int]] = None
        
        # Счётчики кадров
        self._frame_counter: int = 0
        self._frame_interval: int = 1
        
        # Обнаруживаем доступные скины
        self._detect_skins()
        
        # Загружаем все анимации
        self.load_all_animations()
        
        # Если нет анимаций, создаем фейковую
        if not self.cache:
            self._create_fallback_animation()
    
    def _detect_skins(self):
        """Обнаруживает доступные скины в подпапках assets/leshy/."""
        if not self.assets_path.exists():
            return
        
        for item in self.assets_path.iterdir():
            if item.is_dir():
                # Проверяем, является ли папка скином (содержит подпапки с анимациями)
                has_animations = False
                for subitem in item.iterdir():
                    if subitem.is_dir():
                        has_animations = True
                        break
                
                if has_animations:
                    skin_name = item.name.lower()
                    # Проверяем, есть ли это имя в триггерах
                    is_skin = False
                    for trigger_name in self.SKIN_TRIGGERS:
                        if skin_name == trigger_name:
                            is_skin = True
                            break
                    
                    if is_skin:
                        self._available_skins[skin_name] = str(item)
    
    def check_skin_trigger(self, text: str) -> Optional[str]:
        """
        Проверяет текст на наличие триггеров скинов.
        Возвращает имя скина или None.
        """
        text_lower = text.lower()
        
        for skin_name, triggers in self.SKIN_TRIGGERS.items():
            if skin_name not in self._available_skins:
                continue
            
            for trigger in triggers:
                if trigger in text_lower:
                    return skin_name
        
        return None
    
    def activate_skin(self, skin_name: str) -> bool:
        """
        Активирует скин, заменяя все анимации на альтернативный набор.
        """
        if skin_name not in self._available_skins:
            return False
        
        if self._current_skin == skin_name:
            return True
        
        # Загружаем анимации скина если ещё не загружены
        if skin_name not in self._skin_cache:
            self._load_skin_animations(skin_name)
        
        skin_frames = self._skin_cache.get(skin_name, {})
        
        if not skin_frames:
            return False
        
        # Сохраняем оригинальный кэш если это первый скин
        if self._current_skin is None:
            self._skin_cache["_original_"] = self.cache.copy()
        
        # === КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: обновляем существующий словарь, а не заменяем ссылку ===
        self.cache.clear()
        self.cache.update(skin_frames)
        
        # Если в скине нет каких-то анимаций — добавляем из оригинала
        original_cache = self._skin_cache.get("_original_", {})
        for anim_name in ["idle", "idle2", "idle3", "thinking", "talking", "talking2", "lib"]:
            if anim_name not in self.cache and anim_name in original_cache:
                self.cache[anim_name] = original_cache[anim_name]
        
        self._current_skin = skin_name
        
        # Очищаем все ожидающие переключения
        self._one_shot_pending = None
        self._force_switch_pending = None
        
        # === ПРИНУДИТЕЛЬНО обновляем current_frames из нового кэша ===
        target_animation = self.current_animation if self.current_animation in self.cache else "idle"
        
        # Напрямую обновляем кадры, а не через _play_immediate (чтобы избежать гонки с update)
        self.current_frames = self.cache[target_animation]
        self.current_frame_index = 0
        self.current_animation = target_animation
        self.loop = True
        self.is_playing = True
        self._frame_counter = 0
        self._frame_interval = max(1, int(self.get_recommended_interval(target_animation, len(self.current_frames)) / 16))
        return True
    
    def deactivate_skin(self) -> bool:
        """Деактивирует скин, возвращая оригинальные анимации."""
        if self._current_skin is None:
            return False
        
        self._current_skin = None
        
        # Восстанавливаем оригинальный кэш (обновляем существующий словарь)
        if "_original_" in self._skin_cache:
            self.cache.clear()
            self.cache.update(self._skin_cache["_original_"])
        
        # Очищаем все ожидающие переключения
        self._one_shot_pending = None
        self._force_switch_pending = None
        
        # Принудительно обновляем current_frames
        target_animation = self.current_animation if self.current_animation in self.cache else "idle"
        self.current_frames = self.cache[target_animation]
        self.current_frame_index = 0
        self.current_animation = target_animation
        self.loop = True
        self.is_playing = True
        self._frame_counter = 0
        return True
    
    def get_current_skin(self) -> Optional[str]:
        """Возвращает имя текущего активного скина."""
        return self._current_skin
    
    def get_available_skins(self) -> List[str]:
        """Возвращает список доступных скинов."""
        return list(self._available_skins.keys())
    
    def _load_skin_animations(self, skin_name: str):
        """Загружает все анимации скина."""
        if skin_name not in self._available_skins:
            return
        
        skin_path = Path(self._available_skins[skin_name])
        skin_frames: Dict[str, List[QPixmap]] = {}
        
        for item in skin_path.iterdir():
            if item.is_dir():
                anim_name = item.name.lower()
                frames = self._load_animation_frames(item)
                if frames:
                    # Приводим имена к стандартным
                    mapped_name = self._map_animation_name(anim_name)
                    skin_frames[mapped_name] = frames
        
        self._skin_cache[skin_name] = skin_frames
    
    def _map_animation_name(self, folder_name: str) -> str:
        """
        Сопоставляет имя папки скина со стандартным именем анимации.
        Например, папка "idle" → "idle", "think" → "thinking"
        """
        name_mapping = {
            "idle": "idle",
            "idle1": "idle",
            "idle_1": "idle",
            "idle2": "idle2",
            "idle_2": "idle2",
            "idle3": "idle3",
            "idle_3": "idle3",
            "thinking": "thinking",
            "think": "thinking",
            "talking": "talking",
            "talk": "talking",
            "talking2": "talking2",
            "talk2": "talking2",
            "lib": "lib",
            "book": "lib",
            "history": "lib",
        }
        return name_mapping.get(folder_name.lower(), folder_name.lower())
    
    def load_all_animations(self):
        """Загружает все анимации из папки assets/leshy/ (пропускает папки скинов)."""
        if not self.assets_path.exists():
            return
        
        has_animations = False
        
        for item in self.assets_path.iterdir():
            if item.is_dir():
                # ПРОПУСКАЕМ папки, которые являются скинами
                # (содержат подпапки с анимациями, а не файлы .png напрямую)
                if item.name.lower() in self._available_skins:
                    continue
                
                frames = self._load_animation_frames(item)
                if frames:
                    self.cache[item.name] = frames
                    has_animations = True
        
        if not has_animations:
            self._load_static_images()
    
    def _load_static_images(self):
        """Загружает одиночные PNG как статичные кадры (запасной вариант)."""
        if not self.assets_path.exists():
            return
            
        for file in self.assets_path.iterdir():
            if file.suffix.lower() == '.png':
                name = file.stem
                pixmap = QPixmap(str(file))
                if not pixmap.isNull():
                    scaled = pixmap.scaled(280, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.cache[name] = [scaled]
    
    def _create_fallback_animation(self):
        """Создает фейковую анимацию-заглушку."""
        
        from PyQt5.QtGui import QPainter, QColor, QFont
        pixmap = QPixmap(280, 280)
        pixmap.fill(QColor(30, 20, 10))
        
        painter = QPainter(pixmap)
        painter.setPen(QColor(245, 231, 211))
        painter.setFont(QFont("Georgia", 24))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "🌿")
        painter.end()
        
        for name in ["idle", "idle2", "idle3", "thinking", "talking", "talking2", "lib"]:
            self.cache[name] = [pixmap]
    
    def _load_animation_frames(self, folder_path: Path) -> List[QPixmap]:
        """Загружает кадры анимации из папки."""
        frames = []
        
        # Ищем нумерованные файлы (1.png, 2.png, ...)
        index = 1
        while True:
            frame_path = folder_path / f"{index}.png"
            if frame_path.exists():
                pixmap = QPixmap(str(frame_path))
                if not pixmap.isNull():
                    scaled = pixmap.scaled(280, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    frames.append(scaled)
                index += 1
            else:
                break
        
        # Если нет нумерованных — любые PNG
        if not frames:
            for file in sorted(folder_path.iterdir()):
                if file.suffix.lower() == '.png':
                    pixmap = QPixmap(str(file))
                    if not pixmap.isNull():
                        scaled = pixmap.scaled(280, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        frames.append(scaled)
        
        return frames
    
    def get_animation(self, anim_name: str) -> Optional[List[QPixmap]]:
        """Получает анимацию по имени (из кэша или загружает)."""
        # Ищем в текущем кэше
        if anim_name in self.cache:
            return self.cache[anim_name]
        
        # Если активен скин и анимации нет в текущем кэше — ищем в оригинальном
        if self._current_skin and "_original_" in self._skin_cache:
            if anim_name in self._skin_cache["_original_"]:
                return self._skin_cache["_original_"][anim_name]
        
        # Пробуем загрузить из файловой системы (только не скин-папки)
        if anim_name.lower() not in self._available_skins:
            anim_path = self.assets_path / anim_name
            if anim_path.is_dir():
                frames = self._load_animation_frames(anim_path)
                if frames:
                    self.cache[anim_name] = frames
                    return frames
        
        # Пробуем загрузить статичную картинку
        img_path = self.assets_path / f"{anim_name}.png"
        if img_path.exists():
            pixmap = QPixmap(str(img_path))
            if not pixmap.isNull():
                scaled = pixmap.scaled(280, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.cache[anim_name] = [scaled]
                return [scaled]
        
        return None
    
    def get_recommended_interval(self, anim_name: str, frames_count: int = None) -> int:
        """Возвращает рекомендуемый интервал для анимации."""
        base_interval = self.ANIMATION_SPEEDS.get(anim_name, self.ANIMATION_SPEEDS["default"])
        
        if frames_count and frames_count > 1:
            if anim_name.startswith("talking"):
                target_fps = min(18, 2)
                calculated_interval = int(1000 / target_fps)
                if anim_name == "talking":
                    calculated_interval = int(calculated_interval * 1.2)
                return max(50, min(150, calculated_interval))
            elif anim_name.startswith("thinking"):
                target_fps = min(6, 2)
                calculated_interval = int(1000 / target_fps)
                return max(150, min(300, calculated_interval))
            elif anim_name.startswith("idle"):
                target_fps = min(8, 2)
                calculated_interval = int(1000 / target_fps)
                return max(100, min(200, calculated_interval))
        
        return base_interval
    
    # ==================== НОВЫЕ МЕТОДЫ УПРАВЛЕНИЯ ====================
    
    def play_base(self, anim_name: str = "idle", interval: int = None) -> bool:
        """
        Запускает базовую петлю анимации.
        Обычно это idle.
        """
        if anim_name not in self.cache and not self.get_animation(anim_name):
            return False
        
        self._base_animation = anim_name
        return self._play_immediate(anim_name, loop=True, interval=interval)
    
    def play_one_shot(self, anim_name: str, interval: int = None) -> bool:
        """
        Запускает однократную анимацию.
        После завершения автоматически вернётся к базовой (idle).
        Используется для idle2, idle3.
        """
        if anim_name not in self.cache and not self.get_animation(anim_name):
            return False
        
        # Если сейчас играет однократная анимация — заменяем на новую
        self._one_shot_pending = (anim_name, interval or self.get_recommended_interval(anim_name))
        
        # Запускаем немедленно (не ждём окончания текущей)
        return self._play_immediate(anim_name, loop=False, interval=interval)
    
    def play_forced(self, anim_name: str, loop: bool = True, interval: int = None) -> bool:
        """
        Принудительно запускает анимацию, прерывая текущую.
        Используется для thinking, talking.
        """
        if anim_name not in self.cache and not self.get_animation(anim_name):
            if anim_name != "idle" and "idle" in self.cache:
                return self.play_forced("idle", loop=True)
            return False
        
        # Устанавливаем как принудительное переключение
        self._force_switch_pending = (anim_name, loop, interval)
        
        # Запускаем немедленно
        return self._play_immediate(anim_name, loop=loop, interval=interval)
    
    def _play_immediate(self, anim_name: str, loop: bool, interval: int = None) -> bool:
        """Немедленно запускает указанную анимацию."""
        frames = self.cache.get(anim_name) or self.get_animation(anim_name)
        if not frames:
            return False
        
        # Если интервал не указан, вычисляем автоматически
        if interval is None:
            interval = self.get_recommended_interval(anim_name, len(frames))
        
        # Применяем новую анимацию
        self.current_frames = frames
        self.current_frame_index = 0
        self.current_animation = anim_name
        self.loop = loop
        self.interval = interval
        self.is_playing = True
        self._frame_counter = 0
        
        # Вычисляем интервал между кадрами (~60 FPS игровой цикл)
        self._frame_interval = max(1, int(interval / 16))
        
        return True
    
    # ==================== ОСНОВНОЙ МЕТОД ОБНОВЛЕНИЯ ====================
    
    def update(self) -> Optional[QPixmap]:
        """
        Обновляет анимацию на следующий кадр.
        Вызывается из игрового цикла.
        
        Логика:
        1. Если есть принудительное переключение — применяем его
        2. Если текущая анимация не в петле и дошла до конца — возвращаемся к базовой
        3. Если есть ожидающая one-shot — проигрываем её
        4. Иначе продолжаем текущую анимацию
        """
        if not self.is_playing or not self.current_frames:
            return None
        
        # === Проверка принудительного переключения ===
        if self._force_switch_pending:
            anim_name, loop, interval = self._force_switch_pending
            self._force_switch_pending = None
            self._play_immediate(anim_name, loop, interval)
            return self.current_frames[0]
        
        # === Получаем текущий кадр ===
        frame = self.current_frames[self.current_frame_index]
        
        # === Счётчик кадров ===
        self._frame_counter += 1
        
        if self._frame_counter >= self._frame_interval:
            self._frame_counter = 0
            self.current_frame_index += 1
            
            # === Если дошли до конца анимации ===
            if self.current_frame_index >= len(self.current_frames):
                if self.loop:
                    # Петля — начинаем заново
                    self.current_frame_index = 0
                    
                    # Если это базовая анимация и есть ожидающая one-shot — проигрываем её
                    if self.current_animation == self._base_animation and self._one_shot_pending:
                        anim_name, interval = self._one_shot_pending
                        self._one_shot_pending = None
                        self._play_immediate(anim_name, loop=False, interval=interval)
                        return self.current_frames[0]
                else:
                    # Не петля — возвращаемся к базовой анимации
                    self._play_immediate(self._base_animation, loop=True)
                    return self.current_frames[0]
        
        return frame
    
    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================
    
    def stop(self):
        """Останавливает текущую анимацию."""
        self.is_playing = False
        self._one_shot_pending = None
        self._force_switch_pending = None
    
    def get_current_frame(self) -> Optional[QPixmap]:
        """Возвращает текущий кадр анимации."""
        if self.current_frames and self.current_frame_index < len(self.current_frames):
            return self.current_frames[self.current_frame_index]
        return None
    
    def has_animation(self, anim_name: str) -> bool:
        """
        Проверяет, существует ли анимация с таким именем.
        Ищет в текущем кэше И в оригинальном кэше (если активен скин).
        """
        # Проверяем в текущем кэше
        if anim_name in self.cache:
            return True
        
        # Если активен скин — проверяем в оригинальном кэше
        if self._current_skin and "_original_" in self._skin_cache:
            if anim_name in self._skin_cache["_original_"]:
                return True
        
        # Проверяем в файловой системе (только если это не скин-папка)
        anim_path = self.assets_path / anim_name
        if anim_path.is_dir() and anim_name.lower() not in self._available_skins:
            return True
        
        return False
    
    def get_animation_info(self, anim_name: str) -> Optional[dict]:
        """Возвращает информацию об анимации."""
        frames = self.get_animation(anim_name)
        if frames:
            return {
                "name": anim_name,
                "frames_count": len(frames),
                "recommended_interval": self.get_recommended_interval(anim_name, len(frames)),
                "current_interval": self.interval if self.current_animation == anim_name else None
            }
        return None
    
    def is_playing_base(self) -> bool:
        """Проверяет, играет ли сейчас базовая анимация."""
        return self.current_animation == self._base_animation and self.loop
    
    def is_idle(self) -> bool:
        """Проверяет, находится ли анимация в состоянии покоя (idle)."""
        return self.current_animation in ["idle", "idle2", "idle3"] and not self._force_switch_pending