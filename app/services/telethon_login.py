import asyncio
import os
from getpass import getpass
from dotenv import load_dotenv
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from telethon_code import telethon_client

load_dotenv()

async def main():
	print("=== Telethon Login (Terminal) ===")
	phone = os.getenv("TELEGRAM_PHONE") or input("Введите номер телефона (в международном формате, напр. +380...): ").strip()
	await telethon_client.start_login(phone)
	print("Код отправлен в Telegram. Откройте Telegram и посмотрите код подтверждения.")
	while True:
		code = input("Введите код из Telegram (или пусто для отмены): ").strip()
		if not code:
			print("Отменено пользователем.")
			return
		try:
			ok = await telethon_client.complete_login_code(code)
			if ok:
				print("Успешная авторизация.")
				return
			else:
				print("Не авторизовано. Повторите попытку.")
		except SessionPasswordNeededError:
			pwd = getpass("Требуется 2FA пароль. Введите пароль: ")
			ok = await telethon_client.complete_2fa(pwd)
			if ok:
				print("Успешная авторизация (2FA).")
				return
			else:
				print("2FA не прошла. Повторите попытку.")
		except PhoneCodeInvalidError:
			print("Неверный код. Попробуйте снова.")

if __name__ == "__main__":
	asyncio.run(main()) 