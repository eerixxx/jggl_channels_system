# Telegram Channels Admin

Backend-сервис для управления Telegram-каналами, автопостингом и статистикой.

## Возможности

- **Автоматическое обнаружение каналов** — каналы добавляются из Telegram Bot Gateway автоматически
- Управление группами каналов (основной + локализованные версии)
- Создание мультиканальных постов с автопереводом через LLM
- Публикация во все каналы одной группы одной кнопкой
- Отслеживание статистики (подписчики, просмотры, ER, ERR)
- Полноценная Django Admin панель
- REST API для интеграций
- Мониторинг через Prometheus + Grafana + Loki

## Стек технологий

- **Backend:** Django 5.0, Django REST Framework
- **База данных:** PostgreSQL 15
- **Кеш и очереди:** Redis 7
- **Фоновые задачи:** Celery 5, django-celery-beat
- **HTTP-клиент:** httpx (async)
- **Валидация:** Pydantic 2
- **Мониторинг:** Prometheus, Grafana, Loki
- **Сервер:** Gunicorn, WhiteNoise
- **Контейнеризация:** Docker, docker-compose

## Быстрый старт

### 1. Клонирование и настройка

```bash
# Клонируйте репозиторий
cd channels_admin

# Скопируйте пример конфигурации
cp env.example .env

# Отредактируйте .env файл
nano .env
```

### 2. Запуск с Docker Compose

```bash
# Запуск всех сервисов
docker-compose up -d

# Применение миграций
docker-compose exec web python manage.py migrate

# Создание суперпользователя
docker-compose exec web python manage.py createsuperuser

# Загрузка начальных данных (языки)
docker-compose exec web python manage.py loaddata initial_languages
```

### 3. Синхронизация каналов из Telegram Bot Gateway

```bash
# Импортировать каналы, в которых уже есть бот
docker-compose exec web python manage.py sync_bot_channels

# Или в dev-режиме (непрерывная синхронизация)
docker-compose exec web python manage.py sync_bot_channels --continuous --interval 60
```

**Важно:** Каналы добавляются автоматически из Bot Gateway. Не нужно создавать их вручную через Admin панель!

Подробнее: [docs/bot_channels_sync.md](docs/bot_channels_sync.md)

### 4. Доступ к сервисам

| Сервис | URL |
|--------|-----|
| Django Admin | http://localhost:8000/admin/ |
| API | http://localhost:8000/api/v1/ |
| Grafana | http://localhost:3000 |
| Prometheus | http://localhost:9090 |

## Локальная разработка

### Без Docker

```bash
# Создание виртуального окружения
python -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Настройка переменных окружения
export DJANGO_SETTINGS_MODULE=backend.settings.development
export POSTGRES_HOST=localhost
export REDIS_URL=redis://localhost:6379/0

# Миграции
cd backend
python manage.py migrate

# Запуск сервера разработки
python manage.py runserver

# В отдельном терминале - Celery worker
celery -A backend worker -l INFO

# В отдельном терминале - Celery beat
celery -A backend beat -l INFO
```

## Структура проекта

```
channels_admin/
├── backend/
│   ├── backend/           # Django project config
│   │   ├── settings/      # Split settings
│   │   ├── celery.py      # Celery configuration
│   │   └── urls.py
│   └── apps/
│       ├── core/          # Base models, utilities
│       ├── accounts/      # User management
│       ├── telegram_channels/  # Channels & groups
│       ├── posts/         # Multi-channel posts
│       ├── stats/         # Statistics
│       ├── integrations/  # External API clients
│       │   ├── telegram_bot/
│       │   └── translation/
│       └── monitoring/    # Health checks
├── docker/
│   ├── Dockerfile.web
│   ├── Dockerfile.worker
│   └── Dockerfile.beat
├── docs/
│   ├── guide.md          # User guide
│   └── api.md            # API documentation
├── docker-compose.yml
└── requirements.txt
```

## Конфигурация

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `SECRET_KEY` | Django secret key | - |
| `DEBUG` | Debug mode | False |
| `ALLOWED_HOSTS` | Allowed hosts | localhost |
| `POSTGRES_DB` | Database name | channels_admin |
| `POSTGRES_USER` | Database user | postgres |
| `POSTGRES_PASSWORD` | Database password | postgres |
| `REDIS_URL` | Redis URL | redis://redis:6379/0 |
| `TELEGRAM_BOT_SERVICE_URL` | Bot service URL | - |
| `TELEGRAM_BOT_SERVICE_TOKEN` | Bot service token | - |
| `TRANSLATION_SERVICE_URL` | Translation service URL | - |
| `TRANSLATION_SERVICE_TOKEN` | Translation service token | - |

## Интеграции

### Telegram Bot Gateway

Внешний сервис для работы с Telegram Bot API.

**Текущий Gateway:** `http://178.217.98.201:8001`

**Документация:** [API (2).md](API%20(2).md) или http://178.217.98.201:8001/docs

**Ключевые возможности:**

- ✅ Отправка/редактирование/удаление сообщений
- ✅ Автоматическое обнаружение каналов (bot events)
- ✅ Информация о каналах и правах бота
- ✅ Идемпотентность через `Idempotency-Key`
- 📊 **Детальная статистика через MTProto API** (views, reactions, comments, forwards)
- ⚠️ Без MTProto: ограниченная статистика (только member_count через Bot API)

**Webhook endpoints (Gateway → Backend):**

- `POST /api/integrations/telegram-bot/bot-events/` — события добавления/удаления бота
- `POST /api/integrations/telegram-bot/channel-stats/` — статистика каналов
- `POST /api/integrations/telegram-bot/message-stats/` — статистика сообщений
- `POST /api/integrations/telegram-bot/channel-update/` — обновления информации

**Синхронизация каналов:**

```bash
# Импорт каналов из Gateway
python manage.py sync_bot_channels

# Или настройте периодическую синхронизацию через Celery Beat
```

См. подробное руководство: [docs/bot_channels_sync.md](docs/bot_channels_sync.md)

**MTProto для детальной статистики** (опционально):

MTProto API предоставляет точные метрики: views, reactions, comments, forwards.

```bash
# Проверить доступность MTProto
python manage.py check_mtproto_status
```

См. руководство: [docs/mtproto_integration.md](docs/mtproto_integration.md)

### LLM Translation Service

Внешний сервис перевода должен реализовывать:

- `POST /api/v1/translate` - перевод текста
- `POST /api/v1/translate/batch` - пакетный перевод

## Мониторинг

### Prometheus Metrics

Метрики доступны на `/metrics`:
- Django request metrics
- Database connection metrics
- Cache metrics

### Grafana Dashboards

Grafana доступна на порту 3000:
- Логин: admin / admin (по умолчанию)
- Преднастроенные datasources: Prometheus, Loki

### Логи

Логи в JSON-формате отправляются в Loki через Promtail.

## Тестирование

```bash
# Запуск тестов
cd backend
pytest

# С покрытием
pytest --cov=apps

# Только определенное приложение
pytest apps/posts/
```

## Лицензия

MIT License

