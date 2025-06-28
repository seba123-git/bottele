# Telegram Bot for Task Reminders

## Overview

This is a fully functional Telegram bot that manages task reminders between two people (Sebastián and Francisca) on a rotating schedule. The bot successfully tracks whose turn it is to complete a task ("recoger las cacas"), sends automatic reminders every 3 hours (8 AM - 10 PM Chile time), and maintains persistent state. The system is currently running and operational.

## System Architecture

The application has been simplified from the original modular design to a single, stable file architecture:

- **Main Application**: `main.py` contains the complete bot implementation with simplified state management
- **Backup Versions**: Multiple backup files available (`telegram_bot_final.py`, `simple_bot.py`, `telegram_bot_improved.py`)
- **State Management**: Simple JSON file storage (`state.json`) for persistence
- **Documentation**: Comprehensive README.md with usage instructions

The bot uses `python-telegram-bot` v20.8 with job scheduling capabilities for reliable reminder delivery.

## Key Components

### 1. Simplified State Management
- **Storage**: Direct JSON file handling in `state.json`
- **State Data**: Current turn (0/1), last completion date, chat ID
- **Persistence**: Automatic save on every state change
- **Recovery**: Graceful handling of missing or corrupted state files

### 2. Core Bot Features
- **Commands**: `/start`, `/hecho`, `/status`, `/help`
- **Reminders**: Automated every 3 hours during active hours (8 AM - 10 PM)
- **Turn Management**: Automatic rotation between Sebastián and Francisca
- **Timezone**: All operations in Chile timezone (America/Santiago)

### 3. Operational Status
- **Connection**: Successfully connected to Telegram API
- **Scheduler**: APScheduler running with 3-hour intervals
- **Polling**: Active message polling for user interactions
- **Logs**: Real-time logging showing successful operations

## Current Implementation

The bot is currently **running and functional** with the following verified features:

1. **API Connection**: Confirmed connection to Telegram servers
2. **Command Processing**: All commands registered and responsive
3. **Reminder System**: Scheduler active and sending reminders
4. **State Persistence**: JSON state file created and maintained
5. **Error Handling**: Robust error recovery and logging

## Data Flow

1. **Bot Startup**: Loads existing state or creates default configuration
2. **User Registration**: `/start` command registers chat and displays current status
3. **Task Completion**: `/hecho` command marks task done and switches turns
4. **Automatic Reminders**: Every 3 hours during active hours (8 AM - 10 PM Chile)
5. **State Updates**: All changes immediately persisted to JSON file

## External Dependencies

- **python-telegram-bot[job-queue]**: v20.8 - Main bot framework with scheduling
- **pytz**: v2025.2 - Chile timezone support
- **apscheduler**: v3.10.4 - Job scheduling for reminders

## Deployment Strategy

Successfully deployed on Replit with:

- **Token Configuration**: Bot token embedded directly in code
- **File Persistence**: Local `state.json` for state storage
- **Continuous Operation**: Workflow configured to keep bot running
- **Process Management**: Automatic restart on failures

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

- **June 28, 2025**: Completely rebuilt bot architecture for stability
- **June 28, 2025**: Successfully resolved event loop conflicts 
- **June 28, 2025**: Implemented working reminder system with 3-hour intervals
- **June 28, 2025**: Bot now operational and responding to commands
- **June 28, 2025**: Created multiple backup versions for code safety
- **June 28, 2025**: Added comprehensive documentation and README

## Current Status: OPERATIONAL

The bot is running successfully with all core features working:
- ✅ Telegram API connection established
- ✅ Command handlers active (/start, /hecho, /status, /help)
- ✅ 3-hour reminder system operational
- ✅ State persistence working
- ✅ Chile timezone correctly configured
- ✅ Anti-crash system functional