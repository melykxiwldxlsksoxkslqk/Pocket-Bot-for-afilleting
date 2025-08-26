from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
import logging
import asyncio

from app.core.dispatcher import trading_api
from app.core.fsm import Authorization
from app.core.keyboards import get_auth_confirmation_keyboard
from app.core.i18n import t
import app.core.database as db

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "start_user_auth")
async def handle_start_user_auth(callback: CallbackQuery, state: FSMContext):
    """
    Handles the 'start_user_auth' button for regular users.
    """
    lang = db.get_user_lang(callback.from_user.id)
    await callback.message.edit_text(
        t("auth.start_browser", lang) if t("auth.start_browser", lang) != "auth.start_browser" else "⏳ Запускаю браузер для ручної авторизації...\n\nБудь ласка, зачекайте, це може зайняти до 30 секунд.",
        reply_markup=None
    )
    
    # This runs the browser opening in the background
    asyncio.create_task(trading_api.perform_manual_login_start())
    
    await asyncio.sleep(5) # Give some time for the browser to initialize
    
    await callback.message.edit_text(
        t("auth.follow_login_steps", lang) if t("auth.follow_login_steps", lang) != "auth.follow_login_steps" else "🤖 Будь ласка, виконайте вхід в акаунт у вікні браузера, яке відкрилося.\n\nПісля успішного входу та повного завантаження торгової кімнати, натисніть кнопку нижче.",
        reply_markup=get_auth_confirmation_keyboard(lang) # This keyboard should contain 'confirm_auth'
    )
    await state.set_state(Authorization.waiting_for_confirmation)

@router.callback_query(F.data == "confirm_auth", StateFilter(Authorization.waiting_for_confirmation))
async def handle_confirm_auth(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Handles the confirmation from the user that they have logged in.
    """
    lang = db.get_user_lang(callback.from_user.id)
    await callback.message.edit_text(t("auth.checking", lang) if t("auth.checking", lang) != "auth.checking" else "⏳ Перевіряю авторизацію та зберігаю сесію...", reply_markup=None)
    
    # This runs the confirmation logic
    success = await trading_api.perform_manual_login_confirm()
    
    if success:
        trading_api.critical_notification_sent = False # Reset anti-spam flag
        balance = await trading_api.get_balance()
        balance_text = f"${balance:.2f}" if balance is not None else t("auth.balance_na", lang) if t("auth.balance_na", lang) != "auth.balance_na" else "не вдалося отримати"
        await callback.message.edit_text(
            t("auth.success", lang, balance=balance_text) if t("auth.success", lang) != "auth.success" else f"✅ Авторизація пройшла успішно! Сесію збережено.\n\nПоточний баланс: <b>{balance_text}</b>",
            parse_mode="HTML"
        )
        await state.clear()
    else:
        await callback.message.edit_text(t("auth.failed", lang) if t("auth.failed", lang) != "auth.failed" else "❌ Не вдалося підтвердити авторизацію. Будь ласка, спробуйте ще раз:\n\n1. Переконайтесь, що ви увійшли в акаунт.\n2. Оновіть сторінку (F5) у браузері.\n3. Натисніть кнопку підтвердження ще раз.", reply_markup=get_auth_confirmation_keyboard(lang))
    await callback.answer()