"""
admin_panel_handlers.py
Обработчики и вспомогательные функции для админ‑панели Telegram‑бота.
"""

import logging
import json
import os
from datetime import datetime, timedelta, timezone
import asyncio
from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)

from app.core.dispatcher import dp, bot, admin_panel, trading_api
from app.core.keyboards import (
    get_referral_settings_keyboard, 
    get_cancel_keyboard,
    get_back_to_panel_keyboard, 
)
from app.core.fsm import Admin, AuthStates
import app.core.database as db
from app.handlers.user_handlers import show_signal_menu
from app.services.telethon_code import telethon_client
from app.core.i18n import t


router = Router()

@router.callback_query(F.data == "admin_show_signals")
async def admin_show_signals_handler(callback: CallbackQuery, state: FSMContext):
    """Показывает администратору меню сигналов, как обычному пользователю."""
    await show_signal_menu(callback.message, edit=True)
    await callback.answer()

@router.callback_query(F.data == "none")
async def handle_none_callback(callback: CallbackQuery):
    """Обрабляет колбеки от информационных кнопок, просто отвечая на них."""
    await callback.answer()

# region Service Functions
async def show_admin_panel(message: Message | CallbackQuery, state: FSMContext):
    """Відображає головну панель адміністратора."""
    await state.set_state(Admin.admin_menu)
    text = "👨‍💼 <b>Админ‑панель</b>\n\nВыберите опцию для управления ботом:"
    markup = admin_panel.get_admin_keyboard()
    
    if isinstance(message, CallbackQuery):
        try:
            await message.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
        except TelegramBadRequest:
            try:
                await message.message.delete()
            except TelegramBadRequest:
                pass # Игнорируем просроченные или недействительные callback‑запросы
            await message.message.answer(text, reply_markup=markup, parse_mode="HTML")
        finally:
            try:
                await message.answer()
            except TelegramBadRequest:
                # Игнорируем просроченные или недействительные callback‑запросы
                pass
    else:
        await message.answer(text, reply_markup=markup, parse_mode="HTML")

async def _show_settings_panel(message: Message | CallbackQuery, state: FSMContext):
    """Допоміжна функція для відображення меню налаштувань."""
    await state.set_state(Admin.settings)
    text = "⚙️ <b>Настройки</b>\n\nВыберите, что хотите настроить:"
    markup = admin_panel.get_settings_keyboard()
    
    if isinstance(message, CallbackQuery):
        try:
            await message.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
        except TelegramBadRequest:
            try:
                await message.message.delete()
            except TelegramBadRequest:
                pass
            await message.message.answer(text, reply_markup=markup, parse_mode="HTML")
        finally:
            try:
                await message.answer()
            except TelegramBadRequest:
                pass
    else:
        await message.answer(text, reply_markup=markup, parse_mode="HTML")

async def _show_referral_panel(message: Message | CallbackQuery, state: FSMContext):
    """Допоміжна функція для відображення меню реферальних налаштувань."""
    await state.set_state(Admin.referral_settings)
    settings = admin_panel.get_referral_settings()
    text = "🔗 <b>Реферальные настройки</b>\n\nЗдесь вы можете изменить минимальный депозит и реферальную ссылку."
    markup = get_referral_settings_keyboard(settings)

    if isinstance(message, CallbackQuery):
        try:
            await message.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
        except TelegramBadRequest:
            try:
                await message.message.delete()
            except TelegramBadRequest:
                pass
            await message.message.answer(text, reply_markup=markup, parse_mode="HTML")
        finally:
            try:
                await message.answer()
            except TelegramBadRequest:
                pass
    else:
        await message.answer(text, reply_markup=markup, parse_mode="HTML")

# endregion

# region Main Admin Commands
@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """Обробляє команду /admin."""
    if admin_panel.is_admin(message.from_user.id):
        await show_admin_panel(message, state)
    else:
        await message.answer("У вас немає доступу до цієї команди.")

@router.callback_query(F.data == "admin_panel")
async def cq_show_admin_panel(callback: CallbackQuery, state: FSMContext):
    """Обробляє колбек 'admin_panel' для показу головної адмін-панелі."""
    await show_admin_panel(callback, state)

@router.callback_query(F.data == "admin_settings")
async def handle_show_settings(callback: CallbackQuery, state: FSMContext):
    """Обробник для входу в меню налаштувань."""
    await _show_settings_panel(callback, state)

@router.message(Command("stats"))
async def show_stats_command(message: Message):
    """Відображає статистику бота. Тільки для адміністраторів."""
    if not admin_panel.is_admin(message.from_user.id):
        await message.reply("Ця команда доступна лише для адміністраторів.")
        return

    stats = admin_panel.get_statistics()
    
    stats_message = (
        "📊 <b>Статистика бота</b>\n\n"
        f"👤 Унікальні користувачі (в базі): {stats['total_users']}\n"
        f"🚀 Натискання /start: {stats['total_starts']}\n"
        f"✅ Верифіковані користувачі: {stats['verified_users']}\n"
        f"⏳ Користувачі в процесі верифікації: {stats['in_verification_users']}\n"
        f"📈 Згенеровано сигналів (сьогодні): {stats['signals_generated_today']}\n"
        f"📈 Згенеровано сигналів (всього): {stats['signals_generated_total']}"
    )
    
    await message.answer(stats_message, parse_mode="HTML")

# endregion

# region Maintenance
async def _show_maintenance_panel(message: Message | CallbackQuery, state: FSMContext):
    """Допоміжна функція для відображення меню обслуговування."""
    await state.set_state(Admin.maintenance)
    text = "🔄 <b>Управление режимом обслуживания</b>"
    markup = admin_panel.get_maintenance_keyboard()
    
    if isinstance(message, CallbackQuery):
        try:
            await message.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
        except TelegramBadRequest:
            try:
                await message.message.delete()
            except TelegramBadRequest:
                pass
            await message.message.answer(text, reply_markup=markup, parse_mode="HTML")
        finally:
            try:
                await message.answer()
            except TelegramBadRequest:
                pass
    else:
        await message.answer(text, reply_markup=markup, parse_mode="HTML")

@router.callback_query(F.data == "admin_maintenance")
async def handle_show_maintenance_panel(callback: CallbackQuery, state: FSMContext):
    """Обробник для входу в меню обслуговування."""
    await _show_maintenance_panel(callback, state)

@router.callback_query(F.data == "admin_maintenance_toggle")
async def toggle_maintenance_mode(callback: CallbackQuery, state: FSMContext):
    """Перемикає режим обслуговування."""
    new_mode = not admin_panel.get_maintenance_mode()
    admin_panel.set_maintenance_mode(new_mode)
    status = "увімкнено" if new_mode else "вимкнено"
    
    try:
        await callback.answer(f"Режим обслуживания {status}.", show_alert=True)
    except TelegramBadRequest:
        pass
    # Оновлюємо панель обслуговування, щоб показати новий статус
    await _show_maintenance_panel(callback, state)

@router.callback_query(F.data == "admin_set_maintenance_msg")
async def set_maintenance_msg(callback: CallbackQuery, state: FSMContext):
    """Запитує нове повідомлення про тех. роботи."""
    await state.set_state(Admin.change_maintenance_message)
    await callback.message.edit_text(
        f"Текущее сообщение:\n<i>{admin_panel.get_maintenance_message()}</i>\n\n✍️ Введите новое:",
        reply_markup=get_cancel_keyboard("admin_maintenance"), # Назад до меню обслуговування
        parse_mode="HTML"
    )

@router.message(StateFilter(Admin.change_maintenance_message), F.text)
async def process_new_maintenance_message(message: Message, state: FSMContext):
    """Оновлює повідомлення про тех. роботи."""
    admin_panel.set_maintenance_message(message.text.strip())
    await message.answer("✅ <b>Сообщение об обслуживании обновлено.</b>", parse_mode="HTML")
    await _show_maintenance_panel(message, state)

# endregion

# region Statistics
@router.callback_query(F.data == "admin_stats")
async def show_admin_stats(callback: CallbackQuery):
    """Показує статистику бота."""
    stats = admin_panel.get_statistics()
    
    stats_text = (
        "📊 <b>Статистика бота</b>\n\n"
        f"👤 Уникальные пользователи (в базе): {stats['total_users']}\n"
        f"🚀 Нажатий /start: {stats['total_starts']}\n"
        f"✅ Верифицированные пользователи: {stats['verified_users']}\n"
        f"⏳ Пользователи в процессе верификации: {stats['in_verification_users']}\n"
        f"📈 Сгенерировано сигналов (сегодня): {stats['signals_generated_today']}\n"
        f"📈 Сгенерировано сигналов (всего): {stats['signals_generated_total']}"
    )
    
    try:
        await callback.message.edit_text(
            stats_text,
            reply_markup=admin_panel.get_admin_keyboard(),
            parse_mode="HTML",
        )
    except TelegramBadRequest:
        # Повідомлення не змінилося, просто відповідаємо на колбек
        await callback.answer("Данные статистики не изменились.")
    else:
        await callback.answer()
# endregion

# region Broadcast
@router.callback_query(F.data == 'admin_broadcast_menu')
async def broadcast_menu(callback: CallbackQuery, state: FSMContext):
    """Показує меню вибору типу розсилки."""
    await callback.message.edit_text(
        "📨 <b>Рассылка</b>\n\nВыберите, кому отправить сообщение:",
        reply_markup=admin_panel.get_broadcast_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == 'admin_broadcast_all')
async def start_broadcast_all(callback: CallbackQuery, state: FSMContext):
    """Починає процес розсилки для всіх."""
    await state.set_state(Admin.send_broadcast)
    await callback.message.edit_text(
        "📨 Введите сообщение для рассылки. Оно будет отправлено <b>всем</b> пользователям бота.",
        reply_markup=get_cancel_keyboard("admin_broadcast_menu"),
        parse_mode="HTML"
    )

@router.callback_query(F.data == 'admin_broadcast_verified')
async def start_broadcast_verified(callback: CallbackQuery, state: FSMContext):
    """Починає процес розсилки для верифікованих."""
    await state.set_state(Admin.send_verified_broadcast)
    await callback.message.edit_text(
        "📨 Введите сообщение для рассылки. Оно будет отправлено только <b>верифицированным</b> пользователям.",
        reply_markup=get_cancel_keyboard("admin_broadcast_menu"),
        parse_mode="HTML"
    )

@router.message(StateFilter(Admin.send_broadcast), F.text)
async def process_broadcast_message(message: Message, state: FSMContext):
    """Надсилає розсилку всім користувачам."""
    users = db.get_all_users()
    await send_messages_to_users(message, state, list(users.keys()))

@router.message(StateFilter(Admin.send_verified_broadcast), F.text)
async def process_verified_broadcast_message(message: Message, state: FSMContext):
    """Надсилає розсилку верифікованим користувачам."""
    all_users = db.get_all_users()
    verified_user_ids = [uid for uid, udata in all_users.items() if db.is_fully_verified(int(uid))]
    await send_messages_to_users(message, state, verified_user_ids)

async def send_messages_to_users(message: Message, state: FSMContext, user_ids: list):
    """Відправляє повідомлення заданому списку користувачів."""
    total_users = len(user_ids)
    count = 0
    errors = 0
    
    await message.answer(f"⏳ Починаю розсилку для <b>{total_users}</b> користувачів...", parse_mode="HTML")
    
    for user_id in user_ids:
        try:
            await bot.send_message(user_id, message.text, parse_mode="HTML")
            count += 1
            await asyncio.sleep(0.1)  # Невелика затримка
        except Exception as e:
            errors += 1
            logger.warning(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
            
    await message.answer(
        f"✅ <b>Рассылка завершена.</b>\n\n"
        f"📥 Отправлено: <b>{count}</b> из {total_users}\n"
        f"❌ Ошибок: <b>{errors}</b>",
        reply_markup=admin_panel.get_admin_keyboard(),
        parse_mode="HTML"
    )
    await state.clear()

# endregion

# region Settings

# Welcome Message
@router.callback_query(F.data == "admin_set_welcome")
async def set_welcome_msg(callback: CallbackQuery, state: FSMContext):
    """Показывает варианты изменения приветствия (RU/EN)."""
    await state.set_state(Admin.change_welcome_message)
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="RU", callback_data="admin_set_welcome_ru"),
        InlineKeyboardButton(text="EN", callback_data="admin_set_welcome_en"),
    )
    kb.row(InlineKeyboardButton(text=t("admin.settings.back", "ru"), callback_data="admin_settings"))
    await callback.message.edit_text(
        f"Текущее RU:\n<i>{admin_panel.get_welcome_message()}</i>\n\n"
        f"Current EN:\n<i>{admin_panel.get_welcome_message_en()}</i>",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    try:
        await callback.answer()
    except TelegramBadRequest:
        pass

@router.callback_query(F.data == "admin_set_welcome_ru")
async def ask_welcome_ru(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Admin.change_welcome_message)
    await callback.message.edit_text(
        f"<b>Текущее RU сообщение:</b>\n\n<i>{admin_panel.get_welcome_message()}</i>\n\n✍️ Введите новое RU‑сообщение:",
        reply_markup=get_cancel_keyboard("admin_settings"),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_set_welcome_en")
async def ask_welcome_en(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Admin.waiting_for_text_to_edit)
    await callback.message.edit_text(
        f"<b>Current EN message:</b>\n\n<i>{admin_panel.get_welcome_message_en()}</i>\n\n✍️ Enter new EN message:",
        reply_markup=get_cancel_keyboard("admin_settings"),
        parse_mode="HTML"
    )

@router.message(Admin.change_welcome_message, F.text)
async def process_new_welcome_message(message: Message, state: FSMContext):
    admin_panel.set_welcome_message(message.text.strip())
    await message.answer("✅ <b>RU приветствие обновлено!</b>", parse_mode="HTML")
    await _show_settings_panel(message, state)

@router.message(Admin.waiting_for_text_to_edit, F.text)
async def process_new_welcome_message_en(message: Message, state: FSMContext):
    admin_panel.set_welcome_message_en(message.text.strip())
    await message.answer("✅ <b>EN welcome updated!</b>", parse_mode="HTML")
    await _show_settings_panel(message, state)

# Finish Message
@router.callback_query(F.data == "admin_set_finish_msg")
async def set_finish_msg(callback: CallbackQuery, state: FSMContext):
    """Показывает варианты изменения финального сообщения (RU/EN)."""
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="RU", callback_data="admin_set_finish_ru"),
        InlineKeyboardButton(text="EN", callback_data="admin_set_finish_en"),
    )
    kb.row(InlineKeyboardButton(text=t("admin.settings.back", "ru"), callback_data="admin_settings"))
    await callback.message.edit_text(
        f"Текущее RU:\n<i>{admin_panel.get_finish_message()}</i>\n\n"
        f"Current EN:\n<i>{admin_panel.get_finish_message_en()}</i>",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_set_finish_ru")
async def ask_finish_ru(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Admin.change_finish_message)
    await callback.message.edit_text(
        f"<b>Текущее RU сообщение:</b>\n\n<i>{admin_panel.get_finish_message()}</i>\n\n✍️ Введите новое RU‑сообщение:",
        reply_markup=get_cancel_keyboard("admin_settings"),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_set_finish_en")
async def ask_finish_en(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Admin.viewing_stats)
    await callback.message.edit_text(
        f"<b>Current EN message:</b>\n\n<i>{admin_panel.get_finish_message_en()}</i>\n\n✍️ Enter new EN message:",
        reply_markup=get_cancel_keyboard("admin_settings"),
        parse_mode="HTML"
    )

@router.message(Admin.viewing_stats, F.text)
async def process_new_finish_en(message: Message, state: FSMContext):
    admin_panel.set_finish_message_en(message.text.strip())
    await message.answer("✅ <b>EN finish updated!</b>", parse_mode="HTML")
    await _show_settings_panel(message, state)

# Referral Settings
@router.callback_query(F.data == "admin_set_referral")
async def show_referral_settings(callback: CallbackQuery, state: FSMContext):
    """Показує меню налаштувань реферальної програми."""
    await _show_referral_panel(callback, state)

@router.callback_query(F.data == "admin_change_min_deposit")
async def change_min_deposit_start(callback: CallbackQuery, state: FSMContext):
    """Починає процес зміни мінімального депозиту."""
    await state.set_state(Admin.change_min_deposit)
    current_deposit = admin_panel.get_referral_settings().get('min_deposit', 0)
    await callback.message.edit_text(
        f"💰 <b>Поточний мін. депозит:</b> {current_deposit}\n\nВведіть нове значення:",
        reply_markup=get_cancel_keyboard("admin_set_referral"),
        parse_mode="HTML"
    )
    try:
        await callback.answer()
    except TelegramBadRequest:
        pass

@router.message(StateFilter(Admin.change_min_deposit), F.text)
async def process_new_min_deposit(message: Message, state: FSMContext):
    """Обробляє новий мінімальний депозит."""
    try:
        deposit = float(message.text.strip().replace(",", "."))
        if deposit <= 0:
            raise ValueError("Сума повинна бути більше нуля.")
        
        # Використовуємо правильний метод для оновлення
        if admin_panel.update_referral_settings(min_deposit=deposit):
            await message.answer(f"✅ Мінімальный депозит оновлено: <b>${deposit:.2f}</b>", parse_mode="HTML")
            await _show_referral_panel(message, state)
        else:
            await message.answer("❌ Не вдалося оновити мінімальный депозит. Перевірте логи.", parse_mode="HTML")
            
    except ValueError as e:
        logger.error(f"Помилка при оновленні депозиту: {e}")
        await message.answer(
            "⚠️ Будь ласка, введіть коректне числове значення для депозиту (наприклад, 20 або 25.5).",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Неочікувана помилка при оновленні депозиту: {e}")
        await message.answer("❌ Сталася неочікувана помилка. Спробуйте ще раз.", parse_mode="HTML")

@router.callback_query(F.data == "admin_change_ref_link")
async def change_ref_link_start(callback: CallbackQuery, state: FSMContext):
    """Починає процес зміни реферального посилання."""
    await state.set_state(Admin.change_referral_link)
    current_link = admin_panel.get_referral_settings().get('referral_link', 'Не встановлено')
    await callback.message.edit_text(
        f"🔗 <b>Поточне посилання:</b>\n<code>{current_link}</code>\n\nВведіть нове посилання:",
        reply_markup=get_cancel_keyboard("admin_set_referral"),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(StateFilter(Admin.change_referral_link), F.text)
async def process_new_ref_link(message: Message, state: FSMContext):
    """Обробляє нове реферальне посилання."""
    admin_panel.set_referral_link(message.text.strip())
    await message.answer("✅ <b>Реферальная ссылка обновлена.</b>", parse_mode="HTML")
    await state.clear()
    await _show_referral_panel(message, state)

# endregion

# region Auth Management
@router.callback_query(F.data == "admin_auth")
async def admin_auth_callback(callback: CallbackQuery):
    """Колбек для кнопки ручної авторизації адміністратора."""
    if not admin_panel.is_admin(callback.from_user.id):
        await callback.answer("Эта кнопка только для администраторов.", show_alert=True)
        return

    # Запускаємо браузер для ручного входу
    await callback.message.edit_text("⏳ Запускаю браузер для ручної авторизації...")
    await trading_api.auth.manual_login_start()
    
    # Перевіряємо, що драйвер запустився
    if trading_api.auth.driver:
        await callback.message.edit_text(
            "✅ Браузер запущено.\n\n"
            "Будь ласка, увійдіть до свого акаунту Pocket Option у вікні, що відкрилося.\n\n"
            "Після успішного входу та завантаження торгового кабінету, натисніть кнопку нижче.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Я увійшов до акаунту", callback_data="admin_confirm_auth")]
            ])
        )
    else:
        await callback.message.edit_text("❌ Не вдалося запустити браузер Selenium. Перевірте логи на сервері.")
    await callback.answer()
    
@router.callback_query(F.data == "admin_confirm_auth")
async def process_manual_login_confirmation(callback: CallbackQuery, state: FSMContext):
    """Handles the 'I have logged in' confirmation button."""
    await callback.message.edit_text("⏳ Перевіряю підтвердження авторизації та оновлюю сесію...")

    # This single call now handles confirmation, saving cookies, and re-initializing the API
    success = await trading_api.perform_manual_login_confirm()

    if success:
        balance = await trading_api.get_balance()
        balance_text = f"${balance:.2f}" if balance is not None else "не вдалося отримати"
        await callback.message.answer(
            "✅ Авторизація успішна! Сесію оновлено.\n"
            f"API готовий до роботи. Поточний баланс: <b>{balance_text}</b>",
            parse_mode="HTML"
        )
    else:
        await callback.message.answer(
            "❌ Не вдалося підтвердити авторизацію. Переконайтеся, що ви увійшли до акаунту у вікні браузера, та спробуйте знову."
        )
    
    await show_admin_panel(callback, state)


@router.callback_query(F.data == "start_manual_auth")
async def start_manual_auth_handler(callback: CallbackQuery):
    """
    Обробляє виклик 'start_manual_auth' з повідомлення-сповіщення.
    Запитує у адміна підтвердження перед початком процесу авторизації.
    """
    await admin_auth_callback(callback)

@router.callback_query(F.data == "admin_telethon_login")
async def admin_telethon_login(callback: CallbackQuery, state: FSMContext):
    if not admin_panel.is_admin(callback.from_user.id):
        await callback.answer("Эта кнопка только для администраторов.", show_alert=True)
        return
    await callback.message.edit_text(
        "Введіть номер телефону для входу в Telegram у форматі +380...",
        reply_markup=get_cancel_keyboard("admin_panel"),
        parse_mode="HTML"
    )
    await state.set_state(AuthStates.waiting_for_code)  # тимчасово, далі перезапишемо на waiting_for_password/код
    await callback.answer()

@router.message(StateFilter(AuthStates.waiting_for_code), F.text)
async def telethon_receive_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    try:
        await telethon_client.start_login(phone)
        await message.answer("Код надіслано в Telegram. Введіть його тут:")
        await state.set_state(AuthStates.waiting_for_password)  # використаємо як 'waiting_for_code'
    except Exception as e:
        logger.error(f"Помилка надсилання коду: {e}")
        await message.answer("❌ Не вдалося надіслати код. Перевірте номер і спробуйте ще раз.")
        await state.clear()

@router.message(StateFilter(AuthStates.waiting_for_password), F.text)
async def telethon_receive_code(message: Message, state: FSMContext):
    code = message.text.strip()
    try:
        try:
            ok = await telethon_client.complete_login_code(code)
            if ok:
                await message.answer("✅ Вхід успішний! Telethon підключено.")
                await state.clear()
                return
        except Exception as auth_exc:
            from telethon.errors import SessionPasswordNeededError
            if isinstance(auth_exc, SessionPasswordNeededError):
                await message.answer("🔐 Увімкнено двофакторний захист. Введіть ваш пароль 2FA:")
                await state.set_state(AuthStates.waiting_for_confirmation)
                return
            raise
    except Exception as e:
        logger.error(f"Помилка підтвердження коду: {e}")
        await message.answer("❌ Невірний код або помилка підтвердження. Спробуйте ще раз командою /admin.")
        await state.clear()

@router.message(StateFilter(AuthStates.waiting_for_confirmation), F.text)
async def telethon_receive_2fa(message: Message, state: FSMContext):
    password = message.text.strip()
    try:
        ok = await telethon_client.complete_2fa(password)
        if ok:
            await message.answer("✅ Вхід успішний! Telethon підключено.")
        else:
            await message.answer("❌ Не вдалося авторизуватися. Спробуйте ще раз.")
    except Exception as e:
        logger.error(f"Помилка 2FA: {e}")
        await message.answer("❌ Невірний пароль 2FA або інша помилка.")
    finally:
        await state.clear()

# endregion

# region Other
@router.callback_query(F.data == "admin_referrals")
async def show_admin_referrals(callback: CallbackQuery, state: FSMContext):
    """Показує список рефералів."""
    # Ця функція потребує реалізації
    await callback.answer("Эта функция в разработке.", show_alert=True)


@router.callback_query(F.data == "admin_check_cookies")
async def check_cookies_status(callback: CallbackQuery):
    """Перевіряє статус cookie і надсилає звіт."""
    are_valid = trading_api.auth.are_cookies_valid()
    
    if are_valid:
        expiry_time = trading_api.auth.get_expiration_time()
        if expiry_time:
            now = datetime.now(timezone.utc)
            time_left = expiry_time - now
            days = time_left.days
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            expiry_date_str = expiry_time.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

            message_text = (
                f"✅ Статус cookies\n\n"
                f"Cookies действительны. Осталось: {days} дн., {hours} ч., {minutes} мин.\n"
                f"Следующее принудительное обновление: {expiry_date_str}"
            )
        else:
            message_text = "✅ Cookies действительны, но не удалось определить точное время обновления."
    else:
        message_text = "❌ Cookies недействительны или отсутствуют!\n\nНеобходимо провести ручную авторизацию."

    await callback.answer(message_text, show_alert=True)

@router.callback_query(F.data == "admin_workspace")
async def show_admin_workspace(callback: CallbackQuery, state: FSMContext):
    """Показує робочу область (приклад)."""
    # Ця функція потребує реалізації
    await callback.answer("Эта функция в разработке.", show_alert=True)


@router.callback_query(F.data == "admin_panel")
async def back_to_admin_panel(callback: CallbackQuery, state: FSMContext):
    """Обробник для повернення в головне меню адмінки."""
    await state.clear()
    await show_admin_panel(callback, state)

@router.callback_query(F.data == "admin_settings")
async def back_to_settings(callback: CallbackQuery, state: FSMContext):
    """Обробник для повернення в меню налаштувань."""
    await _show_settings_panel(callback, state)

@router.callback_query(F.data == "admin_upload_ssid_json")
async def admin_upload_ssid_json(callback: CallbackQuery):
    """Подсказка админу загрузить JSON с SSID."""
    await callback.message.edit_text(
        "Отправьте сюда JSON-файл, созданный экспортёром (pocket_ssid.json).\n"
        "Формат: {\"ssid\": \"...\", \"cookies\": [...](необязательно), \"expiry\": \"ISO\"(необязательно).",
        reply_markup=get_back_to_panel_keyboard("ru"),
        parse_mode="HTML",
    )
    await callback.answer()