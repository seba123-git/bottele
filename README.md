# Bot de Telegram para Recordatorios

Bot robusto de Telegram que gestiona recordatorios de tareas entre dos personas con rotación automática de turnos.

## Características

- **Recordatorios automáticos**: Cada 3 horas (8 AM - 10 PM) en zona horaria de Chile
- **Sistema anti-crash**: Reintentos automáticos en caso de errores de red
- **Persistencia de estado**: Guarda el estado en archivo JSON
- **Rotación de turnos**: Cambia automáticamente entre las dos personas
- **Zona horaria Chile**: Todas las fechas y horarios en hora chilena

## Comandos del Bot

- `/start` - Iniciar el bot y ver estado actual
- `/hecho` - Marcar tarea como realizada (solo la persona en turno)
- `/status` - Ver estado actual y estadísticas
- `/help` - Mostrar ayuda

## Configuración

1. **Token del Bot**: Configurado en la variable `TOKEN` en `main.py`
2. **Personas**: Configuradas en la lista `PERSONAS` - actualmente "Sebastián" y "Francisca"
3. **Horarios**: Recordatorios entre 8 AM y 10 PM hora Chile
4. **Intervalo**: Recordatorios cada 3 horas

## Archivos del Proyecto

- `main.py` - Código principal del bot (versión estable)
- `telegram_bot_final.py` - Versión avanzada con más características
- `simple_bot.py` - Versión simplificada
- `state.json` - Archivo de estado persistente (se crea automáticamente)
- `telegram_bot.log` - Logs del bot

## Uso

1. Busca tu bot en Telegram usando el nombre que le diste
2. Envía `/start` para activar el bot
3. Cuando complete la tarea, la persona en turno envía `/hecho`
4. El bot automáticamente cambia el turno a la otra persona
5. Recibirás recordatorios cada 3 horas si no se ha marcado la tarea

## Estado del Proyecto

El bot está **funcionando correctamente** y listo para usar. Los logs muestran:
- Conexión exitosa a Telegram API
- Scheduler de recordatorios activo
- Todos los comandos registrados

## Soporte

El bot incluye manejo robusto de errores y se reinicia automáticamente en caso de problemas de conexión.