# API Documentation

## Overview

The Channels Admin API provides RESTful endpoints for managing Telegram channels, posts, and statistics.

**Base URL:** `/api/v1/`

**Authentication:** Token-based authentication (Authorization header)

---

## Authentication

### Token Authentication

Include the token in the Authorization header:

```
Authorization: Token <your-token>
```

For bot service integration:
```
Authorization: Bearer <bot-service-token>
```

---

## Channels API

### List Channel Groups

```
GET /api/v1/channels/groups/
```

**Response:**
```json
{
  "count": 1,
  "results": [
    {
      "id": 1,
      "name": "Main Product Channels",
      "is_active": true,
      "channels_count": 5
    }
  ]
}
```

### Get Channel Group Details

```
GET /api/v1/channels/groups/{id}/
```

**Response:**
```json
{
  "id": 1,
  "name": "Main Product Channels",
  "description": "Primary channels for our product",
  "primary_channel": {
    "id": 1,
    "title": "Product Channel EN",
    "username": "productchannel_en",
    "language_code": "en",
    "is_primary": true,
    "is_active": true,
    "member_count": 50000
  },
  "channels": [...],
  "channels_count": 5,
  "active_channels_count": 5,
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### List Channels

```
GET /api/v1/channels/
```

**Query Parameters:**
- `group` - Filter by group ID
- `language` - Filter by language ID
- `is_active` - Filter by active status
- `is_primary` - Filter by primary status
- `search` - Search by title or username

### Get Channel Details

```
GET /api/v1/channels/{id}/
```

### Sync Channel

```
POST /api/v1/channels/{id}/sync/
```

Triggers a background task to sync channel info from Telegram.

### Verify Bot Permissions

```
POST /api/v1/channels/{id}/verify_bot/
```

Triggers a background task to verify bot permissions.

---

## Posts API

### List Multi-Channel Posts

```
GET /api/v1/posts/multi/
```

**Query Parameters:**
- `group` - Filter by channel group
- `status` - Filter by status (draft, published, etc.)
- `auto_translate_enabled` - Filter by auto-translate setting
- `search` - Search by title or content

**Response:**
```json
{
  "count": 10,
  "results": [
    {
      "id": 1,
      "internal_title": "Product Launch Announcement",
      "group_name": "Main Product Channels",
      "status": "published",
      "channel_posts_count": 5,
      "published_posts_count": 5,
      "auto_translate_enabled": true,
      "created_at": "2024-01-15T10:00:00Z",
      "published_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### Create Multi-Channel Post

```
POST /api/v1/posts/multi/
```

**Request Body:**
```json
{
  "group": 1,
  "internal_title": "New Product Announcement",
  "primary_channel": 1,
  "primary_text_markdown": "**Exciting news!**\n\nWe're launching...",
  "auto_translate_enabled": true,
  "disable_web_page_preview": false,
  "disable_notification": false
}
```

### Get Multi-Channel Post Details

```
GET /api/v1/posts/multi/{id}/
```

### Request Translations

```
POST /api/v1/posts/multi/{id}/request_translations/
```

### Publish All

```
POST /api/v1/posts/multi/{id}/publish_all/
```

### Publish Ready Only

```
POST /api/v1/posts/multi/{id}/publish_ready/
```

### List Channel Posts

```
GET /api/v1/posts/channel/
```

**Query Parameters:**
- `multi_post` - Filter by multi-channel post ID
- `channel` - Filter by channel ID
- `language` - Filter by language ID
- `status` - Filter by status
- `source_type` - Filter by source type (primary, auto_translated, manual)

### Update Channel Post

```
PATCH /api/v1/posts/channel/{id}/
```

**Request Body:**
```json
{
  "text_markdown": "Updated translated text...",
  "manually_edited": true
}
```

### Publish Channel Post

```
POST /api/v1/posts/channel/{id}/publish/
```

### Request Translation for Channel Post

```
POST /api/v1/posts/channel/{id}/request_translation/
```

---

## Statistics API

### Overview

```
GET /api/v1/stats/overview/
```

**Response:**
```json
{
  "total_channel_groups": 2,
  "total_channels": 10,
  "total_subscribers": 500000,
  "avg_er": 2.5,
  "avg_err": 15.3,
  "top_channels": [...],
  "recent_global_stats": [...]
}
```

### Channel Growth

```
GET /api/v1/stats/channel/{channel_id}/growth/
```

**Response:**
```json
{
  "channel_id": 1,
  "channel_title": "Product Channel EN",
  "current_subscribers": 50000,
  "growth_24h": 150,
  "growth_24h_pct": 0.3,
  "growth_7d": 1200,
  "growth_7d_pct": 2.4,
  "growth_30d": 5000,
  "growth_30d_pct": 10.0
}
```

### Group Comparison

```
GET /api/v1/stats/group/{group_id}/comparison/
```

**Response:**
```json
{
  "group_id": 1,
  "group_name": "Main Product Channels",
  "channels": [
    {
      "channel_id": 1,
      "title": "Product Channel EN",
      "language": "en",
      "language_name": "English",
      "subscribers": 50000,
      "growth_7d": 1200,
      "growth_7d_pct": 2.4,
      "views_last_10": 250000,
      "er": 3.2,
      "err": 18.5
    },
    ...
  ]
}
```

### Channel Stats Snapshots

```
GET /api/v1/stats/channel-snapshots/
```

### Post Stats

```
GET /api/v1/stats/post-stats/
```

### Daily Stats

```
GET /api/v1/stats/daily/
```

---

## Bot Service Webhooks

These endpoints receive data from the external Telegram bot service.

### Channel Stats Webhook

```
POST /api/v1/bot/channel-stats/
```

**Headers:**
```
Authorization: Bearer <bot-service-token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "chat_id": "-1001234567890",
  "timestamp": "2024-01-15T10:00:00Z",
  "member_count": 50000,
  "views_last_10_posts": 250000,
  "avg_views_per_post": 25000,
  "er": 3.2,
  "err": 18.5,
  "total_posts": 500,
  "posts_last_24h": 3,
  "posts_last_7d": 15
}
```

### Message Stats Webhook

```
POST /api/v1/bot/message-stats/
```

**Request Body:**
```json
{
  "chat_id": "-1001234567890",
  "message_id": "12345",
  "timestamp": "2024-01-15T10:00:00Z",
  "views": 25000,
  "forwards": 150,
  "reactions_count": 500,
  "reactions": {"👍": 300, "❤️": 150, "🔥": 50},
  "comments": 25
}
```

### Channel Update Webhook

```
POST /api/v1/bot/channel-update/
```

**Request Body:**
```json
{
  "chat_id": "-1001234567890",
  "title": "Product Channel EN",
  "username": "productchannel_en",
  "description": "Official product channel",
  "member_count": 50000,
  "photo_url": "https://...",
  "invite_link": "https://t.me/+abc123",
  "is_admin": true,
  "can_post_messages": true,
  "can_edit_messages": true,
  "can_delete_messages": false
}
```

---

## Monitoring Endpoints

### Health Check (Liveness)

```
GET /health/
```

**Response:**
```json
{"status": "ok"}
```

### Readiness Check

```
GET /ready/
```

**Response:**
```json
{
  "status": "ready",
  "checks": {
    "database": {"healthy": true, "message": "Connected"},
    "redis": {"healthy": true, "message": "Connected"},
    "celery": {"healthy": true, "message": "2 worker(s) active"}
  }
}
```

### System Status

```
GET /status/
```

### Celery Status

```
GET /celery/
```

### Prometheus Metrics

```
GET /metrics
```

---

## Error Responses

All error responses follow this format:

```json
{
  "error": "Error message",
  "detail": "Detailed error description"
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

---

## Rate Limiting

API endpoints may be rate limited. Check response headers:

- `X-RateLimit-Limit` - Maximum requests per window
- `X-RateLimit-Remaining` - Remaining requests
- `X-RateLimit-Reset` - Window reset time

