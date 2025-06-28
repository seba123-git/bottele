#!/usr/bin/env python3
"""
Bot de Telegram para recordatorios de tareas - Versión final
Recordatorios cada 3 horas con zona horaria chilena
Sistema anti-crash con reintentos automáticos
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
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes
from telegram.error import NetworkError, TimedOut, Forbidden

# Configuración de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('telegram_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuración
TOKEN = "8078347729:AAGME0GBMgLh4AgvdF1ChtbWxLW4sRvfS1M"
PERSONAS = ["Sebastián", "Francisca"]
TIMEZONE = pytz.timezone('America/Santiago')
STATE_FILE = "bot_state.json"

class BotState:
    """Maneja el estado persistente del bot"""
    
    def __init__(self):
        self.state = self.load_state()
    
    def load_state(self) -> Dict[str, Any]:
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error cargando estado: {e}")
        
        return {
            "turno": 0,
            "ultimo_dia_realizado": None,
            "recordando": False,
            "chat_id": None
        }
    
    def save_state(self):
        try:
            with open(STATE_FILE, 'w', encoding='utf-8') as f:
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

# Estado global
bot_state = BotState()

class TelegramBot:
    def __init__(self):
        self.app = None
        self.chat_id = bot_state.get_chat_id()
        self.running = False
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start"""
        try:
            self.chat_id = update.effective_chat.id
            bot_state.set_chat_id(self.chat_id)
            
            current_person = PERSONAS[bot_state.get_current_turn()]
            last_day = bot_state.get_last_day()
            
            message = (
                f"🤖 Bot de recordatorios activado!\n\n"
                f"👤 Turno actual: {current_person}\n"
                f"📅 Último día: {last_day.strftime('%d/%m/%Y') if last_day else 'Nunca'}\n\n"
                f"Comandos:\n"
                f"/start - Iniciar bot\n"
                f"/hecho - Marcar tarea realizada\n"
                f"/status - Ver estado\n"
                f"/help - Ayuda\n\n"
                f"⏰ Recordatorios cada 3 horas (8 AM - 10 PM)"
            )
            
            await update.message.reply_text(message)
            logger.info(f"Bot iniciado en chat {self.chat_id}")
            
        except Exception as e:
            logger.error(f"Error en /start: {e}")
    
    async def hecho_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /hecho"""
        try:
            user = update.effective_user
            user_name = user.first_name or user.username or str(user.id)
            
            current_turn = bot_state.get_current_turn()
            expected_person = PERSONAS[current_turn]
            
            # Verificar usuario
            if user_name.lower() != expected_person.lower():
                await update.message.reply_text(
                    f"❌ No es tu turno, {user_name}.\n"
                    f"El turno actual es de: {expected_person}"
                )
                return
            
            # Verificar si ya se hizo hoy
            now = datetime.now(TIMEZONE)
            today = now.date()
            
            if bot_state.is_done_today(today):
                await update.message.reply_text("✅ Ya marcaste la tarea como realizada hoy.")
                return
            
            # Marcar como realizado
            bot_state.mark_done(today)
            bot_state.switch_turn()
            bot_state.stop_reminding()
            
            next_person = PERSONAS[bot_state.get_current_turn()]
            
            message = (
                f"✅ ¡Gracias {user_name}! Tarea realizada.\n"
                f"🔄 Turno cambiado a: {next_person}\n"
                f"📅 Fecha: {today.strftime('%d/%m/%Y')}"
            )
            
            await update.message.reply_text(message)
            logger.info(f"Tarea marcada por {user_name}, turno cambiado a {next_person}")
            
        except Exception as e:
            logger.error(f"Error en /hecho: {e}")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /status"""
        try:
            current_person = PERSONAS[bot_state.get_current_turn()]
            last_day = bot_state.get_last_day()
            is_reminding = bot_state.is_reminding()
            
            now = datetime.now(TIMEZONE)
            
            message = (
                f"📊 Estado actual:\n\n"
                f"👤 Turno: {current_person}\n"
                f"📅 Último día: {last_day.strftime('%d/%m/%Y') if last_day else 'Nunca'}\n"
                f"🔔 Recordando: {'Sí' if is_reminding else 'No'}\n"
                f"🕐 Hora (Chile): {now.strftime('%d/%m/%Y %H:%M')}\n\n"
                f"Personas:\n"
            )
            
            for i, persona in enumerate(PERSONAS):
                icon = "👉" if i == bot_state.get_current_turn() else "   "
                message += f"{icon} {persona}\n"
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Error en /status: {e}")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /help"""
        message = (
            f"🤖 Bot de Recordatorios\n\n"
            f"Comandos:\n"
            f"/start - Iniciar el bot\n"
            f"/hecho - Marcar tarea realizada\n"
            f"/status - Ver estado actual\n"
            f"/help - Mostrar ayuda\n\n"
            f"👥 Personas: {', '.join(PERSONAS)}\n"
            f"⏰ Recordatorios cada 3 horas (8 AM - 10 PM)\n"
            f"🌍 Zona horaria: Chile\n\n"
            f"El bot recuerda automáticamente cuando es tu turno."
        )
        await update.message.reply_text(message)
    
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
            last_day = bot_state.get_last_day()
            current_person = PERSONAS[bot_state.get_current_turn()]
            
            needs_reminder = False
            message_text = ""
            
            if last_day is None:
                needs_reminder = True
                message_text = (
                    f"🔔 ¡Hola {current_person}!\n"
                    f"Es tu turno para recoger las cacas 💩\n"
                    f"Marca /hecho cuando termines"
                )
            elif last_day < today:
                needs_reminder = True
                days_passed = (today - last_day).days
                if days_passed == 1:
                    message_text = (
                        f"🔔 Recordatorio: {current_person}\n"
                        f"Te toca recoger las cacas 💩\n"
                        f"Última vez: {last_day.strftime('%d/%m/%Y')}\n"
                        f"Marca /hecho cuando termines"
                    )
                else:
                    message_text = (
                        f"⚠️ URGENTE: {current_person}\n"
                        f"Han pasado {days_passed} días sin recoger las cacas 💩\n"
                        f"Última vez: {last_day.strftime('%d/%m/%Y')}\n"
                        f"¡Por favor hazlo ya y marca /hecho!"
                    )
            elif last_day == today:
                if bot_state.is_reminding():
                    bot_state.stop_reminding()
                    logger.info("Tarea completada hoy, recordatorios detenidos")
                return
            
            if needs_reminder:
                if not bot_state.is_reminding():
                    bot_state.start_reminding()
                
                await context.bot.send_message(
                    chat_id=self.chat_id,
                    text=message_text
                )
                
                logger.info(f"Recordatorio enviado a {current_person}")
                
        except Forbidden:
            logger.error("Bot bloqueado por el usuario")
        except Exception as e:
            logger.error(f"Error enviando recordatorio: {e}")

# Instancia global del bot
telegram_bot = TelegramBot()

async def reminder_task():
    """Tarea de recordatorios que se ejecuta en segundo plano"""
    while True:
        try:
            await telegram_bot.send_reminder(type('Context', (), {'bot': telegram_bot.app.bot})())
        except Exception as e:
            logger.error(f"Error en tarea de recordatorio: {e}")
        
        # Esperar 3 horas
        await asyncio.sleep(10800)

def signal_handler(signum, frame):
    """Maneja señales de cierre"""
    logger.info(f"Señal recibida: {signum}")
    sys.exit(0)

async def main():
    """Función principal"""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    retry_count = 0
    max_retries = 10
    
    while retry_count < max_retries:
        try:
            logger.info(f"Iniciando bot (intento {retry_count + 1})")
            
            # Crear aplicación
            telegram_bot.app = ApplicationBuilder().token(TOKEN).build()
            
            # Registrar comandos
            telegram_bot.app.add_handler(CommandHandler("start", telegram_bot.start_command))
            telegram_bot.app.add_handler(CommandHandler("hecho", telegram_bot.hecho_command))
            telegram_bot.app.add_handler(CommandHandler("status", telegram_bot.status_command))
            telegram_bot.app.add_handler(CommandHandler("help", telegram_bot.help_command))
            
            # Cargar chat_id si existe
            if bot_state.get_chat_id():
                telegram_bot.chat_id = bot_state.get_chat_id()
            
            logger.info("Bot configurado correctamente")
            telegram_bot.running = True
            
            # Iniciar tarea de recordatorios en segundo plano
            reminder_task_handle = asyncio.create_task(reminder_task())
            
            # Iniciar polling
            logger.info("Iniciando polling...")
            await telegram_bot.app.run_polling(drop_pending_updates=True)
            
        except KeyboardInterrupt:
            logger.info("Bot detenido por el usuario")
            break
            
        except (NetworkError, TimedOut) as e:
            retry_count += 1
            delay = min(60, 10 * retry_count)
            logger.warning(f"Error de red: {e}. Reintentando en {delay}s...")
            await asyncio.sleep(delay)
            
        except Exception as e:
            retry_count += 1
            delay = min(60, 10 * retry_count)
            logger.error(f"Error: {e}. Reintentando en {delay}s...")
            await asyncio.sleep(delay)
    
    logger.info("Bot finalizado después de múltiples intentos")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Programa interrumpido")
    except Exception as e:
        logger.error(f"Error fatal: {e}")