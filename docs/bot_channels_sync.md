# Автоматическая синхронизация каналов с Telegram Bot Gateway

Этот документ описывает, как настроить автоматическое обнаружение и синхронизацию Telegram-каналов через Bot Gateway.

## Как это работает

Telegram Bot Gateway отслеживает, когда бота добавляют или удаляют из каналов, и автоматически уведомляет наш бэкенд. Есть два способа синхронизации:

### 1. Webhook-режим (рекомендуется для продакшна)

Когда бота добавляют/удаляют из канала, Bot Gateway отправляет событие на наш webhook:

```
POST /api/integrations/telegram-bot/bot-events/
```

**Преимущества:**
- Мгновенное обновление
- Не требует периодических задач
- Минимальная нагрузка

**Настройка:**

1. Убедитесь, что webhook-эндпоинт доступен из интернета
2. На стороне Bot Gateway настройте:
   - `EXTERNAL_BACKEND_ENABLED=true`
   - `EXTERNAL_BACKEND_URL=https://your-backend.com/api/integrations/telegram-bot`
   - `EXTERNAL_BACKEND_TOKEN=<ваш токен>`

### 2. Polling-режим (для разработки/тестирования)

Периодически запрашивает обновления через API.

**Преимущества:**
- Работает без публичного адреса
- Подходит для локальной разработки

**Настройка через Celery Beat:**

Добавьте в настройки Celery:

```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Синхронизация каналов каждые 5 минут
    'sync-bot-channels': {
        'task': 'apps.integrations.telegram_bot.tasks.process_bot_updates',
        'schedule': crontab(minute='*/5'),  # Каждые 5 минут
    },
    # ... другие задачи
}
```

## Первичная синхронизация

При первом запуске проекта нужно импортировать существующие каналы:

### Метод 1: Management-команда (рекомендуется)

```bash
# Одноразовая синхронизация
python manage.py sync_bot_channels

# Непрерывная синхронизация (для разработки)
python manage.py sync_bot_channels --continuous --interval 60
```

**Что делает команда:**

1. Подключается к Bot Gateway
2. Получает информацию о боте
3. Обрабатывает pending updates (события о добавлении/удалении бота)
4. Создаёт/обновляет записи Channel в БД
5. Показывает список найденных каналов

**Пример вывода:**

```
Starting Telegram Bot channels synchronization...
Connected to bot: @my_channel_bot (ID: 123456789)
Processing bot updates...
Processed 3 updates
  ✓ Update #456789123 (my_chat_member): processed
  ✓ Update #456789124 (my_chat_member): processed
  - Update #456789125 (channel_post): ignored

Channels where bot is admin:
  • Crypto News EN (@crypto_news_en) [✓ Active] - post, edit, delete
  • Crypto News RU (@crypto_news_ru) [✓ Active] - post, edit
  • Test Channel (@test_private) [✗ Inactive] - post

Synchronization completed.
```

### Метод 2: Через Celery задачу

```python
from apps.integrations.telegram_bot.tasks import process_bot_updates

# Запустить синхронизацию
result = process_bot_updates.delay()
```

### Метод 3: Через Django shell

```python
from apps.integrations.telegram_bot.client import TelegramBotClient

client = TelegramBotClient()
result = client.process_updates_sync()
print(f"Processed {result['processed']} updates")
```

## Проверка синхронизации

### Проверить каналы в БД

```bash
python manage.py shell
```

```python
from apps.telegram_channels.models import Channel

# Все каналы где бот - админ
channels = Channel.objects.filter(bot_admin=True)
for ch in channels:
    print(f"{ch.title} (@{ch.username})")
    print(f"  - Active: {ch.is_active}")
    print(f"  - Can post: {ch.bot_can_post}")
    print(f"  - Members: {ch.member_count}")
    print()
```

### Проверить через Django Admin

```
http://localhost:8000/admin/telegram_channels/channel/
```

Вы должны увидеть список каналов с правильно заполненными полями:
- ✓ Title, Username
- ✓ Bot admin = Yes
- ✓ Bot can post = Yes/No (в зависимости от прав)
- ✓ Member count

## Что происходит при добавлении бота в канал

1. **Администратор добавляет бота в канал через Telegram**
   - Бот должен иметь права администратора
   - Минимальные права: "Post messages"

2. **Telegram уведомляет Bot Gateway**
   - Telegram отправляет `my_chat_member` update

3. **Bot Gateway обрабатывает событие**
   - Определяет тип события: `bot_added`, `bot_removed`, или `bot_permissions_changed`
   - Собирает информацию о канале (название, username, права)

4. **Bot Gateway уведомляет наш бэкенд**
   - **Webhook-режим**: отправляет POST на `/bot-events/`
   - **Polling-режим**: событие ожидает в очереди до вызова `process_updates`

5. **Наш бэкенд создаёт/обновляет Channel**
   - Создаёт запись в БД если канал новый
   - Обновляет права и статус если канал существует
   - Устанавливает язык (по умолчанию English, можно изменить вручную)

## Настройка языков для каналов

После автоматической синхронизации каналы создаются с языком по умолчанию. Чтобы указать правильный язык:

### Через Django Admin

1. Перейдите в Channel
2. Выберите канал
3. Измените поле "Language" на нужный язык
4. Сохраните

### Программно

```python
from apps.telegram_channels.models import Channel, Language

# Установить язык для канала
channel = Channel.objects.get(telegram_chat_id='-1001234567890')
russian = Language.objects.get(code='ru')
channel.language = russian
channel.save()
```

## Troubleshooting

### Каналы не появляются после добавления бота

**Проверьте:**

1. Бот добавлен как **администратор** (не просто участник)
2. У бота есть право "Post messages" (для `bot_can_post=True`)
3. Bot Gateway работает и доступен (`/health`)
4. Webhook настроен правильно (или запущена периодическая задача)
5. Токен в `TELEGRAM_BOT_SERVICE_TOKEN` совпадает с `INTERNAL_API_TOKEN` на Gateway

**Отладка:**

```bash
# Проверить логи Bot Gateway
curl http://178.217.98.201:8001/health

# Проверить логи нашего бэкенда
docker-compose logs -f web

# Вручную запустить синхронизацию
python manage.py sync_bot_channels
```

### Webhook не работает

**Проверьте:**

1. Эндпоинт доступен из интернета:
   ```bash
   curl -X POST https://your-backend.com/api/integrations/telegram-bot/bot-events/ \
     -H "X-Bot-Token: your-token" \
     -H "Content-Type: application/json" \
     -d '{"event": "test"}'
   ```

2. SSL-сертификат валиден (для HTTPS)

3. Firewall не блокирует запросы от Bot Gateway

**Решение:** Используйте polling-режим для разработки

### Права бота не обновляются

После изменения прав в Telegram нужно:

1. **Webhook-режим**: Bot Gateway автоматически отправит событие `bot_permissions_changed`

2. **Polling-режим**: Запустите синхронизацию:
   ```bash
   python manage.py sync_bot_channels
   ```

3. **Вручную**: Запустите задачу:
   ```python
   from apps.integrations.telegram_bot.tasks import verify_bot_permissions
   verify_bot_permissions.delay(channel_id)
   ```

## Рекомендации

### Для Production

- ✅ Используйте webhook-режим
- ✅ Настройте HTTPS с валидным сертификатом
- ✅ Добавьте периодическую проверку как backup (1 раз в час)
- ✅ Мониторьте логи webhook-эндпоинта

### Для Development

- ✅ Используйте polling-режим
- ✅ Запускайте синхронизацию вручную по необходимости
- ✅ Используйте `--continuous` режим для тестирования

## Дополнительные команды

### Обновить информацию о всех каналах

```bash
# Синхронизировать информацию (название, описание, кол-во подписчиков)
python manage.py shell -c "
from apps.integrations.telegram_bot.tasks import sync_all_channels
sync_all_channels.delay()
"
```

### Проверить права бота во всех каналах

```bash
python manage.py shell -c "
from apps.integrations.telegram_bot.tasks import verify_all_channel_permissions
verify_all_channel_permissions.delay()
"
```

### Получить статистику каналов

```bash
python manage.py shell -c "
from apps.stats.tasks import sync_all_channel_stats
sync_all_channel_stats.delay()
"
```

## См. также

- [API Documentation](../API%20(2).md) - Полная документация Bot Gateway API
- [Guide](guide.md) - Общее руководство по проекту
- [API](api.md) - Документация REST API бэкенда

