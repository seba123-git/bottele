"""
Manejo del estado persistente del bot
"""

import json
import logging
from datetime import date
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class BotState:
    """Clase para manejar el estado persistente del bot"""
    
    def __init__(self, state_file: str = "bot_state.json"):
        self.state_file = Path(state_file)
        self.state = self._load_state()
        
    def _load_state(self) -> Dict[str, Any]:
        """Carga el estado desde archivo"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    logger.info("Estado cargado desde archivo")
                    return state
        except Exception as e:
            logger.error(f"Error al cargar estado: {e}")
            
        # Estado por defecto
        return {
            "turno": 0,
            "ultimo_dia_realizado": None,
            "recordando": False,
            "chat_id": None
        }
    
    def _save_state(self):
        """Guarda el estado en archivo"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2, default=str)
                logger.debug("Estado guardado en archivo")
        except Exception as e:
            logger.error(f"Error al guardar estado: {e}")
    
    def get_current_turn(self) -> int:
        """Obtiene el turno actual"""
        return self.state.get("turno", 0)
    
    def switch_turn(self):
        """Cambia el turno"""
        current = self.state.get("turno", 0)
        self.state["turno"] = 1 - current  # Alterna entre 0 y 1
        self._save_state()
        logger.info(f"Turno cambiado a: {self.state['turno']}")
    
    def get_last_day(self) -> Optional[date]:
        """Obtiene la última fecha de realización"""
        last_day_str = self.state.get("ultimo_dia_realizado")
        if last_day_str:
            try:
                return date.fromisoformat(last_day_str)
            except (ValueError, TypeError):
                logger.warning(f"Fecha inválida en estado: {last_day_str}")
        return None
    
    def mark_done(self, day: date):
        """Marca la tarea como realizada en una fecha"""
        self.state["ultimo_dia_realizado"] = day.isoformat()
        self._save_state()
        logger.info(f"Tarea marcada como realizada: {day}")
    
    def is_done_today(self, today: date) -> bool:
        """Verifica si la tarea ya se hizo hoy"""
        last_day = self.get_last_day()
        return last_day == today
    
    def is_reminding(self) -> bool:
        """Verifica si está en modo recordatorio"""
        return self.state.get("recordando", False)
    
    def start_reminding(self):
        """Inicia el modo recordatorio"""
        self.state["recordando"] = True
        self._save_state()
        logger.info("Modo recordatorio activado")
    
    def stop_reminding(self):
        """Detiene el modo recordatorio"""
        self.state["recordando"] = False
        self._save_state()
        logger.info("Modo recordatorio desactivado")
    
    def get_chat_id(self) -> Optional[int]:
        """Obtiene el chat ID"""
        return self.state.get("chat_id")
    
    def set_chat_id(self, chat_id: int):
        """Establece el chat ID"""
        self.state["chat_id"] = chat_id
        self._save_state()
        logger.info(f"Chat ID establecido: {chat_id}")
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Obtiene un resumen del estado"""
        return {
            "turno": self.get_current_turn(),
            "ultimo_dia": self.get_last_day(),
            "recordando": self.is_reminding(),
            "chat_id": self.get_chat_id()
        }
