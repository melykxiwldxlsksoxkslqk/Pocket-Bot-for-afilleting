import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.core.i18n import t

logger = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

class AdminPanel:
    def __init__(self, admin_ids: List[int], data_file: str = os.path.join(DATA_DIR, "admin_data.json")):
        self.admin_ids = admin_ids
        self.data_file = data_file
        # Завантажуємо стартові/дефолтні значення з .env
        self.referral_link = os.getenv("REFERRAL_LINK", "")
        self.min_deposit = float(os.getenv("MIN_DEPOSIT", 20.0))
        
        # Завантажуємо решту даних з файлу або встановлюємо за замовчуванням
        self.data = self._load_data()

        # Перезаписуємо дефолтні значення з .env значеннями з файлу, якщо вони там є
        # Це робить json головним джерелом правди
        self.referral_link = self.data.get('referral_settings', {}).get('referral_link', self.referral_link)
        self.min_deposit = self.data.get('referral_settings', {}).get('min_deposit', self.min_deposit)
        
        # Переконуємося, що в self.data зберігаються актуальні значення
        self.data.setdefault('referral_settings', {})['referral_link'] = self.referral_link
        self.data.setdefault('referral_settings', {})['min_deposit'] = self.min_deposit

        self._migrate_data()
        # Ініціалізуємо статистику, якщо її немає
        if "statistics" not in self.data:
            self.data["statistics"] = {
                "total_starts": 0,
                "signals_generated": 0
            }
            self._save_data()
    
    def _migrate_data(self):
        """
        Переносить старі структури даних до нової.
        - Видаляє поля 'registered' та 'deposited' з даних користувача.
        - Видаляє старі ключі 'stats' та 'daily_stats'.
        """
        updated = False
        
        # Міграція даних користувача
        users = self.data.get("users", {})
        for user_id, user_data in users.items():
            if isinstance(user_data, dict):
                if "registered" in user_data:
                    del user_data["registered"]
                    updated = True
                if "deposited" in user_data:
                    del user_data["deposited"]
                    updated = True
        
        # Міграція статистики
        if "stats" in self.data:
            del self.data["stats"]
            updated = True
        if "daily_stats" in self.data:
            del self.data["daily_stats"]
            updated = True
            
        if updated:
            logger.info("Виконано міграцію даних: видалено застарілі поля та структуру статистики.")
            self._save_data()
    
    def _load_data(self) -> Dict:
        """Завантаження даних адмін-панелі."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return self._get_default_data()
        return self._get_default_data()
    
    def _save_data(self):
        """Збереження даних адмін-панелі."""
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Не вдалося зберегти дані у файл {self.data_file}: {e}")
    
    def _get_default_data(self) -> Dict:
        """Отримання структури даних за замовчуванням."""
        return {
            "broadcasts": [],
            "maintenance_mode": False,
            "maintenance_message": "Бот на технічному обслуговуванні. Спробуйте пізніше.",
            "referral_settings": {
                "min_deposit": 20.0,
                "commission_percent": 30.0,
                "referral_link": "https://pocket-friends.com/r/your_default_link"
            },
            "signal_settings": {
                "min_confidence": 0.7,
                "max_daily_signals": 10
            },
            "file_cache": {},
            "users": {},
            "welcome_message": "👋 Добро пожаловать! Я — BotX BOT, ваш надёжный помощник в мире трейдинга.\n\nМоя цель — предоставлять качественные торговые сигналы и обучающие материалы, чтобы вы уверенно ориентировались на финансовых рынках.\n\nДля удобства используйте кнопки навигации ниже: ‘торговые сигналы’ или ‘обучающие материалы’.👇",
            "welcome_message_en": "👋 Welcome! I'm BotX BOT — your reliable assistant in the trading world.\n\nI provide quality trading signals and educational materials so you can navigate the markets with confidence.\n\nUse the buttons below to proceed: ‘Trading signals’ or ‘Educational materials’.👇",
            "finish_message_en": "Congrats! You have successfully passed verification and got full access to the bot.\n\nNow you can use trading signals and educational materials.",
            "statistics": {
                "total_starts": 0,
                "signals_generated": 0, # Загальна кількість
                "daily_signals": {} # Ключ: "YYYY-MM-DD", Значення: кількість
            }
        }
    
    def is_admin(self, user_id: int) -> bool:
        """Перевірка, чи є користувач адміністратором."""
        return user_id in self.admin_ids
    
    def get_admin_id(self) -> Optional[int]:
        """Повертає ID першого адміністратора зі списку."""
        return self.admin_ids[0] if self.admin_ids else None
    
    def get_admin_keyboard(self, lang: str = "ru") -> InlineKeyboardMarkup:
        """Отримання клавіатури адмін-панелі."""
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text=t("admin.stats", lang), callback_data="admin_stats"),
            InlineKeyboardButton(text=t("admin.broadcast", lang), callback_data="admin_broadcast_menu")
        )
        builder.row(
            InlineKeyboardButton(text=t("admin.settings", lang), callback_data="admin_settings"),
            InlineKeyboardButton(text=t("admin.cookies_status", lang), callback_data="admin_check_cookies")
        )
        builder.row(
            InlineKeyboardButton(text="📄 Загрузить JSON (SSID)", callback_data="admin_upload_ssid_json")
        )
        builder.row(
            InlineKeyboardButton(text=t("admin.maintenance", lang), callback_data="admin_maintenance")
        )
        builder.row(
             InlineKeyboardButton(text=t("admin.go_to_signals", lang), callback_data="admin_show_signals")
        )
        return builder.as_markup()
    
    def get_maintenance_keyboard(self, lang: str = "ru") -> InlineKeyboardMarkup:
        """Отримання клавіатури для меню обслуговування."""
        builder = InlineKeyboardBuilder()
        mode_status = t("maintenance.enabled", lang) if self.get_maintenance_mode() else t("maintenance.disabled", lang)
        toggle_text = t("maintenance.disable_mode", lang) if self.get_maintenance_mode() else t("maintenance.enable_mode", lang)

        builder.row(
            InlineKeyboardButton(text=f"{t('maintenance.status', lang)} {mode_status}", callback_data="none") # Просто для інформації
        )
        builder.row(
            InlineKeyboardButton(text=toggle_text, callback_data="admin_maintenance_toggle")
        )
        builder.row(
            InlineKeyboardButton(text=t("maintenance.change_message", lang), callback_data="admin_set_maintenance_msg")
        )
        return builder.as_markup()
    
    def get_broadcast_keyboard(self, lang: str = "ru") -> InlineKeyboardMarkup:
        """Отримання клавіатури для меню розсилки."""
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text=t("admin.broadcast.all_users", lang), callback_data="admin_broadcast_all")
        )
        builder.row(
            InlineKeyboardButton(text=t("admin.broadcast.verified_only", lang), callback_data="admin_broadcast_verified")
        )
        builder.row(
            InlineKeyboardButton(text=t("back.back", lang), callback_data="admin_panel")
        )
        return builder.as_markup()
    
    def get_settings_keyboard(self, lang: str = "ru") -> InlineKeyboardMarkup:
        """Отримання клавіатури налаштувань."""
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text=t("admin.settings.welcome", lang), callback_data="admin_set_welcome"),
            InlineKeyboardButton(text=t("admin.settings.referral", lang), callback_data="admin_set_referral")
        )
        builder.row(
            InlineKeyboardButton(text=t("admin.settings.finish_msg", lang), callback_data="admin_set_finish_msg")
        )
        builder.row(
            InlineKeyboardButton(text=t("admin.settings.back", lang), callback_data="admin_panel")
        )
        return builder.as_markup()
    
    def add_broadcast(self, message: str, target: str = "all"):
        """Додавання розсилки."""
        broadcast = {
            "message": message,
            "target": target,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "pending"
        }
        self.data["broadcasts"].append(broadcast)
        self._save_data()
    
    def get_pending_broadcasts(self) -> List[Dict]:
        """Отримання очікуючих розсилок."""
        return [b for b in self.data["broadcasts"] if b["status"] == "pending"]
    
    def update_broadcast_status(self, index: int, status: str):
        """Оновлення статусу розсилки."""
        if 0 <= index < len(self.data["broadcasts"]):
            self.data["broadcasts"][index]["status"] = status
            self._save_data()
    
    def get_maintenance_mode(self) -> bool:
        """Отримання поточного режиму обслуговування."""
        return self.data.get("maintenance_mode", False)
    
    def set_maintenance_mode(self, mode: bool) -> bool:
        """Встановлення режиму обслуговування."""
        try:
            self.data["maintenance_mode"] = mode
            self._save_data()
            return True
        except Exception as e:
            logger.error(f"Помилка під час встановлення режиму обслуговування: {e}")
            return False
    
    def get_maintenance_message(self) -> str:
        """Отримання повідомлення про обслуговування."""
        return self.data.get("maintenance_message", "Бот на технічному обслуговуванні. Спробуйте пізніше.")
    
    def set_maintenance_message(self, message: str) -> bool:
        """Встановлення повідомлення про обслуговування."""
        try:
            self.data["maintenance_message"] = message
            self._save_data()
            return True
        except Exception as e:
            logger.error(f"Помилка під час встановлення повідомлення про обслуговування: {e}")
            return False
    
    def set_welcome_message(self, message: str):
        """Оновлення вітального повідомлення."""
        self.data["welcome_message"] = message
        self._save_data()
    
    def set_welcome_message_en(self, message: str):
        """Updates English welcome message."""
        self.data["welcome_message_en"] = message
        self._save_data()
    
    def get_welcome_message(self) -> str:
        """Отримання вітального повідомлення."""
        return self.data.get("welcome_message", self._get_default_data()["welcome_message"])
    
    def get_welcome_message_en(self) -> str:
        """Returns English welcome message."""
        return self.data.get("welcome_message_en", self._get_default_data()["welcome_message_en"])
    
    def update_referral_settings(self, min_deposit: float = None, referral_link: str = None, promo_code: str = None):
        """Оновлення налаштувань реферальної програми."""
        if "referral_settings" not in self.data:
            self.data["referral_settings"] = self._get_default_data()["referral_settings"]
        
        if min_deposit is not None:
         self.data["referral_settings"]["min_deposit"] = min_deposit
        if referral_link is not None:
            self.data["referral_settings"]["referral_link"] = referral_link
        if promo_code is not None:
            self.data["referral_settings"]["promo_code"] = promo_code
        self._save_data()
        return True
    
    def set_referral_link(self, link: str):
        """Встановлює нове реферальне посилання."""
        if "referral_settings" not in self.data:
            self.data["referral_settings"] = self._get_default_data()["referral_settings"]
        self.data["referral_settings"]["referral_link"] = link
        self._save_data()
    
    def get_referral_settings(self) -> Dict:
        """Отримання налаштувань реферальної програми."""
        data = self._load_data()  # Завантажуємо свіжі дані з файлу
        # Для зворотної сумісності, якщо посилання ще в старому місці
        if "referral_link" not in data.get("referral_settings", {}):
            old_link = data.get("settings", {}).get("referral_link")
            if old_link:
                if "referral_settings" not in data:
                    data["referral_settings"] = {}
                data["referral_settings"]["referral_link"] = old_link
                # Видаляємо стару структуру, якщо вона є
                if "settings" in data:
                    data.pop("settings")
                self._save_data(data)

        return data.get("referral_settings", self._get_default_data()["referral_settings"])
    
    def get_file_id(self, file_name: str) -> Optional[str]:
        """Отримує кешований file_id за ім'ям файлу."""
        return self._load_data().get("file_ids", {}).get(file_name)

    def set_file_id(self, file_name: str, file_id: str):
        """Зберігає file_id для файлу."""
        data = self._load_data()
        if "file_ids" not in data:
            data["file_ids"] = {}
        data["file_ids"][file_name] = file_id
        self._save_data()

    def clear_file_id(self, file_name: str) -> bool:
        """Видаляє кешований file_id для зазначеного файлу (щоб оновити картинку)."""
        data = self._load_data()
        file_ids = data.get("file_ids", {})
        if file_name in file_ids:
            try:
                del file_ids[file_name]
                self._save_data()
                return True
            except Exception:
                return False
        return False

    def get_user_stats(self, user_id: int) -> Dict:
        """Отримання статистики користувача."""
        # TODO: Реалізувати статистику користувача
        return {
            "signals_used": 0,
            "success_rate": 0.0,
            "total_trades": 0,
            "last_active": None
        }
    
    def get_global_stats(self) -> Dict:
        """Отримання глобальної статистики."""
        # TODO: Реалізувати глобальну статистику
        return {
            "total_users": 0,
            "active_users": 0,
            "total_signals": 0,
            "success_rate": 0.0
        }
        
    def get_settings(self) -> Dict:
        """Отримання всіх налаштувань."""
        return {
            "welcome_message": self.get_welcome_message(),
            "referral_settings": self.get_referral_settings(),
            "maintenance_mode": self.get_maintenance_mode(),
            "maintenance_message": self.get_maintenance_message()
        }
    
    def get_stats(self) -> Dict:
        """Отримання статистики."""
        users = self.data.get("users", {})
        total_users = len(users)
        verified_users = sum(1 for user_data in users.values() if isinstance(user_data, dict) and user_data.get("is_verified"))
        
        return {
            "total_users": total_users,
            "verified_users": verified_users,
            "active_referrals": 0,  # Можна додати реальну статистику рефералів
            "total_volume": 0.0     # Можна додати реальний оборот
        }
    
    def update_user_activity(self, user_id: str):
        """Оновлення часу останньої активності користувача."""
        user_id = str(user_id)
        # Якщо користувач новий або дані в старому строковому форматі, створюємо/перезаписуємо новий словник
        if user_id not in self.data["users"] or not isinstance(self.data["users"].get(user_id), dict):
            self.data["users"][user_id] = {
                "last_activity": datetime.now().isoformat(),
                "is_verified": False,
                "account_id": None
            }
        else:
            # Інакше просто оновлюємо час
            self.data["users"][user_id]["last_activity"] = datetime.now().isoformat()
        self._save_data()

    def is_user_verified(self, user_id: str) -> bool:
        """Перевіряє, чи верифікований користувач."""
        user = self.data["users"].get(str(user_id))
        return user and isinstance(user, dict) and user.get("is_verified", False)

    def verify_user(self, user_id: str, account_id: str):
        """Позначає користувача як верифікованого і зберігає його ID акаунту."""
        user_id_str = str(user_id)
        user_data = self.data.get("users", {}).get(user_id_str)

        # Перезаписуємо, якщо користувач новий або дані в старому строковому форматі
        if not user_data or not isinstance(user_data, dict):
            self.data["users"][user_id_str] = {
                "last_activity": datetime.now().isoformat(),
                "is_verified": True,
                "account_id": account_id,
                "is_registered": False,
                "has_deposit": False
            }
        else:
            user_data["is_verified"] = True
            user_data["account_id"] = account_id
        self._save_data()

    # --- Методи управління користувачами ---
    def add_or_update_user(self, user_id: int, username: Optional[str] = None, uid: Optional[str] = None):
        """Додає нового користувача або оновлює існуючого, обробляючи застарілі формати даних.
        Повертає True, якщо користувач створений вперше (новий), і False, якщо запис оновлено.
        """
        user_id_str = str(user_id)
        users = self.data.setdefault("users", {})

        is_new_user = False

        # Якщо користувач новий або дані в старому строковому форматі, створюємо/перезаписуємо новий словник
        if user_id_str not in users or not isinstance(users.get(user_id_str), dict):
            users[user_id_str] = {
                "username": username,
                "is_registered": False,
                "has_deposit": False,
                "uid": uid,
                "first_seen": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
            }
            logger.info(f"Створено нового користувача або оновлено дані для {user_id_str}")
            is_new_user = True
        else:
            # Інакше просто оновлюємо час та інші поля
            users[user_id_str]["last_seen"] = datetime.now().isoformat()
            if username:
                users[user_id_str]["username"] = username
            if uid:
                users[user_id_str]["uid"] = uid
        
        self._save_data()
        return is_new_user

    def update_user_field(self, user_id: int, field: str, value: Any):
        """Оновлює конкретне поле для користувача, створюючи його, якщо він не існує."""
        user_id_str = str(user_id)
        users = self.data.setdefault("users", {})
        
        # Переконуємося, що запис користувача існує і є словником перед оновленням
        if user_id_str not in users or not isinstance(users.get(user_id_str), dict):
            # Це створить новий словник користувача або перезапише старий невірний формат
            self.add_or_update_user(user_id)
        
        # Тепер, коли ми впевнені, що користувач існує, оновлюємо поле.
        users[user_id_str][field] = value
        self._save_data()
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Отримує дані користувача."""
        return self.data.get("users", {}).get(str(user_id))

    def get_all_users(self) -> Dict[str, Any]:
        """Повертає словник усіх користувачів."""
        return self.data.get("users", {})

    def get_user_id_by_uid(self, uid: str) -> Optional[int]:
        """Знаходить user_id за його PocketOption UID."""
        users = self.data.get("users", {})
        for user_id, user_data in users.items():
            if isinstance(user_data, dict) and user_data.get("uid") == uid:
                return int(user_id)
        return None

    def is_fully_verified(self, user_id: int) -> bool:
        """Перевіряє, чи є користувач повністю верифікованим (зареєстрований і має депозит)."""
        user = self.get_user(user_id)
        if user and isinstance(user, dict):
            return user.get("is_registered", False) and user.get("has_deposit", False)
        return False
        
    def get_user_uid(self, user_id: int) -> Optional[str]:
        """Отримує PocketOption UID для користувача."""
        user = self.get_user(user_id)
        return user.get("uid") if user and isinstance(user, dict) else None

    # --- Методи статистики ---
    def increment_start_count(self):
        """Збільшує лічильник використання команди /start."""
        self.data.setdefault("statistics", {})["total_starts"] = self.data.get("statistics", {}).get("total_starts", 0) + 1
        self._save_data()

    def increment_signals_generated(self):
        """Збільшує загальну та щоденну кількість згенерованих сигналів."""
        stats = self.data.setdefault("statistics", self._get_default_data()["statistics"])
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # Збільшуємо загальну кількість
        stats["signals_generated"] = stats.get("signals_generated", 0) + 1
        
        # Збільшуємо щоденну кількість
        daily_stats = stats.setdefault("daily_signals", {})
        daily_stats[today_str] = daily_stats.get(today_str, 0) + 1
        
        self._save_data()

    def get_statistics(self) -> Dict:
        """
        Обчислює та повертає словник з поточною статистикою бота.
        """
        stats = self.data.get("statistics", {})
        users = self.data.get("users", {})
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        verified_users = 0
        in_verification = 0
        
        for user in users.values():
            if isinstance(user, dict):
                if user.get("is_registered") and user.get("has_deposit"):
                    verified_users += 1
                elif user.get("is_registered"):
                    in_verification += 1

        return {
            "total_starts": stats.get("total_starts", 0),
            "signals_generated_total": stats.get("signals_generated", 0),
            "signals_generated_today": stats.get("daily_signals", {}).get(today_str, 0),
            "total_users": len(users),
            "verified_users": verified_users,
            "in_verification_users": in_verification
        }

    # --- Управління користувачами ---
    def get_user_language(self, user_id: int) -> str:
        """Отримує мову користувача, за замовчуванням 'ua'."""
        user = self.data["users"].get(str(user_id))
        return user.get("language", "ua") if user else "ua"

    def set_finish_message(self, message: str):
        """Оновлення повідомлення про успішну верифікацію."""
        self.data["finish_message"] = message
        self._save_data()
    
    def get_finish_message(self) -> str:
        """Отримання повідомлення про успішну верифікацію."""
        return self.data.get("finish_message", "🎉 <b>Поздравляем!</b>\n\nВы успешно прошли верификацию и получили полный доступ к боту.\n\nТеперь вы можете пользоваться торговыми сигналами и обучающими материалами.")
    
    def set_finish_message_en(self, message: str):
        self.data["finish_message_en"] = message
        self._save_data()
    
    def get_finish_message_en(self) -> str:
        return self.data.get("finish_message_en", self._get_default_data()["finish_message_en"]) 