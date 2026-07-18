# Деплой на прод (Ubuntu + Docker Hub)

Стек — один контейнер: Telegram-бот на long polling. Входящих
портов нет (nginx и сертификаты не нужны), БД нет — состояние
(контекст чатов) живёт в памяти и очищается при рестарте, это
норма. Образ собирается в GitHub Actions и публикуется в Docker
Hub; на сервере нужны только `docker-compose.yml`, `.env`,
промпты и скрипт бэкапа логов.

MCP-поиск на проде выключен: `RAG_MCP_URL` в `.env` пустой,
бот работает в режиме обычной персоны.

## Схема

```
merge PR в main
  → GitHub Actions (release.yml):
      ruff + pytest
      → build linux/amd64 → Docker Hub: zheka-bot:latest, sha-<коммит>
      → scp docker-compose.yml, backup_logs.sh → сервер
      → ssh: docker compose pull && up -d
      → проверка: контейнер running + «Запускаю polling» в логах

контейнер bot ──polling──> Telegram Bot API
              ──HTTPS───> OpenAI API
              (входящих портов нет)

cron 03:30: backup_logs.sh → s3://zheka-bot/logs/ (cloud.ru)
```

## 1. Публикация образов

### Автоматически (основной путь)

Мерж PR в `main` запускает конвейер (`.github/workflows/release.yml`):

```
тесты → сборка образа → пуш в Docker Hub → деплой на сервер
```

- Образ публикуется с двумя тегами: `latest` и `sha-<коммит>`.
- Деплой: конвейер копирует на сервер актуальные
  `docker-compose.yml` и `backup_logs.sh`, затем по SSH выполняет
  `docker compose pull && up -d` и проверяет, что контейнер
  `running` и в логах есть строка «Запускаю polling». Красный
  прогон в Actions = прод не обновился — смотри лог упавшего job'а.
- `.env` и `prompts/` — единственные файлы, которые обновляются
  на сервере вручную (секреты и промпты в git не хранятся).
  Если новая версия требует новую переменную — сначала добавь её
  в `.env` на сервере, иначе деплой упадёт на проверке здоровья.
- Секреты конвейера (Settings → Secrets → Actions):
  `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `SSH_HOST`, `SSH_USER`,
  `SSH_PRIVATE_KEY` (отдельный деплой-ключ `~/.ssh/zheka_deploy`;
  его публичная часть — третья строка в
  `/root/.ssh/authorized_keys` на сервере).

### Вручную (запасной путь: Actions недоступны, hotfix и т.п.)

```bash
docker login    # один раз
DU=$(grep '^DOCKER_USERNAME=' infra/.env | cut -d= -f2)
docker build --platform linux/amd64 \
  -f infra/docker/bot.Dockerfile -t "$DU/zheka-bot:latest" .
docker push "$DU/zheka-bot:latest"
```

## Структура файлов и папок на сервере

Весь проект на сервере — одна папка `/opt/zheka` (рядом живёт
`/opt/insta-bot` — стеки независимы, общий только docker-демон;
порты 80/443 занимает insta_bot, zheka портов не публикует):

```
/opt/zheka/
├── docker-compose.yml   # копия infra/docker-compose.prod.yml (обновляет CI)
├── .env                 # секреты; chmod 600; только вручную
├── backup_logs.sh       # синк логов в S3 (обновляет CI); запуск из cron
├── prompts/             # НЕ в git; копируются вручную (scp); mount :ro
│   ├── persona.txt      #   в контейнере: /app/infra/persona.txt
│   ├── agent_prompt.txt
│   └── search_classifier.txt
└── logs/                # владелец uid 1000 (пользователь контейнера)
    ├── app.log          # пишет бот; ротация 10 MB / 14 дней (loguru)
    ├── app.*.log.gz     # сжатые ротации
    └── backup.log       # вывод cron-запусков backup_logs.sh
```

Исходный код на сервер не копируется и git не нужен — код
приезжает внутри образа с Docker Hub. Named volumes не
используются: у бота нет состояния, `docker compose down`
ничего не теряет.

## 2. Разовая настройка сервера

Docker уже установлен (insta_bot). Адрес сервера здесь — `<IP>`
(реальный лежит в `HETZNER_SERVER_IP` в локальном `infra/.env`).
Остаётся:

```bash
ssh root@<IP>
mkdir -p /opt/zheka/logs /opt/zheka/prompts
chown 1000:1000 /opt/zheka/logs   # бот в контейнере — uid 1000
```

Скопировать с Mac секреты и промпты:

```bash
scp infra/.env root@<IP>:/opt/zheka/.env
scp infra/persona.txt infra/agent_prompt.txt \
    infra/search_classifier.txt root@<IP>:/opt/zheka/prompts/
ssh root@<IP> 'chmod 600 /opt/zheka/.env'
```

Проверить `.env` на сервере:

- `RAG_MCP_URL=` — пустой (MCP на проде выключен);
- `IMAGE_TAG=latest`;
- заполнены `TENANT_ID`, `AWS_*`, `S3_*` — иначе синк логов
  будет молча пропускаться (предупреждение в backup.log).

## 3. Первый запуск

Важно: перед первым стартом на сервере выключить бота на Mac —
Telegram допускает только один polling-инстанс, второй получит
`TelegramConflictError`.

Штатный путь — мерж PR с инфраструктурой в `main`: конвейер сам
соберёт образ и задеплоит. Вручную (если образ уже в Docker Hub):

```bash
cd /opt/zheka
docker compose pull
docker compose up -d
docker compose logs -f bot   # ждать строку «Запускаю polling»
```

## 4. Обновление версии и откат

Штатное обновление — просто мерж PR в `main`, руками ничего
делать не нужно.

Обновление промптов — только вручную: scp новых файлов в
`/opt/zheka/prompts/` + `docker compose restart bot` (промпты
читаются один раз на старте).

### Откат на предыдущую версию

Каждый релиз зафиксирован тегом `sha-<коммит>`. На сервере:

```bash
cd /opt/zheka
# в .env: IMAGE_TAG=sha-<коммит>   (вместо latest)
docker compose pull
docker compose up -d
```

Возврат: `IMAGE_TAG=latest`, повторить `pull` + `up -d`. Важно:
следующий мерж в main задеплоит `latest` поверх отката — чинить
причину отката нужно до следующего мержа.

## 5. Эксплуатация

```bash
docker compose logs -f bot        # логи приложения (stdout)
tail -f /opt/zheka/logs/app.log   # то же — файл с ротацией
docker compose ps                 # статус контейнера
```

### Бэкап логов в S3

Схема (`/opt/zheka/backup_logs.sh`):

```
логи ./logs/ -> s3://zheka-bot/logs/   (sync, только новое; cloud.ru)
```

S3-доступы — в `.env`: `TENANT_ID`, `AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY`, `S3_BUCKET`, `S3_ENDPOINT`, `S3_REGION`,
`S3_RETENTION_DAYS`. aws-cli запускается одноразовым контейнером
`amazon/aws-cli` — на хост ничего не ставится. Если S3-переменные
пустые, синк пропускается с предупреждением (cron не падает).

Автоматически — раз в день в 03:30 (`crontab -e`; время сдвинуто
относительно бэкапа insta_bot в 03:00):

```
30 3 * * * /opt/zheka/backup_logs.sh >> /opt/zheka/logs/backup.log 2>&1
```

Служебные команды:

```bash
/opt/zheka/backup_logs.sh list       # содержимое бакета и объём
/opt/zheka/backup_logs.sh lifecycle  # разово: включить ротацию в S3
```

`lifecycle` выполняется один раз: применяет к бакету политику
«удалять `logs/*` старше `S3_RETENTION_DAYS` дней» — дальше S3
чистит себя сам.

## Типовые проблемы

| Симптом | Причина и решение |
|---|---|
| `permission denied` на `logs/app.log` | Забыт `chown 1000:1000 /opt/zheka/logs` |
| `TelegramConflictError` в логах | Запущен второй polling-инстанс — чаще всего бот локально на Mac (`uv run zheka`); выключить его |
| Бот падает на старте: ошибка валидации Settings | В `.env` на сервере нет обязательной переменной (`TG_BOT_TOKEN`, `OPEN_AI_KEY`, `LLM_MODEL`) |
| Бот падает: `FileNotFoundError` persona | Не скопированы промпты в `/opt/zheka/prompts/` |
| `pull` не находит образ | Разные `IMAGE_TAG` в `.env`, или не выполнен `docker login` (приватный репозиторий) |
| Job deploy упал в Actions | Смотри шаг с ошибкой: SSH — секреты `SSH_*` и `authorized_keys`; здоровье — на сервере `docker compose logs bot` |
| В бакете нет свежих логов | Проверь `backup.log`, cron-запись и `S3_*` в `.env`; разово запусти `backup_logs.sh` руками |
