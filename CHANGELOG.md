# Changelog

## [1.1.0] - 2024-12-10

### ✨ Новые возможности

#### MTProto API Integration
- 🚀 Добавлена поддержка MTProto API для детальной статистики
- 📊 Точные метрики: просмотры, реакции (с разбивкой), комментарии, пересылки
- 📈 Статистика роста каналов
- 🔄 Автоматический fallback на Bot API если MTProto недоступен

**Новые эндпоинты Gateway:**
- `GET /api/v1/stats/status` - статус MTProto
- `GET /api/v1/stats/channel/{chat_id}` - детальная статистика канала
- `GET /api/v1/stats/message/{chat_id}/{message_id}` - детальная статистика сообщения
- `POST /api/v1/stats/messages/{chat_id}/batch` - батч статистика
- `GET /api/v1/stats/posts/{chat_id}/recent` - статистика последних постов
- `POST /api/v1/stats/connect` - подключение MTProto клиента

**Новые management команды:**
- `python manage.py check_mtproto_status` - проверить статус MTProto
- `python manage.py check_mtproto_status --connect` - подключить MTProto

### 🔄 Изменения

#### Backend Integration
- Обновлены Pydantic-схемы с MTProto моделями
- Добавлены MTProto методы в `TelegramBotClient`
- Обновлены задачи синхронизации для использования MTProto
- Добавлен умный выбор API: MTProto (если доступен) → Bot API (fallback)

#### Database
- `ChannelStatsSnapshot.meta` теперь содержит `source: "mtproto"` или `"bot_api"`
- `PostStats.meta` содержит детальную информацию из MTProto
- Все метрики заполняются реальными данными при использовании MTProto

#### Tasks
- `sync_channel_stats()` - добавлен параметр `use_mtproto=True`
- `sync_post_stats()` - добавлен параметр `use_mtproto=True`
- Автоматический retry при ошибках MTProto
- Graceful fallback на Bot API

### 📚 Документация
- Добавлен `docs/mtproto_integration.md` - полное руководство по MTProto
- Обновлён `README.md` с информацией об MTProto
- Обновлён `env.example` с настройками MTProto

### ⚙️ Настройки

**Новые переменные окружения:**
```env
# Enable MTProto stats usage (on backend side)
TELEGRAM_USE_MTPROTO_STATS=true
```

**На стороне Gateway (для активации MTProto):**
```env
MTPROTO_ENABLED=true
TELEGRAM_API_ID=<your api id>
TELEGRAM_API_HASH=<your api hash>
TELEGRAM_SESSION_STRING=<session string>
```

### 🐛 Исправления
- Исправлена ошибка IndentationError в `views.py`
- Улучшена обработка ошибок в HTTP-клиенте
- Добавлены подробные логи для отладки

---

## [1.0.0] - 2024-12-10

### ✨ Первый релиз

#### Основные возможности
- 📡 Автоматическое обнаружение каналов из Telegram Bot Gateway
- 🌍 Мультиканальные посты с автопереводом
- 📤 Публикация во все каналы одной кнопкой
- 📊 Базовая статистика через Bot API
- 👥 Управление группами каналов
- 🔄 Celery + Beat для фоновых задач
- 📈 Prometheus + Grafana мониторинг

#### Интеграции
- ✅ Telegram Bot Gateway API
- ✅ LLM Translation Middleware (готово к подключению)

#### Management команды
- `python manage.py sync_bot_channels` - импорт каналов
- `python manage.py sync_bot_channels --continuous` - непрерывная синхронизация

#### Webhook endpoints
- `POST /api/integrations/telegram-bot/bot-events/` - события бота
- `POST /api/integrations/telegram-bot/channel-stats/` - статистика каналов
- `POST /api/integrations/telegram-bot/message-stats/` - статистика сообщений
- `POST /api/integrations/telegram-bot/channel-update/` - обновления каналов

---

## Migration Guide: 1.0.0 → 1.1.0

### Для обновления до версии 1.1.0:

1. **Обновите код:**
   ```bash
   git pull origin main
   ```

2. **Пересоберите контейнеры:**
   ```bash
   docker-compose build
   docker-compose up -d
   ```

3. **Миграций БД не требуется** - MTProto использует существующие модели

4. **Проверьте статус MTProto:**
   ```bash
   docker-compose exec web python manage.py check_mtproto_status
   ```

5. **(Опционально) Настройте MTProto на Gateway** для детальной статистики:
   - См. `docs/mtproto_integration.md`

### Breaking Changes

**Нет breaking changes!** Все изменения обратно совместимы.

---

**Полная документация:** [README.md](README.md)

