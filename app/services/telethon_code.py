import logging
import os
import asyncio
from telethon import TelegramClient
from dotenv import load_dotenv
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError

load_dotenv()

API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_NAME = "telethon.session"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelethonClient:
    def __init__(self, session_name, api_id, api_hash):
        logger.info("Initializing Telethon client...")
        self.session_name = session_name
        self.api_id = api_id
        self.api_hash = api_hash
        if not self.api_id or not self.api_hash:
            raise ValueError("API_ID and API_HASH must be set in environment variables.")
        self.client = TelegramClient(self.session_name, int(self.api_id), self.api_hash)
        self.is_connected = False
        self.lock = asyncio.Lock()
        self._phone = None

    async def initialize(self):
        async with self.lock:
            if not self.client.is_connected():
                logger.info("Connecting Telethon client...")
                try:
                    await asyncio.wait_for(self.client.connect(), timeout=20.0)
                    self.is_connected = await self.client.is_user_authorized()
                    if self.is_connected:
                        me = await self.client.get_me()
                        logger.info(f"✅ Telethon client initialized and connected successfully as {me.first_name}.")
                    else:
                        logger.warning("Telethon client connected but user is not authorized. Please log in.")
                except asyncio.TimeoutError:
                    logger.error("❌ Telethon client connection timed out.")
                    self.is_connected = False
                except Exception as e:
                    logger.error(f"❌ Failed to connect Telethon client: {e}")
                    self.is_connected = False
            else:
                logger.info("Telethon client is already connected.")

    async def start_login(self, phone_number: str):
        async with self.lock:
            if not self.client.is_connected():
                await self.client.connect()
            self._phone = phone_number
            logger.info("Sending login code to phone...")
            await self.client.send_code_request(self._phone)
            logger.info("Login code sent.")

    async def complete_login_code(self, code: str) -> bool:
        async with self.lock:
            try:
                result = await self.client.sign_in(self._phone, code)
                self.is_connected = await self.client.is_user_authorized()
                return self.is_connected
            except SessionPasswordNeededError:
                # 2FA required
                logger.info("2FA password required for Telethon login.")
                raise
            except PhoneCodeInvalidError:
                logger.error("Invalid Telegram code provided.")
                raise

    async def complete_2fa(self, password: str) -> bool:
        async with self.lock:
            await self.client.sign_in(password=password)
            self.is_connected = await self.client.is_user_authorized()
            return self.is_connected

    async def disconnect(self):
        async with self.lock:
            if self.client.is_connected():
                logger.info("Disconnecting Telethon client...")
                await self.client.disconnect()
                self.is_connected = False
                logger.info("✅ Telethon client disconnected successfully.")

    async def send_message(self, entity, message):
        async with self.lock:
            if not self.is_connected:
                await self.initialize()
            if not self.is_connected:
                raise ConnectionError("Telethon client is not connected.")
            return await self.client.send_message(entity, message)

    async def get_messages(self, entity, limit=1):
        messages = []
        async with self.lock:
            if not self.is_connected:
                await self.initialize()
            if not self.is_connected:
                raise ConnectionError("Telethon client is not connected.")
            async for message in self.client.iter_messages(entity, limit=limit):
                messages.append(message)
        return messages

# Singleton instance
telethon_client = TelethonClient(SESSION_NAME, API_ID, API_HASH)