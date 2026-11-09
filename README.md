# 💜 Vibe — AI-Assisted Dating Bot

Telegram-бот для знакомств с системой лайков, матчинга и подписки через Telegram Stars.

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![aiogram](https://img.shields.io/badge/aiogram-3.x-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 🚀 Что умеет

- **🔍 Поиск по критериям** — пол, возраст, город
- **❤️ Лайки и 💎 суперлайки** — для выражения симпатии
- **🎯 Матчинг** — при взаимной симпатии открывается чат
- **💬 Чат между пользователями** — через бота с пересылкой сообщений
- **📸 Фото в анкете** — до 3 штук, загрузка через Telegram
- **⭐ Premium-подписка** — через Telegram Stars (250 ⭐ / 30 дней)
- **📊 Система лимитов** — 20 лайков, 1 суперлайк, 50 сообщений в день бесплатно
- **🔐 FSM для регистрации** — пошаговое создание анкеты

---

## 🛠 Технологии

| Слой | Технология |
|------|-----------|
| **Язык** | Python 3.12 |
| **Бот** | aiogram 3.x (async) |
| **БД** | PostgreSQL + SQLAlchemy 2.0 |
| **Миграции** | Alembic |
| **Платежи** | Telegram Stars (XTR) |
| **Конфиг** | python-dotenv |
| **Архитектура** | Модульная (handlers / services / keyboards / middlewares) |

---

## 📁 Структура проекта
dating_ai_bot/
├── src/
│ ├── bot.py # Точка входа
│ ├── config.py # Конфигурация
│ ├── handlers/ # Обработчики сообщений
│ │ ├── start.py # Регистрация (FSM)
│ │ ├── profile.py # Анкеты и фото
│ │ ├── search.py # Поиск, лайки, матчи
│ │ ├── chat.py # Переписка
│ │ └── subscription.py # Оплата Telegram Stars
│ ├── database/
│ │ ├── db.py # Подключение к БД
│ │ └── models.py # Модели SQLAlchemy
│ ├── services/
│ │ ├── matcher.py # Логика поиска
│ │ └── limits.py # Проверка лимитов
│ ├── keyboards/ # Клавиатуры
│ └── middlewares/
│ └── subscription.py # Проверка Premium
├── migrations/ # Alembic
├── .env.example # Шаблон конфига
├── .gitignore
├── requirements.txt
├── LICENSE
└── README.md

text

---

## 👨‍💻 Автор
Пузиков Геннадий (askoline-sketch)

Telegram: @askoline

📝 Лицензия
MIT — см. LICENSE