"""
Utilidades del bot de Telegram
"""

import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Optional

def setup_logging(
    log_file: str = "telegram_bot.log",
    log_level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5
) -> logging.Logger:
    """Configura el sistema de logging"""
    
    # Crear logger principal
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Formato de logs
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para archivo con rotación
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    logger.info("Sistema de logging configurado")
    return logger

def is_valid_time_for_reminder(now: datetime, start_hour: int = 8, end_hour: int = 22) -> bool:
    """Verifica si es un horario válido para enviar recordatorios"""
    return start_hour <= now.hour <= end_hour

def format_date_chile(date_obj: datetime) -> str:
    """Formatea una fecha para mostrar en Chile"""
    return date_obj.strftime("%d/%m/%Y %H:%M")

def safe_file_write(file_path: str, content: str) -> bool:
    """Escribe archivo de forma segura"""
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        logging.error(f"Error al escribir archivo {file_path}: {e}")
        return False

def safe_file_read(file_path: str) -> Optional[str]:
    """Lee archivo de forma segura"""
    try:
        path = Path(file_path)
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        logging.error(f"Error al leer archivo {file_path}: {e}")
    return None

def validate_telegram_token(token: str) -> bool:
    """Valida formato básico del token de Telegram"""
    if not token or len(token) < 10:
        return False
    
    # Formato básico: número:string
    parts = token.split(':')
    if len(parts) != 2:
        return False
    
    try:
        int(parts[0])  # Primera parte debe ser número
        return len(parts[1]) > 10  # Segunda parte debe tener longitud razonable
    except ValueError:
        return False

def get_user_display_name(user) -> str:
    """Obtiene el nombre a mostrar del usuario"""
    if user.first_name:
        return user.first_name
    elif user.username:
        return f"@{user.username}"
    else:
        return f"Usuario {user.id}"

def create_status_message(
    current_person: str,
    last_day: Optional[str],
    is_reminding: bool,
    chat_id: Optional[int],
    personas: list
) -> str:
    """Crea mensaje de estado formateado"""
    status = "🔔 Recordando" if is_reminding else "😴 Esperando"
    
    message = f"""📊 **Estado del Bot**

👤 **Turno actual:** {current_person}
📅 **Último día realizado:** {last_day or 'Nunca'}
🔔 **Estado:** {status}
💬 **Chat ID:** {chat_id or 'No configurado'}

👥 **Personas registradas:**
"""
    
    for i, persona in enumerate(personas):
        icon = "👉" if persona == current_person else "   "
        message += f"{icon} {persona}\n"
    
    return message
