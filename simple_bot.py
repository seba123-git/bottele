#!/usr/bin/env python3
"""
Bot simple de Telegram para recordatorios
Versión estable sin conflictos de bucle de eventos
"""

import asyncio
import json
import logging
import os
from datetime import datetime, date
from typing import Optional, Dict, Any

import pytz
from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes
from telegram.error import NetworkError, TimedOut, Forbidden

# Logging simple
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración
TOKEN = "8078347729:AAGME0GBMgLh4AgvdF1ChtbWxLW4sRvfS1M"
PERSONAS = ["Sebastián", "Francisca"]
TIMEZONE = pytz.timezone('America/Santiago')

class SimpleState:
    def __init__(self):
        self.data = {"turno": 0, "ultimo_dia": None, "chat_id": None}
        self.load()
    
    def load(self):
        try:
            if os.path.exists("state.json"):
                with open("state.json", "r") as f:
                    self.data = json.load(f)
        except:
            pass
    
    def save(self):
        try:
            with open("state.json", "w") as f:
                json.dump(self.data, f)
        except:
            pass
    
    def get_turn(self):
        return self.data.get("turno", 0)
    
    def switch_turn(self):
        self.data["turno"] = 1 - self.data["turno"]
        self.save()
    
    def mark_done(self, day):
        self.data["ultimo_dia"] = day.isoformat()
        self.save()
    
    def get_last_day(self):
        last = self.data.get("ultimo_dia")
        if last:
            try:
                return date.fromisoformat(last)
            except:
                return None
        return None
    
    def set_chat_id(self, chat_id):
        self.data["chat_id"] = chat_id
        self.save()
    
    def get_chat_id(self):
        return self.data.get("chat_id")

state = SimpleState()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    chat_id = update.effective_chat.id
    state.set_chat_id(chat_id)
    
    current_person = PERSONAS[state.get_turn()]
    last_day = state.get_last_day()
    
    message = (
        f"🤖 Bot activado!\n\n"
        f"👤 Turno: {current_person}\n"
        f"📅 Último día: {last_day.strftime('%d/%m/%Y') if last_day else 'Nunca'}\n\n"
        f"Comandos:\n"
        f"/start - Iniciar\n"
        f"/hecho - Marcar realizada\n"
        f"/status - Ver estado\n"
        f"/help - Ayuda"
    )
    
    await update.message.reply_text(message)
    logger.info(f"Bot iniciado en chat {chat_id}")

async def hecho_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /hecho"""
    user = update.effective_user
    user_name = user.first_name or user.username or str(user.id)
    
    current_turn = state.get_turn()
    expected_person = PERSONAS[current_turn]
    
    if user_name.lower() != expected_person.lower():
        await update.message.reply_text(f"❌ No es tu turno {user_name}. Le toca a {expected_person}")
        return
    
    today = datetime.now(TIMEZONE).date()
    last_day = state.get_last_day()
    
    if last_day == today:
        await update.message.reply_text("✅ Ya se marcó hoy")
        return
    
    state.mark_done(today)
    state.switch_turn()
    
    next_person = PERSONAS[state.get_turn()]
    
    message = (
        f"✅ ¡Gracias {user_name}!\n"
        f"🔄 Ahora le toca a: {next_person}\n"
        f"📅 {today.strftime('%d/%m/%Y')}"
    )
    
    await update.message.reply_text(message)
    logger.info(f"Tarea marcada por {user_name}")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /status"""
    current_person = PERSONAS[state.get_turn()]
    last_day = state.get_last_day()
    now = datetime.now(TIMEZONE)
    
    message = (
        f"📊 Estado:\n\n"
        f"👤 Turno: {current_person}\n"
        f"📅 Último día: {last_day.strftime('%d/%m/%Y') if last_day else 'Nunca'}\n"
        f"🕐 Hora Chile: {now.strftime('%d/%m/%Y %H:%M')}\n\n"
        f"Personas:\n"
    )
    
    for i, persona in enumerate(PERSONAS):
        icon = "👉" if i == state.get_turn() else "   "
        message += f"{icon} {persona}\n"
    
    await update.message.reply_text(message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help"""
    message = (
        f"🤖 Bot de Recordatorios\n\n"
        f"Comandos:\n"
        f"/start - Iniciar bot\n"
        f"/hecho - Marcar tarea realizada\n"
        f"/status - Ver estado\n"
        f"/help - Ayuda\n\n"
        f"👥 Personas: {', '.join(PERSONAS)}\n"
        f"🌍 Zona horaria: Chile"
    )
    await update.message.reply_text(message)

async def reminder_job(context: ContextTypes.DEFAULT_TYPE):
    """Envía recordatorios"""
    chat_id = state.get_chat_id()
    if not chat_id:
        return
    
    now = datetime.now(TIMEZONE)
    
    # Solo entre 8 AM y 10 PM
    if not (8 <= now.hour <= 22):
        return
    
    today = now.date()
    last_day = state.get_last_day()
    current_person = PERSONAS[state.get_turn()]
    
    if last_day is None or last_day < today:
        days_passed = 0 if last_day is None else (today - last_day).days
        
        if days_passed <= 1:
            message = f"🔔 {current_person}, te toca recoger las cacas 💩\nMarca /hecho cuando termines"
        else:
            message = f"⚠️ {current_person}, han pasado {days_passed} días!\nRecoger las cacas 💩 y marca /hecho"
        
        try:
            await context.bot.send_message(chat_id=chat_id, text=message)
            logger.info(f"Recordatorio enviado a {current_person}")
        except Exception as e:
            logger.error(f"Error enviando recordatorio: {e}")

def main():
    """Función principal simple"""
    logger.info("Iniciando bot de Telegram...")
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Registrar comandos
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("hecho", hecho_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("help", help_command))
    
    # Configurar recordatorios cada 3 horas
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(reminder_job, interval=10800, first=30)
    
    logger.info("Bot configurado. Iniciando polling...")
    
    # Ejecutar bot
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()