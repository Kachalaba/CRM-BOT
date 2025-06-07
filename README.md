# CRM Bot

Simple Telegram bot for CRM integration.

## Commands

- `/ping` - check bot latency
- `/stats` - show remaining sessions (cached for 30s)

## Running with Docker

Build the image and run:

```bash
docker run -it --env-file .env ghcr.io/<your-github-username>/crm-bot:latest
```

Replace `.env` with your environment file.

## Staging

Test the latest changes here: [Staging Bot](https://t.me/crm_bot_staging).

## Мова

Файли локалей зберігаються у `locales/`. Щоб додати нову мову, створіть JSON-файл з кодом мови та перекладами ключів. Бот автоматично визначає мову користувача з налаштувань Telegram.
