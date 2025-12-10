# Telegram Channels Admin

Backend-сервис для управления Telegram-каналами, автопостингом и статистикой.

## Возможности

- Управление группами каналов (основной + локализованные версии)
- Создание мультиканальных постов с автопереводом через LLM
- Публикация во все каналы одной группы
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

### 3. Доступ к сервисам

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

### Telegram Bot Service

Внешний сервис-бот должен реализовывать API:

- `POST /api/v1/messages/send` - отправка сообщений
- `POST /api/v1/messages/edit` - редактирование
- `GET /api/v1/channels/info` - информация о канале
- `GET /api/v1/channels/stats` - статистика канала
- `GET /api/v1/channels/permissions` - проверка прав

И отправлять webhooks на наши эндпоинты:
- `POST /api/v1/bot/channel-stats/`
- `POST /api/v1/bot/message-stats/`
- `POST /api/v1/bot/channel-update/`

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

