# Pharmacy Telegram Bot

Телеграм-бот аптеки на базе библиотеки `pyTelegramBotAPI`.

## Требования
- Python 3.10+
- Telegram Bot API токен

## Установка

1. Создайте виртуальное окружение и установите зависимости:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Скопируйте файл `.env.example` в `.env` и подставьте свои значения вместо плейсхолдеров:
   - `BOT_TOKEN` – токен вашего бота
   - `ADMIN_IDS` – список ID администраторов через запятую
   - `DB_PATH` – путь к базе (опционально)

3. Запустите бота:
   ```bash
   python bot.py
   ```

## Deploy на Render
На сервисе [Render](https://render.com) создайте новый **Web Service** из репозитория.
Файл `render.yaml` содержит настройки сборки и запуска. Не забудьте указать переменные среды из `.env` в панели управления Render.
В конфигурации используются переменные `BOT_TOKEN`, `ADMIN_IDS` и `DB_PATH`,
которые совпадают с именами из `.env.example`.

## Экспорт заказов
Администратор может экспортировать все заказы командой `/export`. Бот отправит CSV-файл.

