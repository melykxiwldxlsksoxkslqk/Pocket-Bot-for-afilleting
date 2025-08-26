import asyncio
import logging
from datetime import datetime, timedelta
from app.core.dispatcher import bot, admin_panel, trading_api
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

# Пороги для проверки
SESSION_CHECK_INTERVAL_OK = 1800  # 30 минут, если все в порядке
SESSION_CHECK_INTERVAL_ERROR = 3600  # 1 час, если сессия умерла (чтобы не спамить)
PROACTIVE_REFRESH_THRESHOLD_HOURS = 12  # За сколько часов до истечения пытаться обновить

async def periodic_auth_check(bot, trading_api, admin_panel, interval_seconds: int = 3600):
    """
    Periodically checks the API connection status and warns the admin if the session
    is invalid, expired, or expiring soon. Runs once per hour.
    """
    await asyncio.sleep(20) # Initial delay to allow the bot to start up
    logger.info("🚀 Запущена периодическая проверка статуса сессии.")

    while True:
        try:
            admin_id = admin_panel.get_admin_id()
            if not admin_id:
                await asyncio.sleep(interval_seconds)
                continue

            # Check 1: Is connection dead or session expired? (Critical)
            if not await trading_api.is_api_connection_alive():
                # Anti-spam check: only send if a notification hasn't been sent already.
                if not trading_api.critical_notification_sent:
                    logger.warning("Проверка показала, что сессия API недействительна. Отправляю уведомление.")
                    auth_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔑 Обновить сессию", callback_data="start_manual_auth")]
                    ])
                    await bot.send_message(
                        admin_id,
                        "🔴 <b>Критическая ошибка запуска!</b>\n\nСессия API недействительна или отсутствует. Бот не может получать рыночные данные.\n\nНажмите кнопку ниже, чтобы начать процесс авторизации.",
                        reply_markup=auth_keyboard,
                        parse_mode="HTML"
                    )
                    trading_api.critical_notification_sent = True # Set flag after sending
            else:
                # If the connection is alive, reset the flag so it can notify again if it fails later.
                if trading_api.critical_notification_sent:
                    logger.info("Соединение с API восстановлено. Сбрасываю флаг уведомления.")
                    trading_api.critical_notification_sent = False
                
                # Check 2: Is session expiring soon? (Warning)
                expiry_warning = trading_api.auth.get_expiry_warning(days_threshold=3)
                if expiry_warning:
                    logger.info(f"Сессия скоро заканчивается: {expiry_warning}")
                    auth_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔑 Обновить сессию", callback_data="start_manual_auth")]
                    ])
                    await bot.send_message(
                        admin_id,
                        f"🟡 <b>Предупреждение: срок действия сессии скоро закончится</b>\n\n{expiry_warning} Чтобы избежать сбоев в работе, рекомендуется обновить её.",
                        reply_markup=auth_keyboard,
                        parse_mode="HTML"
                    )
                else:
                    logger.info("Проверка сессии: всё хорошо, соединение активное.")

        except Exception as e:
            logger.error(f"Помилка під час періодичної перевірки сесії: {e}", exc_info=True)
            
        await asyncio.sleep(interval_seconds)

async def start_background_tasks():
    """Инициализирует и запускает фоновые задания."""
    logger.info("Запуск фоновых завдань...")
    # Запускаем только одну нашу задачу
    asyncio.create_task(periodic_auth_check(bot, trading_api, admin_panel)) 