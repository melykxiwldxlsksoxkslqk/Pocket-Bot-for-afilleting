import logging
import os
import asyncio
import html
import pytz
import random
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.core.dispatcher import trading_api, admin_panel, bot
import app.core.database as db
from app.core.i18n import t
from app.core.keyboards import (
    get_start_keyboard, get_verification_request_keyboard, get_fully_verified_keyboard,
    get_market_type_keyboard, get_currency_pairs_keyboard, get_trading_time_keyboard,
    get_signal_keyboard, get_reregister_keyboard, get_check_deposit_keyboard,
    get_signal_menu_keyboard, get_retry_signal_keyboard, get_education_prompt_keyboard,
    get_cancel_keyboard, get_signal_confirmation_keyboard, get_language_keyboard
)
from app.core.fsm import Verification, Trading
from app.core.utils import _send_photo_with_caching, _format_asset_name
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)
router = Router()

# --- Lock to prevent concurrent verification requests for the same user ---
verification_locks = {}

ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x) for x in ADMIN_IDS_STR.split(",") if x] if ADMIN_IDS_STR else []

# Secret test UIDs (comma-separated) to bypass registration and deposit checks
SECRET_TEST_UIDS = {x.strip() for x in os.getenv("SECRET_TEST_UIDS", "").split(",") if x.strip()}

# --- Mandatory subscription config & helpers ---
REQUIRED_CHANNELS = ["@bvxbdferherh"]  # Public channel username or chat ID
SUBSCRIPTION_LINKS = [("Наш канал", "https://t.me/bvxbdferherh")]

async def _is_user_subscribed(user_id: int) -> bool:
    """Checks that user is a member of ALL required channels."""
    for channel in REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            status = getattr(member, "status", None)
            status_value = getattr(status, "value", status)
            if status_value not in ("creator", "administrator", "member"):
                return False
        except Exception:
            # If we cannot check (e.g., bot lacks rights), treat as not subscribed
            return False
    return True

def _build_subscription_keyboard(lang: str):
    texts = {
        "ru": {"channel": "📢 Наш канал", "check": "🔄 Проверить подписку", "back": "⬅️ Назад"},
        "en": {"channel": "📢 Our channel", "check": "🔄 Check subscription", "back": "⬅️ Back"},
    }
    tr = texts["en"] if lang == "en" else texts["ru"]
    kb = InlineKeyboardBuilder()
    for _, url in SUBSCRIPTION_LINKS:
        kb.row(InlineKeyboardButton(text=tr["channel"], url=url))
    kb.row(InlineKeyboardButton(text=tr["check"], callback_data="check_subscription"))
    kb.row(InlineKeyboardButton(text=tr["back"], callback_data="back_to_fully_verified"))
    return kb.as_markup()

async def _prompt_subscription(message: Message, lang: str, edit: bool = True):
    captions = {
        "ru": "Для доступа к торговым сигналам необходимо подписаться на наш канал.\nПосле подписки нажмите «Проверить подписку».",
        "en": "To access trading signals, please subscribe to our channel.\nAfter subscribing, press \"Check subscription\".",
    }
    caption = captions["en"] if lang == "en" else captions["ru"]
    try:
        # Сбрасываем кэш id и отправляем корректную картинку под язык
        img_path = ("imagen/start_eng.png" if lang == "en" else "imagen/start_ua.png")
        admin_panel.clear_file_id(img_path)
        await _send_photo_with_caching(message, img_path, caption, _build_subscription_keyboard(lang), edit=edit)
    except (TelegramBadRequest, AttributeError):
        await message.answer(caption, reply_markup=_build_subscription_keyboard(lang))


def _get_yesterday_date(lang: str) -> str:
    """Returns yesterday's date formatted in the user's language."""
    yesterday = datetime.now(pytz.utc) - timedelta(days=1)
    if lang == "en":
        days_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        months_en = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        return f"{days_en[yesterday.weekday()]} {yesterday.day} {months_en[yesterday.month - 1]} {yesterday.year}"
    else:
        days_ru = ["понедельник", "вторник", "среду", "четверг", "пятницу", "субботу", "воскресенье"]
        months_ru = [
            "января", "февраля", "марта", "апреля", "мая", "июня",
            "июля", "августа", "сентября", "октября", "ноября", "декабря"
        ]
        return f"За {days_ru[yesterday.weekday()]} {yesterday.day} {months_ru[yesterday.month - 1]} {yesterday.year} года"

def _generate_dynamic_facts(lang: str) -> str:
    """Generates a localized string with randomized statistics for messages."""
    yesterday_str = _get_yesterday_date(lang)
    partner_income = f"{random.randint(3500, 6800):,}".replace(",", " ")
    forecasts = f"{random.randint(4000, 5000):,}".replace(",", ".")
    success_rate = f"{random.randint(950, 980) / 10:.1f}"
    return (
        f"<b>{t('facts.title', lang)}</b> {yesterday_str}\n\n"
        f"{t('facts.partner_income', lang, amount=partner_income)}\n"
        f"{t('facts.bot_stats', lang, forecasts=forecasts, success_rate=success_rate)}"
    )

# --- Image helper ---
def _img(key: str, lang: str) -> str:
	locale = 'en' if lang == 'en' else 'ru'
	mapping = {
		'start': {'ru': '2step_eng.png', 'en': '2step_ua.png'},
		'market': {'ru': 'market_ua.png', 'en': 'market_eng.png'},
		'currencypair': {'ru': 'currencypair_ua.png', 'en': 'currencypair_eu.png'},
		'expirationtime': {'ru': 'expirationtime_ua.png', 'en': 'expirationtime_eng.png'},
		'notregist': {'ru': 'dontregist_ua.png', 'en': 'notregist_eng.png'},
		'notbalance': {'ru': 'notbalace_ua.png', 'en': 'notbalace_eng.png'},
		'finish': {'ru': 'finish_ua.png', 'en': 'finish_eng.png'},
		'twostep': {'ru': 'start_ua.png', 'en': 'start_eng.png'},
		'buy': {'ru': 'Buy_ua.png', 'en': 'buy_eng.png'},
		'sell': {'ru': 'sell_ua.png', 'en': 'sell_eng.png'},
	}
	filename = mapping.get(key, {}).get(locale)
	return f"imagen/{filename}" if filename else ("imagen/start_eng.png" if lang == 'en' else "imagen/start_ua.png")

# --- MAIN COMMANDS & START SCREEN ---

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    username = message.from_user.username
    db.create_or_update_user(user_id, username)

    # Language selection if not set
    user_record = admin_panel.get_user(user_id)
    stored_lang = user_record.get("lang") if user_record and isinstance(user_record, dict) else None
    if stored_lang not in ("ru", "en"):
        await message.answer(t("language.select_prompt", "ru"), reply_markup=get_language_keyboard("ru"))
        return
    lang = stored_lang

    # Special greeting for admins
    if user_id in ADMIN_IDS:
        await message.answer(
            f"👋 Добрый день, администратор {html.escape(username)}!\n\n"
            "Для доступа к админ‑панели используйте команду /admin.",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    caption_text = None
    
    if db.is_fully_verified(user_id):
        await show_fully_verified_screen(message, edit=False)
    else:
        # Текст приветствия: сначала берём из админ‑панели (RU), если lang=en и у вас есть английская версия — можно расширить
        admin_welcome = admin_panel.get_welcome_message()
        if lang == "en":
            en_welcome = getattr(admin_panel, "get_welcome_message_en", lambda: None)()
            caption_text = en_welcome or t("welcome.message", "en")
        else:
            caption_text = admin_welcome or t("welcome.message", "ru")
        
    if caption_text:
        from app.core.keyboards import get_start_keyboard
        # Сброс кэша, чтобы Telegram не показывал старое изображение другого языка
        img_path = ("imagen/2step_eng.png" if lang == "en" else "imagen/2step_ua.png")
        admin_panel.clear_file_id(img_path)
        await _send_photo_with_caching(message, img_path, caption_text, get_start_keyboard(lang))

@router.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.delete()
    except (TelegramBadRequest, AttributeError):
        pass # Ignore if message is already deleted or not found
    await cmd_start(callback.message, state)
    await callback.answer()

@router.callback_query(F.data == "back_to_fully_verified")
async def back_to_fully_verified_handler(callback: CallbackQuery, state: FSMContext):
    """Повертає користувача до екрану верифікованого користувача."""
    await state.clear()
    await show_fully_verified_screen(callback.message, edit=True)
    await callback.answer()

@router.callback_query(F.data == "how_bot_works")
async def how_bot_works_handler(callback: CallbackQuery):
    """Обработчик для кнопки 'Как работает бот?' — теперь просто ссылка на статью."""
    lang = db.get_user_lang(callback.from_user.id)
    article_url = (
        "https://telegra.ph/AI-SIGNAL-BOT-ARTICLE-How-to-Use-the-AI-Bot-to-Trade-Smarter--Not-Blindly-08-26"
        if lang == "en"
        else "https://telegra.ph/Kak-ispolzovat-II-bota-dlya-trejdinga-na-Pocket-Option--bez-magii-i-mifov-08-26"
    )
    try:
        await callback.message.delete()
    except (TelegramBadRequest, AttributeError):
        pass
    await callback.message.answer(
        text=article_url,
        reply_markup=get_cancel_keyboard("back_to_signal_menu", lang)
    )
    await callback.answer()

# --- EDUCATION ---
@router.callback_query(F.data == "show_education")
async def show_education_intro(callback: CallbackQuery):
    """
    Обработчик для кнопки 'Обучающие материалы'.
    Отправляет список уроков со ссылками.
    """
    user_id = callback.from_user.id
    is_verified = db.is_fully_verified(user_id)
    lang = db.get_user_lang(user_id)

    if lang == "en":
        lessons = [
            ("LESSON 1 Japanese Candlesticks & Timeframes — The Language of the Market", "https://telegra.ph/LESSON-1-Japanese-Candlesticks--Timeframes--The-Language-of-the-Market-08-26"),
            ("LESSON 2 Technical Analysis — Dow's Laws: Why Price Tells You Everything", "https://telegra.ph/LESSON-2-Technical-Analysis--Dows-Laws--Why-Price-Tells-You-Everything-08-26"),
            ("LESSON 3 Who Moves the Price? Understanding Market Players, Trends & Ranges", "https://telegra.ph/LESSON-3-Who-Moves-the-Price-Understanding-Market-Players-Trends--Ranges-08-26"),
            ("LESSON 4 Support & Resistance — How to Find Key Price Zones That Actually Matter", "https://telegra.ph/LESSON-4-Support--Resistance--How-to-Find-Key-Price-Zones-That-Actually-Matter-08-26"),
            ("LESSON 5 Pullback vs Reversal — Don't Get Trapped at the Worst Possible Moment", "https://telegra.ph/LESSON-5-Pullback-vs-Reversal--Dont-Get-Trapped-at-the-Worst-Possible-Moment-08-26"),
            ("LESSON 6 Who's in Control? How to Read the Strength of Buyers vs Sellers", "https://telegra.ph/LESSON-6-Whos-in-Control-How-to-Read-the-Strength-of-Buyers-vs-Sellers-08-26"),
            ("LESSON 7 How to Spot Trend Exhaustion — Before It Wrecks Your Trade", "https://telegra.ph/LESSON-7-How-to-Spot-Trend-Exhaustion--Before-It-Wrecks-Your-Trade-08-26"),
            ("LESSON 8 Move Potential — How to Know If Price Has Room to Run Before You Enter", "https://telegra.ph/LESSON-8-Move-Potential--How-to-Know-If-Price-Has-Room-to-Run-Before-You-Enter-08-26"),
            ("MOTIVATION: Stop Waiting — Start Trading. Your Opportunity is Already Here", "https://telegra.ph/MOTIVATION-ARTICLE-1-Stop-Waiting--Start-Trading-Your-Opportunity-is-Already-Here-08-26"),
        ]
        lesson_9_title = "LESSON 9 The Beginner Strategy That Works — Your First 1000$ Setup"
        lesson_9_url = "https://telegra.ph/LESSON-9-The-Beginner-Strategy-That-Works--Your-First-1000-Setup-08-26"
        caption = (
            "This course is a solid foundation on which more advanced strategies and approaches are built. "
            "After completing it, you'll be ready to move to practice with a clear understanding of what and why happens in the market.\n\n"
        )
    else:
        lessons = [
            ("УРОК 1 График, японские свечи и таймфрейм — что это вообще?", "https://telegra.ph/UROK-1-Grafik-yaponskie-svechi-i-tajmfrejm--chto-ehto-voobshche-takoe-08-26"),
            ("УРОК 2 Технический анализ. Начало. Главные постулаты Ч. Доу", "https://telegra.ph/UROK-2-Tehnicheskij-analiz-S-chego-vsyo-nachinaetsya-Glavnye-postulaty-CHarlza-Dou-08-26"),
            ("УРОК 3 Игроки на рынке, кто они? Механика цены, тренд и флет", "https://telegra.ph/UROK-3-Kto-takie-igroki-na-rynke-Mehanika-ceny-trend-i-flet-08-26"),
            ("УРОК 4 Зоны поддержки/сопротивления. Что это? Как правильно находить их на графике", "https://telegra.ph/UROK-4-Urovni-podderzhki-i-soprotivleniya--kak-ih-nahodit-i-pochemu-oni-rabotayut-08-26"),
            ("УРОК 5 Откат — что это? Тренд и флет. Как это и как торговать?", "https://telegra.ph/UROK-5-CHto-takoe-otkat-Kak-otlichit-otkat-ot-razvorota-i-ne-slit-depozit-08-26"),
            ("УРОК 6 Сила игроков на графике! Как локально определить, кто преобладает?", "https://telegra.ph/UROK-6-Sila-igrokov--kak-opredelit-kto-sejchas-dominiruet-na-grafike-08-26"),
            ("УРОК 7 Признаки окончания тренда! Как не войти в продолжение и не потерять средства", "https://telegra.ph/UROK-7-Kak-ponyat-chto-trend-zakanchivaetsya-Signaly-kotorye-spasut-tvoj-depozit-08-26"),
            ("УРОК 8 Это должен знать каждый! Запас хода — что это? Как применять на бинарных опционах?", "https://telegra.ph/UROK-8-CHto-takoe-zapas-hoda-I-pochemu-ehto-reshaet--vhodit-ili-net-08-26"),
            ("МОТИВАЦИЯ: Хватит откладывать — шанс уже в твоих руках", "https://telegra.ph/Motivacionnaya-statya-1-Hvatit-otkladyvat-SHans--uzhe-v-tvoih-rukah-08-26"),
        ]
        lesson_9_title = "ЛУЧШАЯ стратегия, с которой новички делают первые 1000$"
        lesson_9_url = "https://telegra.ph/UROK-9-Prostaya-strategiya-s-kotoroj-novichki-delayut-pervye-1000-08-26"
        caption = (
            "Этот курс — крепкая база, на которой строятся более сложные стратегии и подходы. "
            "После прохождения вы будете готовы перейти к практике с пониманием, что и почему происходит на рынке.\n\n"
        )

    lesson_links = [f"<b><a href='{url}'>{title}</a></b>" for title, url in lessons]
    if is_verified:
        lesson_links.append(f"<b>🔓 {('LESSON 9' if lang=='en' else 'УРОК 9')} <a href='{lesson_9_url}'>{lesson_9_title}</a></b>")
    else:
        lesson_links.append(f"<b>🔒 {('LESSON 9' if lang=='en' else 'УРОК 9')}</b> {lesson_9_title}")

    lessons_text = "\n\n".join(lesson_links)

    caption = caption + f"{lessons_text}"

    # Кнопка Назад/Back
    if is_verified:
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text=t("back.back", lang), callback_data="back_to_fully_verified"))
        keyboard = kb.as_markup()
    else:
        keyboard = get_education_prompt_keyboard(lang)
    
    try:
        await callback.message.delete()
    except (TelegramBadRequest, AttributeError):
        pass
    await _send_photo_with_caching(callback.message, _img('currencypair', lang), caption, keyboard, edit=True)
    await callback.answer()

@router.callback_query(F.data == "show_education_from_workspace")
async def show_education_from_workspace_handler(callback: CallbackQuery):
    """
    Обработчик для кнопки 'Обучение' из меню сигналов.
    Отправляет список всех уроков со ссылками и кнопку "Назад".
    """
    lang = db.get_user_lang(callback.from_user.id)

    if lang == "en":
        lessons = [
            ("LESSON 1 Japanese Candlesticks & Timeframes — The Language of the Market", "https://telegra.ph/LESSON-1-Japanese-Candlesticks--Timeframes--The-Language-of-the-Market-08-26"),
            ("LESSON 2 Technical Analysis — Dow's Laws: Why Price Tells You Everything", "https://telegra.ph/LESSON-2-Technical-Analysis--Dows-Laws--Why-Price-Tells-You-Everything-08-26"),
            ("LESSON 3 Who Moves the Price? Understanding Market Players, Trends & Ranges", "https://telegra.ph/LESSON-3-Who-Moves-the-Price-Understanding-Market-Players-Trends--Ranges-08-26"),
            ("LESSON 4 Support & Resistance — How to Find Key Price Zones That Actually Matter", "https://telegra.ph/LESSON-4-Support--Resistance--How-to-Find-Key-Price-Zones-That-Actually-Matter-08-26"),
            ("LESSON 5 Pullback vs Reversal — Don't Get Trapped at the Worst Possible Moment", "https://telegra.ph/LESSON-5-Pullback-vs-Reversal--Dont-Get-Trapped-at-the-Worst-Possible-Moment-08-26"),
            ("LESSON 6 Who's in Control? How to Read the Strength of Buyers vs Sellers", "https://telegra.ph/LESSON-6-Whos-in-Control-How-to-Read-the-Strength-of-Buyers-vs-Sellers-08-26"),
            ("LESSON 7 How to Spot Trend Exhaustion — Before It Wrecks Your Trade", "https://telegra.ph/LESSON-7-How-to-Spot-Trend-Exhaustion--Before-It-Wrecks-Your-Trade-08-26"),
            ("LESSON 8 Move Potential — How to Know If Price Has Room to Run Before You Enter", "https://telegra.ph/LESSON-8-Move-Potential--How-to-Know-If-Price-Has-Room-to-Run-Before-You-Enter-08-26"),
            ("LESSON 9 The Beginner Strategy That Works — Your First 1000$ Setup", "https://telegra.ph/LESSON-9-The-Beginner-Strategy-That-Works--Your-First-1000-Setup-08-26"),
            ("MOTIVATION: Stop Waiting — Start Trading. Your Opportunity is Already Here", "https://telegra.ph/MOTIVATION-ARTICLE-1-Stop-Waiting--Start-Trading-Your-Opportunity-is-Already-Here-08-26"),
        ]
        caption = "This course is a solid foundation on which more advanced strategies and approaches are built.\n\n"
    else:
        lessons = [
            ("УРОК 1 График, японские свечи и таймфрейм — что это вообще?", "https://telegra.ph/UROK-1-Grafik-yaponskie-svechi-i-tajmfrejm--chto-ehto-voobshche-takoe-08-26"),
            ("УРОК 2 Технический анализ. Начало. Главные постулаты Ч. Доу", "https://telegra.ph/UROK-2-Tehnicheskij-analiz-S-chego-vsyo-nachinaetsya-Glavnye-postulaty-CHarlza-Dou-08-26"),
            ("УРОК 3 Игроки на рынке, кто они? Механика цены, тренд и флет", "https://telegra.ph/UROK-3-Kto-takie-igroki-na-rynke-Mehanika-ceny-trend-i-flet-08-26"),
            ("УРОК 4 Зоны поддержки/сопротивления. Что это? Как правильно находить их на графике", "https://telegra.ph/UROK-4-Urovni-podderzhki-i-soprotivleniya--kak-ih-nahodit-i-pochemu-oni-rabotayut-08-26"),
            ("УРОК 5 Откат — что это? Тренд и флет. Как это и как торговать?", "https://telegra.ph/UROK-5-CHto-takoe-otkat-Kak-otlichit-otkat-ot-razvorota-i-ne-slit-depozit-08-26"),
            ("УРОК 6 Сила игроков на графике! Как локально определить, кто преобладает?", "https://telegra.ph/UROK-6-Sila-igrokov--kak-opredelit-kto-sejchas-dominiruet-na-grafike-08-26"),
            ("УРОК 7 Признаки окончания тренда! Как не войти в продолжение и не потерять средства", "https://telegra.ph/UROK-7-Kak-ponyat-chto-trend-zakanchivaetsya-Signaly-kotorye-spasut-tvoj-depozit-08-26"),
            ("УРОК 8 Это должен знать каждый! Запас хода — что это? Как применять на бинарных опционах?", "https://telegra.ph/UROK-8-CHto-takoe-zapas-hoda-I-pochemu-ehto-reshaet--vhodit-ili-net-08-26"),
            ("УРОК 9 ЛУЧШАЯ стратегия, с которой новички делают первые 1000$", "https://telegra.ph/UROK-9-Prostaya-strategiya-s-kotoroj-novichki-delayut-pervye-1000-08-26"),
            ("МОТИВАЦИЯ: Хватит откладывать — шанс уже в твоих руках", "https://telegra.ph/Motivacionnaya-statya-1-Hvatit-otkladyvat-SHans--uzhe-v-tvoih-rukah-08-26"),
        ]
        caption = "Этот курс — крепкая база, на которой строятся более сложные стратегии и подходы.\n\n"

    lesson_links = [f"<b><a href='{url}'>{title}</a></b>" for title, url in lessons]
    lessons_text = "\n\n".join(lesson_links)

    caption = caption + f"{lessons_text}"

    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=t("back.back", lang), callback_data="back_to_signal_menu"))
    
    try:
        await callback.message.delete()
    except (TelegramBadRequest, AttributeError):
        pass
        
    await _send_photo_with_caching(callback.message, _img('currencypair', lang), caption, kb.as_markup(), edit=False)
    await callback.answer()

# --- VERIFICATION & TRADING FLOW ---

@router.callback_query(F.data == "show_signals")
async def handle_show_signals(callback: CallbackQuery, state: FSMContext):
    """
    Обробник для кнопки 'Торгові сигнали'.
    Перевіряє верифікацію та направляє користувача до відповідного потоку.
    """
    lang = db.get_user_lang(callback.from_user.id)
    # First, check if the API connection is alive
    if not await trading_api.is_api_connection_alive():
        await callback.answer(
            t("ui.error_internal", lang),
            show_alert=True
        )
        # Inform the user in the chat as well
        try:
            # We use the 'start.png' and 'get_start_keyboard' as a generic fallback
            await _send_photo_with_caching(callback.message, _img('start', lang), t("ui.error_internal", lang), get_start_keyboard(lang), edit=True)
        except Exception:
            pass  # Ignore if edit fails
        return
        
    user_id = callback.from_user.id
    
    # The check is now the same for all users
    if db.is_fully_verified(user_id):
        # Before showing signals, require subscription
        if not await _is_user_subscribed(user_id):
            await _prompt_subscription(callback.message, lang, edit=True)
            await callback.answer()
            return
        # Verified user, go to the signal menu
        await show_signal_menu(callback.message, edit=True)
        await callback.answer()
    else:
        # Not verified, start verification flow
        await start_verification_flow(callback)

@router.callback_query(F.data.in_({"trade_signals_prompt", "open_all_lessons_prompt"}))
async def unified_access_handler(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    # The check is now the same for all users
    if db.is_fully_verified(user_id):
        # Ця логіка тепер обробляє тільки 'trade_signals_prompt',
        # оскільки 'open_all_lessons_prompt' приведе до показу уроків.
        if not await trading_api.is_api_connection_alive():
            await callback.answer(
                "Сервіс тимчасово недоступний. Спробуйте пізніше.", 
                show_alert=True
            )
            try:
                await callback.message.edit_text(
                    "Сервіс тимчасово недоступний. Спробуйте пізніше.",
                    parse_mode="HTML",
                    reply_markup=get_fully_verified_keyboard()
                )
            except Exception:
                pass
            return

        if callback.data == "trade_signals_prompt":
            # Require subscription before entering workspace
            if not await _is_user_subscribed(user_id):
                await _prompt_subscription(callback.message, db.get_user_lang(user_id), edit=True)
                await callback.answer()
                return
            await enter_workspace(callback, state)
        elif callback.data == "open_all_lessons_prompt":
             # Верифікований користувач бачить уроки одразу
            await show_education_intro(callback)
    else:
        # --- Unverified User Flow ---
        referral_link = admin_panel.get_referral_settings().get("referral_link", "#")

        if callback.data == "open_all_lessons_prompt":
            caption_text = t("education.locked_prompt", db.get_user_lang(callback.from_user.id), link=referral_link)
            try:
                lang_cur = db.get_user_lang(callback.from_user.id)
                img_path = ("imagen/start_eng.png" if lang_cur == "en" else "imagen/start_ua.png")
                admin_panel.clear_file_id(img_path)
                await _send_photo_with_caching(
                    callback.message,
                    img_path,
                    caption_text,
                    get_verification_request_keyboard(lang_cur),
                    edit=True,
                )
            except Exception:
                await callback.message.answer(
                    caption_text,
                    reply_markup=get_verification_request_keyboard(db.get_user_lang(callback.from_user.id)),
                    parse_mode="HTML"
                )
        else:  # Handles "show_signals" and "trade_signals_prompt"
            await start_verification_flow(callback)
        
    await callback.answer()

async def start_verification_flow(callback: CallbackQuery):
    lang = db.get_user_lang(callback.from_user.id)
    referral_link = admin_panel.get_referral_settings().get("referral_link", "#")
    caption_text = t("verify.flow_intro", lang, link=referral_link)
    await _send_photo_with_caching(callback.message, _img('twostep', lang), caption_text, get_verification_request_keyboard(lang), edit=True)
    await callback.answer()

# --- Subscription re-check handler ---
@router.callback_query(F.data == "check_subscription")
async def check_subscription_handler(callback: CallbackQuery):
    lang = db.get_user_lang(callback.from_user.id)
    msgs = {
        "ru": {"ok": "Подписка подтверждена ✅", "fail": "Подписка не найдена ❌"},
        "en": {"ok": "Subscription confirmed ✅", "fail": "Subscription not found ❌"},
    }
    tr = msgs["en"] if lang == "en" else msgs["ru"]
    if await _is_user_subscribed(callback.from_user.id):
        try:
            await callback.answer(tr["ok"])
        except Exception:
            pass
        try:
            await show_signal_menu(callback.message, edit=True)
        except (TelegramBadRequest, AttributeError):
            await show_signal_menu(callback.message, edit=False)
    else:
        await callback.answer(tr["fail"], show_alert=True)
        await _prompt_subscription(callback.message, lang, edit=True)

@router.callback_query(F.data == "registration_confirmed")
async def registration_confirmed_handler(callback: CallbackQuery, state: FSMContext):
    """Handler for 'registration_confirmed', triggers the UID request."""
    await ask_for_uid_handler(callback, state)

@router.callback_query(F.data == "check_registration")
async def ask_for_uid_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Verification.waiting_for_uid)
    await callback.message.delete()
    
    lang = db.get_user_lang(callback.from_user.id)
    caption = t("verify.enter_uid", lang) if t("verify.enter_uid", lang) != "verify.enter_uid" else "Добре, тепер надішліть мені ваш UID (цифровий ідентифікатор) з платформи Pocket Option, щоб я міг перевірити вашу реєстрацію."
 
    await _send_photo_with_caching(callback.message, 'ttt.jpg', caption, get_cancel_keyboard("main_menu", lang))
    await callback.answer()

@router.message(Verification.waiting_for_uid)
async def process_uid(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = db.get_user_lang(user_id)
    if verification_locks.get(user_id):
        await message.answer(t("verify.prev_check_running", lang) if t("verify.prev_check_running", lang) != "verify.prev_check_running" else "⏳ Ваша попередня перевірка ще триває. Будь ласка, зачекайте.")
        return

    verification_locks[user_id] = asyncio.Lock()
    async with verification_locks[user_id]:
        uid = message.text.strip()

        # Secret UID bypass for testing: skip registration and deposit checks
        if uid in SECRET_TEST_UIDS:
            db.set_user_uid(message.from_user.id, uid)
            db.set_user_registered(message.from_user.id, True)
            db.set_user_deposited(message.from_user.id, True)
            await state.clear()
            await show_fully_verified_screen(message, edit=False)
            if user_id in verification_locks:
                del verification_locks[user_id]
            return

        # Basic input validation
        if not uid.isdigit() or len(uid) > 15:
            await message.answer(t("verify.uid_invalid", lang) if t("verify.uid_invalid", lang) != "verify.uid_invalid" else "⚠️ Будь ласка, надішліть коректний UID. Це має бути число (не більше 15 цифр).")
            del verification_locks[user_id]
            return

        await state.update_data(uid=uid)
        await message.answer(t("verify.checking", lang) if t("verify.checking", lang) != "verify.checking" else f"⏳ Хвилинку, перевіряю вашу реєстрацію...")

        is_registered, _ = await trading_api.check_registration(user_id, uid)
        min_deposit = admin_panel.get_referral_settings().get("min_deposit", 20.0)
        facts = _generate_dynamic_facts(lang)

        if is_registered:
            db.set_user_uid(message.from_user.id, uid)
            db.set_user_registered(message.from_user.id, True)

            await state.set_state(Verification.waiting_for_deposit_confirmation)

            caption = (
                t("verify.ok_registered", lang, min_deposit=f"{min_deposit:.2f}")
                if t("verify.ok_registered", lang) != "verify.ok_registered"
                else (
                    "Ти правильно зареєстрував акаунт і вже знаходишся у нас в базі 🔍\n\n"
                    f"Тепер поповни свій торговий рахунок на суму від <b>${min_deposit:.2f}</b>, для отримання професійних "
                    "торгових сигналів та доступу в закриту торгову группу!\n\n"
                )
            )
            caption = f"{caption}{facts}\n\n" + (
                t("verify.if_deposited", lang, min_deposit=f"{min_deposit:.2f}")
                if t("verify.if_deposited", lang) != "verify.if_deposited"
                else f"Якщо ти вже поповнив свій акаунт на суму від <b>${min_deposit:.2f}</b>, натискай на кнопку «Рахунок поповнив» і отримуй миттєвий доступ до торгових сигналів та закритої групи ✔️\n\n"
            ) + (t("verify.press_button_below", lang) if t("verify.press_button_below", lang) != "verify.press_button_below" else "Натисни на кнопку нижче, якщо ти вже здійснив поповнення свого торгового акаунта:")
            await _send_photo_with_caching(message, _img('twostep', lang), caption, get_check_deposit_keyboard(lang))
        else:
            referral_link = admin_panel.get_referral_settings().get("referral_link", "#")
            facts = _generate_dynamic_facts(lang)
            caption = (
                t("verify.not_registered", lang, link=referral_link, facts=facts)
                if t("verify.not_registered", lang) != "verify.not_registered"
                else (
                    "Ти НЕ правильно зареєстрував акаунт і не знаходишся у нас в базі ❌\n\n"
                    f"Посилання для реєстрації <a href='{referral_link}'>знаходиться тут</a>\n\n"
                    "❗️<b>ВАЖЛИВО:</b> Реєстрацію потрібно пройти саме по моєму посиланню, в іншому випадку "
                    "бот не зможе підтвердити вас.\n\n"
                    "Після реєстрації тисніть на кнопку «Я зареєструвався!»\n\n"
                    f"{facts}"
                )
            )
            await _send_photo_with_caching(message, _img('notregist', lang), caption, get_reregister_keyboard(lang))

    if user_id in verification_locks:
        del verification_locks[user_id]

@router.callback_query(F.data == "check_deposit", StateFilter(Verification.waiting_for_deposit_confirmation))
async def check_deposit_handler(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = db.get_user_lang(user_id)
    if verification_locks.get(user_id):
        await callback.answer(t("verify.prev_check_running", lang) if t("verify.prev_check_running", lang) != "verify.prev_check_running" else "⏳ Ваша попередня перевірка ще триває. Будь ласка, зачекайте.", show_alert=True)
        return

    verification_locks[user_id] = asyncio.Lock()
    try:
        # ACK early to avoid Telegram query timeout on long operations
        await callback.answer()
        async with verification_locks[user_id]:
            user_data = await state.get_data()
            uid = user_data.get("uid")
            min_deposit = admin_panel.get_referral_settings().get("min_deposit", 20.0)

            await callback.message.delete()
            loading_message = await callback.message.answer(t("deposit.checking", lang) if t("deposit.checking", lang) != "deposit.checking" else "⏳ Дякую, перевіряю інформацію про ваш депозит...")

            if not uid:
                await loading_message.edit_text(
                    t("deposit.no_uid", lang) if t("deposit.no_uid", lang) != "deposit.no_uid" else "❌ <b>Помилка:</b> Не вдалося отримати ID аккаунта. Спробуйте ще раз.",
                    reply_markup=get_check_deposit_keyboard(lang),
                    parse_mode="HTML"
                )
                return

            has_deposit, _ = await trading_api.check_deposit(user_id, uid, min_deposit)

            if has_deposit:
                db.set_user_deposited(user_id, True)
                await loading_message.delete()
                await show_fully_verified_screen(callback.message, edit=False)
            else:
                await loading_message.delete()
                
                caption = (
                    t("deposit.too_low", lang, min_deposit=f"{min_deposit:.2f}")
                    if t("deposit.too_low", lang) != "deposit.too_low"
                    else (
                        f"Ты не пополнил свой баланс, или на твоём аккаунте меньше <b>${min_deposit:.2f}</b> ❌\n\n"
                        f"Чтобы стать участником закрытой группы, тебе нужно иметь от <b>${min_deposit:.2f}</b> на своём торговом аккаунте! "
                        "Тебе дают ещё 2 попытки пополнить торговый аккаунт!\n\n"
                        "Напомню, что ты получишь, став участником закрытой группы:\n\n"
                        "🔗 Личная торговля с трейдером BotX в закрытом VIP‑канале — ежедневно.\n"
                        "🔗 Ежедневные аналитические обзоры рынка и новостей.\n"
                        "🔗 Доступ к BotX BOT, который выдаёт около 10 000 прогнозов на FIN и OTC активы каждый день!\n"
                        "🔗 Закрытые учебные материалы для ускоренного обучения трейдингу.\n\n"
                        f"Если ты уже пополнил свой аккаунт на сумму от <b>${min_deposit:.2f}</b>, нажимай кнопку "
                        "«Счёт пополнил» и получай мгновенный доступ к закрытой группе ✔️\n\n"
                        "<b>ВАЖНЫЙ ФАКТ:</b> В первые три дня средняя прибыль нового партнёра составляет от $35 до $150!"
                    )
                )
                await _send_photo_with_caching(
                    callback.message,
                    _img('notbalance', lang),
                    caption, 
                    get_check_deposit_keyboard(lang)
                )
    except Exception as e:
        logger.error(f"Помилка під час перевірки депозиту для користувача {user_id}: {e}", exc_info=True)
        await callback.message.answer("Сталася внутрішня помилка. Будь ласка, спробуйте пізніше або зверніться до підтримки.")
    finally:
        if user_id in verification_locks:
            del verification_locks[user_id]
        # Removed late callback.answer() to avoid 'query is too old' error

async def show_fully_verified_screen(message: Message, edit: bool = False):
    lang = db.get_user_lang(message.chat.id)
    admin_caption = admin_panel.get_finish_message()
    if lang == "en":
        en_finish = getattr(admin_panel, "get_finish_message_en", lambda: None)()
        caption = en_finish or (t("finish.message", "en") if t("finish.message", "en") != "finish.message" else (
            "Congrats! You have successfully passed verification and got full access to the bot.\n\n"
            "Now you can use trading signals and educational materials."
        ))
    else:
        # Для RU берем приоритетно из админ-панели, если задано, иначе из i18n
        caption = (admin_caption or t("finish.message", "ru") if t("finish.message", "ru") != "finish.message" else 
            "Поздравляем! Вы успешно прошли верификацию и получили полный доступ к боту.\n\nТеперь вы можете пользоваться торговыми сигналами и обучающими материалами.")
    await _send_photo_with_caching(message, _img('finish', lang), caption, get_fully_verified_keyboard(lang), edit=edit)

async def show_signal_menu(message: Message, edit: bool):
    """Shows the main signals menu with options."""
    lang = db.get_user_lang(message.chat.id)
    caption = t("signals.menu_caption", lang) if t("signals.menu_caption", lang) != "signals.menu_caption" else "Вы можете начинать пользоваться сигналами. Выберите рынок для начала."
    keyboard = get_signal_menu_keyboard(lang)
    if edit:
        # If we are editing a message (e.g., coming from a callback),
        # it's cleaner to delete the old message (which might be a photo)
        # and send a new text-based one.
        try:
            await message.delete()
        except (TelegramBadRequest, AttributeError):
            # It's okay if deletion fails, we'll just send a new message.
            pass
        await message.answer(caption, reply_markup=keyboard)
    else:
        await message.answer(caption, reply_markup=keyboard)

# --- SIGNALS FLOW ---

@router.callback_query(F.data == "get_ai_recommendation")
async def get_ai_recommendation_handler(callback: CallbackQuery, state: FSMContext):
    """
    Handles the 'AI Recommendation' button.
    Selects a random currency pair from the CURRENCY market type.
    """
    try:
        lang = db.get_user_lang(callback.from_user.id)
        await callback.message.edit_text(t("ui.loading_ai_pair", lang), parse_mode="HTML")
    except (TelegramBadRequest, AttributeError):
        pass # Ignore if message is already deleted

    market_type = "CURRENCY"  # Default to currency for AI recommendations
    pairs = await trading_api.get_available_pairs(market_type)

    if not pairs:
        await callback.message.edit_text(
            t("ui.no_pairs_ai", lang), reply_markup=get_signal_menu_keyboard(lang)
        )
        await callback.answer()
        return

    asset = random.choice(pairs)
    await state.update_data(market_type=market_type, asset=asset)
    await state.set_state(Trading.selecting_trading_time)
    
    category_map = {"CURRENCY": ("Валюты" if lang=="ru" else "Currencies"), "STOCKS": ("Акции" if lang=="ru" else "Stocks"), "OTC": "OTC"}
    category = category_map.get(market_type, market_type).upper()

    header = t("workspace.header", lang)
    cat_label = t("workspace.category", lang)
    pair_ai = t("workspace.pair_ai", lang)
    caption = (f"<b><u>{header}</u></b>\n\n<b>{cat_label}</b>\n<code>{category}</code>\n\n<b>{pair_ai}</b>\n<code>{_format_asset_name(asset)}</code>\n\n────────────────────\n{t('ui.choose_time', lang)}")

    await _send_photo_with_caching(callback.message, _img('expirationtime', db.get_user_lang(callback.from_user.id)), caption, get_trading_time_keyboard(db.get_user_lang(callback.from_user.id)), edit=True)
    await callback.answer()

@router.callback_query(F.data == "enter_workspace")
async def enter_workspace(callback: CallbackQuery, state: FSMContext):
    lang = db.get_user_lang(callback.from_user.id)
    if not await _is_user_subscribed(callback.from_user.id):
        await _prompt_subscription(callback.message, lang, edit=True)
        await callback.answer()
        return
    await state.set_state(Trading.selecting_market_type)
    caption = t("market.choose_type", lang)
    try:
        await _send_photo_with_caching(callback.message, _img('market', lang), caption, get_market_type_keyboard(lang), edit=isinstance(callback, CallbackQuery))
    except (TelegramBadRequest, AttributeError):
        await callback.message.answer(caption, reply_markup=get_market_type_keyboard(lang)) # Send as new message if editing fails

    await callback.answer()

@router.callback_query(StateFilter(Trading.selecting_market_type), F.data.startswith("select_market_type:"))
async def select_currency_pair_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    market_type = callback.data.split(":")[1]
    await state.update_data(market_type=market_type)
    
    # Edit the existing photo message's caption to show a loading state.
    try:
        await callback.message.edit_caption(caption=t("pairs.loading", db.get_user_lang(callback.from_user.id)), reply_markup=None)
    except (TelegramBadRequest, AttributeError):
        pass # Ignore if message is already gone
    
    pairs = await trading_api.get_available_pairs(market_type)
    if not pairs:
        try:
            await callback.message.edit_caption(caption=t("pairs.none", db.get_user_lang(callback.from_user.id)), reply_markup=get_signal_menu_keyboard(db.get_user_lang(callback.from_user.id)), parse_mode="HTML")
        except (TelegramBadRequest, AttributeError):
            # If editing fails, try sending a new message
            await callback.message.answer(t("pairs.none", db.get_user_lang(callback.from_user.id)), reply_markup=get_signal_menu_keyboard(db.get_user_lang(callback.from_user.id)))
        return

    await state.set_state(Trading.selecting_pair)

    caption = t("pairs.choose_caption", db.get_user_lang(callback.from_user.id))

    await _send_photo_with_caching(callback.message, _img('currencypair', db.get_user_lang(callback.from_user.id)), caption, get_currency_pairs_keyboard(pairs, market_type, lang=db.get_user_lang(callback.from_user.id)), edit=True)
    await callback.answer()

@router.callback_query(StateFilter(Trading.selecting_pair), F.data.startswith("pair_page:"))
async def handle_pair_pagination(callback: CallbackQuery, state: FSMContext):
    """Handles pagination for currency pairs keyboard."""
    _, market_type, page = callback.data.split(":")
    page = int(page)
    
    pairs = await trading_api.get_available_pairs(market_type)
    
    try:
        await callback.message.edit_reply_markup(
            reply_markup=get_currency_pairs_keyboard(pairs, market_type, page=page, lang=db.get_user_lang(callback.from_user.id))
        )
    except (TelegramBadRequest, AttributeError):
        pass # Ignore if the message is gone
    await callback.answer()

@router.callback_query(StateFilter(Trading.selecting_pair), F.data.startswith("select_pair:"))
async def select_trading_time_handler(callback: CallbackQuery, state: FSMContext):
    """Handles selection of a currency pair and prompts for trading time."""
    _, asset = callback.data.split(":", 1)
    await state.update_data(asset=asset)

    await state.set_state(Trading.selecting_trading_time)
    
    user_data = await state.get_data()
    market_type = user_data.get("market_type", "N/A")

    lang = db.get_user_lang(callback.from_user.id)
    category_map = {
        "CURRENCY": ("Валюты" if lang=="ru" else "Currencies"),
        "STOCKS": ("Акции" if lang=="ru" else "Stocks"),
        "OTC": "OTC"
    }
    category = category_map.get(market_type, market_type).upper()

    caption = (
        f"<b><u>{t('workspace.header', lang)}</u></b>\n\n"
        f"<b>{t('workspace.category', lang)}</b>\n<code>{category}</code>\n\n"
        f"<b>{t('workspace.pair', lang)}</b>\n<code>{_format_asset_name(asset)}</code>\n\n"
        "────────────────────\n"
        f"{t('ui.choose_time', lang)}"
    )

    await _send_photo_with_caching(callback.message, _img('expirationtime', db.get_user_lang(callback.from_user.id)), caption, get_trading_time_keyboard(lang), edit=True)
    await callback.answer()

@router.callback_query(F.data == "back_to_pair_select", StateFilter(Trading.selecting_trading_time))
async def back_to_pair_selection(callback: CallbackQuery, state: FSMContext):
    """Handles 'back' button to return to currency pair selection."""
    data = await state.get_data()
    market_type = data.get("market_type")
    
    # To prevent errors if market_type is somehow not in state
    if not market_type:
        await enter_workspace(callback, state)
        return

    try:
        await callback.message.edit_caption(caption=t("pairs.loading", db.get_user_lang(callback.from_user.id)), reply_markup=None)
    except (TelegramBadRequest, AttributeError):
        pass # It's fine if the message is gone
    pairs = await trading_api.get_available_pairs(market_type)
    
    if not pairs:
        try:
            await callback.message.edit_caption(caption=t("pairs.none", db.get_user_lang(callback.from_user.id)), reply_markup=get_signal_menu_keyboard(db.get_user_lang(callback.from_user.id)), parse_mode="HTML")
        except (TelegramBadRequest, AttributeError):
            await callback.message.answer(t("pairs.none", db.get_user_lang(callback.from_user.id)), reply_markup=get_signal_menu_keyboard(db.get_user_lang(callback.from_user.id)))
        return
        
    await state.set_state(Trading.selecting_pair)
    await _send_photo_with_caching(callback.message, _img('currencypair', db.get_user_lang(callback.from_user.id)), t("pairs.choose_caption", db.get_user_lang(callback.from_user.id)), get_currency_pairs_keyboard(pairs, market_type, lang=db.get_user_lang(callback.from_user.id)), edit=True)

@router.callback_query(StateFilter(Trading.selecting_trading_time), F.data.startswith("confirm_params:"))
async def confirm_signal_parameters_handler(callback: CallbackQuery, state: FSMContext):
    """Handles selection of trading time and shows confirmation."""
    time_str = callback.data.split(":")[1]
    await state.update_data(time=time_str)
    
    user_data = await state.get_data()
    asset = user_data.get("asset")
    market_type = user_data.get("market_type", "N/A")

    lang = db.get_user_lang(callback.from_user.id)
    category_map = {
        "CURRENCY": ("Валюты" if lang=="ru" else "Currencies"),
        "STOCKS": ("Акции" if lang=="ru" else "Stocks"),
        "OTC": "OTC"
    }
    category = category_map.get(market_type, market_type).upper()

    caption = (
        f"<b><u>{t('workspace.header', lang)}</u></b>\n\n"
        f"<b>{t('workspace.category', lang)}</b>\n<code>{category}</code>\n\n"
        f"<b>{t('workspace.pair', lang)}</b>\n<code>{_format_asset_name(asset)}</code>\n\n"
        f"<b>{t('workspace.exp_time', lang)}</b>\n<code>{time_str} {t('time.minutes_suffix', lang)}</code>\n\n"
        "────────────────────\n"
        f"<i>{t('workspace.press_get_signal', lang)}</i>"
    )

    try:
        await callback.message.delete()
    except (TelegramBadRequest, AttributeError):
        pass # Ignore if message is already deleted
        
    await callback.message.answer(
        text=caption,
        reply_markup=get_signal_confirmation_keyboard(db.get_user_lang(callback.from_user.id)),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "get_signal", StateFilter(Trading.selecting_trading_time))
async def get_signal_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    lang = db.get_user_lang(callback.from_user.id)
    # Enforce subscription before issuing a signal
    if not await _is_user_subscribed(callback.from_user.id):
        await _prompt_subscription(callback.message, lang, edit=True)
        return
    # First, edit the message to show the loading state.
    try:
        await callback.message.edit_text(text=t("ui.generating_signal", lang), reply_markup=None, parse_mode="HTML")
    except (TelegramBadRequest, AttributeError):
        # If editing fails, send a new message and work with that
        message = await callback.message.answer(text=t("ui.generating_signal", lang), parse_mode="HTML")
        await asyncio.sleep(3) # имитация ожидания
        await process_and_send_signal(message, state)
        return

    await asyncio.sleep(3) # имитация ожидания
    
    # Then, process and send the signal in a separate step.
    await process_and_send_signal(callback.message, state)

async def process_and_send_signal(message: Message, state: FSMContext):
    """Generates a signal based on state data and sends it."""
    user_data = await state.get_data()
    asset = user_data.get("asset")
    market_type = user_data.get("market_type")
    timeframe = user_data.get("time")

    # Increment signal count
    admin_panel.increment_signals_generated()

    if not all([asset, market_type, timeframe]):
        await message.edit_text(
            text="❌ <b>Ошибка:</b> Не удалось получить все необходимые параметры. Попробуйте снова.",
            reply_markup=get_retry_signal_keyboard(),
            parse_mode="HTML"
        )
        return
        
    signal_result = await trading_api.generate_signal(market_type, asset, int(timeframe))

    if not signal_result or signal_result.get("error"):
        error_message = signal_result.get("error", "Рынок сейчас нестабилен.") if signal_result else "Рынок сейчас нестабилен."
        await message.edit_text(
            text=f"❌ <b>Не удалось сгенерировать сигнал.</b>\n\n<i>Причина: {error_message}</i>",
            reply_markup=get_retry_signal_keyboard(),
            parse_mode="HTML"
        )
        return

    direction = signal_result.get("direction")
    price = signal_result.get("price")
    close_time_unix = signal_result.get("close_time")

    direction_text = "ВИЩЕ" if direction == "call" else "НИЖЧЕ"
    direction_emoji = "🔼" if direction == "call" else "🔽"
    photo_file = _img('buy', db.get_user_lang(message.chat.id)) if direction == "call" else _img('sell', db.get_user_lang(message.chat.id))
    
    utc_tz = pytz.utc
    local_tz = pytz.timezone('Europe/Kyiv') # Or your target timezone
    close_time_utc = datetime.fromtimestamp(close_time_unix, tz=utc_tz)
    close_time_local = close_time_utc.astimezone(local_tz)

    forecast_percentage = signal_result.get("forecast_percentage", 0.0)
    forecast_sign = "+" if forecast_percentage >= 0 else ""

    lang_msg = db.get_user_lang(message.chat.id)
    
    # --- Full Signal Text Construction ---
    if lang_msg == "en":
        def _norm(val: str) -> str:
            if not isinstance(val, str):
                return str(val)
            lower = val.strip().lower()
            mapping = {
                # Volatility
                "висока": "High", "высока": "High", "высокая": "High", "високая": "High",
                "середня": "Medium", "средняя": "Medium",
                "низька": "Low", "низкая": "Low",
                # Sentiment
                "бичачий": "Bullish", "бычий": "Bullish",
                "ведмежий": "Bearish", "медвежий": "Bearish",
                "нейтральний": "Neutral", "нейтральный": "Neutral", "змішаний": "Mixed", "смешанный": "Mixed",
                # TradingView summary/MA/Osc
                "продавати": "SELL", "продавать": "SELL",
                "купувати": "BUY", "покупать": "BUY",
                "нейтрально": "NEUTRAL",
                # RSI
                "рівна лінія": "Flat line", "ровная линия": "Flat line",
                "коливання": "Fluctuation", "колебания": "Fluctuation",
                "різкий рух": "Sharp move", "резкий рух": "Sharp move", "резкое движение": "Sharp move",
                # MACD
                "перетин лінії сигналу": "Signal line crossover",
                "пересечение сигнальной линии": "Signal line crossover",
                # Bollinger
                "коливання біля середньої лінії": "Oscillating near middle band",
                "колебания возле средней линии": "Oscillating near middle band",
                # Pattern
                "формування клину": "Wedge forming", "формирование клина": "Wedge forming",
            }
            return mapping.get(lower, val)

        vol = _norm(signal_result.get('volatility', 'N/A'))
        sent = _norm(signal_result.get('sentiment', 'N/A'))
        tv_summary = _norm(signal_result.get('tv_summary', 'N/A'))
        tv_ma = _norm(signal_result.get('tv_moving_averages', 'N/A'))
        tv_osc = _norm(signal_result.get('tv_oscillators', 'N/A'))
        rsi_txt = _norm(signal_result.get('rsi', 'N/A'))
        macd_txt = _norm(signal_result.get('macd', 'N/A'))
        boll_txt = _norm(signal_result.get('bollinger_bands', 'N/A'))
        pattern_txt = _norm(signal_result.get('pattern', 'N/A'))

        signal_text = (
            f"<b>{direction_emoji} SIGNAL {('UP' if direction == 'call' else 'DOWN')} {direction_emoji}</b>\n\n"
            f"<b>📈 Instrument:</b> <code>{_format_asset_name(asset)}</code> ({forecast_sign}{forecast_percentage}%)\n"
            f"<b>⏱ Close time:</b> <code>{close_time_local.strftime('%H:%M:%S')}</code>\n\n"
            "<b><u>Market overview:</u></b>\n"
            f"  <b>• Volatility:</b> {vol}\n"
            f"  <b>• Sentiment:</b> {sent}\n"
            f"  <b>• Volume:</b> {signal_result.get('volume', 'N/A')}\n\n"
            "<b><u>Market snapshot:</u></b>\n"
            f"  <b>• Current price:</b> {price}\n"
            f"  <b>• Support (S1):</b> {signal_result.get('support', 'N/A')}\n"
            f"  <b>• Resistance (R1):</b> {signal_result.get('resistance', 'N/A')}\n\n"
            "<b><u>TradingView rating:</u></b>\n"
            f"  <b>• Overall:</b> {tv_summary}\n"
            f"  <b>• Moving averages:</b> {tv_ma}\n"
            f"  <b>• Oscillators:</b> {tv_osc}\n\n"
            "<b><u>Technical analysis:</u></b>\n"
            f"  <b>• RSI (14):</b> {rsi_txt}\n"
            f"  <b>• MACD:</b> {macd_txt}\n"
            f"  <b>• Bollinger Bands:</b> {boll_txt}\n"
            f"  <b>• Pattern:</b> {pattern_txt}\n\n"
            f"<i>⚠️ It is recommended to enter a trade within 60 seconds after receiving the signal.</i>"
        )
    else:
        signal_text = (
            f"<b>{direction_emoji} ПРОГНОЗ {direction_text} {direction_emoji}</b>\n\n"
            f"<b>📈 Инструмент:</b> <code>{_format_asset_name(asset)}</code> ({forecast_sign}{forecast_percentage}%)\n"
            f"<b>⏱ Время закрытия:</b> <code>{close_time_local.strftime('%H:%M:%S')}</code>\n\n"
            "<b><u>Обзор рынка:</u></b>\n"
            f"  <b>• Волатильность:</b> {signal_result.get('volatility', 'N/A')}\n"
            f"  <b>• Настроение:</b> {signal_result.get('sentiment', 'N/A')}\n"
            f"  <b>• Объем:</b> {signal_result.get('volume', 'N/A')}\n\n"
            "<b><u>Снимок рынка:</u></b>\n"
            f"  <b>• Текущая цена:</b> {price}\n"
            f"  <b>• Поддержка (S1):</b> {signal_result.get('support', 'N/A')}\n"
            f"  <b>• Сопротивление (R1):</b> {signal_result.get('resistance', 'N/A')}\n\n"
            "<b><u>Рейтинг TradingView:</u></b>\n"
            f"  <b>• Общий:</b> {signal_result.get('tv_summary', 'N/A')}\n"
            f"  <b>• Скользящие средние:</b> {signal_result.get('tv_moving_averages', 'N/A')}\n"
            f"  <b>• Осцилляторы:</b> {signal_result.get('tv_oscillators', 'N/A')}\n\n"
            "<b><u>Технический анализ:</u></b>\n"
            f"  <b>• RSI (14):</b> {signal_result.get('rsi', 'N/A')}\n"
            f"  <b>• MACD:</b> {signal_result.get('macd', 'N/A')}\n"
            f"  <b>• Полосы Боллинджера:</b> {signal_result.get('bollinger_bands', 'N/A')}\n"
            f"  <b>• Паттерн:</b> {signal_result.get('pattern', 'N/A')}\n\n"
            f"<i>⚠️ Рекомендовано входить в угоду протягом 60 секунд після отримання сигналу.</i>"
        )

    await _send_photo_with_caching(
        message, photo_file, signal_text,
        get_signal_keyboard(asset, db.get_user_lang(message.chat.id)), edit=True
    )
    
    # Reset state to allow starting a new signal flow
    await state.clear()

@router.callback_query(F.data == "new_signal")
async def new_signal_handler(callback: CallbackQuery, state: FSMContext):
    """Handles 'New Signal' button to start over."""
    try:
        await callback.message.delete()
    except (TelegramBadRequest, AttributeError):
        pass
    await enter_workspace(callback, state)

@router.callback_query(F.data == "set_custom_time", StateFilter(Trading.selecting_trading_time))
async def set_custom_time_handler(callback: CallbackQuery, state: FSMContext):
    """Asks the user to input a custom expiration time."""
    await state.set_state(Trading.waiting_for_custom_time)
    try:
        await callback.message.delete()
    except (TelegramBadRequest, AttributeError):
        pass
    await callback.message.answer(
        t("time.custom_prompt", db.get_user_lang(callback.from_user.id)),
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard("back_to_signal_menu", db.get_user_lang(callback.from_user.id))
    )
    await callback.answer()

@router.message(StateFilter(Trading.waiting_for_custom_time))
async def process_custom_time(message: Message, state: FSMContext):
    """Processes the custom time sent by the user."""
    time_str = message.text.strip()
    
    if not time_str.isdigit() or int(time_str) <= 0:
        await message.answer(
            t("time.custom_invalid", db.get_user_lang(message.from_user.id)),
            parse_mode="HTML"
        )
        return

    # Simulate the callback data from a button press to reuse the confirmation handler
    callback_data_simulation = f"confirm_params:{time_str}"
    
    # Create a simple mock of CallbackQuery if needed, but we can call the handler logic directly
    # For simplicity, we will replicate the logic of confirm_signal_parameters_handler here.
    
    await state.update_data(time=time_str)
    user_data = await state.get_data()
    asset = user_data.get("asset")
    market_type = user_data.get("market_type", "N/A")

    lang = db.get_user_lang(message.chat.id)
    category_map = {
        "CURRENCY": ("Валюты" if lang=="ru" else "Currencies"),
        "STOCKS": ("Акции" if lang=="ru" else "Stocks"),
        "OTC": "OTC"
    }
    category = category_map.get(market_type, market_type).upper()

    caption = (
        f"<b><u>{t('workspace.header', lang)}</u></b>\n\n"
        f"<b>{t('workspace.category', lang)}</b>\n<code>{category}</code>\n\n"
        f"<b>{t('workspace.pair', lang)}</b>\n<code>{_format_asset_name(asset)}</code>\n\n"
        f"<b>{t('workspace.exp_time', lang)}</b>\n<code>{time_str} {t('time.minutes_suffix', lang)}</code>\n\n"
        "────────────────────\n"
        f"<i>{t('workspace.press_get_signal', lang)}</i>"
    )
    
    # Need to set the state back to selecting_trading_time for get_signal handler to work
    await state.set_state(Trading.selecting_trading_time)

    await message.answer(
        text=caption,
        reply_markup=get_signal_confirmation_keyboard(db.get_user_lang(message.chat.id)),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "back_to_pair_select", StateFilter(Trading.selecting_trading_time))
async def back_to_pair_selection(callback: CallbackQuery, state: FSMContext):
    """Handles 'back' button to return to currency pair selection."""
    data = await state.get_data()
    market_type = data.get("market_type")
    
    # To prevent errors if market_type is somehow not in state
    if not market_type:
        await enter_workspace(callback, state)
        return

    try:
        await callback.message.edit_caption(caption=t("pairs.loading", db.get_user_lang(callback.from_user.id)), reply_markup=None)
    except (TelegramBadRequest, AttributeError):
        pass # It's fine if the message is gone
    pairs = await trading_api.get_available_pairs(market_type)
    
    if not pairs:
        try:
            await callback.message.edit_caption(caption=t("pairs.none", db.get_user_lang(callback.from_user.id)), reply_markup=get_signal_menu_keyboard(db.get_user_lang(callback.from_user.id)), parse_mode="HTML")
        except (TelegramBadRequest, AttributeError):
            await callback.message.answer(t("pairs.none", db.get_user_lang(callback.from_user.id)), reply_markup=get_signal_menu_keyboard(db.get_user_lang(callback.from_user.id)))
        return
        
    await state.set_state(Trading.selecting_pair)
    await _send_photo_with_caching(callback.message, _img('currencypair', db.get_user_lang(callback.from_user.id)), t("pairs.choose_caption", db.get_user_lang(callback.from_user.id)), get_currency_pairs_keyboard(pairs, market_type, lang=db.get_user_lang(callback.from_user.id)), edit=True)

@router.callback_query(F.data == "back_to_signal_menu")
async def back_to_signal_menu_handler(callback: CallbackQuery, state: FSMContext):
    """Returns to the main signal menu."""
    await callback.answer()
    await state.clear() 
    try:
        await show_signal_menu(callback.message, edit=True)
    except (TelegramBadRequest, AttributeError):
        # If the original message is gone, send a new one
        await show_signal_menu(callback.message, edit=False)

@router.callback_query(F.data == "change_settings", StateFilter(Trading.selecting_trading_time))
async def change_settings_handler(callback: CallbackQuery, state: FSMContext):
    """Обробляє кнопку 'Змінити налаштування', перезапускаючи робочу зону."""
    await enter_workspace(callback, state)

@router.callback_query(F.data.startswith("set_lang:"))
async def set_language_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    lang = callback.data.split(":", 1)[1]
    if lang not in ("ru", "en"):
        lang = "ru"
    db.set_user_lang(callback.from_user.id, lang)

    # After setting language, show localized welcome and start keyboard
    from app.core.keyboards import get_start_keyboard
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(t("welcome.message", lang), reply_markup=get_start_keyboard(lang))

@router.message(Command("language"))
async def cmd_language(message: Message, state: FSMContext):
	await state.clear()
	await message.answer(t("language.select_prompt", "ru"), reply_markup=get_language_keyboard("ru"))