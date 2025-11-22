# 🚀 Публикация на GitHub

## Шаг 1: Создайте репозиторий на GitHub

1. Перейдите на https://github.com/new
2. Repository name: `claude-api-minimal`
3. Description: `Minimal Claude Code API - Free Version with HTTP endpoint and session support`
4. Public ✅ (для бесплатной версии)
5. **НЕ** добавляйте README, .gitignore, license (уже есть в проекте)
6. Нажмите "Create repository"

## Шаг 2: Подключите локальный репозиторий

```bash
cd /mnt/c/Users/vlad2/PycharmProjects/cladius/project

# Добавьте remote (замените vlad29042 на ваш GitHub username)
git remote add origin https://github.com/vlad29042/claude-api-minimal.git

# Переименуйте ветку в main
git branch -M main

# Запушьте код
git push -u origin main
```

При запросе credentials используйте:
- Username: ваш GitHub username
- Password: `YOUR_GITHUB_TOKEN`

## Шаг 3: Обновите документацию

После создания репозитория обновите ссылки в документации:

```bash
# Замените vlad29042 на реальный
sed -i 's/YOUR_REPO_URL/https:\/\/github.com\/vlad29042\/claude-api-minimal.git/g' *.md
sed -i 's/vlad29042/your-actual-username/g' *.md install.sh

git add .
git commit -m "Update repository links in documentation"
git push
```

## Альтернатива: Используйте GitHub CLI

```bash
# Установите GitHub CLI (если нужно)
sudo apt install gh

# Авторизуйтесь
gh auth login

# Создайте и запушьте репозиторий одной командой
gh repo create claude-api-minimal --public --source=. --push
```

## Проверка

После пуша:
- Репозиторий доступен: https://github.com/vlad29042/claude-api-minimal
- README отображается корректно
- Установочный скрипт работает:
  ```bash
  curl -fsSL https://raw.githubusercontent.com/vlad29042/claude-api-minimal/main/install.sh | bash
  ```

## Добавление в описание репозитория

```
Minimal Claude Code API - Free Version

✅ Single HTTP endpoint with session support
✅ FastAPI server with auto-deployment
✅ Complete documentation and tests
✅ Ubuntu installation script
✅ 85% smaller than full version

Quick start:
curl -fsSL https://raw.githubusercontent.com/vlad29042/claude-api-minimal/main/install.sh | bash
```

## Topics (теги для GitHub)

Добавьте topics в настройках репозитория:
- `claude`
- `claude-ai`
- `fastapi`
- `api`
- `python`
- `chatbot`
- `rest-api`
- `minimal`
- `free`

## License

Добавьте MIT License через GitHub interface:
Settings → Add a license → Choose MIT License

## GitHub Pages (опционально)

Можно создать красивую документацию:
Settings → Pages → Source: main → /docs

Создайте папку docs/ с HTML версией документации.
