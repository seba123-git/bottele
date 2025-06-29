#!/usr/bin/env python3
"""
Bot simple de Telegram para recordatorios
Versión estable sin conflictos de bucle de eventos
"""

import json
import logging
import os
from datetime import datetime, date
from threading import Thread

import pytz
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Logging simple
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración
TOKEN = os.environ.get("TOKEN", "tu_token_aqui")  # Mejor usar variable de entorno en Railway
PERSONAS = ["Sebastián", "Francisca"]
TIMEZONE = pytz.timezone('America/Santiago')

class SimpleState:
    def __init__(self):
        self.data = {"turno": 0, "ultimo_dia": None, "chat_id": None, "usuarios_registrados": {}}
        self.load()
    
    def load(self):
        try:
            if os.path.exists("state.json"):
                with open("state.json", "r") as f:
                    self.data = json.load(f)
        except Exception as e:
            logger.error(f"Error cargando estado: {e}")
    
    def save(self):
        try:
            with open("state.json", "w") as f:
                json.dump(self.data, f)
        except Exception as e:
            logger.error(f"Error guardando estado: {e}")
    
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
    
    def get_registered_user(self, user_id):
        return self.data.get("usuarios_registrados", {}).get(str(user_id))
    
    def register_user(self, user_id, name):
        self.data.setdefault("usuarios_registrados", {})[str(user_id)] = name
        self.save()

state = SimpleState()

# Flask app para mantener vivo Railway
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot activo"

def run_flask():
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start con saludo"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    nombre = state.get_registered_user(user_id)

    state.set_chat_id(chat_id)

    current_person = PERSONAS[state.get_turn()]
    last_day = state.get_last_day()

    saludo = f"👋 ¡Hola {nombre}!\n\n" if nombre else ""

    message = (
        saludo +
        f"🤖 Bot activado!\n\n"
        f"👤 Turno: {current_person}\n"
        f"📅 Último día: {last_day.strftime('%d/%m/%Y') if last_day else 'Nunca'}\n\n"
        f"Comandos:\n"
        f"/start - Iniciar\n"
        f"/registrar <nombre> - Identificarte (ej: /registrar Sebastián)\n"
        f"/hecho - Marcar realizada\n"
        f"/status - Ver estado\n"
        f"/help - Ayuda"
    )

    await update.message.reply_text(message)
    logger.info(f"Bot iniciado en chat {chat_id} por {nombre if nombre else 'usuario no registrado'}")

async def registrar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /registrar para asociar usuario con nombre."""
    chat_id = update.effective_chat.id
    args = context.args
    if not args:
        await update.message.reply_text("Por favor escribe: /registrar Sebastián o /registrar Francisca")
        return

    nombre = args[0].capitalize()
    if nombre not in PERSONAS:
        await update.message.reply_text(f"Nombre inválido. Debe ser uno de: {', '.join(PERSONAS)}")
        return

    user_id = update.effective_user.id

    # Guardar registro
    state.register_user(user_id, nombre)

    await update.message.reply_text(f"✅ Registrado como {nombre}. Gracias!")

async def hecho_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /hecho con validación de usuario registrado"""
    user = update.effective_user
    user_id = user.id

    # Verificar si el usuario está registrado
    usuario_registrado = state.get_registered_user(user_id)

    if not usuario_registrado:
        await update.message.reply_text(
            "❌ No estás registrado. Usa /registrar Sebastián o /registrar Francisca para registrarte."
        )
        return

    current_turn = state.get_turn()
    expected_person = PERSONAS[current_turn]

    if usuario_registrado != expected_person:
        await update.message.reply_text(f"❌ No es tu turno {usuario_registrado}. Le toca a {expected_person}")
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
        f"✅ ¡Gracias {usuario_registrado}!\n"
        f"🔄 Ahora le toca a: {next_person}\n"
        f"📅 {today.strftime('%d/%m/%Y')}"
    )

    await update.message.reply_text(message)
    logger.info(f"Tarea marcada por {usuario_registrado}")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /status con saludo"""
    user_id = update.effective_user.id
    nombre = state.get_registered_user(user_id)

    current_person = PERSONAS[state.get_turn()]
    last_day = state.get_last_day()
    now = datetime.now(TIMEZONE)

    saludo = f"👋 ¡Hola {nombre}!\n\n" if nombre else ""

    message = (
        saludo +
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
        f"/registrar <nombre> - Identificarte (ej: /registrar Sebastián)\n"
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

    keep_alive()  # Inicia servidor web para Railway

    app = ApplicationBuilder().token(TOKEN).build()

    # Registrar comandos
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("registrar", registrar_command))
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
