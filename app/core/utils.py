from aiogram.types import Message, BufferedInputFile, InputMediaPhoto, FSInputFile
from aiogram.exceptions import TelegramBadRequest
import random
from datetime import datetime, timedelta
import locale
import asyncio
import logging
import os
import pytz
from loguru import logger
from functools import wraps

logger = logging.getLogger(__name__)

def async_retry(max_retries=3, delay=2, allowed_exceptions=()):
    """
    A decorator to retry an async function if it fails.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except allowed_exceptions as e:
                    logger.warning(f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__} due to allowed exception: {e}. Retrying...")
                    if attempt + 1 == max_retries:
                        raise  # Re-raise the last exception
                    await asyncio.sleep(delay)
                except Exception as e:
                    logger.error(
                        f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__} with an unexpected exception: {e}",
                        exc_info=True
                    )
                    # For unexpected errors, we might not want to retry, so we re-raise immediately.
                    # Or, to be safe, we can continue retrying. For now, let's re-raise.
                    raise
            # This part should not be reachable if max_retries > 0
            return None
        return wrapper
    return decorator

async def check_api_initialized(message: Message) -> bool:
    """Перевірка ініціалізації API"""
    from app.core.dispatcher import trading_api
    if not trading_api.is_initialized:
        await message.answer("⏳ Ініціалізація API...")
        success = await trading_api.confirm_auth()
        if not success:
            await message.answer("❌ Помилка ініціалізації API. Спробуйте пізніше.")
            return False
    return True 

async def _send_photo_with_caching(
    message: Message,
    photo_filename: str,
    caption: str,
    reply_markup: object = None,
    edit: bool = False,
    parse_mode: str = "HTML"
):
    """
    Sends a photo, using a cached file_id if available.
    If edit is True, it tries to edit the existing message.
    If editing fails, it deletes the old message and sends a new one.
    """
    from app.core.dispatcher import admin_panel
    file_id = admin_panel.get_file_id(photo_filename)
    # The script runs from the root, so we can just use the filename.
    # To be safe, we ensure it's an absolute path from the current working directory.
    photo_path = os.path.abspath(photo_filename)

    # --- New logic: Always delete and send for 'edit' to avoid race conditions ---
    if edit:
        try:
            # First, try to delete the message this interaction came from.
            # This is often cleaner than trying to edit it, especially if it's a photo.
            await message.delete()
        except TelegramBadRequest as e:
            # If the message is already gone, that's fine.
            # We only log a warning for other, unexpected errors.
            if "message to delete not found" not in str(e):
                logger.warning(f"Could not delete message before sending new one: {e}")
        
        # Now, send a new message in the same chat.
        # We need to use message.chat.id because the original message is gone.
        return await message.bot.send_photo(
            chat_id=message.chat.id,
            photo=FSInputFile(photo_path) if file_id is None else file_id,
            caption=caption,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )

    # --- Original logic for sending a new message ---
    if file_id:
        try:
            sent_message = await message.answer_photo(
                photo=file_id,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            return sent_message
        except TelegramBadRequest:
            logger.warning(f"Failed to send photo with cached file_id {file_id}. Resending as a new file.")
            # Fall through to send as a new file

    # Send as a new file and cache the ID
    try:
        sent_message = await message.answer_photo(
            photo=FSInputFile(photo_path),
            caption=caption,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        if sent_message.photo:
            admin_panel.set_file_id(photo_filename, sent_message.photo[-1].file_id)
        return sent_message
    except Exception as e:
        logger.error(f"Failed to send photo from path {photo_path}: {e}")
        return None

def _format_asset_name(asset: str) -> str:
    """Форматує технічну назву активу в читабельний вигляд."""
    name_upper = asset.upper()
    is_otc = name_upper.endswith('_OTC')
    
    # Видаляємо суфікс _OTC для базової обробки
    clean_name = name_upper.removesuffix('_OTC')

    # Перевіряємо, чи це стандартна валютна пара (6 літер)
    if len(clean_name) == 6 and clean_name.isalpha():
        formatted_pair = f"{clean_name[:3]}/{clean_name[3:]}"
        if is_otc:
            return f"{formatted_pair} OTC"
        return formatted_pair
    
    # Для інших випадків (акції, індекси тощо) повертаємо назву як є,
    # але додаємо ' OTC' якщо потрібно
    if is_otc:
        return f"{clean_name} OTC"
    return clean_name