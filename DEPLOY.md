# Инструкция по развертыванию бота на сервере

## Варианты хостинга

1. **VPS (Virtual Private Server)**
   - DigitalOcean (от $5/месяц)
   - Vultr (от $3.50/месяц)
   - Linode (от $5/месяц)

2. **Облачные платформы**
   - Heroku
   - PythonAnywhere
   - Google Cloud Platform

## Шаги по развертыванию на VPS

1. **Подготовка сервера**
   ```bash
   # Обновление системы
   sudo apt update && sudo apt upgrade -y
   
   # Установка необходимых пакетов
   sudo apt install python3-pip python3-venv git screen -y
   
   # Установка Chrome и ChromeDriver
   wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
   sudo dpkg -i google-chrome-stable_current_amd64.deb
   sudo apt --fix-broken install
   ```

2. **Клонирование репозитория**
   ```bash
   git clone <ваш-репозиторий>
   cd <директория-проекта>
   ```

3. **Настройка виртуального окружения**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Настройка переменных окружения**
   ```bash
   # Создание файла .env
   nano .env
   
   # Добавление необходимых переменных
   BOT_TOKEN=ваш_токен_бота
   ADMIN_IDS=id1,id2,id3
   ```

5. **Запуск бота в фоновом режиме**
   ```bash
   # Создание нового screen-сессии
   screen -S trading_bot
   
   # Активация виртуального окружения и запуск бота
   source .venv/bin/activate
   python bot.py
   
   # Отключение от screen-сессии (Ctrl+A, затем D)
   ```

6. **Управление ботом**
   ```bash
   # Просмотр активных screen-сессий
   screen -ls
   
   # Подключение к сессии бота
   screen -r trading_bot
   
   # Остановка бота
   # Внутри screen-сессии: Ctrl+C
   # Затем: Ctrl+D для выхода
   ```

## Автоматический перезапуск при сбоях

1. **Создание systemd сервиса**
   ```bash
   sudo nano /etc/systemd/system/trading-bot.service
   ```

2. **Содержимое файла сервиса**
   ```ini
   [Unit]
   Description=Trading Bot Service
   After=network.target

   [Service]
   User=<ваш-пользователь>
   WorkingDirectory=/path/to/your/bot
   Environment=PATH=/path/to/your/bot/.venv/bin
   ExecStart=/path/to/your/bot/.venv/bin/python bot.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

3. **Активация сервиса**
   ```bash
   sudo systemctl enable trading-bot
   sudo systemctl start trading-bot
   ```

## Мониторинг

1. **Просмотр логов**
   ```bash
   sudo journalctl -u trading-bot -f
   ```

2. **Статус сервиса**
   ```bash
   sudo systemctl status trading-bot
   ```

## Рекомендации по безопасности

1. Настройте файрвол
2. Используйте SSH-ключи вместо паролей
3. Регулярно обновляйте систему
4. Настройте резервное копирование данных
5. Используйте сложные пароли для всех сервисов

## Решение проблем

1. **Бот не запускается**
   - Проверьте логи: `sudo journalctl -u trading-bot -f`
   - Убедитесь, что все зависимости установлены
   - Проверьте права доступа к файлам

2. **Проблемы с Chrome/ChromeDriver**
   - Убедитесь, что версии совместимы
   - Проверьте наличие всех необходимых библиотек

3. **Проблемы с авторизацией**
   - Проверьте валидность cookies
   - Убедитесь, что IP-адрес не заблокирован 