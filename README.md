# Kraken Client — сайт + лаунчер

## Состав проекта

- `kraken-site/` — сайт на Flask (тарифы, регистрация/вход, профиль, админка) + JSON API для лаунчера.
- `kraken-launcher/` — отдельное Electron-приложение (папка рядом с этой).

## 1. Локальный запуск сайта

```bash
cd kraken-site
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # заполните значения
export $(cat .env | xargs)   # или используйте python-dotenv/flask run с .flaskenv
python app.py
```

По умолчанию без `DATABASE_URL` используется локальный SQLite-файл — удобно для разработки.

## 2. База данных на Neon

1. Создайте проект на neon.com, скопируйте **pooled** connection string.
2. Вставьте его в `DATABASE_URL` (переменные окружения Vercel и/или `.env`).
3. Таблицы создаются автоматически при первом запуске (`db.create_all()`), миграции не нужны для старта.

## 3. Деплой на Vercel

1. Залейте `kraken-site/` в отдельный GitHub-репозиторий.
2. Импортируйте репозиторий на vercel.com.
3. В Settings → Environment Variables добавьте: `DATABASE_URL`, `SECRET_KEY`, `ADMIN_USERNAMES`, `GITHUB_REPO`, `GITHUB_TOKEN` (если репозиторий приватный), `KRAKEN_ENC_KEY_B64`.
4. Деплой подхватит `vercel.json` (используется `@vercel/python`).

Первый зарегистрированный пользователь с логином из `ADMIN_USERNAMES` получает доступ к `/admin`.

## 4. Публикация сборки клиента

Каждый релиз мода публикуется как **зашифрованный** `.enc`-файл в GitHub Releases репозитория из `GITHUB_REPO`:

```bash
cd kraken-site
export KRAKEN_ENC_KEY_B64=...   # тот же ключ, что и на Vercel
python tools/encrypt_build.py KrakenClient.jar KrakenClient.enc
# затем создайте GitHub Release и прикрепите KrakenClient.enc как asset
```

Если `KRAKEN_ENC_KEY_B64` ещё нет — скрипт сам сгенерирует ключ при первом запуске, его нужно один раз сохранить в переменные окружения сайта.

## 5. Как работает связка сайт ↔ лаунчер ↔ игра

1. Пользователь регистрируется и покупает тариф на сайте → админ вручную подтверждает оплату в `/admin` (реальный платёжный шлюз пока не подключён — сейчас это ручное подтверждение, при желании подключите позже платёжный API, например ЮKassa).
2. В лаунчере пользователь входит тем же логином/паролем → лаунчер получает `license_token` и запоминает его локально.
3. Лаунчер считает HWID компьютера и присылает его на `/api/launcher/verify`. Первый вход привязывает HWID к аккаунту; смена ПК требует покупки «Сброс HWID».
4. Если подписка активна и HWID совпадает, `/api/launcher/manifest` отдаёт ссылку на `.enc` в GitHub Releases и ключ расшифровки.
5. Лаунчер скачивает `.enc`, расшифровывает (AES-256-CBC) в `.jar` и кладёт его в папку `mods` (путь определяется автоматически, его можно сменить в лаунчере).

## 6. Запуск лаунчера

```bash
cd kraken-launcher
npm install
npm start
```

Для сборки установщиков: `npm run dist` (electron-builder, конфиг уже в `package.json`).

## Что стоит сделать дальше

- Подключить реальный платёжный шлюз вместо ручного подтверждения.
- Добавить rate-limiting на `/api/launcher/login` (например Flask-Limiter) от подбора паролей.
- Подписать exe/dmg лаунчера, чтобы антивирусы не ругались на автозагрузчик.
