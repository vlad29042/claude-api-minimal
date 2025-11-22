# 🚀 Установка на Ubuntu Server

## Быстрая установка (одной командой)

```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_REPO/main/install.sh | bash
```

## Ручная установка

### 1. Загрузите проект на сервер

```bash
# Через git
git clone https://github.com/YOUR_REPO/claude-api.git
cd claude-api

# Или через scp
scp -r project/ user@server:/home/user/claude-api/
ssh user@server
cd claude-api
```

### 2. Запустите установщик

```bash
chmod +x install.sh
./install.sh
```

Скрипт автоматически:
- ✅ Установит Python 3 и Node.js (если нужно)
- ✅ Установит Claude CLI
- ✅ Создаст виртуальное окружение
- ✅ Установит зависимости
- ✅ Создаст systemd service
- ✅ Запустит API сервер

### 3. Аутентификация Claude CLI

**Вариант A: Использовать API ключ**
```bash
nano ~/.claude-api/.env
# Добавьте: ANTHROPIC_API_KEY=sk-ant-...
sudo systemctl restart claude-api
```

**Вариант B: Локальная подписка**
```bash
claude setup-token
# Следуйте инструкциям на экране
```

### 4. Проверка работы

```bash
# Статус сервиса
sudo systemctl status claude-api

# Health check
curl http://localhost:8001/health

# Тест API
cd ~/claude-api
source venv/bin/activate
python3 test_server.py
```

## 📋 Управление сервисом

```bash
# Запуск
sudo systemctl start claude-api

# Остановка
sudo systemctl stop claude-api

# Перезапуск
sudo systemctl restart claude-api

# Статус
sudo systemctl status claude-api

# Логи (реального времени)
sudo journalctl -u claude-api -f

# Логи (файл)
tail -f ~/claude-api/server.log
```

## ⚙️ Конфигурация

Отредактируйте `~/.claude-api/.env`:

```bash
nano ~/claude-api/.env
```

Основные параметры:
```env
CLAUDE_API_KEY=your-secret-key-here
PORT=8001
HOST=0.0.0.0
CLAUDE_TIMEOUT_SECONDS=300
CLAUDE_MAX_TURNS=50
```

После изменений:
```bash
sudo systemctl restart claude-api
```

## 🌐 Доступ извне (опционально)

### Nginx reverse proxy

```bash
sudo apt install nginx

sudo nano /etc/nginx/sites-available/claude-api
```

Добавьте:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Активируйте:
```bash
sudo ln -s /etc/nginx/sites-available/claude-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Firewall

```bash
# Разрешить порт 8001 (если нужен прямой доступ)
sudo ufw allow 8001/tcp

# Или только HTTP через nginx
sudo ufw allow 'Nginx Full'
```

## 🔒 Безопасность

### Обязательно сделать в продакшене:

1. **Смените API ключ**
   ```bash
   nano ~/claude-api/.env
   # Установите сложный CLAUDE_API_KEY (32+ символа)
   ```

2. **Используйте HTTPS**
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

3. **Ограничьте доступ к порту**
   ```bash
   # Если используете nginx - закройте прямой доступ
   sudo ufw deny 8001/tcp
   ```

## 🗑️ Удаление

```bash
cd ~/claude-api
chmod +x uninstall.sh
./uninstall.sh
```

## 🐛 Решение проблем

### Сервис не запускается

```bash
# Проверьте логи
sudo journalctl -u claude-api -n 50

# Проверьте права
ls -la ~/claude-api/

# Переустановите зависимости
cd ~/claude-api
source venv/bin/activate
pip install -r requirements.txt --force-reinstall
```

### Claude CLI не работает

```bash
# Проверьте установку
which claude
claude --version

# Проверьте аутентификацию
ls -la ~/.claude/

# Переустановите
sudo npm uninstall -g @anthropic-ai/claude-cli
sudo npm install -g @anthropic-ai/claude-cli
claude setup-token
```

### Порт занят

```bash
# Найдите процесс
sudo lsof -i :8001

# Убейте процесс
sudo kill <PID>

# Перезапустите сервис
sudo systemctl restart claude-api
```

## 📊 Мониторинг

### Просмотр логов

```bash
# Все логи
tail -f ~/claude-api/server.log

# Только ошибки
tail -f ~/claude-api/server.log | grep -i error

# Systemd журнал
sudo journalctl -u claude-api -f
```

### Проверка производительности

```bash
# CPU и память
top -p $(pgrep -f minimal_server.py)

# Детальная статистика
sudo systemctl status claude-api
```

## 🆘 Поддержка

- **Документация**: [README.md](README.md)
- **Тесты**: [TEST_RESULTS.md](TEST_RESULTS.md)
- **Быстрый старт**: [QUICKSTART.md](QUICKSTART.md)

## Системные требования

- **OS**: Ubuntu 20.04+ (или Debian-based)
- **Python**: 3.8+
- **Node.js**: 14+ (автоматически устанавливается)
- **RAM**: 512MB минимум
- **Disk**: 1GB свободного места
- **Network**: Доступ к API Anthropic (если используется API ключ)
