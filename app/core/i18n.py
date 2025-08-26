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
		"welcome.message": "👋 Добро пожаловать! Используйте меню ниже, чтобы продолжить.",

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
		"workspace.category": "КАТЕГОРИЯ",
		"workspace.pair": "ПАРА",
		"workspace.pair_ai": "ПАРА (AI выбор)",
		"workspace.exp_time": "ВРЕМЯ ЭКСПИРАЦИИ",
		"workspace.press_get_signal": "Нажмите 'Получить сигнал', чтобы подтвердить.",
		"menu.workspace": "▶️ Рабочая зона",
		"menu.education": "🎓 Обучение",
		"menu.how": "❓ Как работает бот?",
		"menu.support": "Поддержка",
		"menu.group": "Закрытая группа",

		# Admin panel labels
		"admin.stats": "📊 Статистика",
		"admin.broadcast": "📨 Рассылка",
		"admin.settings": "⚙️ Настройки",
		"admin.cookies_status": "🍪 Статус cookies",
		"admin.maintenance": "🛠 Обслуживание",
		"admin.go_to_signals": "📈 К сигналам",
		"admin.back_to_panel": "⬅️ Назад в админ-панель",
		"admin.broadcast.all_users": "👥 Всем пользователям",
		"admin.broadcast.verified_only": "✅ Только верифицированным",
		"admin.settings.welcome": "👋 Приветствие",
		"admin.settings.referral": "🔗 Реферальные настройки",
		"admin.settings.finish_msg": "🎉 Сообщение после верификации",
		"admin.settings.back": "⬅️ Назад в панель",

		# Maintenance labels
		"maintenance.enabled": "включён",
		"maintenance.disabled": "выключен",
		"maintenance.status": "🛠 Режим обслуживания:",
		"maintenance.enable_mode": "🟢 Включить режим обслуживания",
		"maintenance.disable_mode": "🔴 Выключить режим обслуживания",
		"maintenance.change_message": "✏️ Изменить сообщение",

		"facts.title": "ФАКТЫ:",
		"facts.partner_income": "🔗 Общий доход партнёров за этот день: <b>${amount}</b>",
		"facts.bot_stats": "🔗 Статистика BotX BOT: сгенерировано ⁃ <b>{forecasts}</b> прогнозов ⁃ <b>{success_rate}%</b> закрыто в плюс",

		"how.text": "<b>Как работают наши торговые сигналы?</b> 🤖✨\n\nКаждый прогноз основан на комплексном анализе рынка в реальном времени. Наш алгоритм учитывает:\n\n🔹 <b>Технические индикаторы:</b> RSI, MACD, полосы Боллинджера.\n🔹 <b>Графические паттерны:</b> Поиск устойчивых моделей на графике.\n🔹 <b>Рыночные настроения:</b> Анализ объёмов и волатильности.\n\nТолько когда большинство факторов указывают на сильное движение, бот генерирует точный сигнал. Это ваш персональный аналитик 24/7.",

		"ui.loading_ai_pair": "🤖 <b>Подбираю для вас лучшую пару...</b>",
		"ui.no_pairs_ai": "К сожалению, сейчас нет доступных пар для автоматического выбора. Попробуйте выбрать рынок и пару вручную.",
		"ui.loading_pairs": "⏳ Загружаю доступные пары...",
		"ui.choose_pair": "📈 <b>Выберите валютную пару:</b>",
		"ui.choose_time": "⏱ <b>Выберите время экспирации:</b>",
		"ui.generating_signal": "⏳ Думаю над сигналом...",
		"ui.error_internal": "Произошла внутренняя ошибка. Попробуйте позже или обратитесь в поддержку.",
		"ui.service_unavailable": "Сервис временно недоступен. Попробуйте позже.",

		"auth.required": "🔴 Для доступа к этой функции требуется авторизация.",
		"auth.critical_error": "🔴 <b>Критическая ошибка запуска!</b>\n\nСессия API недействительна или отсутствует. Бот не может получать рыночные данные.\n\nНажмите кнопку ниже, чтобы начать процесс авторизации.",
		"auth.start_browser": "⏳ Запускаю браузер для ручной авторизации...\n\nПожалуйста, подождите, это может занять до 30 секунд.",
		"auth.follow_login_steps": "🤖 Пожалуйста, выполните вход в аккаунт в открывшемся окне браузера.\n\nПосле успешного входа и полной загрузки торговой комнаты нажмите кнопку ниже.",
		"auth.checking": "⏳ Проверяю авторизацию и сохраняю сессию...",
		"auth.balance_na": "не удалось получить",
		"auth.success": "✅ Авторизация прошла успешно! Сессия сохранена.\n\nТекущий баланс: <b>{balance}</b>",
		"auth.failed": "❌ Не удалось подтвердить авторизацию. Попробуйте ещё раз:\n\n1. Убедитесь, что вы вошли в аккаунт.\n2. Обновите страницу (F5) в браузере.\n3. Нажмите кнопку подтверждения ещё раз.",
		"session.expired_warning": "🟡 <b>Предупреждение: срок действия сессии скоро закончится</b>\n\n{expiry_warning} Чтобы избежать сбоев в работе, рекомендуется обновить её.",

		"verify.enter_uid": "Отправьте ваш Pocket Option UID (цифровой идентификатор), чтобы я мог проверить вашу регистрацию.",
		"verify.prev_check_running": "⏳ Предыдущая проверка ещё выполняется. Пожалуйста, подождите.",
		"verify.uid_invalid": "⚠️ Пожалуйста, отправьте корректный UID. Это должно быть число (не более 15 цифр).",
		"verify.checking": "⏳ Один момент, проверяю вашу регистрацию...",
		"verify.ok_registered": "Вы правильно зарегистрировали аккаунт и уже находитесь в нашей базе 🔍\n\nТеперь пополните торговый счёт на сумму от <b>${min_deposit}</b>, чтобы получить профессиональные торговые сигналы и доступ в закрытую группу!\n\n",
		"verify.if_deposited": "Если вы уже пополнили счёт на сумму от <b>${min_deposit}</b>, нажмите кнопку ‘Счёт пополнил’ и получите мгновенный доступ к сигналам и закрытой группе ✔️\n\n",
		"verify.press_button_below": "Нажмите кнопку ниже, если вы уже внесли депозит:",
		"verify.not_registered": "❌ К сожалению, я не нашёл пользователя с таким UID, зарегистрированного по нашей ссылке.\n\nПожалуйста, проверьте UID или зарегистрируйтесь снова по ссылке: {link}\n\n{facts}",
		"verify.already_verified": "✅ Вы уже прошли верификацию. Можете пользоваться всеми функциями бота.",
		"verify.flow_intro": "В торговом боте BotX сигналы формируются на основе собственного алгоритма, разработанного с учётом многолетнего опыта в трейдинге.\n\nЧтобы активировать торгового бота BotX и получить доступ в закрытое сообщество, вам нужно зарегистрироваться у брокера Pocket Option и отправить сюда свой ID торгового аккаунта.\n\nСсылка для регистрации ({link}).\n\n❗️ВАЖНО: Регистрацию нужно пройти именно по моей ссылке, иначе бот не сможет подтвердить вас.\n\nПосле регистрации нажмите кнопку «Я зарегистрировался!».",

		"deposit.checking": "⏳ Спасибо, проверяю информацию о вашем депозите...",
		"deposit.no_uid": "❌ <b>Ошибка:</b> Не удалось получить ID аккаунта. Попробуйте ещё раз.",
		"deposit.too_low": "❌ Похоже, ваш счёт ещё не пополнен на необходимую сумму.\n\nПожалуйста, убедитесь, что депозит не менее <b>${min_deposit}</b> и попробуйте ещё раз.",

		"signals.menu_caption": "Вы можете начинать пользоваться сигналами. Выберите рынок для начала.",
		"verify.i_registered": "✅ Я зарегистрировался!",
		"verify.have_account_other_link": "🤔 У меня уже есть аккаунт не по твоей ссылке",
		"verify.check_registration": "✅ Проверить регистрацию",
		"deposit.confirm_button": "✅ Счёт пополнил",
		"education.open_all": "🔓 Открыть все уроки",
		"education.prompt": "Доступ к обучающим материалам предоставляется после полной верификации аккаунта. Это необходимо для доступа к эксклюзивным стратегиям.",
		"time.custom_prompt": "Пожалуйста, введите желаемое время экспирации в минутах (например, <b>5</b>) и отправьте его.",
		"time.custom_invalid": "❌ <b>Ошибка:</b> Пожалуйста, введите время в виде положительного целого числа (например, 3).",

		"finish.message": "Поздравляем! Вы успешно прошли верификацию и получили полный доступ к боту.\n\nТеперь вы можете пользоваться торговыми сигналами и обучающими материалами."
	},
	"en": {
		"language.select_prompt": "Please select your language / Пожалуйста, выберите язык:",
		"language.ru": "Русский",
		"language.en": "English",

		"start.trading_signals": "🚀 Trading signals",
		"start.education": "🎓 Educational materials",
		"welcome.message": "👋 Welcome! Use the menu below to continue.",

		"back.back": "⬅️ Back",
		"back.to_menu": "🏠 Back to menu",
		"back.to_pair_select": "⬅️ Back to pair selection",

		"market.choose_type": "🏢 <b>Select market type:</b>",
		"market.currencies": "📈 Currencies",
		"market.otc": "📉 OTC",

		"pairs.loading": "⏳ Loading available pairs...",
		"pairs.none": "❌ No pairs are available for this market right now.",
		"pairs.choose_caption": "📈 <b>Select a currency pair:</b>",
		"pairs.ai_reco": "✨ AI recommendation",
		"nav.prev": "⬅️",
		"nav.next": "➡️",

		"time.minutes_suffix": "min",
		"time.set_custom": "✏️ Enter custom time",

		"confirm.get_signal": "✅ Get signal",
		"confirm.change_settings": "✏️ Change settings",

		"signal.new": "🔄 New signal",
		"workspace.enter": "▶️ Enter workspace",
		# Workspace labels
		"workspace.header": "WORKSPACE",
		"workspace.category": "CATEGORY",
		"workspace.pair": "PAIR",
		"workspace.pair_ai": "PAIR (AI pick)",
		"workspace.exp_time": "EXPIRATION TIME",
		"workspace.press_get_signal": "Press 'Get signal' to confirm.",
		"menu.workspace": "▶️ Workspace",
		"menu.education": "🎓 Education",
		"menu.how": "❓ How does the bot work?",
		"menu.support": "Support",
		"menu.group": "Private group",

		# Admin panel labels
		"admin.stats": "📊 Stats",
		"admin.broadcast": "📨 Broadcast",
		"admin.settings": "⚙️ Settings",
		"admin.cookies_status": "🍪 Cookies status",
		"admin.maintenance": "🛠 Maintenance",
		"admin.go_to_signals": "📈 Go to signals",
		"admin.back_to_panel": "⬅️ Back to admin panel",
		"admin.broadcast.all_users": "👥 All users",
		"admin.broadcast.verified_only": "✅ Verified only",
		"admin.settings.welcome": "👋 Welcome message",
		"admin.settings.referral": "🔗 Referral settings",
		"admin.settings.finish_msg": "🎉 Finish message",
		"admin.settings.back": "⬅️ Back to panel",

		# Maintenance labels
		"maintenance.enabled": "enabled",
		"maintenance.disabled": "disabled",
		"maintenance.status": "🛠 Maintenance mode:",
		"maintenance.enable_mode": "🟢 Enable maintenance mode",
		"maintenance.disable_mode": "🔴 Disable maintenance mode",
		"maintenance.change_message": "✏️ Change message",

		"facts.title": "FACTS:",
		"facts.partner_income": "🔗 Total partner income today: <b>${amount}</b>",
		"facts.bot_stats": "🔗 BotX BOT stats: generated ⁃ <b>{forecasts}</b> forecasts ⁃ <b>{success_rate}%</b> closed in profit",

		"how.text": "<b>How do our trading signals work?</b> 🤖✨\n\nEach signal is backed by comprehensive real-time market analysis. Our algorithm considers:\n\n🔹 <b>Technical indicators:</b> RSI, MACD, Bollinger Bands.\n🔹 <b>Chart patterns:</b> Recognition of strong models on the chart.\n🔹 <b>Market sentiment:</b> Volume and volatility analysis.\n\nOnly when most factors indicate a strong move does the bot generate a precise signal. This is your 24/7 personal analyst.",

		"ui.loading_ai_pair": "🤖 <b>Picking the best pair for you...</b>",
		"ui.no_pairs_ai": "Unfortunately, no pairs are currently available for automatic selection. Try choosing the market and pair manually.",
		"ui.loading_pairs": "⏳ Loading available pairs...",
		"ui.choose_pair": "📈 <b>Select a currency pair:</b>",
		"ui.choose_time": "⏱ <b>Select expiration time:</b>",
		"ui.generating_signal": "⏳ Thinking about the signal...",
		"ui.error_internal": "An internal error occurred. Please try again later or contact support.",

		"auth.start_browser": "⏳ Launching browser for manual authorization...\n\nPlease wait, this may take up to 30 seconds.",
		"auth.follow_login_steps": "🤖 Please log in to your account in the opened browser window.\n\nAfter successful login and full loading of the trading room, press the button below.",
		"auth.checking": "⏳ Checking authorization and saving session...",
		"auth.balance_na": "could not retrieve",
		"auth.success": "✅ Authorization successful! Session saved.\n\nCurrent balance: <b>{balance}</b>",
		"auth.failed": "❌ Could not confirm authorization. Please try again:\n\n1. Make sure you are logged in.\n2. Refresh the page (F5) in the browser.\n3. Press the confirmation button again.",

		"verify.enter_uid": "Please send your Pocket Option UID (numeric ID) so I can check your registration.",
		"verify.prev_check_running": "⏳ Your previous check is still running. Please wait.",
		"verify.uid_invalid": "⚠️ Please send a valid UID. It must be a number (no more than 15 digits).",
		"verify.checking": "⏳ One moment, checking your registration...",
		"verify.ok_registered": "Your account is correctly registered and is in our database 🔍\n\nNow top up your trading account with at least <b>${min_deposit}</b> to get professional trading signals and access to the private group!\n\n",
		"verify.if_deposited": "If you have already deposited at least <b>${min_deposit}</b>, press the ‘Account funded’ button to get instant access to the signals and the private group ✔️\n\n",
		"verify.press_button_below": "Press the button below if you have already made the deposit:",
		"verify.not_registered": "Your account is NOT correctly registered and is not in our database ❌\n\nRegistration link <a href='{link}'>is here</a>\n\n❗️<b>IMPORTANT:</b> You must register via my link; otherwise, the bot cannot confirm you.\n\nAfter registration, press the ‘I have registered!’ button\n\n{facts}",

		"deposit.checking": "⏳ Thanks, checking your deposit info...",
		"deposit.no_uid": "❌ <b>Error:</b> Could not get the account ID. Please try again.",
		"deposit.too_low": "You have not funded your balance, or your account has less than <b>${min_deposit}</b> ❌\n\nTo join the private group you need at least <b>${min_deposit}</b> on your trading account! You have 2 more attempts to fund your trading account.\n\nYou will get:\n\n🔗 Personal trading with BotX in a private VIP channel — daily.\n🔗 Daily market news and analytics.\n🔗 Access to BotX BOT that gives around 10,000 forecasts for FIN and OTC assets every day!\n🔗 Private educational materials for faster learning.\n\nIf you have already deposited at least <b>${min_deposit}</b>, press the ‘Account funded’ button to get instant access to the private group ✔️\n\n<b>IMPORTANT FACT:</b> During the first three days the average profit of a new partner is from $35 to $150!",

		"signals.menu_caption": "You can start using signals. Choose a market to begin.",
		"verify.i_registered": "✅ I have registered!",
		"verify.have_account_other_link": "🤔 I already have an account NOT via your link",
		"verify.check_registration": "✅ Check registration",
		"deposit.confirm_button": "✅ Account funded",
		"education.open_all": "🔓 Unlock all lessons",
		"time.custom_prompt": "Please enter the desired expiration time in minutes (e.g., <b>5</b>) and send it.",
		"time.custom_invalid": "❌ <b>Error:</b> Please enter a positive integer number of minutes (e.g., 3).",

		"verify.flow_intro": "In the BotX trading bot, signals are generated based on our proprietary algorithm developed with a professional approach and years of trading experience.\n\nTo activate the BotX trading bot and get access to the private community, you need to register with the Pocket Option broker and send your trading account ID here.\n\n<a href='{link}'>Registration link</a>.\n\n❗️<b>IMPORTANT:</b> You must register using my link; otherwise, the bot will not be able to confirm you.\n\nAfter registration, press the ‘I have registered’ button!",
		"education.locked_prompt": "To unlock all lessons, the BotX bot and get access to the private community, you need to register with the Pocket Option broker and send your trading account ID here.\n\nRegistration link <a href='{link}'>HERE</a>.\n\n❗️<b>IMPORTANT:</b> You must register using my link; otherwise, the bot will not be able to confirm you.\n\nAfter registration, press the ‘I have registered’ button!\n\nP.S. If you already have a broker account but not via our link, press the button ‘I already have an account not via your link’.",

		"finish.message": "Congrats! You have successfully passed verification and got full access to the bot.\n\nNow you can use trading signals and educational materials."
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