import logging
from typing import Optional, Dict, Any


logger = logging.getLogger(__name__)


def create_or_update_user(user_id: int, username: Optional[str] = None):
    """Створює або оновлює користувача в 'базі даних'. Плюс інкрементує старт лише для нових користувачів."""
    from app.core.dispatcher import admin_panel
    is_new = admin_panel.add_or_update_user(user_id, username=username)
    if is_new:
        # Засчитываем старт только при первом появлении пользователя
        admin_panel.increment_start_count()


def set_user_registered(user_id: int, is_registered: bool):
    """Встановлює статус реєстрації користувача."""
    from app.core.dispatcher import admin_panel
    admin_panel.update_user_field(user_id, "is_registered", is_registered)


def set_user_deposited(user_id: int, has_deposit: bool):
    """Встановлює статус депозиту користувача."""
    from app.core.dispatcher import admin_panel
    admin_panel.update_user_field(user_id, "has_deposit", has_deposit)


def set_user_uid(user_id: int, uid: str):
    """Встановлює PocketOption UID для користувача."""
    from app.core.dispatcher import admin_panel
    admin_panel.update_user_field(user_id, "uid", uid)


def is_fully_verified(user_id: int) -> bool:
    """Перевіряє, чи є користувач повністю верифікованим."""
    from app.core.dispatcher import admin_panel
    return admin_panel.is_fully_verified(user_id)


def get_user_uid(user_id: int) -> Optional[str]:
    """Отримує PocketOption UID користувача."""
    from app.core.dispatcher import admin_panel
    return admin_panel.get_user_uid(user_id)


def get_all_users() -> Dict[str, Any]:
    """Повертає словник усіх користувачів."""
    from app.core.dispatcher import admin_panel
    return admin_panel.get_all_users()


def get_user_id_by_uid(uid: str) -> Optional[int]:
    """Отримує Telegram user_id за PocketOption UID."""
    from app.core.dispatcher import admin_panel
    return admin_panel.get_user_id_by_uid(uid)


def set_user_lang(user_id: int, lang: str):
    """Зберігає мову користувача ("ru" або "en")."""
    from app.core.dispatcher import admin_panel
    admin_panel.update_user_field(user_id, "lang", lang)


def get_user_lang(user_id: int) -> str:
    """Повертає налаштовану мову користувача, за замовчуванням 'ru'."""
    from app.core.dispatcher import admin_panel
    user = admin_panel.get_user(user_id)
    if user and isinstance(user, dict):
        return user.get("lang", "ru")
    return "ru" 