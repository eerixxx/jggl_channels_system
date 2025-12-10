# MTProto API Integration для детальной статистики

## Что такое MTProto API?

MTProto - это нативный протокол Telegram, который предоставляет доступ к детальной статистике, недоступной через Bot API:

| Метрика | Bot API | MTProto API |
|---------|---------|-------------|
| Количество подписчиков | ✅ | ✅ |
| Точное количество просмотров | ❌ | ✅ |
| Реакции (с разбивкой по эмодзи) | ❌ | ✅ |
| Комментарии/Replies | ❌ | ✅ |
| Пересылки | ❌ | ✅ |
| Количество онлайн | ❌ | ✅ |
| Статистика роста канала | ❌ | ✅ |

## Архитектура

```
┌─────────────────┐
│  Django Backend │
│   (Наш проект)  │
└────────┬────────┘
         │ HTTP API
         ↓
┌─────────────────┐
│  Bot Gateway    │
│  (Микросервис)  │
└────┬───────┬────┘
     │       │
     │       └──→ MTProto (детальная статистика)
     │
     └──→ Bot API (базовые операции)
```

**Важно:** MTProto настраивается на стороне **Bot Gateway**, а не на нашем бэкенде!

## Настройка MTProto на Bot Gateway

### 1. Получите API credentials

1. Перейдите на https://my.telegram.org
2. Войдите с номером телефона
3. Перейдите в "API development tools"
4. Создайте приложение и получите:
   - `api_id` (число)
   - `api_hash` (строка)

### 2. Сгенерируйте session string

На сервере с Bot Gateway:

```bash
cd /path/to/bot-gateway

# Установите Telethon если ещё не установлен
pip install telethon

# Запустите скрипт генерации сессии
python scripts/generate_session.py
```

Скрипт попросит:
- API ID
- API Hash
- Номер телефона
- Код подтверждения

В результате вы получите **session string** - длинную строку вроде:
```
1AaBbCc2DdEe3...
```

### 3. Настройте переменные окружения на Gateway

Добавьте в `.env` файл Bot Gateway:

```env
# MTProto Configuration
MTPROTO_ENABLED=true
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_SESSION_STRING=1AaBbCc2DdEe3...
```

### 4. Перезапустите Bot Gateway

```bash
docker-compose restart bot-gateway
# или
systemctl restart bot-gateway
```

### 5. Проверьте статус

Из нашего Django бэкенда:

```bash
python manage.py check_mtproto_status
```

**Ожидаемый вывод:**

```
Checking MTProto API status on Telegram Bot Gateway...

MTProto API Status:
  Enabled:    ✓ True
  Available:  ✓ True
  Connected:  ✓ True
  Has API ID: ✓ True
  Has Hash:   ✓ True
  Has Session:✓ True

✅ MTProto API is ENABLED and CONNECTED
Backend will automatically use MTProto for detailed statistics.
```

## Использование в нашем Backend

### Автоматическое использование

После настройки MTProto на Gateway наш бэкенд **автоматически** начнёт использовать детальную статистику!

Все периодические задачи Celery автоматически переключаются на MTProto, если он доступен:

```python
# Эта задача автоматически использует MTProto если доступен
from apps.stats.tasks import sync_channel_stats
sync_channel_stats.delay(channel_id)  # Использует MTProto
```

### Ручное управление

Вы можете явно указать использовать или не использовать MTProto:

```python
from apps.stats.tasks import sync_channel_stats, sync_post_stats

# Принудительно использовать MTProto
sync_channel_stats.delay(channel_id, use_mtproto=True)

# Принудительно использовать Bot API (без MTProto)
sync_channel_stats.delay(channel_id, use_mtproto=False)

# То же для статистики постов
sync_post_stats.delay(channel_post_id, use_mtproto=True)
```

### Проверка статуса через Python

```python
from apps.integrations.telegram_bot.client import TelegramBotClient

client = TelegramBotClient()
status = client.get_mtproto_status_sync()

print(f"MTProto enabled: {status.get('enabled')}")
print(f"MTProto connected: {status.get('connected')}")
```

### Получение детальной статистики вручную

```python
from apps.integrations.telegram_bot.client import TelegramBotClient

client = TelegramBotClient()

# Детальная статистика канала
channel_stats = client.get_detailed_channel_stats_sync(
    chat_id="-1001234567890"
)
print(f"Subscribers: {channel_stats['channel']['participants_count']}")
print(f"Online: {channel_stats['channel']['online_count']}")

# Детальная статистика сообщения
message_stats = client.get_detailed_message_stats_sync(
    chat_id="-1001234567890",
    message_id=123,
)
print(f"Views: {message_stats['views']}")
print(f"Reactions: {message_stats['reactions']}")

# Статистика последних постов
recent_posts = client.get_recent_posts_stats_sync(
    chat_id="-1001234567890",
    limit=50,
)
print(f"Average views: {recent_posts['average']['views']}")
print(f"Total reactions: {recent_posts['totals']['reactions']}")
```

## Влияние на модели Django

### ChannelStatsSnapshot

С MTProto поля заполняются реальными данными:

```python
snapshot = ChannelStatsSnapshot.objects.latest('timestamp')

# С Bot API: всё кроме subscribers_count = 0
# С MTProto: все поля заполнены!
print(snapshot.subscribers_count)  # 15000
print(snapshot.views_last_10_posts)  # 450000 (было 0)
print(snapshot.avg_views_per_post)   # 45000.0 (было 0)
print(snapshot.er_last_10_posts)     # 2.5 (было 0)
print(snapshot.err_last_10_posts)    # 1.8 (было 0)
```

### PostStats

С MTProto записи содержат полные данные:

```python
post_stats = PostStats.objects.latest('timestamp')

# С Bot API: большинство полей = 0
# С MTProto: все поля заполнены!
print(post_stats.views)              # 45000 (было 0)
print(post_stats.reactions_count)    # 320 (было 0)
print(post_stats.reactions_breakdown)  # {"👍": 200, "❤️": 80, "🔥": 40}
print(post_stats.comments_count)     # 45 (было 0)
print(post_stats.forwards)           # 120 (было 0)
print(post_stats.er)                 # 2.1% (рассчитано)
print(post_stats.err)                # 0.9% (рассчитано)
```

## Проверка работы MTProto

### 1. Проверьте статус

```bash
python manage.py check_mtproto_status
```

### 2. Синхронизируйте статистику канала

```bash
python manage.py shell -c "
from apps.stats.tasks import sync_channel_stats
from apps.telegram_channels.models import Channel

channel = Channel.objects.first()
if channel:
    sync_channel_stats.delay(channel.pk, use_mtproto=True)
    print(f'Stats sync scheduled for: {channel.title}')
"
```

### 3. Проверьте результат через несколько секунд

```bash
python manage.py shell -c "
from apps.stats.models import ChannelStatsSnapshot

latest = ChannelStatsSnapshot.objects.latest('timestamp')
print(f'Source: {latest.meta.get(\"source\")}')
print(f'Subscribers: {latest.subscribers_count}')
print(f'Avg views/post: {latest.avg_views_per_post}')
print(f'ER: {latest.er_last_10_posts}%')
print(f'ERR: {latest.err_last_10_posts}%')
"
```

Если `source: mtproto` и поля заполнены - MTProto работает! ✅

## Производительность

### Bot API (без MTProto)

- **Скорость:** Быстро (~100ms на запрос)
- **Данные:** Только количество подписчиков
- **Лимиты:** Telegram Bot API rate limits

### MTProto API

- **Скорость:** Медленнее (~500-2000ms на запрос)
- **Данные:** Полная детальная статистика
- **Лимиты:** Более мягкие лимиты, но всё равно есть

### Рекомендации

1. **Для каналов:**
   - Синхронизируйте раз в 15-30 минут (уже настроено в Celery Beat)
   - MTProto запросы достаточно "тяжёлые"

2. **Для постов:**
   - Синхронизируйте после публикации и затем раз в час
   - Для старых постов (>7 дней) синхронизируйте реже

3. **Fallback:**
   - Если MTProto недоступен, автоматически используется Bot API
   - Никаких ошибок - просто меньше данных

## Troubleshooting

### MTProto не подключается

**Проверьте:**

1. API credentials правильные:
   ```bash
   # На сервере с Bot Gateway
   curl http://localhost:8001/api/v1/stats/status \
     -H "Authorization: Bearer <token>"
   ```

2. Session string валиден
3. Номер телефона, с которого создана сессия, имеет доступ к каналам

### MTProto часто отключается

MTProto сессии могут истекать. Чтобы переподключиться:

```bash
# Из нашего бэкенда
python manage.py check_mtproto_status --connect

# Или на стороне Gateway
curl -X POST http://178.217.98.201:8001/api/v1/stats/connect \
  -H "Authorization: Bearer <token>"
```

### Статистика всё равно = 0

**Причины:**

1. MTProto не настроен на Gateway (проверьте `check_mtproto_status`)
2. Канал не поддерживает статистику (слишком мало подписчиков)
3. Бот не имеет права просматривать статистику

**Решение:**

1. Убедитесь что MTProto enabled и connected
2. Для статистики нужно >50-100 подписчиков
3. Бот должен быть админом с правами на чтение

## Мониторинг MTProto

### Проверка статуса через API

Endpoint для мониторинга:
```bash
curl http://178.217.98.201:8001/api/v1/stats/status \
  -H "Authorization: Bearer <token>"
```

### Логи

MTProto события логируются:

```bash
# Наш бэкенд
docker-compose logs -f web | grep -i mtproto

# Bot Gateway
docker-compose logs -f bot-gateway | grep -i mtproto
```

### Prometheus метрики

Gateway экспортирует метрики MTProto:

```
# Успешные запросы MTProto
bot_gateway_mtproto_requests_total{status="success"} 42

# Ошибки MTProto
bot_gateway_mtproto_requests_total{status="error"} 2

# Статус соединения (1 = connected, 0 = disconnected)
bot_gateway_mtproto_connected 1
```

## FAQ

### Обязательно ли использовать MTProto?

**Нет!** Проект работает и без MTProto, просто статистика будет ограничена (только member_count).

### Можно ли использовать MTProto только для некоторых каналов?

Да! MTProto настраивается глобально на Gateway, но наш бэкенд автоматически использует его для всех каналов. Если нужно выборочно - можно передавать `use_mtproto=False` в задачах.

### Как часто обновлять статистику с MTProto?

Рекомендации:
- **Каналы:** 15-30 минут (текущая настройка)
- **Посты (свежие):** 10-15 минут
- **Посты (старые >7 дней):** раз в день

### MTProto безопасен?

Да, это официальный протокол Telegram. Но:
- ✅ Используйте отдельную учетную запись (не личную)
- ✅ Храните session string в секрете
- ✅ Используйте 2FA на аккаунте

### Что если я превышу rate limits?

Gateway автоматически:
1. Обрабатывает FloodWait ошибки
2. Делает exponential backoff
3. Переключается на Bot API если MTProto недоступен

Наш бэкенд:
- Автоматически ретраит задачи
- Логирует ошибки
- Использует fallback к Bot API

## См. также

- [API (3).md](../API%20(3).md) - Полная документация Gateway API с MTProto
- [bot_channels_sync.md](bot_channels_sync.md) - Синхронизация каналов
- [Guide](guide.md) - Общее руководство

## Полезные команды

```bash
# Проверить статус MTProto
python manage.py check_mtproto_status

# Попытаться подключить MTProto
python manage.py check_mtproto_status --connect

# Синхронизировать статистику с MTProto
python manage.py shell -c "
from apps.stats.tasks import sync_all_channel_stats
sync_all_channel_stats.delay()
"

# Проверить последнюю статистику
python manage.py shell -c "
from apps.stats.models import ChannelStatsSnapshot
latest = ChannelStatsSnapshot.objects.latest('timestamp')
print(f'Source: {latest.meta.get(\"source\")}')
print(f'Views: {latest.views_last_10_posts}')
print(f'ER: {latest.er_last_10_posts}%')
"
```

---

**MTProto опционален, но значительно улучшает качество данных!** 📊

