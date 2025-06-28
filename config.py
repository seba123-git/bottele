"""
Configuración del bot de Telegram
"""

import os
from typing import List

class Config:
    """Clase de configuración del bot"""
    
    def __init__(self):
        # Token del bot (obligatorio)
        self.TOKEN = os.getenv("TELEGRAM_TOKEN", "TU_TOKEN_AQUI")
        
        # Validar token
        if self.TOKEN == "TU_TOKEN_AQUI":
            raise ValueError(
                "Por favor configura el token del bot en la variable de entorno TELEGRAM_TOKEN "
                "o modifica el valor por defecto en config.py"
            )
        
        # Nombres de las personas (modificar según necesidad)
        self.PERSONAS: List[str] = ["Sebastián", "Francisca"]
        
        # Configuración de recordatorios
        self.REMINDER_INTERVAL_HOURS = 3
        self.REMINDER_START_HOUR = 8  # 8 AM
        self.REMINDER_END_HOUR = 22   # 10 PM
        
        # Archivos de persistencia
        self.STATE_FILE = "bot_state.json"
        self.LOG_FILE = "telegram_bot.log"
        
        # Configuración de logging
        self.LOG_LEVEL = "INFO"
        self.LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
        self.LOG_BACKUP_COUNT = 5
        
        # Chat ID por defecto (se puede obtener dinámicamente)
        self.DEFAULT_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", None)
        
    def validate(self) -> bool:
        """Valida la configuración"""
        if not self.TOKEN or self.TOKEN == "TU_TOKEN_AQUI":
            return False
            
        if not self.PERSONAS or len(self.PERSONAS) < 2:
            return False
            
        return True
