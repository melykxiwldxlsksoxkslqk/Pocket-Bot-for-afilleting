# Simple i18n utility
from typing import Dict

SUPPORTED_LANGS = {"ru", "en"}
DEFAULT_LANG = "ru"

TRANSLATIONS: Dict[str, Dict[str, str]] = {
	"ru": {
		"language.select_prompt": "Пожалуйста, выберите язык / Please select your language:",
		"language.ru": "Русский",
		"language.en": "English",

		"start.trading_signals": "🚀 Торговые сигналы",
		"start.education": "🎓 Обучающие материалы",

		"back.back": "⬅️ Назад",
		"back.to_menu": "🏠 Назад в меню",
		"back.to_pair_select": "⬅️ Назад к выбору пары",

		"market.choose_type": "🏢 <b>Выберите тип рынка:</b>",
		"market.currencies": "📈 Валюты",
		"market.otc": "📉 OTC",

		"pairs.loading": "⏳ Загружаю доступные пары...",
		"pairs.none": "❌ Сейчас нет доступных пар для этого рынка.",
		"pairs.choose_caption": "📈 <b>Выберите валютную пару:</b>",
		"pairs.ai_reco": "✨ Рекомендация от ИИ",
		"nav.prev": "⬅️",
		"nav.next": "➡️",

		"time.minutes_suffix": "мин",
		"time.set_custom": "✏️ Указать своё время",

		"confirm.get_signal": "✅ Получить сигнал",
		"confirm.change_settings": "✏️ Изменить настройки",

		"signal.new": "🔄 Новый сигнал",
		"workspace.enter": "▶️ Войти в рабочую зону",
		# Workspace labels
		"workspace.header": "РАБОЧАЯ ЗОНА",
		"workspace.category": "Категория:",
		"workspace.pair": "Пара:",
		"workspace.pair_ai": "Пара (рекомендация ИИ):",
		"workspace.exp_time": "Время экспирации:",
		"ui.choose_time": "Выберите время экспирации, затем нажмите ‘Получить сигнал’.",
		"ui.loading_ai_pair": "⏳ Подбираю актив...",
		"ui.no_pairs_ai": "❌ Сейчас нет доступных пар. Попробуйте позже.",

		"workspace.press_get_signal": "Нажмите ‘Получить сигнал’, чтобы получить параметры сделки.",
		"menu.group": "👥 Группа",
		"menu.support": "🆘 Поддержка",
		"menu.how": "📖 Как работает бот?",
		"menu.workspace": "🧩 Рабочая зона",
		"menu.education": "🎓 Обучение",

		"facts.title": "Факты за",
		"facts.partner_income": "Средний доход нового партнёра: ${amount}",
		"facts.bot_stats": "Бот ежедневно делает около {forecasts} прогнозов с точностью {success_rate}%",
	},
	"en": {
		"language.select_prompt": "Please select your language / Пожалуйста, выберите язык:",
		"language.ru": "Русский",
		"language.en": "English",

		"start.trading_signals": "🚀 Trading signals",
		"start.education": "🎓 Educational materials",

		"back.back": "⬅️ Back",
		"back.to_menu": "🏠 Back to menu",
		"back.to_pair_select": "⬅️ Back to pair selection",

		"market.choose_type": "🏢 <b>Select market type:</b>",
		"market.currencies": "📈 Currencies",
		"market.otc": "📉 OTC",

		"pairs.loading": "⏳ Loading available pairs...",
		"pairs.none": "❌ No available pairs for this market right now.",
		"pairs.choose_caption": "📈 <b>Select a currency pair:</b>",
		"pairs.ai_reco": "✨ AI Recommendation",
		"nav.prev": "⬅️",
		"nav.next": "➡️",

		"time.minutes_suffix": "min",
		"time.set_custom": "✏️ Set custom time",

		"confirm.get_signal": "✅ Get signal",
		"confirm.change_settings": "✏️ Change settings",

		"signal.new": "🔄 New signal",
		"workspace.enter": "▶️ Enter workspace",
		# Workspace labels
		"workspace.header": "WORKSPACE",
		"workspace.category": "Category:",
		"workspace.pair": "Pair:",
		"workspace.pair_ai": "Pair (AI recommendation):",
		"workspace.exp_time": "Expiration time:",
		"ui.choose_time": "Choose expiration time then press ‘Get signal’.",
		"ui.loading_ai_pair": "⏳ Picking an asset...",
		"ui.no_pairs_ai": "❌ No pairs available. Try later.",

		"workspace.press_get_signal": "Press ‘Get signal’ to receive trade parameters.",
		"menu.group": "👥 Group",
		"menu.support": "🆘 Support",
		"menu.how": "📖 How the bot works?",
		"menu.workspace": "🧩 Workspace",
		"menu.education": "🎓 Education",

		"facts.title": "Facts for",
		"facts.partner_income": "Average new partner income: ${amount}",
		"facts.bot_stats": "The bot makes about {forecasts} forecasts daily with {success_rate}% accuracy",
	}
}


def t(key: str, lang: str = DEFAULT_LANG, **kwargs) -> str:
	"""Translate a key into the desired language with optional formatting."""
	lang_code = lang if lang in SUPPORTED_LANGS else DEFAULT_LANG
	catalog = TRANSLATIONS.get(lang_code, {})
	text = catalog.get(key) or TRANSLATIONS[DEFAULT_LANG].get(key) or key
	if kwargs:
		try:
			return text.format(**kwargs)
		except Exception:
			return text
	return text 