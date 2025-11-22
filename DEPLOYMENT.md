# 🚀 Развертывание на Ubuntu - Пошаговая инструкция

## Вариант 1: Автоматическая установка (рекомендуется)

### На вашем Ubuntu сервере выполните:

```bash
# 1. Загрузите проект (замените на ваш путь)
cd ~
git clone https://github.com/vlad29042/claude-api-minimal.git claude-api
cd claude-api

# 2. Запустите установщик
chmod +x install.sh
./install.sh
```

**Установщик автоматически:**
- ✅ Установит все зависимости (Python, Node.js, Claude CLI)
- ✅ Создаст виртуальное окружение
- ✅ Настроит systemd service
- ✅ Запустит API сервер на порту 8001

**Время установки:** ~5 минут

## Вариант 2: Через SCP с локальной машины

```bash
# На вашем компьютере
cd /mnt/c/Users/vlad2/PycharmProjects/cladius
scp -r project/ user@your-server-ip:/home/user/claude-api/

# На сервере
ssh user@your-server-ip
cd ~/claude-api
chmod +x install.sh
./install.sh
```

## После установки

### 1. Настройте аутентификацию Claude

**Вариант A: API ключ Anthropic**
```bash
nano ~/claude-api/.env
# Добавьте строку:
# ANTHROPIC_API_KEY=sk-ant-api03-ваш-ключ
sudo systemctl restart claude-api
```

**Вариант B: Локальная подписка (бесплатная)**
```bash
claude setup-token
# Следуйте инструкциям в браузере
```

### 2. Проверьте работу

```bash
# Статус сервиса
sudo systemctl status claude-api

# Health check
curl http://localhost:8001/health
# Должен вернуть: {"status":"ok"}

# Запустите тесты
cd ~/claude-api
source venv/bin/activate
python3 test_server.py
```

## Управление сервисом

```bash
# Старт
sudo systemctl start claude-api

# Стоп
sudo systemctl stop claude-api

# Рестарт
sudo systemctl restart claude-api

# Логи
tail -f ~/claude-api/server.log
```

## Доступ к API

### Локально на сервере
```bash
curl -X POST http://localhost:8001/api/v1/chat \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello", "user_id": 1}'
```

### Извне (настройте Nginx)

```bash
sudo apt install nginx

sudo nano /etc/nginx/sites-available/claude-api
```

Вставьте:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Активируйте:
```bash
sudo ln -s /etc/nginx/sites-available/claude-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
sudo ufw allow 'Nginx Full'
```

## HTTPS (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
# Следуйте инструкциям
```

## Структура после установки

```
/home/user/claude-api/
├── minimal_server.py          # Сервер
├── claude_cli/                # Библиотека
├── venv/                      # Virtual environment
├── .env                       # Конфигурация
├── server.log                 # Логи
└── test_server.py            # Тесты

/etc/systemd/system/
└── claude-api.service         # Systemd service
```

## Файлы конфигурации

### ~/.claude-api/.env
```env
CLAUDE_API_KEY=your-secret-here
PORT=8001
HOST=0.0.0.0
CLAUDE_TIMEOUT_SECONDS=300
CLAUDE_MAX_TURNS=50
```

### /etc/systemd/system/claude-api.service
```ini
[Unit]
Description=Claude Code Minimal API Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/home/your-user/claude-api
ExecStart=/home/your-user/claude-api/venv/bin/python3 minimal_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Безопасность в продакшене

1. **Измените API ключ** в .env (минимум 32 символа)
2. **Настройте HTTPS** через certbot
3. **Ограничьте доступ:**
   ```bash
   # Закройте прямой доступ к порту
   sudo ufw deny 8001/tcp
   # Разрешите только через nginx
   sudo ufw allow 'Nginx Full'
   ```

## Мониторинг

```bash
# Логи в реальном времени
sudo journalctl -u claude-api -f

# Статус процесса
ps aux | grep minimal_server

# Использование ресурсов
top -p $(pgrep -f minimal_server.py)
```

## Удаление

```bash
cd ~/claude-api
chmod +x uninstall.sh
./uninstall.sh
```

## Решение проблем

### Сервис не запускается
```bash
sudo journalctl -u claude-api -n 50
```

### Порт занят
```bash
sudo lsof -i :8001
sudo kill <PID>
sudo systemctl restart claude-api
```

### Claude не аутентифицирован
```bash
claude setup-token
# ИЛИ
echo "ANTHROPIC_API_KEY=sk-ant-..." >> ~/claude-api/.env
sudo systemctl restart claude-api
```

## Тестирование

После установки запустите полный тест:

```bash
cd ~/claude-api
source venv/bin/activate
python3 test_server.py
```

Должно вывести:
```
✅ Health check OK
✅ Response received
✅ Session continued
```

## Поддержка

- Полная документация: [README.md](README.md)
- Установка: [INSTALL.md](INSTALL.md)
- Быстрый старт: [QUICKSTART.md](QUICKSTART.md)
- Результаты тестов: [TEST_RESULTS.md](TEST_RESULTS.md)

---

**🎉 После успешной установки API будет доступен на http://your-server:8001**
