# Изменения в бесплатной версии

## Удаленные компоненты

### Директории
- ❌ `company_data/` - управление компаниями и их данными
- ❌ `config/` - шаблоны хуков и конфигурации уровней доступа
- ❌ `examples/` - примеры использования

### Модули
- ❌ `claude_cli/metrics.py` - сбор метрик и Prometheus
- ❌ `claude_cli/monitor.py` - мониторинг использования инструментов
- ❌ `claude_cli/background_tasks.py` - фоновые задачи
- ❌ `claude_cli/cache.py` - кэширование

### Функционал из facade.py
- ❌ Tool validation - валидация разрешенных инструментов
- ❌ Tool monitoring - отслеживание использования инструментов
- ❌ SDK fallback - резервный вызов через SDK
- ❌ `get_tool_stats()` - статистика по инструментам
- ❌ `get_user_summary()` - сводка по пользователю
- ❌ `continue_session()` - автопродолжение последней сессии
- ❌ Admin instructions generator - генерация инструкций для администраторов
- ❌ Tool error messages - детальные сообщения об ошибках инструментов

### Функционал из fastapi_server.py
- ❌ Rate limiting - ограничение частоты запросов
- ❌ Error tracking - отслеживание ошибок
- ❌ Request logging middleware - детальное логирование запросов
- ❌ Metrics middleware - сбор метрик по запросам
- ❌ Security headers middleware - заголовки безопасности
- ❌ Template auto-discovery - автообнаружение шаблонов хуков
- ❌ Company session management - управление сессиями компаний
- ❌ File operations tracking - отслеживание файловых операций
- ❌ Agent execution tracking - отслеживание запуска суб-агентов
- ❌ Library synchronization - синхронизация библиотек компаний

### API Endpoints (удалены)
- ❌ `POST /api/v1/chat/stream` - стриминг ответов через SSE
- ❌ `GET /api/v1/sessions/{session_id}` - информация о сессии
- ❌ `GET /api/v1/sessions/user/{user_id}` - сессии пользователя
- ❌ `DELETE /api/v1/sessions/{session_id}` - удаление сессии
- ❌ `POST /api/v1/sessions/cleanup` - очистка истекших сессий
- ❌ `GET /api/stats` - статистика сервиса
- ❌ `GET /api/debug` - отладочная информация
- ❌ `GET /api/debug/errors` - последние ошибки
- ❌ `GET /metrics` - Prometheus метрики
- ❌ `GET /api/templates` - список шаблонов
- ❌ `GET /api/templates/{level}` - детали шаблона

## Что осталось

### Сохранен основной функционал
- ✅ `minimal_server.py` - упрощенный FastAPI сервер
- ✅ `POST /api/v1/chat` - базовый endpoint для чата
- ✅ `GET /health` - проверка здоровья сервиса
- ✅ Управление сессиями (в памяти)
- ✅ Базовая авторизация по API ключу
- ✅ CORS поддержка

### Модули
- ✅ `claude_cli/facade.py` - упрощенная интеграция (без валидации)
- ✅ `claude_cli/integration.py` - управление процессами Claude
- ✅ `claude_cli/session.py` - управление сессиями
- ✅ `claude_cli/config.py` - конфигурация
- ✅ `claude_cli/exceptions.py` - исключения
- ✅ `claude_cli/parser.py` - парсинг
- ✅ `claude_cli/storage/` - хранилище (in-memory)

## Миграция на полную версию

Если вам потребуются удаленные функции:

1. **Метрики и мониторинг** - восстановите `metrics.py` и `monitor.py`
2. **Rate limiting** - добавьте middleware из оригинального `fastapi_server.py`
3. **Управление компаниями** - восстановите `company_data/` и `config/`
4. **Tool validation** - восстановите код валидации в `facade.py`
5. **Дополнительные endpoints** - скопируйте из оригинального сервера

## Размер проекта

**Было:**
- ~2340 строк кода в fastapi_server.py
- ~564 строк в facade.py
- Множество дополнительных модулей

**Стало:**
- ~185 строк в minimal_server.py
- ~170 строк в facade.py (упрощенная версия)
- Только необходимые модули

**Сокращение: ~85% кода удалено**
