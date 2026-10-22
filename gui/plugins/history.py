# gui/plugins/history.py (исправленная версия с явным указанием пути)
"""
Плагин для сохранения и загрузки истории вопросов и ответов.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from collections import deque
from PyQt5.QtCore import QObject, pyqtSignal


class HistoryPlugin(QObject):
    """
    Плагин для управления историей вопросов.
    """
    
    history_changed = pyqtSignal()
    history_cleared = pyqtSignal()
    entry_added = pyqtSignal(dict)
    entry_removed = pyqtSignal(int)
    
    def __init__(self, max_size: int = 100, history_file: str = None):
        super().__init__()
        
        self.max_size = max_size
        self.history: deque = deque(maxlen=max_size)
        
        # Определяем путь к файлу истории
        if history_file is None:
            # По умолчанию в домашней папке пользователя
            home_dir = Path.home()
            self.history_file = home_dir / ".leshy_history.json"
        else:
            self.history_file = Path(history_file)
        
        # Создаем директорию, если её нет
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        
        self._current_id = 0
        self._is_loading = False
        
        print(f"📂 Файл истории будет сохранен в: {self.history_file}")
        
        # Загружаем историю при инициализации
        self.load_history()
    
    def add_entry(self, question: str, answer: str, category: str = "general") -> int:
        """Добавляет запись в историю."""
        if not question or not answer:
            return -1
        
        self._current_id += 1
        
        entry = {
            "id": self._current_id,
            "question": question.strip(),
            "answer": answer.strip(),
            "category": category,
            "timestamp": datetime.now().isoformat(),
            "date": datetime.now().strftime("%d.%m.%Y"),
            "time": datetime.now().strftime("%H:%M:%S"),
            "length": len(answer)
        }
        
        self.history.append(entry)
        self.entry_added.emit(entry)
        self.history_changed.emit()
        
        # Автоматически сохраняем после добавления
        self.save_history()
        
        return self._current_id
    
    def get_history(self, limit: int = None, category: str = None) -> List[Dict[str, Any]]:
        """Возвращает историю с возможностью фильтрации."""
        history_list = list(self.history)
        
        if category:
            history_list = [e for e in history_list if e.get("category") == category]
        
        if limit:
            history_list = history_list[-limit:]
        
        return history_list
    
    def get_last_entry(self) -> Optional[Dict[str, Any]]:
        """Возвращает последнюю запись в истории."""
        if self.history:
            return self.history[-1]
        return None
    
    def get_entry_by_id(self, entry_id: int) -> Optional[Dict[str, Any]]:
        """Возвращает запись по ID."""
        for entry in self.history:
            if entry.get("id") == entry_id:
                return entry
        return None
    
    def search_history(self, query: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """Поиск по истории."""
        if not query:
            return list(self.history)
        
        results = []
        query = query if case_sensitive else query.lower()
        
        for entry in self.history:
            question = entry.get("question", "")
            answer = entry.get("answer", "")
            
            if not case_sensitive:
                question = question.lower()
                answer = answer.lower()
            
            if query in question or query in answer:
                results.append(entry)
        
        return results
    
    def remove_entry(self, entry_id: int) -> bool:
        """Удаляет запись по ID."""
        for i, entry in enumerate(self.history):
            if entry.get("id") == entry_id:
                del self.history[i]
                self.entry_removed.emit(entry_id)
                self.history_changed.emit()
                self.save_history()
                return True
        return False
    
    def clear_history(self):
        """Очищает всю историю."""
        self.history.clear()
        self._current_id = 0
        self.history_cleared.emit()
        self.history_changed.emit()
        self.save_history()
    
    def save_history(self):
        """Сохраняет историю в JSON файл."""
        try:
            # Подготавливаем данные для сохранения
            data = {
                "version": "1.0",
                "max_size": self.max_size,
                "current_id": self._current_id,
                "entries": list(self.history),
                "last_updated": datetime.now().isoformat(),
                "total_entries": len(self.history)
            }
            
            # Сохраняем в файл
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ История сохранена: {len(self.history)} записей")
            print(f"   📁 {self.history_file}")
            
        except Exception as e:
            print(f"❌ Ошибка сохранения истории: {e}")
    
    def load_history(self):
        """Загружает историю из JSON файла."""
        if not self.history_file.exists():
            print(f"ℹ️ Файл истории не найден: {self.history_file}")
            print(f"   Будет создан новый файл при первом сохранении")
            return
        
        try:
            self._is_loading = True
            
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Проверяем структуру данных
            if "entries" not in data:
                print("❌ Неверный формат файла истории")
                return
            
            # Загружаем записи
            entries = data.get("entries", [])
            self.history = deque(entries, maxlen=self.max_size)
            self._current_id = data.get("current_id", len(entries))
            
            print(f"✅ История загружена: {len(self.history)} записей")
            print(f"   📁 {self.history_file}")
            
        except json.JSONDecodeError as e:
            print(f"❌ Ошибка чтения JSON: {e}")
            print(f"   Файл поврежден: {self.history_file}")
            # Создаем резервную копию поврежденного файла
            if self.history_file.exists():
                backup = self.history_file.with_suffix('.json.bak')
                try:
                    self.history_file.rename(backup)
                    print(f"   Создана резервная копия: {backup}")
                except Exception:
                    pass
        except Exception as e:
            print(f"❌ Ошибка загрузки истории: {e}")
        finally:
            self._is_loading = False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Возвращает статистику по истории."""
        if not self.history:
            return {
                "total": 0,
                "categories": {},
                "average_length": 0,
                "last_week": 0,
                "today": 0
            }
        
        # Категории
        categories = {}
        for entry in self.history:
            category = entry.get("category", "general")
            categories[category] = categories.get(category, 0) + 1
        
        # Средняя длина ответа
        total_length = sum(e.get("length", 0) for e in self.history)
        avg_length = total_length // len(self.history) if self.history else 0
        
        # За последнюю неделю
        from datetime import datetime, timedelta
        week_ago = datetime.now() - timedelta(days=7)
        last_week = 0
        today = 0
        today_str = datetime.now().strftime("%d.%m.%Y")
        
        for entry in self.history:
            try:
                entry_date = datetime.fromisoformat(entry.get("timestamp", ""))
                if entry_date >= week_ago:
                    last_week += 1
                if entry.get("date") == today_str:
                    today += 1
            except (ValueError, TypeError):
                pass
        
        return {
            "total": len(self.history),
            "categories": categories,
            "average_length": avg_length,
            "last_week": last_week,
            "today": today
        }
    
    def export_to_csv(self, filename: str = None) -> bool:
        """Экспортирует историю в CSV файл."""
        if not self.history:
            print("❌ Нет данных для экспорта")
            return False
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"leshy_history_{timestamp}.csv"
        
        try:
            import csv
            
            with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
                if self.history:
                    fieldnames = ["id", "question", "answer", "category", "date", "time", "timestamp"]
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for entry in self.history:
                        row = {k: entry.get(k, "") for k in fieldnames}
                        writer.writerow(row)
            
            print(f"✅ История экспортирована в: {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка экспорта: {e}")
            return False
    
    def export_to_text(self, filename: str = None) -> bool:
        """Экспортирует историю в текстовый файл."""
        if not self.history:
            print("❌ Нет данных для экспорта")
            return False
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"leshy_history_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("📚 ИСТОРИЯ ВОПРОСОВ И ОТВЕТОВ ЛЕШЕГО\n")
                f.write(f"📅 Сгенерировано: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
                f.write(f"📊 Всего записей: {len(self.history)}\n")
                f.write("=" * 80 + "\n\n")
                
                for i, entry in enumerate(reversed(self.history), 1):
                    f.write(f"[{i}] {entry.get('date', '')} {entry.get('time', '')}\n")
                    f.write(f"❓ Вопрос: {entry.get('question', '')}\n")
                    f.write(f"💬 Ответ: {entry.get('answer', '')}\n")
                    f.write(f"🏷️ Категория: {entry.get('category', 'general')}\n")
                    f.write("-" * 40 + "\n\n")
            
            print(f"✅ История экспортирована в: {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка экспорта: {e}")
            return False
    
    def get_categories(self) -> List[str]:
        """Возвращает список всех категорий в истории."""
        categories = set()
        for entry in self.history:
            category = entry.get("category", "general")
            categories.add(category)
        return sorted(list(categories))
    
    def get_size(self) -> int:
        """Возвращает текущий размер истории."""
        return len(self.history)
    
    def is_full(self) -> bool:
        """Проверяет, достигла ли история максимального размера."""
        return len(self.history) >= self.max_size
    
    def get_file_path(self) -> str:
        """Возвращает путь к файлу истории."""
        return str(self.history_file)