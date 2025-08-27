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
from PIL import Image

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

async def _send_album_with_caching(
    message: Message,
    photo_filenames: list[str],
    caption: str,
    reply_markup: object = None,
    parse_mode: str = "HTML"
):
    """Отправляет медиагруппу (альбом) фото одним сообщением.
    Первая картинка содержит подпись, остальные — без подписи. Используется кэш file_id.
    """
    from app.core.dispatcher import admin_panel
    media = []
    for idx, name in enumerate(photo_filenames):
        abs_path = os.path.abspath(name)
        cached_id = admin_panel.get_file_id(name)
        if cached_id:
            media.append(InputMediaPhoto(media=cached_id, caption=caption if idx == 0 else None, parse_mode=parse_mode))
        else:
            media.append(InputMediaPhoto(media=FSInputFile(abs_path), caption=caption if idx == 0 else None, parse_mode=parse_mode))
    try:
        sent_messages = await message.bot.send_media_group(chat_id=message.chat.id, media=media)
        # Кэшируем file_id
        for item, name in zip(sent_messages, photo_filenames):
            if getattr(item, "photo", None):
                admin_panel.set_file_id(name, item.photo[-1].file_id)
        # Попробуем прикрепить клавиатуру к ПЕРВОМУ сообщению (именно там подпись)
        if reply_markup and sent_messages:
            try:
                await message.bot.edit_message_caption(
                    chat_id=message.chat.id,
                    message_id=sent_messages[0].message_id,
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            except Exception as e:
                logger.warning(f"Could not set keyboard via caption edit for album: {e}")
                # Вторая попытка: только разметка
                try:
                    await message.bot.edit_message_reply_markup(
                        chat_id=message.chat.id,
                        message_id=sent_messages[0].message_id,
                        reply_markup=reply_markup
                    )
                except Exception as e2:
                    logger.warning(f"Could not set reply_markup for album: {e2}")
                    # Фолбэк: отправляем отдельное сообщение только с клавиатурой
                    try:
                        await message.answer("\u2060", reply_markup=reply_markup)  # invisible spacer
                    except Exception as e3:
                        logger.warning(f"Could not send fallback keyboard message: {e3}")
        return sent_messages
    except Exception as e:
        logger.error(f"Failed to send album: {e}")
        # Фолбэк: отправить первое фото с подписью
        return await _send_photo_with_caching(message, photo_filenames[0], caption, reply_markup)

def compose_vertical_collage(image_paths: list[str], out_path: str, max_width: int = 1280, bg_color: tuple = (255, 255, 255), spacing: int = 8) -> str:
    """Склеивает несколько изображений вертикально в один файл и возвращает путь сохранения.
    - Масштабирует изображения по ширине не более max_width с сохранением пропорций
    - Между блоками добавляет отступ spacing
    """
    if not image_paths:
        raise ValueError("image_paths is empty")

    images: list[Image.Image] = []
    for p in image_paths:
        if not os.path.exists(p):
            continue
        img = Image.open(p).convert("RGB")
        # Масштабируем по ширине, если необходимо
        if img.width > max_width:
            new_height = int(img.height * (max_width / img.width))
            img = img.resize((max_width, new_height), Image.LANCZOS)
        images.append(img)

    if not images:
        raise ValueError("no valid images to compose")

    target_width = max(i.width for i in images)
    total_height = sum(i.height for i in images) + spacing * (len(images) - 1)

    canvas = Image.new("RGB", (target_width, total_height), color=bg_color)

    y = 0
    for idx, img in enumerate(images):
        # Центрируем по ширине, если изображение уже меньше максимальной ширины
        x = (target_width - img.width) // 2
        canvas.paste(img, (x, y))
        y += img.height
        if idx < len(images) - 1:
            y += spacing

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    canvas.save(out_path, format="JPEG", quality=90)
    return out_path

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