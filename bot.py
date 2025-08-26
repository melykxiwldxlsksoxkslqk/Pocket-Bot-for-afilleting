import asyncio
import logging
import os
import sys
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand

# Загрузка переменных окружения и настройка логирования
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

# Импорт основных компонентов после настройки
from app.core.dispatcher import dp, bot, admin_panel, trading_api, telethon_client
from app.services.background import periodic_auth_check
from app.core.middleware import MaintenanceMiddleware, AdminCheckMiddleware
from app.handlers import user_handlers
from app.handlers import admin_panel_handlers
from app.handlers import auth_handlers

async def _ensure_telethon_authorized() -> bool:
	"""Проверяет авторизацию Telethon и при необходимости запускает терминальный логин."""
	await telethon_client.initialize()
	if getattr(telethon_client, 'is_connected', False):
		return True
	logger.warning("Telethon не авторизован. Запускаю терминальный логин (telethon_login.py)...")
	base_dir = os.path.dirname(__file__)
	script_path = os.path.join(base_dir, 'app', 'services', 'telethon_login.py')
	if not os.path.exists(script_path):
		script_path = os.path.join(base_dir, 'telethon_login.py')
	if not os.path.exists(script_path):
		logger.error("Не найден telethon_login.py. Остановка.")
		return False
	# Запускаем интерактивный скрипт в том же терминале и ждём завершени{20E763FD-DA44-4FE9-A10B-E2396B0DA7ED}.png
	base_dir = os.path.dirname(__file__)
	script_path = os.path.join(base_dir, 'app', 'services', 'telethon_login.py')
	if not os.path.exists(script_path):
		script_path = os.path.join(base_dir, 'telethon_login.py')
	proc = await asyncio.create_subprocess_exec(sys.executable, script_path)
	ret = await proc.wait()
	if ret != 0:
		logger.error(f"telethon_login.py завершился с кодом {ret}")
		return False
	await telethon_client.initialize()
	return getattr(telethon_client, 'is_connected', False)

async def main():
	"""Основная функция для запуска бота"""
	# 1. Инициализация Telethon клиента (и авторизация при необходимости)
	auth_ok = await _ensure_telethon_authorized()
	if not auth_ok:
		logger.error("Telethon не авторизован. Завершаю работу бота. Повторите запуск после успешного входа.")
		return

	# 2. Инициализация сессии TradingAPI (Telethon client уже внедрен через dispatcher)
	is_session_valid = await trading_api.initialize_session()
	if not is_session_valid:
		admin_id = admin_panel.get_admin_id()
		if admin_id:
			try:
				auth_keyboard = InlineKeyboardMarkup(inline_keyboard=[
					[InlineKeyboardButton(text="🔑 Авторизоваться", callback_data="start_manual_auth")]
				])
				await bot.send_message(
					admin_id,
					"🔴 <b>Критическая ошибка запуска!</b>\n\nСессия API недействительна или отсутствует. Бот не может получать рыночные данные.\n\nНажмите кнопку ниже, чтобы начать процесс авторизации.",
					parse_mode="HTML",
					reply_markup=auth_keyboard
				)
				trading_api.critical_notification_sent = True
				logger.warning("Отправлено срочное уведомление администратору о недействительной сессии.")
			except TelegramForbiddenError:
				logger.error("Не удалось отправить сообщение админу: бот заблокирован.")
			except Exception as e:
				logger.error(f"Не удалось отправить сообщение админу: {e}")

	# 3. Регистрация middleware
	dp.update.middleware(MaintenanceMiddleware())
	admin_panel_handlers.router.message.middleware(AdminCheckMiddleware())
	admin_panel_handlers.router.callback_query.middleware(AdminCheckMiddleware())
	
	# 4. Настройка и запуск фоновых задач
	auth_task = asyncio.create_task(periodic_auth_check(bot, trading_api, admin_panel))
	
	# 5. Регистрация роутеров
	logger.info("Регистрация роутеров...")
	dp.include_router(user_handlers.router)
	dp.include_router(admin_panel_handlers.router)
	dp.include_router(auth_handlers.router)
	logger.info("Роутеры успешно зарегистрированы.")

	# 6. Запуск бота
	await bot.delete_webhook(drop_pending_updates=True)
	logger.info("Запуск поллинга...")
	try:
		await dp.start_polling(bot, skip_updates=True)
	finally:
		# Корректное завершение работы
		logger.info("Бот останавливается...")
		
		# Остановка асинхронных задач
		auth_task.cancel()

		# Отключение Telethon клиента
		await telethon_client.disconnect()
		
		# Сохранение данных админ-панели
		logger.info("Сохранение данных...")
		admin_panel._save_data()
		
		# Закрытие Selenium WebDriver
		if trading_api and trading_api.auth and trading_api.auth.driver:
			logger.info("Закрытие Selenium WebDriver...")
			trading_api.auth.close()
		
		# Закрытие сессии бота
		await bot.session.close()
		logger.info("Бот был успешно остановлен.")

if __name__ == "__main__":
	try:
		asyncio.run(main()) 
	except (KeyboardInterrupt, SystemExit):
		logger.info("Получен сигнал на завершение работы.")