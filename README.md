# TSUTMB Hostel

VK-бот для управления данными общежития и синхронизации с Google Sheets.

## Конфигурация

Production-конфигурация передаётся через environment variables. Секреты не хранятся в Git.

Обязательные переменные:

- `GROUP_ACCESS_TOKEN` — токен VK-группы.
- `CONVERSATION_ID` — основной peer/conversation ID.
- `ADMINS_CONVERSATION_ID` — peer/conversation ID администраторов.
- `SPREADSHEET_ID` — ID Google Sheets документа.
- `SHEETS_SERVICE_ACCOUNT_JSON` — полный JSON Google service account. Для локальной разработки вместо него можно использовать `SHEETS_SERVICE_ACCOUNT_FILENAME` и файл в `resources/`.

Остальные значения и defaults перечислены в `.env.example`.

## Логи и OpenTelemetry

По умолчанию приложение пишет логи в stderr (`LOG_CONSOLE_ENABLED=true`), а файловое логирование выключено.

Экспорт логов через OpenTelemetry подготовлен, но выключен по умолчанию. Для OTLP/HTTP collector (в том числе SigNoz) используются:

- `OTEL_ENABLED=true`;
- `OTEL_SERVICE_NAME=tsutmb-hostel`;
- `OTEL_EXPORTER_OTLP_ENDPOINT=http://collector:4318`;
- `OTEL_EXPORTER_OTLP_HEADERS` — необязательные `key=value` пары через запятую;
- `OTEL_LOG_LEVEL=INFO`.

К endpoint автоматически добавляется `/v1/logs`, если suffix ещё не указан. Ошибка инициализации telemetry не останавливает основной бот. После проверки OTLP-приёма можно установить `LOG_CONSOLE_ENABLED=false`, чтобы не дублировать application logs в Docker stdout/stderr.

## Локальный запуск

1. Скопировать `.env.example` в `.env` и заполнить значения.
2. При использовании file-based Google credentials положить `service_account.json` в `resources/`.
3. Запустить `docker compose up --build`.

`resources/`, `.env`, service-account credentials и runtime logs исключены из Git и Docker build context.

## Deployment

Для Coolify приложение собирается напрямую из `Dockerfile`. Environment variables задаются в Coolify; production service-account JSON передаётся через `SHEETS_SERVICE_ACCOUNT_JSON`, поэтому отдельный credential-файл и persistent volume для него не нужны.

GitHub Actions выполняет Ruff, format check, Python compile check и проверочную Docker-сборку. CI не публикует production image: deployment platform сама собирает выбранный commit.
