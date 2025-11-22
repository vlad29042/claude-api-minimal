# Claude Code Minimal API - Free Version 🚀

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Status](https://img.shields.io/badge/status-ready-brightgreen.svg)

Минимальная HTTP API для работы с Claude Code через командную строку. Всего один endpoint, максимальная простота.

## ✨ Особенности

- ✅ **Один HTTP endpoint** - POST /api/v1/chat
- ✅ **Поддержка session_id** - продолжение диалога
- ✅ **Простая авторизация** - Bearer token
- ✅ **Автоустановка** - один скрипт для Ubuntu
- ✅ **Systemd service** - автозапуск при перезагрузке
- ✅ **Полная документация** - примеры и тесты
- ✅ **Максимально легкая версия** - минимум зависимостей

## 🚀 Быстрая установка

### Ubuntu/Debian (автоматически)

```bash
curl -fsSL https://raw.githubusercontent.com/vlad29042/claude-api-minimal/main/install.sh | bash
```

Скрипт автоматически установит все зависимости и запустит сервер на порту 8001.

### Вручную

```bash
git clone https://github.com/vlad29042/claude-api-minimal.git
cd claude-api-minimal
pip install -r requirements.txt
python3 minimal_server.py
```

## 📖 Использование

### Создать новую сессию

```bash
curl -X POST http://localhost:8001/api/v1/chat \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Привет! Скажи hello",
    "user_id": 1
  }'
```

**Ответ:**
```json
{
  "content": "Hello!",
  "session_id": "abc-123",
  "cost": 0.001,
  "duration_ms": 1500
}
```

### Продолжить диалог

```bash
curl -X POST http://localhost:8001/api/v1/chat \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Что я сказал до этого?",
    "session_id": "abc-123",
    "user_id": 1
  }'
```

**Ответ:**
```json
{
  "content": "Ты сказал 'Привет! Скажи hello'",
  "session_id": "abc-123",
  "cost": 0.001,
  "duration_ms": 2000
}
```

## 🔧 Конфигурация

Отредактируйте `.env`:

```env
CLAUDE_API_KEY=your-secret-key-here
PORT=8001
HOST=0.0.0.0
CLAUDE_TIMEOUT_SECONDS=300
CLAUDE_MAX_TURNS=50
```

### Аутентификация Claude CLI

API автоматически пытается найти credentials Claude CLI. Если не сработало, используйте один из вариантов:

**Вариант A: API ключ Anthropic**
```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
```

**Вариант B: Локальная подписка (бесплатно)**
```bash
# Если вы установили через install.sh и уже залогинены
sudo -u claude claude  # запустите как пользователь claude
# Внутри Claude CLI выполните:
/login

# Или аутентифицируйтесь через токен
claude setup-token
```

**Вариант C: Ручное копирование credentials (если уже есть)**
```bash
# Если у вас уже есть credentials в ~/.claude/.credentials.json
sudo mkdir -p /home/claude/.claude
sudo cp ~/.claude/.credentials.json /home/claude/.claude/
sudo chown claude:claude /home/claude/.claude/.credentials.json
sudo chmod 600 /home/claude/.claude/.credentials.json
sudo systemctl restart claude-api
```

**❓ Проверка аутентификации:**
```bash
# Проверить наличие credentials
ls -la /home/claude/.claude/.credentials.json

# Проверить логи на ошибки аутентификации
sudo journalctl -u claude-api -f | grep -i auth
```

## 📋 API Endpoints

### POST /api/v1/chat

Отправить сообщение Claude с опциональным продолжением сессии.

**Request:**
```json
{
  "prompt": "Ваш вопрос",
  "session_id": "optional-session-id",
  "user_id": 123
}
```

**Response:**
```json
{
  "content": "Ответ от Claude",
  "session_id": "session-id",
  "cost": 0.001,
  "duration_ms": 1500
}
```

### GET /health

Проверка состояния сервиса.

**Response:**
```json
{
  "status": "ok"
}
```

## 🐳 Docker (скоро)

```bash
docker run -p 8001:8001 \
  -e CLAUDE_API_KEY=your-key \
  vlad29042/claude-api-minimal
```

## 📊 Сравнение с полной версией

| Функция | Минимальная | Полная |
|---------|-------------|--------|
| HTTP API | ✅ | ✅ |
| Session support | ✅ | ✅ |
| Метрики | ❌ | ✅ |
| Rate limiting | ❌ | ✅ |
| Управление компаниями | ❌ | ✅ |
| Tool validation | ❌ | ✅ |
| Templates | ❌ | ✅ |
| Размер кода | ~200 строк | ~2500 строк |

## 🛠️ Управление (systemd)

```bash
# Запуск
sudo systemctl start claude-api

# Остановка
sudo systemctl stop claude-api

# Перезапуск
sudo systemctl restart claude-api

# Логи
sudo journalctl -u claude-api -f
```

## 📚 Документация

- [Установка на Ubuntu](INSTALL.md)
- [Развертывание](DEPLOYMENT.md)
- [Результаты тестов](TEST_RESULTS.md)
- [Список изменений](CHANGES.md)

## 🧪 Тестирование

```bash
# Автоматические тесты
python3 test_server.py

# Health check
curl http://localhost:8001/health
```

## 🔒 Безопасность

⚠️ **Перед продакшеном:**

1. Смените `CLAUDE_API_KEY` на сложный ключ (32+ символа)
2. Настройте HTTPS через nginx + certbot
3. Ограничьте CORS для конкретных доменов
4. Добавьте rate limiting (опционально)

**Аутентификация:**
- Можно использовать API ключ Anthropic
- Или работать по локальной подписке Claude (бесплатно)

## 📦 Зависимости

- Python 3.8+
- FastAPI
- Uvicorn
- Claude CLI
- Anthropic API key или локальная подписка

## 🔍 Troubleshooting

### Ошибка: "Claude CLI is not authenticated"

Это означает, что API не может найти credentials для Claude CLI.

**Решение 1: Проверьте наличие credentials**
```bash
ls -la /home/claude/.claude/.credentials.json
```

Если файла нет:

**Решение 2: Скопируйте существующие credentials**
```bash
# Если у вас уже есть credentials (вы залогинены в Claude CLI)
sudo mkdir -p /home/claude/.claude
sudo cp ~/.claude/.credentials.json /home/claude/.claude/
sudo chown claude:claude /home/claude/.claude/.credentials.json
sudo chmod 600 /home/claude/.claude/.credentials.json
sudo systemctl restart claude-api
```

**Решение 3: Создайте новые credentials**
```bash
# Запустите Claude CLI от имени пользователя claude
sudo -u claude claude

# Внутри CLI выполните:
/login

# Следуйте инструкциям для входа
```

**Решение 4: Используйте API ключ Anthropic**
```bash
# Добавьте в .env файл
echo "ANTHROPIC_API_KEY=sk-ant-ваш-ключ-здесь" | sudo tee -a /home/claude/claude-api/.env
sudo systemctl restart claude-api
```

### Проверка работоспособности

```bash
# 1. Проверьте статус сервиса
sudo systemctl status claude-api

# 2. Проверьте логи
sudo journalctl -u claude-api -n 50 --no-pager

# 3. Проверьте health endpoint
curl http://localhost:8001/health

# 4. Сделайте тестовый запрос
curl -X POST http://localhost:8001/api/v1/chat \
  -H "Authorization: Bearer $(grep CLAUDE_API_KEY /home/claude/claude-api/.env | cut -d= -f2)" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hi", "user_id": 1}'
```

### Сервис не запускается

```bash
# Проверьте детальные логи
sudo journalctl -u claude-api -xe

# Проверьте права доступа
ls -la /home/claude/claude-api/

# Проверьте что Claude CLI установлен
which claude
claude --version

# Переустановите Claude CLI если нужно
sudo npm install -g @anthropic-ai/claude-code
```

## 📄 Лицензия

MIT License - используйте свободно.

## 🔗 Ссылки

- [Claude Code](https://claude.com/claude-code)
- [Anthropic API](https://docs.anthropic.com/)
- [GitHub Repository](https://github.com/vlad29042/claude-api-minimal)

---

**Создано с помощью Claude Code** 🤖
