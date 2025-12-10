# LLM Translation Middleware - API Documentation

## Overview

LLM Translation Middleware — внутренний HTTP-сервис для автоматического перевода текстов с помощью LLM с максимальным сохранением markdown-разметки.

## Base URL

```
http://178.217.98.201:8002
```

## Authentication

Все запросы к API (кроме `/health` и `/metrics`) требуют заголовок авторизации:

```
Authorization: Bearer 669d2bb55f63c5145eff622ce926ad52ef266e39c983b572a5ac45159fddf6e9
```

---

## Endpoints

### 1. Health Check

**GET** `/health`

Проверка работоспособности сервиса.

**Response:**
```json
{
  "status": "healthy"
}
```

---

### 2. Get Supported Languages

**GET** `/api/v1/languages`

Получить список поддерживаемых языков для перевода.

**Headers:**
```
Authorization: Bearer <API_TOKEN>
```

**Response:**
```json
{
  "languages": [
    { "code": "en", "name": "English" },
    { "code": "ru", "name": "Russian" },
    { "code": "de", "name": "German" },
    { "code": "fr", "name": "French" },
    { "code": "es", "name": "Spanish" },
    { "code": "it", "name": "Italian" },
    { "code": "pt", "name": "Portuguese" },
    { "code": "zh", "name": "Chinese" },
    { "code": "ja", "name": "Japanese" },
    { "code": "ko", "name": "Korean" },
    { "code": "ar", "name": "Arabic" },
    { "code": "hi", "name": "Hindi" },
    { "code": "tr", "name": "Turkish" },
    { "code": "pl", "name": "Polish" },
    { "code": "nl", "name": "Dutch" },
    { "code": "sv", "name": "Swedish" },
    { "code": "da", "name": "Danish" },
    { "code": "no", "name": "Norwegian" },
    { "code": "fi", "name": "Finnish" },
    { "code": "cs", "name": "Czech" },
    { "code": "uk", "name": "Ukrainian" },
    { "code": "el", "name": "Greek" },
    { "code": "he", "name": "Hebrew" },
    { "code": "th", "name": "Thai" },
    { "code": "vi", "name": "Vietnamese" },
    { "code": "id", "name": "Indonesian" },
    { "code": "ms", "name": "Malay" },
    { "code": "ro", "name": "Romanian" },
    { "code": "hu", "name": "Hungarian" },
    { "code": "bg", "name": "Bulgarian" }
  ]
}
```

---

### 3. Translate Text (Single Language)

**POST** `/api/v1/translate`

Перевод markdown-текста на один язык.

**Headers:**
```
Authorization: Bearer <API_TOKEN>
Content-Type: application/json
```

**Request Body:**
```json
{
  "text": "# Hello World\n\nThis is a **test** message with [a link](https://example.com).",
  "source_language": "en",
  "target_language": "ru",
  "tone": "professional",
  "context": "technical documentation",
  "preserve_formatting": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | Yes | Markdown текст для перевода (макс. 12000 символов) |
| `source_language` | string | Yes | Код исходного языка (например: "en", "ru") |
| `target_language` | string | Yes | Код целевого языка |
| `tone` | string | No | Тон перевода: `formal`, `casual`, `professional` (default: `professional`) |
| `context` | string | No | Контекст для более точного перевода (например: "crypto news", "medical") |
| `preserve_formatting` | boolean | No | Сохранять markdown форматирование (default: `true`) |

**Response (200 OK):**
```json
{
  "translation": "# Привет, мир\n\nЭто **тестовое** сообщение со [ссылкой](https://example.com).",
  "warnings": [],
  "tokens_used": 350
}
```

| Field | Type | Description |
|-------|------|-------------|
| `translation` | string | Переведённый текст с сохранением markdown |
| `warnings` | array | Предупреждения о проблемах с форматированием |
| `tokens_used` | integer | Количество использованных токенов |

---

### 4. Batch Translate (Multiple Languages)

**POST** `/api/v1/translate/batch`

Перевод текста на несколько языков одновременно.

**Headers:**
```
Authorization: Bearer <API_TOKEN>
Content-Type: application/json
```

**Request Body:**
```json
{
  "text": "# Hello World\n\nThis is a **test** message.",
  "source_language": "en",
  "target_languages": ["ru", "de", "fr"],
  "tone": "casual",
  "context": "crypto news",
  "preserve_formatting": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | Yes | Markdown текст для перевода |
| `source_language` | string | Yes | Код исходного языка |
| `target_languages` | array | Yes | Массив кодов целевых языков (макс. 20) |
| `tone` | string | No | Тон перевода |
| `context` | string | No | Контекст для перевода |
| `preserve_formatting` | boolean | No | Сохранять markdown форматирование |

**Response (200 OK):**
```json
{
  "results": [
    {
      "target_language": "ru",
      "translation": "# Привет, мир\n\nЭто **тестовое** сообщение.",
      "warnings": [],
      "tokens_used": 318
    },
    {
      "target_language": "de",
      "translation": "# Hallo Welt\n\nDas ist eine **Test**-Nachricht.",
      "warnings": [],
      "tokens_used": 320
    },
    {
      "target_language": "fr",
      "translation": "# Bonjour le monde\n\nCeci est un message de **test**.",
      "warnings": [],
      "tokens_used": 322
    }
  ],
  "total_tokens_used": 960
}
```

---

### 5. Prometheus Metrics

**GET** `/metrics`

Метрики в формате Prometheus.

**Available Metrics:**
- `translation_requests_total{operation, status}` - количество запросов
- `translation_errors_total{operation, error_code}` - количество ошибок
- `translation_request_duration_seconds{operation}` - время выполнения запросов
- `translation_tokens_used_total{provider, model}` - использованные токены

---

## Error Responses

Все ошибки возвращаются в формате:

```json
{
  "code": "ERROR_CODE",
  "error": "Human readable message",
  "details": {}
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Отсутствует или неверный токен |
| `INVALID_LANGUAGE` | 400 | Неподдерживаемый язык |
| `EMPTY_TEXT` | 400 | Пустой текст |
| `TEXT_TOO_LONG` | 400 | Текст превышает 12000 символов |
| `LLM_RATE_LIMIT` | 429 | Превышен лимит запросов к LLM |
| `LLM_UNAVAILABLE` | 503 | LLM провайдер недоступен |
| `LLM_TIMEOUT` | 504 | Таймаут запроса к LLM |
| `LLM_BAD_RESPONSE` | 502 | Некорректный ответ от LLM |
| `INTERNAL_ERROR` | 500 | Внутренняя ошибка сервера |

### Example Error Response

```json
{
  "code": "TEXT_TOO_LONG",
  "error": "Text length (15000) exceeds maximum allowed (12000)",
  "details": {
    "length": 15000,
    "max_length": 12000
  }
}
```

---

## Usage Examples

### cURL

**Single Translation:**
```bash
curl -X POST http://178.217.98.201:8002/api/v1/translate \
  -H "Authorization: Bearer 669d2bb55f63c5145eff622ce926ad52ef266e39c983b572a5ac45159fddf6e9" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "# Hello World\n\nThis is a **test** message.",
    "source_language": "en",
    "target_language": "ru",
    "tone": "professional"
  }'
```

**Batch Translation:**
```bash
curl -X POST http://178.217.98.201:8002/api/v1/translate/batch \
  -H "Authorization: Bearer 669d2bb55f63c5145eff622ce926ad52ef266e39c983b572a5ac45159fddf6e9" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, world!",
    "source_language": "en",
    "target_languages": ["ru", "de", "fr"],
    "tone": "casual"
  }'
```

### Python

```python
import httpx

BASE_URL = "http://178.217.98.201:8002"
API_TOKEN = "669d2bb55f63c5145eff622ce926ad52ef266e39c983b572a5ac45159fddf6e9"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# Single translation
response = httpx.post(
    f"{BASE_URL}/api/v1/translate",
    headers=headers,
    json={
        "text": "# Hello World\n\nThis is a **test** message.",
        "source_language": "en",
        "target_language": "ru",
        "tone": "professional"
    }
)
result = response.json()
print(result["translation"])

# Batch translation
response = httpx.post(
    f"{BASE_URL}/api/v1/translate/batch",
    headers=headers,
    json={
        "text": "Hello, world!",
        "source_language": "en",
        "target_languages": ["ru", "de", "fr"],
        "tone": "casual"
    }
)
batch_result = response.json()
for item in batch_result["results"]:
    print(f"{item['target_language']}: {item['translation']}")
```

### JavaScript/Node.js

```javascript
const BASE_URL = "http://178.217.98.201:8002";
const API_TOKEN = "669d2bb55f63c5145eff622ce926ad52ef266e39c983b572a5ac45159fddf6e9";

async function translate(text, sourceLang, targetLang, tone = "professional") {
  const response = await fetch(`${BASE_URL}/api/v1/translate`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${API_TOKEN}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      text,
      source_language: sourceLang,
      target_language: targetLang,
      tone
    })
  });
  
  return response.json();
}

// Usage
const result = await translate(
  "# Hello World\n\nThis is a **test** message.",
  "en",
  "ru"
);
console.log(result.translation);
```

---

## Rate Limits

- Сервис использует retry механизм с exponential backoff
- При превышении лимитов OpenAI возвращается ошибка `LLM_RATE_LIMIT`
- Рекомендуется реализовать client-side rate limiting

## Notes

- Максимальный размер текста: **12000 символов**
- Markdown форматирование сохраняется автоматически
- URL в ссылках не переводятся
- Код (inline и блоки) не переводится
- Request ID возвращается в заголовке `X-Request-ID` для трекинга

---

## Server Configuration

**Domain/IP:** `178.217.98.201`  
**Port:** `8002`  
**Protocol:** HTTP

### Environment Variables (for administrators)

```bash
INTERNAL_API_TOKEN=<secure-token>
OPENAI_API_KEY=<openai-key>
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
HTTP_PROXY=<proxy-url-if-needed>
```

---

## Status

| Component | Status |
|-----------|--------|
| Service | ✅ Running |
| Health Endpoint | ✅ Available |
| Metrics | ✅ Available |
| OpenAI Integration | ⚠️ Requires proxy from RU region |

