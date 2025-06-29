import os
import json
from datetime import datetime, timedelta
import pytz
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from apscheduler.schedulers.background import BackgroundScheduler

# Constantes
TIMEZONE = pytz.timezone("America/Santiago")
PERSONAS = ["Sebastián", "Francisca"]
STATE_FILE = "state.json"

# Clase para manejar el estado persistente
class SimpleState:
    def __init__(self):
        self.data = {
            "turno": 0,
            "ultimo_dia": None,
            "chat_id": None,
            "usuarios": {},  # chat_id -> nombre identificado
            "hechos": {"Sebastián": False, "Francisca": False},
        }
        self.load()

    def load(self):
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, "r") as f:
                    self.data = json.load(f)
                    # Convertir ultimo_dia a datetime si no es None
                    if self.data["ultimo_dia"]:
                        self.data["ultimo_dia"] = datetime.strptime(
                            self.data["ultimo_dia"], "%Y-%m-%d"
                        ).date()
        except Exception:
            pass

    def save(self):
        try:
            to_save = self.data.copy()
            # Guardar ultimo_dia como string para JSON
            if to_save["ultimo_dia"]:
                to_save["ultimo_dia"] = to_save["ultimo_dia"].strftime("%Y-%m-%d")
            with open(STATE_FILE, "w") as f:
                json.dump(to_save, f)
        except Exception:
            pass

    def get_turn(self):
        return self.data["turno"]

    def set_turn(self, valor):
        self.data["turno"] = valor
        self.save()

    def get_last_day(self):
        return self.data["ultimo_dia"]

    def set_last_day(self, valor):
        self.data["ultimo_dia"] = valor
        self.save()

    def get_chat_id(self):
        return self.data["chat_id"]

    def set_chat_id(self, valor):
        self.data["chat_id"] = valor
        self.save()

    def set_usuario(self, chat_id, nombre):
        self.data["usuarios"][str(chat_id)] = nombre
        self.save()

    def get_usuario(self, chat_id):
        return self.data["usuarios"].get(str(chat_id))

    def marcar_hecho(self, nombre):
        self.data["hechos"][nombre] = True
        self.save()

    def esta_hecho(self, nombre):
        return self.data["hechos"].get(nombre, False)

    def reset_hechos(self):
        for p in PERSONAS:
            self.data["hechos"][p] = False
        self.save()


state = SimpleState()

# Función para obtener el nombre del usuario según chat_id
def obtener_nombre_usuario(chat_id):
    nombre = state.get_usuario(chat_id)
    if nombre in PERSONAS:
        return nombre
    return None

# Comando /soy para identificar usuario
async def soy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text(
            "❌ Debes escribir tu nombre: /soy Sebastián o /soy Francisca"
        )
        return

    nombre = context.args[0].capitalize()
    if nombre not in PERSONAS:
        await update.message.reply_text(f"❌ Nombre inválido. Usa solo: {', '.join(PERSONAS)}")
        return

    state.set_usuario(chat_id, nombre)
    await update.message.reply_text(
        f"✅ Hola {nombre}, te he registrado para que el bot te reconozca."
    )

# Comando /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state.set_chat_id(chat_id)

    nombre_usuario = obtener_nombre_usuario(chat_id)
    if not nombre_usuario:
        saludo = "Hola! Usa /soy Sebastián o /soy Francisca para identificarte."
    else:
        saludo = f"Hola {nombre_usuario}!"

    current_person = PERSONAS[state.get_turn()]
    last_day = state.get_last_day()

    message = (
        f"{saludo}\n\n"
        f"🤖 Bot activado!\n\n"
        f"👤 Turno: {current_person}\n"
        f"📅 Último día: {last_day.strftime('%d/%m/%Y') if last_day else 'Nunca'}\n\n"
        f"Comandos:\n"
        f"/start - Iniciar\n"
        f"/hecho - Marcar realizada\n"
        f"/status - Ver estado\n"
        f"/help - Ayuda\n"
        f"/soy - Identifícate: /soy Sebastián o /soy Francisca"
    )
    await update.message.reply_text(message)

# Comando /status
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    nombre_usuario = obtener_nombre_usuario(chat_id)

    if not nombre_usuario:
        saludo = "Hola! Usa /soy Sebastián o /soy Francisca para identificarte."
    else:
        saludo = f"Hola {nombre_usuario}!"

    current_person = PERSONAS[state.get_turn()]
    last_day = state.get_last_day()
    now = datetime.now(TIMEZONE)

    hechos_str = ""
    for persona in PERSONAS:
        hecho = "✅" if state.esta_hecho(persona) else "❌"
        hechos_str += f"{persona}: {hecho}\n"

    message = (
        f"{saludo}\n\n"
        f"📊 Estado:\n\n"
        f"👤 Turno: {current_person}\n"
        f"📅 Último día: {last_day.strftime('%d/%m/%Y') if last_day else 'Nunca'}\n"
        f"🕐 Hora Chile: {now.strftime('%d/%m/%Y %H:%M')}\n\n"
        f"Personas:\n"
        f"{hechos_str}"
    )

    await update.message.reply_text(message)

# Comando /hecho
async def hecho_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    nombre_usuario = obtener_nombre_usuario(chat_id)

    if not nombre_usuario:
        await update.message.reply_text(
            "❌ No estás identificado. Por favor usa /soy Sebastián o /soy Francisca para identificarse."
        )
        return

    current_turn = state.get_turn()
    if PERSONAS[current_turn] != nombre_usuario:
        await update.message.reply_text(
            f"❌ No es tu turno, {nombre_usuario}. Ahora es el turno de {PERSONAS[current_turn]}."
        )
        return

    today = datetime.now(TIMEZONE).date()
    last_day = state.get_last_day()

    if last_day == today:
        await update.message.reply_text("⚠️ Ya marcaste hecho hoy.")
        return

    # Marcar hecho y avanzar turno si ambas personas han hecho su tarea
    state.marcar_hecho(nombre_usuario)

    if all(state.esta_hecho(p) for p in PERSONAS):
        # Cambiar turno
        nuevo_turno = (current_turn + 1) % len(PERSONAS)
        state.set_turn(nuevo_turno)
        state.set_last_day(today)
        state.reset_hechos()
        await update.message.reply_text(
            f"✅ Tarea marcada. Cambio de turno a {PERSONAS[nuevo_turno]}."
        )
    else:
        await update.message.reply_text(
            f"✅ Tarea marcada para {nombre_usuario}. Falta que la otra persona lo haga."
        )

# Comando /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "Comandos disponibles:\n"
        "/start - Iniciar y mostrar estado\n"
        "/soy [nombre] - Identifícate (Sebastián o Francisca)\n"
        "/hecho - Marcar que realizaste tu tarea\n"
        "/status - Ver estado actual\n"
        "/help - Mostrar esta ayuda\n"
    )
    await update.message.reply_text(message)

# Función para enviar recordatorios sólo entre 8am y 22pm
def enviar_recordatorios(application):
    ahora = datetime.now(TIMEZONE)
    if ahora.hour < 8 or ahora.hour > 22:
        return  # No enviar fuera de horario

    current_turn = state.get_turn()
    persona = PERSONAS[current_turn]

    # Verificamos si la persona ya marcó hecho hoy
    if state.esta_hecho(persona):
        return

    chat_id = state.get_chat_id()
    if not chat_id:
        return

    texto = (
        f"⏰ Recordatorio: Es tu turno, {persona}. "
        "Por favor, realiza la tarea y usa /hecho cuando termines."
    )
    application.bot.send_message(chat_id=chat_id, text=texto)

# Inicializar bot y scheduler
async def main():
    token = os.getenv("BOT_TOKEN")  # Coloca tu token aquí o en variables entorno
    if not token:
        print("ERROR: No se encontró la variable de entorno BOT_TOKEN")
        return

    application = (
        ApplicationBuilder().token(token).build()
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("soy", soy_command))
    application.add_handler(CommandHandler("hecho", hecho_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("help", help_command))

    # Scheduler para recordatorios cada 3 horas (ejemplo)
    scheduler = BackgroundScheduler(timezone=TIMEZONE)
    scheduler.add_job(
        lambda: enviar_recordatorios(application),
        "interval",
        hours=3,
        next_run_time=datetime.now(TIMEZONE)
    )
    scheduler.start()

    print("Bot iniciado...")
    await application.run_polling()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
