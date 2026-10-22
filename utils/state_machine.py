# utils/state_machine.py (исправленный с лучшей обработкой)
"""
Конечный автомат (State Machine) для управления состояниями Лешего.
Позволяет четко контролировать переходы между состояниями.
"""

from enum import Enum, auto
from typing import Optional, Callable, Dict, Any
import logging


class LeshyState(Enum):
    """Состояния, в которых может находиться Леший."""
    IDLE = auto()          # Ожидание
    INPUT = auto()         # Поле ввода активно
    THINKING = auto()      # Думает над ответом
    TALKING = auto()       # Отвечает (печатает текст)
    ANSWER_VISIBLE = auto() # Ответ показан полностью
    HISTORY = auto()       # Просмотр истории (добавлено)


class StateMachine:
    """
    Конечный автомат для управления состояниями.
    Позволяет задавать действия при входе и выходе из состояний.
    """
    
    def __init__(self, initial_state: LeshyState = LeshyState.IDLE):
        self.current_state = initial_state
        self.previous_state = None
        self._transitions: Dict[LeshyState, Dict[LeshyState, Callable]] = {}
        self._on_enter: Dict[LeshyState, Callable] = {}
        self._on_exit: Dict[LeshyState, Callable] = {}
        self._state_data: Dict[LeshyState, Any] = {}  # Для хранения данных состояния
        self._is_transitioning = False
        
    def add_transition(self, from_state: LeshyState, to_state: LeshyState, 
                       condition: Optional[Callable[[], bool]] = None):
        """
        Добавляет правило перехода из одного состояния в другое.
        Если condition задана, переход возможен только если она вернет True.
        """
        if from_state not in self._transitions:
            self._transitions[from_state] = {}
        self._transitions[from_state][to_state] = condition or (lambda: True)
        
    def add_on_enter(self, state: LeshyState, callback: Callable):
        """Добавляет действие при входе в состояние."""
        self._on_enter[state] = callback
        
    def add_on_exit(self, state: LeshyState, callback: Callable):
        """Добавляет действие при выходе из состояния."""
        self._on_exit[state] = callback
        
    def set_state_data(self, state: LeshyState, data: Any):
        """Сохраняет данные для состояния."""
        self._state_data[state] = data
        
    def get_state_data(self, state: LeshyState, default: Any = None) -> Any:
        """Получает данные для состояния."""
        return self._state_data.get(state, default)
        
    def transition_to(self, new_state: LeshyState) -> bool:
        """
        Пытается перейти в новое состояние.
        Возвращает True, если переход успешен.
        """
        if self._is_transitioning:
            logging.warning("Уже выполняется переход, игнорируем запрос")
            return False
            
        # Проверяем, разрешен ли переход
        if self.current_state in self._transitions:
            if new_state in self._transitions[self.current_state]:
                condition = self._transitions[self.current_state][new_state]
                try:
                    if not condition():
                        return False
                except Exception as e:
                    logging.error(f"Ошибка в условии перехода: {e}")
                    return False
            else:
                # Переход не разрешен
                logging.debug(f"Переход из {self.current_state} в {new_state} не разрешен")
                return False
        
        self._is_transitioning = True
        
        try:
            # Выполняем выход из текущего состояния
            if self.current_state in self._on_exit:
                self._on_exit[self.current_state]()
                
            # Сохраняем предыдущее состояние
            self.previous_state = self.current_state
            
            # Меняем состояние
            self.current_state = new_state
            
            # Выполняем вход в новое состояние
            if new_state in self._on_enter:
                self._on_enter[new_state]()
                
            return True
        except Exception as e:
            logging.error(f"Ошибка при переходе состояний: {e}")
            # Пытаемся восстановиться
            if self.previous_state is not None:
                self.current_state = self.previous_state
            return False
        finally:
            self._is_transitioning = False
        
    def can_transition_to(self, new_state: LeshyState) -> bool:
        """Проверяет, возможен ли переход в новое состояние."""
        if self.current_state in self._transitions:
            if new_state in self._transitions[self.current_state]:
                condition = self._transitions[self.current_state][new_state]
                try:
                    return condition()
                except Exception:
                    return False
        return False
        
    def get_state(self) -> LeshyState:
        """Возвращает текущее состояние."""
        return self.current_state
        
    def is_state(self, state: LeshyState) -> bool:
        """Проверяет, находится ли автомат в указанном состоянии."""
        return self.current_state == state
    
    def is_any_state(self, *states: LeshyState) -> bool:
        """Проверяет, находится ли автомат в одном из указанных состояний."""
        return self.current_state in states
    
    def reset(self, new_state: LeshyState = LeshyState.IDLE):
        """Сбрасывает автомат в указанное состояние."""
        self.current_state = new_state
        self.previous_state = None
        self._state_data.clear()