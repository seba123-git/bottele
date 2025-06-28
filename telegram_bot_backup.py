#!/usr/bin/env python3
"""
Bot de Telegram para Recordatorios - Backup Principal
Versión estable y funcional con todas las características
"""

import json
import logging
import os
from datetime import datetime, date
from typing import Optional

import pytz
from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuración principal
TOKEN = "TU_TOKEN_AQUI"  # Reemplazar con tu token
PERSONAS = ["Sebastián", "Francisca"]
TIMEZONE = pytz.timezone('America/Santiago')

class SimpleState:
    """Manejo simple del estado del bot"""
    
    def __init__(self):
        self.data = {"turno": 0, "ultimo_dia": None, "chat_id": None}
        self.load()
    
    def load(self):
        """Carga el estado desde archivo JSON"""
        try:
            if os.path.exists("state.json"):
                with open("state.json", "r", encoding='utf-8') as f:
                    self.data = json.load(f)
                    logger.info("Estado cargado correctamente")
        except Exception as e:
            logger.warning(f"Error cargando estado: {e}")
    
    def save(self):
        """Guarda el estado en archivo JSON"""
        try:
            with open("state.json", "w", encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error guardando estado: {e}")
    
    def get_turn(self):
        """Obtiene el turno actual (0 o 1)"""
        return self.data.get("turno", 0)
    
    def switch_turn(self):
        """Cambia al siguiente turno"""
        self.data["turno"] = 1 - self.data["turno"]
        self.save()
        logger.info(f"Turno cambiado a: {PERSONAS[self.data['turno']]}")
    
    def mark_done(self, day):
        """Marca la tarea como realizada en una fecha"""
        self.data["ultimo_dia"] = day.isoformat()
        self.save()
        logger.info(f"Tarea marcada como realizada: {day}")
    
    def get_last_day(self):
        """Obtiene la última fecha de realización"""
        last = self.data.get("ultimo_dia")
        if last:
            try:
                return date.fromisoformat(last)
            except:
                return None
        return None
    
    def set_chat_id(self, chat_id):
        """Establece el ID del chat principal"""
        self.data["chat_id"] = chat_id
        self.save()
        logger.info(f"Chat ID configurado: {chat_id}")
    
    def get_chat_id(self):
        """Obtiene el ID del chat principal"""
        return self.data.get("chat_id")

# Instancia global del estado
state = SimpleState()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start - Inicia el bot y muestra estado"""
    try:
        chat_id = update.effective_chat.id
        state.set_chat_id(chat_id)
        
        current_person = PERSONAS[state.get_turn()]
        last_day = state.get_last_day()
        now = datetime.now(TIMEZONE)
        
        message = (
            f"🤖 Bot de Recordatorios Activado\n\n"
            f"👤 Turno actual: {current_person}\n"
            f"📅 Último día realizado: {last_day.strftime('%d/%m/%Y') if last_day else 'Nunca'}\n"
            f"🕐 Hora actual (Chile): {now.strftime('%d/%m/%Y %H:%M')}\n\n"
            f"📋 Comandos disponibles:\n"
            f"/start - Mostrar este mensaje\n"
            f"/hecho - Marcar tarea realizada\n"
            f"/status - Ver estado detallado\n"
            f"/help - Mostrar ayuda\n\n"
            f"⏰ Recordatorios cada 3 horas (8 AM - 10 PM)"
        )
        
        await update.message.reply_text(message)
        logger.info(f"Bot iniciado por usuario en chat {chat_id}")
        
    except Exception as e:
        logger.error(f"Error en comando start: {e}")
        await update.message.reply_text("❌ Error iniciando el bot")

async def hecho_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /hecho - Marca la tarea como realizada"""
    try:
        user = update.effective_user
        user_name = user.first_name or user.username or str(user.id)
        
        current_turn = state.get_turn()
        expected_person = PERSONAS[current_turn]
        
        # Verificar si es el turno correcto
        if user_name.lower() != expected_person.lower():
            await update.message.reply_text(
                f"❌ No es tu turno, {user_name}\n"
                f"Le toca a: {expected_person}"
            )
            return
        
        today = datetime.now(TIMEZONE).date()
        last_day = state.get_last_day()
        
        # Verificar si ya se marcó hoy
        if last_day == today:
            await update.message.reply_text("✅ Ya se marcó como realizada hoy")
            return
        
        # Marcar como realizada y cambiar turno
        state.mark_done(today)
        state.switch_turn()
        
        next_person = PERSONAS[state.get_turn()]
        
        message = (
            f"✅ ¡Perfecto, {user_name}!\n"
            f"📅 Tarea realizada: {today.strftime('%d/%m/%Y')}\n"
            f"🔄 Ahora le toca a: {next_person}\n\n"
            f"¡Gracias por ser responsable! 🎉"
        )
        
        await update.message.reply_text(message)
        logger.info(f"Tarea marcada por {user_name}, turno cambiado a {next_person}")
        
    except Exception as e:
        logger.error(f"Error en comando hecho: {e}")
        await update.message.reply_text("❌ Error procesando comando")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /status - Muestra el estado detallado"""
    try:
        current_person = PERSONAS[state.get_turn()]
        last_day = state.get_last_day()
        now = datetime.now(TIMEZONE)
        
        # Calcular días desde la última vez
        if last_day:
            days_ago = (now.date() - last_day).days
            if days_ago == 0:
                last_status = "Hoy ✅"
            elif days_ago == 1:
                last_status = "Ayer"
            else:
                last_status = f"Hace {days_ago} días"
        else:
            last_status = "Nunca ❌"
        
        message = (
            f"📊 Estado del Bot\n\n"
            f"👤 Turno actual: {current_person}\n"
            f"📅 Última realización: {last_status}\n"
            f"🕐 Hora Chile: {now.strftime('%d/%m/%Y %H:%M')}\n\n"
            f"👥 Rotación de personas:\n"
        )
        
        for i, persona in enumerate(PERSONAS):
            icon = "👉" if i == state.get_turn() else "   "
            message += f"{icon} {persona}\n"
        
        message += f"\n⏰ Próximo recordatorio: Cada 3 horas (8 AM - 10 PM)"
        
        await update.message.reply_text(message)
        logger.info("Estado consultado")
        
    except Exception as e:
        logger.error(f"Error en comando status: {e}")
        await update.message.reply_text("❌ Error obteniendo estado")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help - Muestra ayuda detallada"""
    try:
        message = (
            f"🤖 Bot de Recordatorios de Tareas\n\n"
            f"📝 Descripción:\n"
            f"Este bot ayuda a {' y '.join(PERSONAS)} a recordar "
            f"alternar la responsabilidad de recoger las cacas.\n\n"
            f"📋 Comandos:\n"
            f"/start - Iniciar bot y ver estado\n"
            f"/hecho - Marcar tarea realizada (solo quien tiene el turno)\n"
            f"/status - Ver estado detallado\n"
            f"/help - Mostrar esta ayuda\n\n"
            f"⚙️ Características:\n"
            f"• Recordatorios automáticos cada 3 horas\n"
            f"• Horario: 8 AM - 10 PM (Chile)\n"
            f"• Rotación automática de turnos\n"
            f"• Persistencia de datos\n\n"
            f"🌍 Zona horaria: América/Santiago (Chile)\n"
            f"👥 Personas: {', '.join(PERSONAS)}"
        )
        
        await update.message.reply_text(message)
        logger.info("Ayuda mostrada")
        
    except Exception as e:
        logger.error(f"Error en comando help: {e}")
        await update.message.reply_text("❌ Error mostrando ayuda")

async def reminder_job(context: ContextTypes.DEFAULT_TYPE):
    """Trabajo de recordatorios automáticos"""
    try:
        chat_id = state.get_chat_id()
        if not chat_id:
            logger.warning("No hay chat_id configurado para recordatorios")
            return
        
        now = datetime.now(TIMEZONE)
        
        # Solo enviar recordatorios entre 8 AM y 10 PM
        if not (8 <= now.hour <= 22):
            logger.info(f"Fuera del horario de recordatorios: {now.hour}:00")
            return
        
        today = now.date()
        last_day = state.get_last_day()
        current_person = PERSONAS[state.get_turn()]
        
        # Solo recordar si no se ha hecho hoy
        if last_day is None or last_day < today:
            days_passed = 0 if last_day is None else (today - last_day).days
            
            if days_passed == 0:
                urgency = "🔔"
                message = f"{urgency} {current_person}, te toca recoger las cacas 💩"
            elif days_passed == 1:
                urgency = "⚠️"
                message = f"{urgency} {current_person}, ¡ya es hora! Recoger las cacas 💩"
            else:
                urgency = "🚨"
                message = f"{urgency} {current_person}, ¡HAN PASADO {days_passed} DÍAS! Recoger las cacas 💩"
            
            message += f"\n\n📝 Marca /hecho cuando termines"
            
            await context.bot.send_message(chat_id=chat_id, text=message)
            logger.info(f"Recordatorio enviado a {current_person} (días: {days_passed})")
        else:
            logger.info("Tarea ya realizada hoy, no se envía recordatorio")
            
    except Exception as e:
        logger.error(f"Error en recordatorio automático: {e}")

def main():
    """Función principal del bot"""
    logger.info("=== Iniciando Bot de Telegram ===")
    
    if TOKEN == "TU_TOKEN_AQUI":
        logger.error("❌ Debes configurar tu TOKEN de Telegram")
        return
    
    try:
        # Crear aplicación
        app = ApplicationBuilder().token(TOKEN).build()
        
        # Registrar comandos
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("hecho", hecho_command))
        app.add_handler(CommandHandler("status", status_command))
        app.add_handler(CommandHandler("help", help_command))
        
        # Configurar recordatorios cada 3 horas
        job_queue = app.job_queue
        if job_queue:
            # Primer recordatorio después de 30 segundos, luego cada 3 horas
            job_queue.run_repeating(
                reminder_job, 
                interval=10800,  # 3 horas en segundos
                first=30
            )
            logger.info("Recordatorios configurados: cada 3 horas")
        
        logger.info("Bot configurado correctamente")
        logger.info("Iniciando polling...")
        
        # Ejecutar bot
        app.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
        
    except Exception as e:
        logger.error(f"Error crítico: {e}")
        raise

if __name__ == "__main__":
    main()