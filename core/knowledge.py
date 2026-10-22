# core/knowledge.py (финальная версия — без ошибок)
"""
Мозг Лешего: поиск ответов в книге знаний и генерация fallback-ответов.
Поддерживает контекстно-зависимые фразы с псевдорандомом.
Все фразы загружаются из JSON-файлов.
Fallback-ответы (ошибки) НИКОГДА не показывают контекстные поздравления.
"""

import json
import os
import sys
import random
from typing import Optional, Dict, List, Any
from pathlib import Path
from datetime import datetime

# TF-IDF imports
# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.metrics.pairwise import cosine_similarity
# import numpy as np


class LeshyWisdom:
    """Хранитель знаний. Ищет ответы на вопросы пользователя."""
    
    HOLIDAYS = {
        "01.01": "new_year", "02.01": "new_year", "03.01": "new_year",
        "04.01": "new_year", "05.01": "new_year", "06.01": "new_year",
        "07.01": "christmas",
        "14.02": "valentine",
        "23.02": "defender",
        "08.03": "womens_day",
        "01.04": "april_fool",
        "01.05": "may_day",
        "09.05": "victory_day",
        "01.09": "knowledge_day",
        "05.10": "teacher_day",
        "31.10": "halloween",
        "31.12": "new_year_eve",
    }
    
    ERROR_CATEGORIES = [
        "philosophical", "humorous", "forest", "magic",
        "funny", "short", "office", "self_joke", "kind"
    ]
    
    def __init__(self, knowledge_base_path: str = None, personal_dates: dict = None):
        if getattr(sys, 'frozen', False):
            self._base_path = Path(sys._MEIPASS)
        else:
            self._base_path = Path(__file__).parent
        
        if knowledge_base_path is None:
            knowledge_base_path = self._base_path / "knowledge_base.json"
        
        self.knowledge_base_path = knowledge_base_path
        self.knowledge_base: List[Dict[str, Any]] = []
        self.PERSONAL_DATES = personal_dates or {}
        
        self._fallback_cache: Dict[str, List[str]] = {}
        self._loading_cache: Dict[str, List[str]] = {}
        self._greeting_given_today: Dict[str, bool] = {}
        self._last_greeting_date = None
        
        self.load_knowledge()
        self._load_phrases()
    
    # ========== КОНТЕКСТ И СЧЁТЧИКИ ==========
    
    def _reset_daily_counters(self):
        today = datetime.now().date()
        if self._last_greeting_date != today:
            self._greeting_given_today = {}
            self._last_greeting_date = today
    
    def _mark_given(self, flag: str):
        self._greeting_given_today[flag] = True
    
    def _is_given(self, flag: str) -> bool:
        return self._greeting_given_today.get(flag, False)
    
    def _get_context(self) -> dict:
        now = datetime.now()
        hour, month, day, weekday = now.hour, now.month, now.day, now.weekday()
        
        if 6 <= hour < 12:
            time_of_day = "morning"
        elif 12 <= hour < 18:
            time_of_day = "day"
        elif 18 <= hour < 24:
            time_of_day = "evening"
        else:
            time_of_day = "night"
        
        if 3 <= month <= 5:
            season = "spring"
        elif 6 <= month <= 8:
            season = "summer"
        elif 9 <= month <= 11:
            season = "autumn"
        else:
            season = "winter"
        
        date_key = f"{day:02d}.{month:02d}"
        holiday = self.HOLIDAYS.get(date_key)
        
        personal_event = None
        is_birthday_today = False
        days_until_birthday = None
        
        if date_key in self.PERSONAL_DATES:
            info = self.PERSONAL_DATES[date_key]
            if info.get("type") == "birthday":
                is_birthday_today = True
                holiday = "birthday"
                personal_event = "birthday"
        
        if not is_birthday_today:
            for date_str, info in self.PERSONAL_DATES.items():
                if info.get("type") == "birthday":
                    bday_day, bday_month = map(int, date_str.split("."))
                    bday_this_year = datetime(now.year, bday_month, bday_day)
                    if bday_this_year < now:
                        bday_this_year = datetime(now.year + 1, bday_month, bday_day)
                    days_until_birthday = (bday_this_year - now).days
                    if days_until_birthday <= 7:
                        personal_event = "birthday_soon"
                        holiday = "birthday_soon"
                    break
        
        return {
            "time_of_day": time_of_day,
            "season": season,
            "holiday": holiday,
            "personal_event": personal_event,
            "is_birthday_today": is_birthday_today,
            "days_until_birthday": days_until_birthday,
            "is_weekend": weekday >= 5,
            "hour": hour, "month": month, "weekday": weekday,
        }
    
    # ========== ЗАГРУЗКА ДАННЫХ ==========
    
    def _load_json(self, filename: str) -> dict:
        # Пробуем сначала рядом с базой знаний (core/), потом в корне _base_path
        candidates = []
        if self.knowledge_base_path:
            kb_dir = Path(self.knowledge_base_path).parent
            candidates.append(kb_dir / filename)
        candidates.append(self._base_path / filename)
        candidates.append(self._base_path / "core" / filename)

        for path in candidates:
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception as e:
                    print(f"❌ Ошибка загрузки {path}: {e}")
                    return {}

        print(f"⚠️ Файл не найден ни по одному пути: {filename}")
        print(f"   Проверенные пути: {[str(p) for p in candidates]}")
        return {}
    
    def _load_phrases(self):
        self._fallback_cache = self._load_json("fallback_answers.json")
        self._loading_cache = self._load_json("loading_phrases.json")
        
        error_count = sum(
            len(v) for k, v in self._fallback_cache.items()
            if k in self.ERROR_CATEGORIES and isinstance(v, list)
        )
        loading_count = sum(
            len(v) for v in self._loading_cache.values() if isinstance(v, list)
        )
        print(f"✅ Загружено фраз: {error_count} ошибочных, {loading_count} загрузочных")
        
        if error_count == 0:
            print("❌ ВНИМАНИЕ: В fallback_answers.json нет категорий ошибок!")
            print("   Добавьте хотя бы одну из: " + ", ".join(self.ERROR_CATEGORIES))
    
    def _get_phrases_by_keys(self, cache: dict, keys: List[str]) -> List[str]:
        for key in keys:
            if key in cache and isinstance(cache[key], list) and cache[key]:
                return cache[key]
        return []
    
    def load_knowledge(self):
        if not os.path.exists(self.knowledge_base_path):
            print(f"❌ Книга знаний не найдена: {self.knowledge_base_path}")
            return
        try:
            with open(self.knowledge_base_path, 'r', encoding='utf-8') as f:
                self.knowledge_base = json.load(f)
            print(f"✅ База знаний загружена: {len(self.knowledge_base)} записей")
        except Exception as e:
            print(f"❌ Ошибка загрузки базы знаний: {e}")
    
    # ========== ВЫБОР ФРАЗ ==========
    
    def _weighted_choice(self, candidates: List[tuple]) -> Optional[List[str]]:
        """
        candidates: [(phrases, weight, flag), ...]
        weight >= 100 → обязательно. Иначе random(1-100) <= weight.
        """
        if not candidates:
            return None
        
        mandatory = [c for c in candidates if c[1] >= 100]
        if mandatory:
            phrases, weight, flag = mandatory[0]
            self._mark_given(flag)
            return phrases
        
        for phrases, weight, flag in candidates:
            if weight <= 0:
                continue
            if random.randint(1, 100) <= weight:
                self._mark_given(flag)
                return phrases
        
        return None
    
    def _weighted_category_choice(self, weights: Dict[str, int]) -> Optional[str]:
        total = sum(weights.values())
        if total == 0:
            return None
        roll = random.randint(1, total)
        cumulative = 0
        for category, weight in weights.items():
            cumulative += weight
            if roll <= cumulative:
                return category
        return None
    
    def _get_contextual_phrases(self, phrase_type: str = "fallback") -> List[str]:
        self._reset_daily_counters()
        context = self._get_context()
        
        if phrase_type == "loading":
            return self._get_loading_phrases(context)
        else:
            return self._get_fallback_phrases(context)
    
    def _get_loading_phrases(self, context: dict) -> List[str]:
        """Загрузочные фразы МОГУТ быть контекстными."""
        cache = self._loading_cache
        if not cache:
            return ["Ищу ответ..."]
        
        candidates = []
        
        if context.get("is_birthday_today"):
            flag = "birthday"
            weight = 100 if not self._is_given(flag) else 40
            phrases = self._get_phrases_by_keys(cache, [
                f"birthday_{context['time_of_day']}",
                f"birthday_{context['season']}",
                "birthday"
            ])
            if phrases:
                candidates.append((phrases, weight, flag))
        
        if context.get("personal_event") == "birthday_soon":
            flag = "birthday_soon"
            phrases = self._get_phrases_by_keys(cache, ["birthday_soon"])
            if phrases:
                candidates.append((phrases, 30, flag))
        
        holiday = context.get("holiday")
        if holiday and holiday not in ["birthday", "birthday_soon"]:
            flag = f"holiday_{holiday}"
            phrases = self._get_phrases_by_keys(cache, [holiday])
            if phrases:
                candidates.append((phrases, 40, flag))
        
        time_season = f"{context['time_of_day']}_{context['season']}"
        flag = f"time_{context['time_of_day']}"
        if not self._is_given(flag):
            phrases = self._get_phrases_by_keys(cache, [time_season, context["time_of_day"]])
            if phrases:
                candidates.append((phrases, 25, flag))
        
        flag = f"season_{context['season']}"
        if not self._is_given(flag):
            phrases = self._get_phrases_by_keys(cache, [context["season"]])
            if phrases:
                candidates.append((phrases, 15, flag))
        
        chosen = self._weighted_choice(candidates)
        if chosen:
            return chosen
        
        general = ["calm", "funny", "book", "poetic", "confident", "grumpy", "proverbs", "spells"]
        for key in general:
            if key in cache and isinstance(cache[key], list) and cache[key]:
                return cache[key]
        
        all_phrases = []
        for v in cache.values():
            if isinstance(v, list):
                all_phrases.extend(v)
        return all_phrases if all_phrases else ["Ищу ответ..."]
    
    def _get_fallback_phrases(self, context: dict) -> List[str]:
        """
        Fallback-ответы НИКОГДА не показывают контекстные поздравления.
        Только категории ошибок с весами, зависящими от контекста.
        """
        cache = self._fallback_cache
        
        weights = {
            "philosophical": 15, "humorous": 15, "forest": 15,
            "magic": 15, "funny": 10, "short": 10,
            "office": 10, "self_joke": 5, "kind": 5,
        }
        
        # Коррекция по сезону
        season = context.get("season")
        if season == "winter":
            weights.update(forest=25, magic=20, philosophical=15, humorous=10, funny=10, kind=10, short=5, office=5)
        elif season == "summer":
            weights.update(humorous=25, funny=20, forest=15, philosophical=10, kind=10, magic=10, short=5, office=5)
        elif season == "autumn":
            weights.update(philosophical=25, office=20, forest=15, magic=15, humorous=10, funny=5, kind=5, short=5)
        elif season == "spring":
            weights.update(magic=25, kind=20, forest=15, philosophical=10, humorous=10, funny=10, short=5, office=5)
        
        # Коррекция по дню рождения
        if context.get("is_birthday_today"):
            weights.update(kind=30, philosophical=20, humorous=15, funny=15, forest=10, magic=5, short=3, office=2)
        
        # Коррекция по праздникам
        holiday = context.get("holiday")
        if holiday in ("new_year", "new_year_eve"):
            weights.update(magic=30, kind=25, philosophical=15, humorous=10, funny=10, forest=5, short=3, office=2)
        elif holiday == "halloween":
            weights.update(magic=35, funny=20, self_joke=15, humorous=15, forest=10, short=5)
        elif holiday == "april_fool":
            weights.update(humorous=40, funny=30, self_joke=20, short=10)
        
        chosen = self._weighted_category_choice(weights)
        
        if chosen and chosen in cache and isinstance(cache[chosen], list) and cache[chosen]:
            return cache[chosen]
        
        all_errors = []
        for cat in self.ERROR_CATEGORIES:
            if cat in cache and isinstance(cache[cat], list):
                all_errors.extend(cache[cat])
        return all_errors if all_errors else ["Ох, растерялся я... Спросите о Word или Excel!"]
    
    # ========== ПУБЛИЧНЫЕ МЕТОДЫ ==========
    
    def find_answer(self, user_query: str) -> Optional[Dict[str, Any]]:
        if not user_query:
            return None
        
        user_words = set(user_query.lower().split())
        best_match, max_matches, best_relevance = None, 0, 0.0
        
        for item in self.knowledge_base:
            all_text = " ".join(item.get("keywords", [])) + " " + item.get("question", "")
            all_words = set(all_text.lower().split())
            matches = len(user_words.intersection(all_words))
            relevance = matches / len(user_words) if user_words else 0
            
            if matches > max_matches or (matches == max_matches and relevance > best_relevance):
                max_matches, best_relevance, best_match = matches, relevance, item
        
        return best_match if best_match and max_matches > 0 else None
    
    def get_loading_phrase(self) -> str:
        phrases = self._get_contextual_phrases("loading")
        return random.choice(phrases) if phrases else "Ищу ответ..."
    
    def get_fallback_answer(self) -> str:
        phrases = self._get_contextual_phrases("fallback")
        return random.choice(phrases) if phrases else "Ох, растерялся я... Спросите о Word или Excel!"
    
    def ask_question(self, user_query: str) -> tuple:
        result = self.find_answer(user_query)
        if result and result.get("answer"):
            return result["answer"], False
        return self.get_fallback_answer(), True
    
    def get_context_info(self) -> dict:
        return self._get_context()