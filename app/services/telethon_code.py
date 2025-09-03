import logging
import os
import asyncio
from telethon import TelegramClient
from dotenv import load_dotenv
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
try:
    # Newer Telethon versions
    from telethon.errors import AuthRestartError
except Exception:
    try:
        # Older Telethon path
        from telethon.errors.rpcerrorlist import AuthRestartError
    except Exception:
        class AuthRestartError(Exception):
            pass

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

    async def _ensure_connected(self, max_attempts: int = 4, base_delay: float = 2.0) -> bool:
        """Ensure client has an active connection with limited retries and backoff."""
        for attempt in range(1, max_attempts + 1):
            try:
                if self.client.is_connected():
                    return True
                logger.info(f"Connecting Telethon client (attempt {attempt}/{max_attempts})...")
                await asyncio.wait_for(self.client.connect(), timeout=20.0)
                if self.client.is_connected():
                    return True
            except Exception as e:
                logger.warning(f"Connect attempt {attempt} failed: {e}")
                try:
                    await self.client.disconnect()
                except Exception:
                    pass
                await asyncio.sleep(base_delay * attempt)
        return False

    async def _reconnect(self):
        """Force reconnect with a short delay."""
        try:
            await self.client.disconnect()
        except Exception:
            pass
        await asyncio.sleep(1.5)
        await self._ensure_connected()

    async def initialize(self):
        async with self.lock:
            ok = await self._ensure_connected()
            if not ok:
                logger.error("❌ Telethon client could not establish connection after retries.")
                self.is_connected = False
                return
            self.is_connected = await self.client.is_user_authorized()
            if self.is_connected:
                try:
                    me = await self.client.get_me()
                    logger.info(f"✅ Telethon client initialized and connected successfully as {getattr(me, 'first_name', 'unknown')}.")
                except Exception:
                    logger.info("✅ Telethon client initialized and connected successfully.")
            else:
                logger.warning("Telethon client connected but user is not authorized. Please log in.")

    async def start_login(self, phone_number: str):
        async with self.lock:
            ok = await self._ensure_connected()
            if not ok:
                raise ConnectionError("Cannot connect to Telegram. Try again later.")
            self._phone = phone_number
            logger.info("Sending login code to phone...")
            for attempt in range(1, 4):
                try:
                    await self.client.send_code_request(self._phone)
                    logger.info("Login code sent.")
                    break
                except AuthRestartError as e:
                    logger.warning(f"AuthRestartError on send_code_request (attempt {attempt}/3): {e}. Restarting authorization flow...")
                    await self._reconnect()
                    await asyncio.sleep(2)
                except ConnectionError as e:
                    logger.warning(f"Disconnected during send_code_request (attempt {attempt}/3): {e}. Reconnecting...")
                    await self._reconnect()
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout during send_code_request (attempt {attempt}/3). Retrying...")
                    await self._reconnect()
                except Exception as e:
                    logger.error(f"Unexpected error on send_code_request: {e}")
                    await self._reconnect()
                if attempt == 3:
                    raise

    async def complete_login_code(self, code: str) -> bool:
        async with self.lock:
            await self._ensure_connected()
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
            await self._ensure_connected()
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