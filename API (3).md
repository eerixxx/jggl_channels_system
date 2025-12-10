# Telegram Bot Gateway API Documentation

## Общая информация

**Base URL:** `http://178.217.98.201:8001`

**Версия API:** v1

**Формат данных:** JSON

## Аутентификация

Все API-эндпоинты (кроме `/health`, `/ready`, `/live`, `/metrics`) требуют аутентификации через Bearer-токен.

### Заголовок авторизации

```
Authorization: Bearer <INTERNAL_API_TOKEN>
```

### Пример запроса

```bash
curl -X POST http://178.217.98.201:8001/api/v1/messages/send \
  -H "Authorization: Bearer gateway-secure-token-2024-xyz" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": -1001234567890, "text": "Hello!"}'
```

### Ошибки аутентификации

| HTTP код | Код ошибки | Описание |
|----------|------------|----------|
| 401 | `UNAUTHORIZED` | Токен отсутствует или неверный |

---

## Эндпоинты сообщений

### POST /api/v1/messages/send

Отправка сообщения в Telegram-канал.

#### Заголовки

| Заголовок | Обязательный | Описание |
|-----------|--------------|----------|
| `Authorization` | Да | Bearer-токен |
| `Content-Type` | Да | `application/json` |
| `Idempotency-Key` | Нет | UUID для идемпотентности |

#### Тело запроса

```json
{
  "chat_id": -1001234567890,
  "text": "Текст сообщения",
  "photo_url": "https://example.com/image.jpg",
  "parse_mode": "HTML",
  "disable_web_page_preview": false,
  "disable_notification": false
}
```

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| `chat_id` | `int \| string` | Да | ID канала или @username |
| `text` | `string` | Да | Текст сообщения (1-4096 символов) |
| `photo_url` | `string` | Нет | URL фото для отправки |
| `parse_mode` | `string` | Нет | Режим парсинга: `HTML`, `Markdown`, `MarkdownV2`. По умолчанию: `HTML` |
| `disable_web_page_preview` | `boolean` | Нет | Отключить превью ссылок |
| `disable_notification` | `boolean` | Нет | Отправить без звука |

#### Успешный ответ (200 OK)

```json
{
  "success": true,
  "chat_id": -1001234567890,
  "message_id": 123,
  "date": "2024-01-15T10:30:00Z",
  "text": "Текст сообщения",
  "raw": { ... }
}
```

#### Пример с curl

```bash
# Отправка текстового сообщения
curl -X POST http://178.217.98.201:8001/api/v1/messages/send \
  -H "Authorization: Bearer gateway-secure-token-2024-xyz" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": -1001234567890,
    "text": "<b>Важное</b> сообщение!",
    "parse_mode": "HTML"
  }'

# Отправка фото с подписью
curl -X POST http://178.217.98.201:8001/api/v1/messages/send \
  -H "Authorization: Bearer gateway-secure-token-2024-xyz" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": -1001234567890,
    "text": "Подпись к фото",
    "photo_url": "https://example.com/photo.jpg"
  }'

# Идемпотентная отправка
curl -X POST http://178.217.98.201:8001/api/v1/messages/send \
  -H "Authorization: Bearer gateway-secure-token-2024-xyz" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000" \
  -d '{
    "chat_id": -1001234567890,
    "text": "Это сообщение отправится только один раз"
  }'
```

---

### POST /api/v1/messages/edit

Редактирование существующего сообщения.

#### Тело запроса

```json
{
  "chat_id": -1001234567890,
  "message_id": 123,
  "text": "Обновлённый текст",
  "parse_mode": "HTML",
  "disable_web_page_preview": false
}
```

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| `chat_id` | `int \| string` | Да | ID канала |
| `message_id` | `int` | Да | ID сообщения для редактирования |
| `text` | `string` | Да | Новый текст (1-4096 символов) |
| `parse_mode` | `string` | Нет | Режим парсинга |
| `disable_web_page_preview` | `boolean` | Нет | Отключить превью ссылок |

#### Успешный ответ (200 OK)

```json
{
  "success": true,
  "chat_id": -1001234567890,
  "message_id": 123,
  "text": "Обновлённый текст",
  "raw": { ... }
}
```

#### Пример

```bash
curl -X POST http://178.217.98.201:8001/api/v1/messages/edit \
  -H "Authorization: Bearer gateway-secure-token-2024-xyz" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": -1001234567890,
    "message_id": 123,
    "text": "<i>Отредактировано</i>",
    "parse_mode": "HTML"
  }'
```

---

### POST /api/v1/messages/delete

Удаление сообщения.

#### Тело запроса

```json
{
  "chat_id": -1001234567890,
  "message_id": 123
}
```

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| `chat_id` | `int \| string` | Да | ID канала |
| `message_id` | `int` | Да | ID сообщения для удаления |

#### Успешный ответ (200 OK)

```json
{
  "success": true,
  "chat_id": -1001234567890,
  "message_id": 123
}
```

#### Пример

```bash
curl -X POST http://178.217.98.201:8001/api/v1/messages/delete \
  -H "Authorization: Bearer gateway-secure-token-2024-xyz" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": -1001234567890,
    "message_id": 123
  }'
```

---

### GET /api/v1/messages/stats

Получение статистики сообщения.

#### Query-параметры

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `chat_id` | `int \| string` | Да | ID канала |
| `message_id` | `int` | Да | ID сообщения |

#### Успешный ответ (200 OK)

```json
{
  "success": true,
  "chat_id": -1001234567890,
  "message_id": 123,
  "views": null,
  "forwards": null,
  "reactions": null,
  "reply_count": null,
  "date": null,
  "raw": {
    "note": "Detailed message statistics are not available via Telegram Bot API"
  }
}
```

> **Примечание:** Telegram Bot API не предоставляет детальную статистику сообщений. Для получения полной статистики используйте MTProto API.

#### Пример

```bash
curl -X GET "http://178.217.98.201:8001/api/v1/messages/stats?chat_id=-1001234567890&message_id=123" \
  -H "Authorization: Bearer gateway-secure-token-2024-xyz"
```

---

### POST /api/v1/messages/stats/batch

Получение статистики для нескольких сообщений.

#### Тело запроса

```json
{
  "messages": [
    {"chat_id": -1001234567890, "message_id": 123},
    {"chat_id": -1001234567890, "message_id": 124},
    {"chat_id": -1001234567890, "message_id": 125}
  ]
}
```

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| `messages` | `array` | Да | Массив сообщений (1-100 элементов) |
| `messages[].chat_id` | `int \| string` | Да | ID канала |
| `messages[].message_id` | `int` | Да | ID сообщения |

#### Успешный ответ (200 OK)

```json
{
  "success": true,
  "results": [
    {
      "success": true,
      "chat_id": -1001234567890,
      "message_id": 123,
      "views": null,
      "forwards": null
    },
    ...
  ],
  "errors": []
}
```

---

## Эндпоинты каналов

### GET /api/v1/channels/info

Получение информации о канале.

#### Query-параметры

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `chat_id` | `int \| string` | Да | ID канала или @username |

#### Успешный ответ (200 OK)

```json
{
  "success": true,
  "chat_id": -1001234567890,
  "title": "My Channel",
  "username": "my_channel",
  "description": "Channel description",
  "invite_link": "https://t.me/+abc123",
  "photo": {
    "small_file_id": "...",
    "big_file_id": "...",
    "small_file_url": "https://...",
    "big_file_url": "https://..."
  },
  "member_count": 1500,
  "linked_chat_id": -1001987654321,
  "type": "channel",
  "raw": { ... }
}
```

#### Пример

```bash
curl -X GET "http://178.217.98.201:8001/api/v1/channels/info?chat_id=-1001234567890" \
  -H "Authorization: Bearer gateway-secure-token-2024-xyz"

# Или по username
curl -X GET "http://178.217.98.201:8001/api/v1/channels/info?chat_id=@my_channel" \
  -H "Authorization: Bearer gateway-secure-token-2024-xyz"
```

---

### GET /api/v1/channels/permissions

Получение прав бота в канале.

#### Query-параметры

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `chat_id` | `int \| string` | Да | ID канала |

#### Успешный ответ (200 OK)

```json
{
  "success": true,
  "chat_id": -1001234567890,
  "is_member": true,
  "is_admin": true,
  "can_post_messages": true,
  "can_edit_messages": true,
  "can_delete_messages": true,
  "can_restrict_members": false,
  "can_invite_users": true,
  "can_pin_messages": true,
  "can_manage_chat": true,
  "status": "administrator",
  "raw": { ... }
}
```

#### Пример

```bash
curl -X GET "http://178.217.98.201:8001/api/v1/channels/permissions?chat_id=-1001234567890" \
  -H "Authorization: Bearer gateway-secure-token-2024-xyz"
```

---

### GET /api/v1/channels/stats

Получение статистики канала.

#### Query-параметры

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `chat_id` | `int \| string` | Да | ID канала |

#### Успешный ответ (200 OK)

```json
{
  "success": true,
  "chat_id": -1001234567890,
  "member_count": 1500,
  "title": "My Channel",
  "raw": {
    "note": "Detailed channel statistics (ERR, ER, views) are not available via Telegram Bot API"
  }
}
```

> **Примечание:** Telegram Bot API предоставляет только количество подписчиков. Для ERR, ER и детальной аналитики используйте Telegram Analytics API.

---

## Webhook-эндпоинты

### POST /webhooks/channel-stats

Приём статистики канала для пересылки в Core-бэкенд.

#### Тело запроса

```json
{
  "chat_id": -1001234567890,
  "member_count": 1500,
  "title": "My Channel"
}
```

---

### POST /webhooks/message-stats

Приём статистики сообщения.

#### Тело запроса

```json
{
  "chat_id": -1001234567890,
  "message_id": 123,
  "views": 500,
  "forwards": 10
}
```

---

### POST /webhooks/channel-update

Приём обновлений информации о канале.

#### Тело запроса

```json
{
  "chat_id": -1001234567890,
  "title": "New Title",
  "username": "new_username",
  "description": "New description"
}
```

---

## Служебные эндпоинты

### GET /health

Проверка здоровья сервиса.

**Аутентификация:** Не требуется

```json
{
  "status": "healthy",
  "service": "telegram-bot-gateway",
  "version": "1.0.0"
}
```

### GET /ready

Проверка готовности к приёму запросов.

**Аутентификация:** Не требуется

```json
{
  "status": "ready",
  "service": "telegram-bot-gateway",
  "version": "1.0.0"
}
```

### GET /live

Проверка жизнеспособности.

**Аутентификация:** Не требуется

```json
{
  "status": "alive",
  "service": "telegram-bot-gateway",
  "version": "1.0.0"
}
```

### GET /metrics

Prometheus-метрики.

**Аутентификация:** Не требуется

**Content-Type:** `text/plain; charset=utf-8`

```
# HELP bot_gateway_requests_total Total number of requests by operation and status
# TYPE bot_gateway_requests_total counter
bot_gateway_requests_total{operation="messages_send",status="success"} 42.0
...
```

### GET /docs

Swagger UI документация.

### GET /redoc

ReDoc документация.

### GET /openapi.json

OpenAPI спецификация в JSON.

---

## Коды ошибок

Все ошибки возвращаются в едином формате:

```json
{
  "code": "ERROR_CODE",
  "error": "Человекочитаемое описание ошибки",
  "details": {
    "additional": "info"
  }
}
```

### Таблица кодов

| Код | HTTP | Описание |
|-----|------|----------|
| `UNAUTHORIZED` | 401 | Неверный или отсутствующий токен авторизации |
| `VALIDATION_ERROR` | 422 | Ошибка валидации запроса |
| `INVALID_CHAT_ID` | 400 | Неверный chat_id или канал не существует |
| `INVALID_MESSAGE_ID` | 404 | Сообщение не найдено |
| `BOT_NOT_ADMIN` | 403 | Бот не является администратором канала |
| `BOT_CANNOT_POST` | 403 | Бот не имеет права публиковать сообщения |
| `TELEGRAM_RATE_LIMIT` | 429 | Превышен лимит запросов к Telegram API |
| `TELEGRAM_UNAVAILABLE` | 503 | Telegram API временно недоступен |
| `TELEGRAM_BAD_REQUEST` | 400 | Некорректный запрос к Telegram API |
| `TIMEOUT` | 504 | Таймаут запроса |
| `IDEMPOTENCY_CONFLICT` | 409 | Запрос с таким Idempotency-Key уже обрабатывается |
| `INTERNAL_ERROR` | 500 | Внутренняя ошибка сервера |

### Примеры ошибок

**401 Unauthorized:**
```json
{
  "code": "UNAUTHORIZED",
  "error": "Invalid API token",
  "details": {}
}
```

**400 Invalid Chat ID:**
```json
{
  "code": "INVALID_CHAT_ID",
  "error": "Chat ID '-123' is invalid or does not exist.",
  "details": {
    "chat_id": "-123"
  }
}
```

**429 Rate Limit:**
```json
{
  "code": "TELEGRAM_RATE_LIMIT",
  "error": "Rate limit exceeded. Retry after 30 seconds.",
  "details": {
    "retry_after": 30
  }
}
```

**422 Validation Error:**
```json
{
  "code": "VALIDATION_ERROR",
  "error": "Request validation failed",
  "details": {
    "errors": [
      {
        "loc": ["body", "chat_id"],
        "msg": "Field required",
        "type": "missing"
      }
    ]
  }
}
```

---

## Идемпотентность

Для предотвращения дублирования сообщений при повторных запросах используйте заголовок `Idempotency-Key`:

```bash
curl -X POST http://178.217.98.201:8001/api/v1/messages/send \
  -H "Authorization: Bearer gateway-secure-token-2024-xyz" \
  -H "Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": -100, "text": "Test"}'
```

### Поведение:
- **Первый запрос:** Сообщение отправляется, результат кэшируется
- **Повторные запросы с тем же ключом:** Возвращается закэшированный результат без повторной отправки
- **TTL:** 24 часа (настраивается через `IDEMPOTENCY_TTL_SECONDS`)

---

## Rate Limiting

Сервис обрабатывает rate-limit от Telegram API:

1. При получении 429 от Telegram — автоматический retry с ожиданием `retry_after`
2. Максимум 3 попытки (настраивается через `MAX_TELEGRAM_RETRIES`)
3. Exponential backoff: 1s → 2s → 4s

При исчерпании попыток возвращается ошибка `TELEGRAM_RATE_LIMIT`.

---

## Примеры использования

### Python (requests)

```python
import requests

API_URL = "http://178.217.98.201:8001"
API_TOKEN = "your-secret-token"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json",
}

# Отправка сообщения
response = requests.post(
    f"{API_URL}/api/v1/messages/send",
    headers=headers,
    json={
        "chat_id": -1001234567890,
        "text": "<b>Hello</b> from Python!",
        "parse_mode": "HTML",
    },
)
print(response.json())

# Получение информации о канале
response = requests.get(
    f"{API_URL}/api/v1/channels/info",
    headers=headers,
    params={"chat_id": -1001234567890},
)
print(response.json())
```

### Python (httpx async)

```python
import httpx
import asyncio

async def send_message():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://178.217.98.201:8001/api/v1/messages/send",
            headers={
                "Authorization": "Bearer your-token",
                "Content-Type": "application/json",
            },
            json={
                "chat_id": -1001234567890,
                "text": "Async message!",
            },
        )
        return response.json()

result = asyncio.run(send_message())
print(result)
```

### JavaScript (fetch)

```javascript
const API_URL = 'http://178.217.98.201:8001';
const API_TOKEN = 'your-secret-token';

async function sendMessage(chatId, text) {
  const response = await fetch(`${API_URL}/api/v1/messages/send`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${API_TOKEN}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      chat_id: chatId,
      text: text,
      parse_mode: 'HTML',
    }),
  });
  return response.json();
}

sendMessage(-1001234567890, '<b>Hello</b> from JS!')
  .then(console.log);
```

---

## Эндпоинты управления ботом

### GET /api/v1/bot/info

Получение информации о боте.

#### Успешный ответ (200 OK)

```json
{
  "success": true,
  "bot_id": 123456789,
  "username": "my_bot",
  "first_name": "My Bot",
  "can_join_groups": true,
  "can_read_all_group_messages": false,
  "supports_inline_queries": false
}
```

### GET /api/v1/bot/webhook

Получение текущей конфигурации Telegram webhook.

#### Успешный ответ (200 OK)

```json
{
  "success": true,
  "url": "https://example.com/api/v1/webhooks/telegram",
  "has_custom_certificate": false,
  "pending_update_count": 0,
  "max_connections": 40,
  "allowed_updates": ["my_chat_member", "channel_post"]
}
```

### POST /api/v1/bot/webhook/set

Настройка Telegram webhook для получения обновлений.

#### Query параметры

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `url` | `string` | Нет | URL для webhook. Если не указан, используется `TELEGRAM_WEBHOOK_URL` из конфига |
| `secret_token` | `string` | Нет | Секретный токен для валидации запросов от Telegram |
| `max_connections` | `int` | Нет | Макс. количество одновременных подключений (1-100). По умолчанию: 40 |

#### Успешный ответ (200 OK)

```json
{
  "success": true,
  "message": "Webhook configured: https://example.com/api/v1/webhooks/telegram",
  "url": "https://example.com/api/v1/webhooks/telegram"
}
```

#### Пример с curl

```bash
curl -X POST "http://178.217.98.201:8001/api/v1/bot/webhook/set?url=https://myserver.com" \
  -H "Authorization: Bearer gateway-secure-token-2024-xyz"
```

### POST /api/v1/bot/webhook/delete

Удаление Telegram webhook (переключение на режим polling).

#### Query параметры

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `drop_pending_updates` | `boolean` | Нет | Удалить все ожидающие обновления |

#### Успешный ответ (200 OK)

```json
{
  "success": true,
  "message": "Webhook removed"
}
```

### GET /api/v1/bot/updates

Получение ожидающих обновлений через long polling (работает только без настроенного webhook).

#### Query параметры

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `offset` | `int` | Нет | Смещение для обновлений |
| `limit` | `int` | Нет | Количество обновлений (1-100). По умолчанию: 100 |
| `timeout` | `int` | Нет | Таймаут long polling (0-60). По умолчанию: 0 |

#### Успешный ответ (200 OK)

```json
{
  "success": true,
  "count": 2,
  "updates": [
    {
      "update_id": 123456789,
      "my_chat_member": {
        "chat": {"id": -1001234567890, "title": "My Channel", "type": "channel"},
        "old_chat_member": {"status": "left"},
        "new_chat_member": {"status": "administrator"}
      }
    }
  ]
}
```

### POST /api/v1/bot/updates/process

Получение и обработка ожидающих обновлений. Автоматически уведомляет внешний бэкенд об изменениях членства бота.

#### Успешный ответ (200 OK)

```json
{
  "success": true,
  "processed": 2,
  "results": [
    {"update_id": 123456789, "status": "processed", "type": "my_chat_member"},
    {"update_id": 123456790, "status": "ignored", "type": "unknown"}
  ]
}
```

---

## Webhook для приёма обновлений от Telegram

### POST /api/v1/webhooks/telegram

Эндпоинт для приёма обновлений от Telegram Bot API (режим webhook).

**Важно:** Этот эндпоинт должен быть доступен из интернета. Telegram будет отправлять сюда POST-запросы с обновлениями.

При получении обновления `my_chat_member` (добавление/удаление бота из канала), gateway автоматически отправляет уведомление на внешний бэкенд.

#### Обрабатываемые типы обновлений

| Тип | Описание |
|-----|----------|
| `my_chat_member` | Изменение статуса бота в чате (добавлен/удалён) |
| `channel_post` | Новый пост в канале |
| `edited_channel_post` | Редактирование поста в канале |

---

## Уведомления о событиях бота (Bot Events)

Когда бота добавляют или удаляют из канала/группы, gateway автоматически отправляет HTTP-запрос на внешний бэкенд.

### Payload события

```json
{
  "event": "bot_added",
  "chat_id": -1001234567890,
  "chat_title": "My Channel",
  "chat_username": "my_channel",
  "chat_type": "channel",
  "old_status": "left",
  "new_status": "administrator",
  "permissions": {
    "can_post_messages": true,
    "can_edit_messages": true,
    "can_delete_messages": true,
    "can_restrict_members": false,
    "can_invite_users": true,
    "can_pin_messages": true,
    "can_manage_chat": true
  }
}
```

### Типы событий

| Событие | Описание |
|---------|----------|
| `bot_added` | Бот добавлен как администратор |
| `bot_removed` | Бот удалён из канала/группы |
| `bot_permissions_changed` | Права бота изменены (остаётся администратором) |

### HTTP-заголовки

| Заголовок | Описание |
|-----------|----------|
| `X-Bot-Token` | Токен авторизации (из `EXTERNAL_BACKEND_TOKEN`) |
| `X-Event-Type` | Тип события: `bot_added`, `bot_removed`, `bot_permissions_changed` |
| `X-Request-ID` | ID запроса для трассировки |
| `Content-Type` | `application/json` |

### Эндпоинт на внешнем бэкенде

Gateway отправляет POST-запрос на:
```
{EXTERNAL_BACKEND_URL}/bot-events
```

### Пример обработчика на Django

```python
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def bot_events_handler(request):
    # Проверка токена
    token = request.headers.get('X-Bot-Token')
    if token != 'your-secret-token':
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    data = json.loads(request.body)
    event = data.get('event')
    chat_id = data.get('chat_id')
    chat_title = data.get('chat_title')
    
    if event == 'bot_added':
        # Бот добавлен в канал
        Channel.objects.update_or_create(
            telegram_id=chat_id,
            defaults={
                'title': chat_title,
                'username': data.get('chat_username'),
                'is_active': True,
            }
        )
    elif event == 'bot_removed':
        # Бот удалён из канала
        Channel.objects.filter(telegram_id=chat_id).update(is_active=False)
    
    return JsonResponse({'status': 'ok'})
```

### Пример обработчика на FastAPI

```python
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

app = FastAPI()

class BotEvent(BaseModel):
    event: str
    chat_id: int
    chat_title: Optional[str]
    chat_username: Optional[str]
    chat_type: Optional[str]
    old_status: Optional[str]
    new_status: Optional[str]
    permissions: Optional[Dict[str, Any]]

@app.post("/bot-events")
async def handle_bot_event(
    payload: BotEvent,
    x_bot_token: str = Header(...),
):
    if x_bot_token != "your-secret-token":
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if payload.event == "bot_added":
        print(f"Bot added to: {payload.chat_title} ({payload.chat_id})")
        # Сохранить в БД
    elif payload.event == "bot_removed":
        print(f"Bot removed from: {payload.chat_title} ({payload.chat_id})")
        # Обновить статус в БД
    
    return {"status": "ok"}
```

---

## Детальная статистика (MTProto API)

MTProto API предоставляет детальную статистику, недоступную через Bot API:
- Точное количество просмотров
- Детализация реакций (с указанием emoji)
- Количество комментариев
- Статистика роста канала

### Настройка MTProto

1. Получите API credentials на https://my.telegram.org
2. Сгенерируйте session string:

```bash
python scripts/generate_session.py
```

3. Добавьте в `.env`:

```bash
MTPROTO_ENABLED=true
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_SESSION_STRING=your_session_string
```

### GET /api/v1/stats/status

Проверка статуса MTProto API.

#### Успешный ответ (200 OK)

```json
{
  "enabled": true,
  "available": true,
  "connected": true,
  "has_api_id": true,
  "has_api_hash": true,
  "has_session": true
}
```

### GET /api/v1/stats/channel/{chat_id}

Детальная статистика канала.

#### Успешный ответ (200 OK)

```json
{
  "success": true,
  "channel": {
    "chat_id": -1001234567890,
    "title": "My Channel",
    "username": "my_channel",
    "participants_count": 15000,
    "admins_count": 5,
    "online_count": 1200,
    "about": "Channel description",
    "is_verified": false,
    "is_megagroup": false,
    "is_broadcast": true,
    "can_view_stats": true
  },
  "growth_stats": {
    "period": {
      "min_date": "2024-01-01T00:00:00",
      "max_date": "2024-01-15T00:00:00"
    },
    "followers": {
      "current": 15000,
      "previous": 14500
    },
    "views_per_post": {
      "current": 5000,
      "previous": 4800
    }
  }
}
```

### GET /api/v1/stats/message/{chat_id}/{message_id}

Детальная статистика сообщения.

#### Успешный ответ (200 OK)

```json
{
  "success": true,
  "chat_id": -1001234567890,
  "message_id": 123,
  "views": 5000,
  "forwards": 150,
  "replies": 45,
  "reactions": {
    "total_count": 320,
    "reactions": [
      {"emoji": "👍", "count": 200},
      {"emoji": "❤️", "count": 80},
      {"emoji": "🔥", "count": 40}
    ]
  },
  "date": "2024-01-15T10:30:00Z",
  "pinned": false
}
```

### POST /api/v1/stats/messages/{chat_id}/batch

Статистика нескольких сообщений за один запрос.

#### Тело запроса

```json
[123, 124, 125, 126, 127]
```

#### Успешный ответ (200 OK)

```json
{
  "success": true,
  "chat_id": -1001234567890,
  "count": 5,
  "messages": [
    {
      "message_id": 123,
      "views": 5000,
      "forwards": 150,
      "replies": 45,
      "reactions": {"total_count": 320, "reactions": [...]}
    },
    ...
  ]
}
```

### GET /api/v1/stats/posts/{chat_id}/recent

Статистика последних постов в канале.

#### Query параметры

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `limit` | `int` | Нет | Количество постов (1-100). По умолчанию: 50 |
| `before` | `datetime` | Нет | Получить посты до этой даты |

#### Успешный ответ (200 OK)

```json
{
  "success": true,
  "chat_id": -1001234567890,
  "count": 50,
  "totals": {
    "views": 250000,
    "forwards": 5000,
    "reactions": 15000,
    "replies": 2000
  },
  "average": {
    "views": 5000,
    "forwards": 100,
    "reactions": 300,
    "replies": 40
  },
  "posts": [
    {
      "message_id": 123,
      "text": "Текст поста...",
      "has_media": true,
      "views": 5000,
      "forwards": 150,
      "replies": 45,
      "reactions_count": 320,
      "date": "2024-01-15T10:30:00Z",
      "pinned": false
    },
    ...
  ]
}
```

### POST /api/v1/stats/connect

Подключение MTProto клиента.

#### Успешный ответ (200 OK)

```json
{
  "success": true,
  "connected": true,
  "message": "MTProto client connected successfully"
}
```

---

## Переменные окружения

| Переменная | Обязательная | Описание | По умолчанию |
|------------|--------------|----------|--------------|
| `TELEGRAM_BOT_TOKEN` | Да | Токен Telegram-бота | — |
| `INTERNAL_API_TOKEN` | Да | Токен для API-аутентификации | — |
| `TELEGRAM_API_BASE` | Нет | Base URL Telegram API | `https://api.telegram.org` |
| `TELEGRAM_TIMEOUT_SECONDS` | Нет | Таймаут запросов к Telegram | `10` |
| `MAX_TELEGRAM_RETRIES` | Нет | Макс. количество повторов | `3` |
| `IDEMPOTENCY_BACKEND` | Нет | Бэкенд: `memory` или `redis` | `memory` |
| `IDEMPOTENCY_TTL_SECONDS` | Нет | TTL для idempotency-ключей | `86400` |
| `REDIS_URL` | Нет | URL Redis | `redis://localhost:6379/0` |
| `LOG_LEVEL` | Нет | Уровень логирования | `INFO` |
| `LOG_DIR` | Нет | Директория для логов | `logs` |
| `LOG_RETENTION_DAYS` | Нет | Срок хранения логов | `7` |
| `HOST` | Нет | Хост для сервера | `0.0.0.0` |
| `PORT` | Нет | Порт для сервера | `8000` |
| `EXTERNAL_BACKEND_ENABLED` | Нет | Включить отправку событий бота | `true` |
| `EXTERNAL_BACKEND_URL` | Нет | URL внешнего бэкенда для событий | — |
| `EXTERNAL_BACKEND_TOKEN` | Нет | Токен авторизации для внешнего бэкенда | — |
| `NOTIFY_ON_CHANNEL_POSTS` | Нет | Уведомлять о новых постах в каналах | `false` |
| `TELEGRAM_WEBHOOK_ENABLED` | Нет | Включить режим webhook | `false` |
| `TELEGRAM_WEBHOOK_URL` | Нет | Публичный URL для webhook | — |
| `TELEGRAM_WEBHOOK_SECRET` | Нет | Секретный токен для валидации webhook | — |
| `MTPROTO_ENABLED` | Нет | Включить MTProto API | `false` |
| `TELEGRAM_API_ID` | Нет | API ID с my.telegram.org | — |
| `TELEGRAM_API_HASH` | Нет | API Hash с my.telegram.org | — |
| `TELEGRAM_SESSION_STRING` | Нет | Session string для Telethon | — |
