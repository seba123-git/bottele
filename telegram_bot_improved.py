#!/usr/bin/env python3
"""
Bot mejorado de Telegram para recordatorios de tareas
Versión robusta con recordatorios cada 3 horas y manejo de errores
Compatible con zona horaria chilena
"""

import asyncio
import json
import logging
import os
import signal
import sys
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any

import pytz
from telegram import Update
from telegram.ext import (
    Application, 
    ApplicationBuilder, 
    CommandHandler, 
    ContextTypes
)
from telegram.error import NetworkError, TimedOut, BadRequest, Forbidden

# Configuración básica
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('telegram_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Variables globales
TOKEN = os.getenv("TELEGRAM_TOKEN", "TU_TOKEN_AQUI")
PERSONAS = ["Sebastián", "Francisca"]
TIMEZONE = pytz.timezone('America/Santiago')
STATE_FILE = "bot_state.json"

class BotStateManager:
    """Maneja el estado persistente del bot"""
    
    def __init__(self, filename: str = STATE_FILE):
        self.filename = filename
        self.state = self.load_state()
    
    def load_state(self) -> Dict[str, Any]:
        """Carga el estado desde archivo"""
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error cargando estado: {e}")
        
        # Estado por defecto
        return {
            "turno": 0,
            "ultimo_dia_realizado": None,
            "recordando": False,
            "chat_id": None
        }
    
    def save_state(self):
        """Guarda el estado en archivo"""
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error guardando estado: {e}")
    
    def get_current_turn(self) -> int:
        return self.state.get("turno", 0)
    
    def switch_turn(self):
        self.state["turno"] = 1 - self.state["turno"]
        self.save_state()
    
    def get_last_day(self) -> Optional[date]:
        last_day_str = self.state.get("ultimo_dia_realizado")
        if last_day_str:
            try:
                return date.fromisoformat(last_day_str)
            except (ValueError, TypeError):
                return None
        return None
    
    def mark_done(self, day: date):
        self.state["ultimo_dia_realizado"] = day.isoformat()
        self.save_state()
    
    def is_done_today(self, today: date) -> bool:
        last_day = self.get_last_day()
        return last_day == today if last_day else False
    
    def is_reminding(self) -> bool:
        return self.state.get("recordando", False)
    
    def start_reminding(self):
        self.state["recordando"] = True
        self.save_state()
    
    def stop_reminding(self):
        self.state["recordando"] = False
        self.save_state()
    
    def get_chat_id(self) -> Optional[int]:
        return self.state.get("chat_id")
    
    def set_chat_id(self, chat_id: int):
        self.state["chat_id"] = chat_id
        self.save_state()

class TelegramBot:
    """Bot principal de Telegram"""
    
    def __init__(self):
        self.state = BotStateManager()
        self.app = None
        self.running = False
        self.chat_id = None
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start"""
        try:
            self.chat_id = update.effective_chat.id
            self.state.set_chat_id(self.chat_id)
            
            current_person = PERSONAS[self.state.get_current_turn()]
            last_day = self.state.get_last_day()
            
            message = (
                f"🤖 Bot de recordatorios activado!\n\n"
                f"👤 Turno actual: {current_person}\n"
                f"📅 Último día realizado: {last_day.strftime('%d/%m/%Y') if last_day else 'Nunca'}\n\n"
                f"Comandos:\n"
                f"/start - Iniciar bot\n"
                f"/hecho - Marcar tarea realizada\n"
                f"/status - Ver estado actual\n"
                f"/help - Mostrar ayuda\n\n"
                f"⏰ Recordatorios cada 3 horas (8 AM - 10 PM)"
            )
            
            await update.message.reply_text(message)
            logger.info(f"Bot iniciado en chat {self.chat_id}")
            
        except Exception as e:
            logger.error(f"Error en /start: {e}")
            await self.send_error_message(update, "Error al iniciar bot")
    
    async def hecho_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /hecho"""
        try:
            user = update.effective_user
            user_name = user.first_name or user.username or str(user.id)
            
            current_turn = self.state.get_current_turn()
            expected_person = PERSONAS[current_turn]
            
            # Verificar usuario
            if not self.is_correct_user(user_name, expected_person):
                await update.message.reply_text(
                    f"❌ No es tu turno, {user_name}.\n"
                    f"El turno actual es de: {expected_person}"
                )
                return
            
            # Verificar si ya se hizo hoy
            now = datetime.now(TIMEZONE)
            today = now.date()
            
            if self.state.is_done_today(today):
                await update.message.reply_text("✅ Ya marcaste la tarea como realizada hoy.")
                return
            
            # Marcar como realizado
            self.state.mark_done(today)
            self.state.switch_turn()
            self.state.stop_reminding()
            
            next_person = PERSONAS[self.state.get_current_turn()]
            
            message = (
                f"✅ ¡Gracias {user_name}! Tarea marcada como realizada.\n"
                f"🔄 Turno cambiado a: {next_person}\n"
                f"📅 Fecha: {today.strftime('%d/%m/%Y')}"
            )
            
            await update.message.reply_text(message)
            logger.info(f"Tarea marcada por {user_name}, turno cambiado a {next_person}")
            
        except Exception as e:
            logger.error(f"Error en /hecho: {e}")
            await self.send_error_message(update, "Error al marcar tarea")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /status"""
        try:
            current_person = PERSONAS[self.state.get_current_turn()]
            last_day = self.state.get_last_day()
            is_reminding = self.state.is_reminding()
            
            now = datetime.now(TIMEZONE)
            
            message = (
                f"📊 Estado actual:\n\n"
                f"👤 Turno: {current_person}\n"
                f"📅 Último día: {last_day.strftime('%d/%m/%Y') if last_day else 'Nunca'}\n"
                f"🔔 Recordando: {'Sí' if is_reminding else 'No'}\n"
                f"🕐 Hora actual (Chile): {now.strftime('%d/%m/%Y %H:%M')}\n\n"
                f"Personas:\n"
            )
            
            for i, persona in enumerate(PERSONAS):
                icon = "👉" if i == self.state.get_current_turn() else "   "
                message += f"{icon} {persona}\n"
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Error en /status: {e}")
            await self.send_error_message(update, "Error al obtener estado")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /help"""
        message = (
            f"🤖 Bot de Recordatorios - Ayuda\n\n"
            f"Comandos disponibles:\n"
            f"/start - Iniciar el bot\n"
            f"/hecho - Marcar tarea como realizada\n"
            f"/status - Ver estado actual\n"
            f"/help - Mostrar esta ayuda\n\n"
            f"👥 Personas: {', '.join(PERSONAS)}\n"
            f"⏰ Recordatorios: Cada 3 horas (8 AM - 10 PM)\n"
            f"🌍 Zona horaria: Chile (Santiago)\n\n"
            f"El bot recuerda automáticamente cuando es tu turno."
        )
        await update.message.reply_text(message)
    
    def is_correct_user(self, user_name: str, expected_person: str) -> bool:
        """Verifica si el usuario es correcto"""
        if not user_name:
            return False
        return user_name.lower() == expected_person.lower()
    
    async def send_error_message(self, update: Update, message: str):
        """Envía mensaje de error de forma segura"""
        try:
            await update.message.reply_text(f"❌ {message}")
        except Exception as e:
            logger.error(f"Error enviando mensaje de error: {e}")
    
    async def send_reminder(self, context):
        """Envía recordatorios periódicos"""
        try:
            if not self.chat_id:
                logger.warning("No hay chat_id para recordatorios")
                return
            
            now = datetime.now(TIMEZONE)
            
            # Solo entre 8 AM y 10 PM
            if not (8 <= now.hour <= 22):
                logger.debug(f"Horario no apropiado: {now.hour}:00")
                return
            
            today = now.date()
            last_day = self.state.get_last_day()
            current_person = PERSONAS[self.state.get_current_turn()]
            
            # Determinar si necesita recordatorio
            needs_reminder = False
            message_type = ""
            
            if last_day is None:
                needs_reminder = True
                message_type = "first_time"
            elif last_day < today:
                needs_reminder = True
                days_passed = (today - last_day).days
                message_type = "daily" if days_passed == 1 else "overdue"
            elif last_day == today:
                if self.state.is_reminding():
                    self.state.stop_reminding()
                    logger.info("Tarea completada hoy, recordatorios detenidos")
                return
            
            if needs_reminder:
                if not self.state.is_reminding():
                    self.state.start_reminding()
                
                # Crear mensaje
                if message_type == "first_time":
                    message = (
                        f"🔔 ¡Hola {current_person}!\n"
                        f"Es tu turno para recoger las cacas 💩\n"
                        f"Cuando termines, marca /hecho"
                    )
                elif message_type == "daily":
                    message = (
                        f"🔔 Recordatorio: {current_person}\n"
                        f"Te toca recoger las cacas 💩\n"
                        f"Última vez: {last_day.strftime('%d/%m/%Y')}\n"
                        f"Marca /hecho cuando termines"
                    )
                elif message_type == "overdue":
                    days_passed = (today - last_day).days
                    message = (
                        f"⚠️ URGENTE: {current_person}\n"
                        f"Han pasado {days_passed} días sin recoger las cacas 💩\n"
                        f"Última vez: {last_day.strftime('%d/%m/%Y')}\n"
                        f"¡Por favor hazlo ya y marca /hecho!"
                    )
                
                await context.bot.send_message(
                    chat_id=self.chat_id,
                    text=message
                )
                
                logger.info(f"Recordatorio ({message_type}) enviado a {current_person}")
                
        except Forbidden:
            logger.error("Bot bloqueado por el usuario")
        except Exception as e:
            logger.error(f"Error enviando recordatorio: {e}")
    
    async def start_bot(self):
        """Inicia el bot"""
        try:
            if TOKEN == "TU_TOKEN_AQUI":
                logger.error("Token no configurado. Configura TELEGRAM_TOKEN")
                return
            
            # Crear aplicación
            self.app = ApplicationBuilder().token(TOKEN).build()
            
            # Registrar comandos
            self.app.add_handler(CommandHandler("start", self.start_command))
            self.app.add_handler(CommandHandler("hecho", self.hecho_command))
            self.app.add_handler(CommandHandler("status", self.status_command))
            self.app.add_handler(CommandHandler("help", self.help_command))
            
            # Configurar recordatorios cada 3 horas
            job_queue = self.app.job_queue
            if job_queue:
                job_queue.run_repeating(
                    self.send_reminder,
                    interval=timedelta(hours=3),
                    first=timedelta(seconds=10)
                )
            
            # Cargar chat_id si existe
            if self.state.get_chat_id():
                self.chat_id = self.state.get_chat_id()
            
            logger.info("Bot iniciado correctamente")
            self.running = True
            
            # Iniciar polling
            await self.app.run_polling(drop_pending_updates=True)
            
        except Exception as e:
            logger.error(f"Error iniciando bot: {e}")
            raise
    
    async def stop_bot(self):
        """Detiene el bot"""
        try:
            self.running = False
            if self.app:
                await self.app.stop()
                logger.info("Bot detenido correctamente")
        except Exception as e:
            logger.error(f"Error deteniendo bot: {e}")

# Instancia global
telegram_bot = TelegramBot()

def signal_handler(signum, frame):
    """Maneja señales de cierre"""
    logger.info(f"Señal recibida: {signum}")
    asyncio.create_task(telegram_bot.stop_bot())
    sys.exit(0)

async def main():
    """Función principal con reintentos automáticos"""
    # Configurar señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    max_retries = 5
    retry_delay = 10
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Iniciando bot (intento {attempt + 1}/{max_retries})")
            await telegram_bot.start_bot()
            
        except KeyboardInterrupt:
            logger.info("Bot detenido por el usuario")
            break
            
        except (NetworkError, TimedOut) as e:
            logger.warning(f"Error de red: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Reintentando en {retry_delay} segundos...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
            else:
                logger.error("Máximo de reintentos alcanzado")
                break
                
        except Exception as e:
            logger.error(f"Error crítico: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Reintentando en {retry_delay} segundos...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
            else:
                logger.error("Máximo de reintentos alcanzado")
                break
    
    logger.info("Bot finalizado")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Programa interrumpido")
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        sys.exit(1)