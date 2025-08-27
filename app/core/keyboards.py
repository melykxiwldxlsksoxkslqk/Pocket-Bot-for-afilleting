from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.core.utils import _format_asset_name
from app.core.i18n import t


def get_language_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=t("language.ru", lang), callback_data="set_lang:ru"),
        InlineKeyboardButton(text=t("language.en", lang), callback_data="set_lang:en"),
    )
    return builder.as_markup()


def get_start_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавіатура для стартового екрану."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t("start.trading_signals", lang), callback_data="show_signals"))
    builder.row(InlineKeyboardButton(text=t("start.education", lang), callback_data="show_education"))
    return builder.as_markup()


def get_verification_request_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Кнопки для старту верифікації: 'Я зареєструвався!' та 'У мене вже є акаунт'."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t("verify.i_registered", lang), callback_data="registration_confirmed"))
    builder.row(InlineKeyboardButton(text=t("verify.have_account_other_link", lang), url="https://teletype.in/@botx/PXB0G-8YLUu"))
    return builder.as_markup()


def get_check_registration_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Кнопка для перевірки реєстрації."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t("verify.check_registration", lang), callback_data="check_registration"))
    return builder.as_markup()


def get_check_deposit_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Кнопка для перевірки депозиту."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t("deposit.confirm_button", lang), callback_data="check_deposit"))
    return builder.as_markup()


def get_fully_verified_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавіатура для повністю верифікованого користувача."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t("start.trading_signals", lang), callback_data="show_signals"))
    builder.row(InlineKeyboardButton(text=t("menu.group", lang), url="https://t.me/+c2XcSr7zbGZlMzEx"))
    builder.row(InlineKeyboardButton(text=t("start.education", lang), callback_data="show_education"))
    return builder.as_markup()


def get_market_type_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Створює клавіатуру для вибору ринку (Валюти, OTC)."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=t("market.currencies", lang), callback_data="select_market_type:CURRENCY"),
        InlineKeyboardButton(text=t("market.otc", lang), callback_data="select_market_type:OTC")
    )
    builder.row(InlineKeyboardButton(text=t("back.back", lang), callback_data="back_to_signal_menu"))
    return builder.as_markup()


def get_currency_pairs_keyboard(pairs: list, market_type: str, page: int = 1, per_page: int = 8, lang: str = "ru") -> InlineKeyboardMarkup:
    """Створює клавіатуру з посторінковою навігацією для валютних пар."""
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text=t("pairs.ai_reco", lang), callback_data="get_ai_recommendation"))
    
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    
    # Кнопки для пар
    for pair in pairs[start_index:end_index]:
        formatted_name = _format_asset_name(pair)
        builder.row(InlineKeyboardButton(text=formatted_name, callback_data=f"select_pair:{pair}"))
    
    # Кнопки навігації
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text=t("nav.prev", lang), callback_data=f"pair_page:{market_type}:{page-1}"))
    
    total_pages = (len(pairs) + per_page - 1) // per_page
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text=t("nav.next", lang), callback_data=f"pair_page:{market_type}:{page+1}"))
        
    if nav_buttons:
        builder.row(*nav_buttons)
        
    builder.row(InlineKeyboardButton(text=t("back.to_menu", lang), callback_data="back_to_signal_menu"))
    return builder.as_markup()


def get_trading_time_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавіатура для вибору часу експірації."""
    builder = InlineKeyboardBuilder()
    minutes = [1, 2, 3, 4, 5, 10, 15]
    buttons = [InlineKeyboardButton(text=f"{m} {t('time.minutes_suffix', lang)}", callback_data=f"confirm_params:{m}") for m in minutes]
    
    # Розміщуємо по 3 кнопки в ряд
    for i in range(0, len(buttons), 3):
        builder.row(*buttons[i:i+3])
        
    builder.row(InlineKeyboardButton(text=t("time.set_custom", lang), callback_data="set_custom_time"))
    builder.row(InlineKeyboardButton(text=t("back.to_pair_select", lang), callback_data="back_to_pair_select"))
    return builder.as_markup()


def get_signal_confirmation_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавіатура для підтвердження налаштувань та отримання сигналу."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t("confirm.get_signal", lang), callback_data="get_signal"))
    builder.row(InlineKeyboardButton(text=t("confirm.change_settings", lang), callback_data="change_settings"))
    return builder.as_markup()


def get_signal_keyboard(asset: str, lang: str = "ru") -> InlineKeyboardMarkup:
    """Returns the keyboard with options after receiving a signal."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=t("signal.new", lang), callback_data="new_signal")
    )
    return builder.as_markup()


def get_deposit_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Returns a keyboard for confirming a deposit."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Рахунок поповнив", callback_data="check_deposit")
    )
    return builder.as_markup()


def get_enter_workspace_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Returns a keyboard with a single button to enter the workspace."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=t("workspace.enter", lang), callback_data="enter_workspace")
    )
    return builder.as_markup()


def get_reregister_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура для процесса перерегистрации."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t("verify.i_registered", lang), callback_data="check_registration"))
    builder.row(InlineKeyboardButton(text=t("verify.have_account_other_link", lang), url="https://teletype.in/@botx/PXB0G-8YLUu"))
    return builder.as_markup()

# --- Клавиатуры Администратора ---

def get_admin_auth_keyboard() -> InlineKeyboardMarkup:
    """Кнопка для ручной авторизации админа."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Авторизоваться", callback_data="admin_auth"))
    return builder.as_markup()


def get_cancel_keyboard(back_callback: str, lang: str = "ru") -> InlineKeyboardMarkup:
    """Универсальная кнопка 'Назад'."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t("back.back", lang), callback_data=back_callback))
    return builder.as_markup()


def get_signal_menu_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура для главного меню сигналов."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t("menu.workspace", lang), callback_data="enter_workspace"))
    builder.row(InlineKeyboardButton(text=t("menu.education", lang), callback_data="show_education_from_workspace"))
    article_url = (
        "https://telegra.ph/AI-SIGNAL-BOT-ARTICLE-How-to-Use-the-AI-Bot-to-Trade-Smarter--Not-Blindly-08-26"
        if lang == "en"
        else "https://telegra.ph/Kak-ispolzovat-II-bota-dlya-trejdinga-na-Pocket-Option--bez-magii-i-mifov-08-26"
    )
    builder.row(InlineKeyboardButton(text=t("menu.how", lang), url=article_url))
    builder.row(
        InlineKeyboardButton(text=t("menu.support", lang), url="https://t.me/botx_sup"),
        InlineKeyboardButton(text=t("menu.group", lang), url="https://t.me/+c2XcSr7zbGZlMzEx")
    )
    return builder.as_markup()


def get_retry_signal_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура после получения сигнала."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔄 Попробовать ещё", callback_data="enter_workspace"))
    builder.row(InlineKeyboardButton(text=t("back.to_menu", lang), callback_data="back_to_signal_menu"))
    return builder.as_markup()


def get_education_prompt_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура для запроса на верификацию из раздела обучения."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t("education.open_all", lang), callback_data="open_all_lessons_prompt"))
    builder.row(InlineKeyboardButton(text=t("start.trading_signals", lang), callback_data="trade_signals_prompt"))
    return builder.as_markup()


def get_back_to_panel_keyboard(lang: str = "ru"):
    """Возвращает клавиатуру с кнопкой 'Назад в админ-панель'."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t("admin.back_to_panel", lang), callback_data="admin_panel"))
    return builder.as_markup()


def get_auth_confirmation_keyboard(lang: str = "ru"):
    """Возвращает клавиатуру для подтверждения ручной авторизации."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t("auth.confirm_logged_in", lang), callback_data="confirm_auth"))
    return builder.as_markup()


def get_referral_settings_keyboard(settings: dict) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру для настроек реферальной программы."""
    builder = InlineKeyboardBuilder()
    min_deposit = settings.get('min_deposit', 20)
    
    builder.row(
        InlineKeyboardButton(text=f"💰 Депозит: ${min_deposit}", callback_data="admin_change_min_deposit"),
        InlineKeyboardButton(text="🔗 Изменить ссылку", callback_data="admin_change_ref_link")
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад к настройкам", callback_data="admin_settings"))
    return builder.as_markup() 